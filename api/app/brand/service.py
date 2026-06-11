import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func

# CHUYỂN ĐỔI: Dùng AsyncGroq để tránh block hệ thống async
from groq import AsyncGroq 

from app.rag.models import DocumentPage
from app.config import get_settings
from .models import Brand, BrandProfile, BrandVoiceRule, BrandMessaging, BrandContentExample
from .schemas import (
    BrandProfileSchema, WriterScope, DesignerScope, AdsScope, LandingPageScope
)
from app.tasks.service import create_task, update_task, finish_task, fail_task

logger = logging.getLogger(__name__)
settings = get_settings()

# Khởi tạo Async Client
groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)

class BrandProfileService:
    # In-memory cache: {brand_id: {scope_name: (profile, version, ttl)}}
    _cache: Dict[str, Any] = {}
    CACHE_TTL = 3600  # 1 hour

    @classmethod
    async def generate_from_documents_bg(
        cls,
        db: AsyncSession,
        brand_id: str,
        document_ids: list[int],
        task_id: int,
    ) -> None:
        """Background version với task tracking — không return, chỉ update DB"""
        try:
            # ── Step 1: Fetch documents ──
            result = await db.execute(
                select(DocumentPage)
                .where(DocumentPage.document_id.in_(document_ids))
            )
            pages = result.scalars().all()

            if not pages:
                await fail_task(db, task_id, error_message="Không tìm thấy dữ liệu knowledge page.")
                return

            await update_task(db, task_id, steps_done=1)

            # ── Step 2: Call Groq ──
            context = "\n\n".join(page.content for page in pages if page.content)
            profile_data = await cls.extract_brand_profile(context=context)

            await update_task(db, task_id, steps_done=2)

            # ── Step 3: Save to DB ──
            await cls.save_profile(db=db, brand_id=brand_id, data=profile_data)

            await finish_task(db, task_id, steps_done=3)
            logger.info(f"Task {task_id} completed for brand {brand_id}")

        except Exception as e:
            logger.error(f"Background task {task_id} failed: {str(e)}")
            await fail_task(db, task_id, error_message=str(e))
            
    @staticmethod
    async def call_groq_json(prompt: str) -> dict:
        """Calls Groq forcing a clean native JSON object return (Refactored to Async)"""
        try:
            # Thêm await vào đây
            response = await groq_client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an elite brand strategist. You must respond ONLY with a valid JSON object matching the strictly requested schema. Do not output markdown fences."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Groq API Error: {str(e)}")
            raise RuntimeError(f"Lỗi kết nối hoặc xử lý từ Groq LLM: {str(e)}")

    @classmethod
    async def extract_brand_profile(cls, context: str) -> dict:
        """Extracts brand profile (Refactored to Async)"""
        prompt = f"""
    You are an elite brand strategist.

    Analyze the following knowledge base.

    Knowledge:
    {context}

    Return ONLY valid JSON.

    {{
        "positioning": "",
        "audience": "",
        "brand_voice_rules": {{
            "forbidden_words": [],
            "tone_patterns": [],
            "cta_patterns": []
        }},
        "messaging": {{
            "pain_points": [],
            "objections": [
                {{
                    "objection": "",
                    "counter": ""
                }}
            ],
            "proof_points": []
        }},
        "content_examples": {{
            "blog_post": null,
            "social_post": null,
            "ad_copy": null,
            "landing_page": null
        }},
        "visual_identity": {{
            "style_description": "",
            "color_palette": [],
            "mood": ""
        }}
    }}
    """
        # Await hàm call_groq_json đã chuyển sang async
        result = await cls.call_groq_json(prompt)
        BrandProfileSchema(**result)
        return result

    @classmethod
    async def generate_from_documents(
        cls,
        db: AsyncSession,
        brand_id: str,
        document_ids: list[int],
    ) -> BrandProfileSchema:
        """SỬA LỖI: Thụt lề chuẩn hóa và tích hợp async liền mạch"""
        result = await db.execute(
            select(DocumentPage)
            .where(DocumentPage.document_id.in_(document_ids))
        )

        pages = result.scalars().all()

        if not pages:
            raise ValueError("Không tìm thấy dữ liệu knowledge page.")

        context = "\n\n".join(
            page.content for page in pages if page.content
        )

        # Thêm await vào đây
        profile_data = await cls.extract_brand_profile(context=context)

        return await cls.save_profile(
            db=db,
            brand_id=brand_id,
            data=profile_data,
        )

    @staticmethod
    def validate_input(data: dict) -> dict:
        """Validate and sanitize array sizes to ensure safety limits"""
        if "brand_voice_rules" in data:
            rules = data["brand_voice_rules"]
            if "forbidden_words" in rules:
                rules["forbidden_words"] = [w.strip() for w in rules["forbidden_words"] if w.strip()][:20]
            if "tone_patterns" in rules:
                rules["tone_patterns"] = [t.strip() for t in rules["tone_patterns"] if t.strip()][:5]
            if "cta_patterns" in rules:
                rules["cta_patterns"] = [c.strip() for c in rules["cta_patterns"] if c.strip()][:5]
        
        if "messaging" in data:
            msg = data["messaging"]
            if "pain_points" in msg:
                msg["pain_points"] = [p.strip() for p in msg["pain_points"] if p.strip()][:5]
            if "objections" in msg:
                msg["objections"] = msg["objections"][:5]
            if "proof_points" in msg:
                msg["proof_points"] = [pr.strip() for pr in msg["proof_points"] if pr.strip()][:10]
        
        return data

    @classmethod
    async def save_profile(cls, db: AsyncSession, brand_id: str, data: dict) -> BrandProfileSchema:
        """Saves or updates brand profile using Bulk Saving to avoid database overhead"""
        data = cls.validate_input(data)
        schema = BrandProfileSchema(**data)
        
        # 1. Update/Create BrandProfile Core
        result = await db.execute(select(BrandProfile).filter(BrandProfile.brand_id == brand_id))
        profile = result.scalars().first()
        
        if not profile:
            profile = BrandProfile(brand_id=brand_id, version=1)
        else:
            profile.version += 1
            
        profile.positioning = schema.positioning
        profile.audience = schema.audience
        profile.visual_identity = schema.visual_identity.model_dump()
        profile.updated_at = datetime.utcnow()
        profile.mined_at = datetime.utcnow()
        db.add(profile)
        
        # 2. Clear old transactional data rows safely
        await db.execute(delete(BrandVoiceRule).filter(BrandVoiceRule.brand_id == brand_id))
        await db.execute(delete(BrandMessaging).filter(BrandMessaging.brand_id == brand_id))
        await db.execute(delete(BrandContentExample).filter(BrandContentExample.brand_id == brand_id))
        
        # 3. Prepare list of DB objects for optimal Bulk Save
        bulk_objects = []
        
        for word in schema.brand_voice_rules.forbidden_words:
            bulk_objects.append(BrandVoiceRule(id=str(uuid.uuid4()), brand_id=brand_id, rule_type="forbidden_word", value=word))
        for pattern in schema.brand_voice_rules.tone_patterns:
            bulk_objects.append(BrandVoiceRule(id=str(uuid.uuid4()), brand_id=brand_id, rule_type="tone_pattern", value=pattern))
        for cta in schema.brand_voice_rules.cta_patterns:
            bulk_objects.append(BrandVoiceRule(id=str(uuid.uuid4()), brand_id=brand_id, rule_type="cta_pattern", value=cta))
            
        for pain in schema.messaging.pain_points:
            bulk_objects.append(BrandMessaging(id=str(uuid.uuid4()), brand_id=brand_id, message_type="pain_point", value=pain))
        for proof in schema.messaging.proof_points:
            bulk_objects.append(BrandMessaging(id=str(uuid.uuid4()), brand_id=brand_id, message_type="proof_point", value=proof))
        for obj in schema.messaging.objections:
            bulk_objects.append(BrandMessaging(id=str(uuid.uuid4()), brand_id=brand_id, message_type="objection", objection=obj.objection, counter=obj.counter))
            
        examples_dict = schema.content_examples.model_dump()
        for ex_type, content in examples_dict.items():
            if content:
                bulk_objects.append(BrandContentExample(id=str(uuid.uuid4()), brand_id=brand_id, example_type=ex_type, content=content))
                
        # 4. Fire execution to Database Engine
        db.add_all(bulk_objects)
        await db.commit()
        
        cls._invalidate_cache(brand_id)
        return schema

    @classmethod
    async def get_full_profile(cls, db: AsyncSession, brand_id: str) -> BrandProfileSchema:
        """Get full brand profile with high speed query groupings"""
        cached = cls._get_cache(brand_id, "full")
        if cached:
            return cached
            
        res_profile = await db.execute(select(BrandProfile).filter(BrandProfile.brand_id == brand_id))
        profile = res_profile.scalars().first()
        if not profile:
            raise ValueError(f"Hồ sơ thương hiệu của ID {brand_id} không tồn tại.")
            
        res_rules = await db.execute(select(BrandVoiceRule).filter(BrandVoiceRule.brand_id == brand_id))
        rules = res_rules.scalars().all()
        
        res_messages = await db.execute(select(BrandMessaging).filter(BrandMessaging.brand_id == brand_id))
        messages = res_messages.scalars().all()
        
        res_examples = await db.execute(select(BrandContentExample).filter(BrandContentExample.brand_id == brand_id))
        examples = res_examples.scalars().all()
        
        schema = BrandProfileSchema(
            positioning=profile.positioning,
            audience=profile.audience,
            visual_identity=profile.visual_identity,
            brand_voice_rules={
                "forbidden_words": [r.value for r in rules if r.rule_type == "forbidden_word"],
                "tone_patterns": [r.value for r in rules if r.rule_type == "tone_pattern"],
                "cta_patterns": [r.value for r in rules if r.rule_type == "cta_pattern"]
            },
            messaging={
                "pain_points": [m.value for m in messages if m.message_type == "pain_point"],
                "proof_points": [m.value for m in messages if m.message_type == "proof_point"],
                "objections": [{"objection": m.objection, "counter": m.counter} for m in messages if m.message_type == "objection"]
            },
            content_examples={
                "blog_post": next((e.content for e in examples if e.example_type == "blog_post"), None),
                "social_post": next((e.content for e in examples if e.example_type == "social_post"), None),
                "ad_copy": next((e.content for e in examples if e.example_type == "ad_copy"), None),
                "landing_page": next((e.content for e in examples if e.example_type == "landing_page"), None)
            }
        )
        
        cls._set_cache(brand_id, "full", schema, profile.version)
        return schema

    @classmethod
    async def get_writer_scope(cls, db: AsyncSession, brand_id: str) -> WriterScope:
        cached = cls._get_cache(brand_id, "writer")
        if cached: return cached
        
        full = await cls.get_full_profile(db, brand_id)
        scope = WriterScope(
            positioning=full.positioning, audience=full.audience,
            brand_voice_rules=full.brand_voice_rules, messaging=full.messaging,
            content_examples={
                "blog_post": full.content_examples.blog_post,
                "social_post": full.content_examples.social_post
            }
        )
        # TỐI ƯU: Trích xuất version trực tiếp từ cache vừa nạp của hàm get_full_profile
        version = cls._cache[f"{brand_id}:full"][1]
        cls._set_cache(brand_id, "writer", scope, version)
        return scope

    @classmethod
    async def get_designer_scope(cls, db: AsyncSession, brand_id: str) -> DesignerScope:
        cached = cls._get_cache(brand_id, "designer")
        if cached: return cached
        
        full = await cls.get_full_profile(db, brand_id)
        scope = DesignerScope(positioning=full.positioning, visual_identity=full.visual_identity)
        
        version = cls._cache[f"{brand_id}:full"][1]
        cls._set_cache(brand_id, "designer", scope, version)
        return scope

    @classmethod
    async def get_ads_scope(cls, db: AsyncSession, brand_id: str) -> AdsScope:
        cached = cls._get_cache(brand_id, "ads")
        if cached: return cached
        
        full = await cls.get_full_profile(db, brand_id)
        scope = AdsScope(
            positioning=full.positioning, audience=full.audience,
            brand_voice_rules=full.brand_voice_rules, messaging=full.messaging,
            content_examples={"ad_copy": full.content_examples.ad_copy}
        )
        
        version = cls._cache[f"{brand_id}:full"][1]
        cls._set_cache(brand_id, "ads", scope, version)
        return scope

    @classmethod
    async def get_landing_page_scope(cls, db: AsyncSession, brand_id: str) -> LandingPageScope:
        cached = cls._get_cache(brand_id, "landing_page")
        if cached: return cached
        
        full = await cls.get_full_profile(db, brand_id)
        scope = LandingPageScope(**full.model_dump())
        
        version = cls._cache[f"{brand_id}:full"][1]
        cls._set_cache(brand_id, "landing_page", scope, version)
        return scope

    @staticmethod
    def _get_cache(brand_id: str, scope: str):
        key = f"{brand_id}:{scope}"
        if key in BrandProfileService._cache:
            cached_data, _, cached_time = BrandProfileService._cache[key]
            if datetime.utcnow() - cached_time < timedelta(seconds=BrandProfileService.CACHE_TTL):
                return cached_data
        return None

    @staticmethod
    def _set_cache(brand_id: str, scope: str, data, version: int):
        key = f"{brand_id}:{scope}"
        BrandProfileService._cache[key] = (data, version, datetime.utcnow())

    @staticmethod
    def _invalidate_cache(brand_id: str):
        keys_to_delete = [k for k in BrandProfileService._cache.keys() if k.startswith(brand_id)]
        for key in keys_to_delete:
            del BrandProfileService._cache[key]