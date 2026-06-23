"""
app/rag/services/ingest.py
RAG ingestion - VRAM 4GB, load/unload per batch, dọn sạch VRAM.
"""

import asyncio
import gc
import logging
import os
import time
import numpy as np
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.research.models import ResearchResult, FbPost, FbComment
from app.rag.services.keyword import KeywordRAG
from app.rag.services.comment import CommentRAG
from app.rag.services.social import SocialPostRAG
from app.rag.services.image_rag import ImageRAG
from app.rag.services.embedder import get_embedder

log = logging.getLogger("rag.ingest")

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER: Dọn sạch VRAM
# ═══════════════════════════════════════════════════════════════════════════════

def _clear_vram():
    """Dọn sạch VRAM — xóa model, gc, empty_cache."""
    import torch
    torch.cuda.empty_cache()
    torch.cuda.synchronize()
    gc.collect()
    torch.cuda.empty_cache()
    log.info("[vram] đã dọn sạch VRAM")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN: Trigger RAG Ingestion
# ═══════════════════════════════════════════════════════════════════════════════

async def trigger_rag_ingestion(db: AsyncSession, business_id: str) -> dict:
    """
    Phases:
    1. Keywords (batch 10) → dọn VRAM
    2. Posts (batch 5) → dọn VRAM  
    3. Comments (batch 10) → dọn VRAM
    4. Images (model khác, batch 2) → dọn VRAM
    """
    # Timestamp để dedupe_key unique mỗi lần chạy
    run_id = str(int(time.time()))
    
    try:
        stmt = select(ResearchResult).where(
            ResearchResult.business_id == business_id
        )
        result = await db.execute(stmt)
        research = result.scalar_one_or_none()
        
        if not research:
            log.warning(f"[rag] ResearchResult not found: {business_id}")
            return {"status": "error", "error": "ResearchResult not found"}
        
        log.info(f"[rag] START ingestion: {business_id} | run_id={run_id}")
        
        stats = {
            "status": "ok",
            "keywords": {"ok": 0, "error": 0},
            "posts": {"ok": 0, "error": 0},
            "comments": {"ok": 0, "error": 0},
            "images": {"ok": 0, "error": 0},
        }
        
        try:
            # ═════════════════════════════════════════════════════════════════
            # PHASE 1: Keywords (batch 10)
            # ═════════════════════════════════════════════════════════════════
            log.info("[rag] === PHASE 1: Keywords ===")
            kw_stats = await _ingest_keywords_phase(
                business_id,
                research.suggestions_tagged or {},
                research.serp_data.get("content_angle", []) if research.serp_data else [],
                run_id,
            )
            stats["keywords"] = kw_stats
            log.info(f"[rag] Keywords xong: {kw_stats}")
            
            _clear_vram()
            await asyncio.sleep(1)
            
            # ═════════════════════════════════════════════════════════════════
            # PHASE 2: Posts (batch 5)
            # ═════════════════════════════════════════════════════════════════
            log.info("[rag] === PHASE 2: Posts ===")
            post_stmt = select(FbPost).where(FbPost.business_id == business_id)
            post_result = await db.execute(post_stmt)
            posts = [p.content for p in post_result.scalars().all() if p.content]
            
            post_stats = await _ingest_posts_phase(business_id, posts, run_id)
            stats["posts"] = post_stats
            log.info(f"[rag] Posts xong: {post_stats}")
            
            _clear_vram()
            await asyncio.sleep(1)
            
            # ═════════════════════════════════════════════════════════════════
            # PHASE 3: Comments (batch 10)
            # ═════════════════════════════════════════════════════════════════
            log.info("[rag] === PHASE 3: Comments ===")
            cmt_stmt = select(FbComment).where(FbComment.business_id == business_id)
            cmt_result = await db.execute(cmt_stmt)
            comments = []
            for c in cmt_result.scalars().all():
                comments.append({
                    "author": c.author or "Ẩn danh",
                    "comment": c.comment or "",
                    "replies": c.replies or []
                })
            
            cmt_stats = await _ingest_comments_phase(business_id, comments, run_id)
            stats["comments"] = cmt_stats
            log.info(f"[rag] Comments xong: {cmt_stats}")
            
            _clear_vram()
            await asyncio.sleep(1)
            
            # ═════════════════════════════════════════════════════════════════
            # PHASE 4: Images (model KHÁC, batch 2)
            # ═════════════════════════════════════════════════════════════════
            log.info("[rag] === PHASE 4: Images ===")
            photo_urls = []
            fb_data = getattr(research, 'fb_data', None) or {}
            if fb_data:
                photo_urls = fb_data.get("photo", []) or []
            
            img_stats = await _ingest_images_phase(business_id, photo_urls)
            stats["images"] = img_stats
            log.info(f"[rag] Images xong: {img_stats}")
            
            _clear_vram()
            
            log.info(f"[rag] ✅ DONE: {business_id} | {stats}")
            return stats

        except Exception as e:
            log.error(f"[rag] phase error: {e}", exc_info=True)
            stats["status"] = "error"
            stats["error"] = str(e)
            _clear_vram()
            return stats
        
    except Exception as e:
        log.error(f"[rag] ❌ error: {e}", exc_info=True)
        _clear_vram()
        return {"status": "error", "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: Keywords (batch 10)
# ═══════════════════════════════════════════════════════════════════════════════

async def _ingest_keywords_phase(
    business_id: str,
    suggestions_tagged: dict,
    content_angles: list,
    run_id: str,
) -> dict:
    stats = {"ok": 0, "error": 0}
    
    try:
        all_kw = []
        for category, keywords in (suggestions_tagged or {}).items():
            if isinstance(keywords, list):
                all_kw.extend(keywords)
        all_kw.extend(content_angles or [])
        
        seen = set()
        unique_kw = []
        for kw in all_kw:
            if kw and kw not in seen:
                seen.add(kw)
                unique_kw.append(kw)
        
        if not unique_kw:
            log.info("[keywords] không có keyword nào")
            return stats
        
        log.info(f"[keywords] {len(unique_kw)} keywords, batch 10")
        
        krag = KeywordRAG()
        embedder = get_embedder()
        BATCH_SIZE = 10
        
        for batch_idx in range(0, len(unique_kw), BATCH_SIZE):
            batch = unique_kw[batch_idx:batch_idx + BATCH_SIZE]
            batch_num = batch_idx // BATCH_SIZE + 1
            
            try:
                log.info(f"[keywords] batch {batch_num}: load embedder...")
                embedder._load()
                
                embs = await embedder.encode(batch)
                
                records = []
                for i, kw in enumerate(batch):
                    records.append({
                        "text": kw,
                        "chunk_type": "keyword",
                        "chunk_id": f"kw_{run_id}_{batch_idx}_{i}",
                        "business_id": business_id,
                        "source_id": f"research_kw_{run_id}_{hash(kw)}",
                        "source_type": "keyword",
                    })
                
                result = await krag._store.add_precomputed_batch(
                    records, embs, dedupe_key=f"kw_{run_id}_{batch_idx}"
                )
                
                if result == "ok":
                    stats["ok"] += len(records)
                    log.info(f"[keywords] batch {batch_num}: ✅ {len(records)} added")
                else:
                    stats["error"] += len(records)
                    log.warning(f"[keywords] batch {batch_num}: ⚠️ {result}")
                
                embedder.unload()
                _clear_vram()
                await asyncio.sleep(0.5)
                
            except Exception as e:
                log.error(f"[keywords] batch {batch_num} lỗi: {e}")
                stats["error"] += len(batch)
                embedder.unload()
                _clear_vram()
        
        return stats
        
    except Exception as e:
        log.error(f"[keywords] phase lỗi: {e}")
        return stats


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: Posts (batch 5)
# ═══════════════════════════════════════════════════════════════════════════════

async def _ingest_posts_phase(
    business_id: str,
    posts: list,
    run_id: str,
) -> dict:
    stats = {"ok": 0, "error": 0}
    
    if not posts:
        log.info("[posts] không có post nào")
        return stats
    
    log.info(f"[posts] {len(posts)} posts, batch 5")
    
    srag = SocialPostRAG()
    embedder = get_embedder()
    BATCH_SIZE = 5
    
    for batch_idx in range(0, len(posts), BATCH_SIZE):
        batch = posts[batch_idx:batch_idx + BATCH_SIZE]
        batch_num = batch_idx // BATCH_SIZE + 1
        
        try:
            records = []
            texts = []
            
            for i, post_text in enumerate(batch):
                if not post_text:
                    log.debug(f"[posts] post {i} rỗng, bỏ qua")
                    continue
                
                text = str(post_text).strip()
                if not text:
                    continue
                
                # Tách title/body đơn giản
                lines = text.split("\n", 1)
                title = lines[0][:100] if lines[0] else ""
                body = lines[1] if len(lines) > 1 else ""
                full_text = f"{title} {body}".strip()
                
                if not full_text:
                    log.debug(f"[posts] post {i} sau xử lý rỗng")
                    continue
                
                texts.append(full_text)
                records.append({
                    "text": full_text,
                    "chunk_type": "post",
                    "chunk_id": f"post_{run_id}_{batch_idx}_{i}",
                    "business_id": business_id,
                    "source_id": f"research_post_{run_id}_{batch_idx}_{i}",
                    "source_type": "social",
                })
            
            if not records:
                log.info(f"[posts] batch {batch_num}: không có record hợp lệ")
                continue
            
            log.info(f"[posts] batch {batch_num}: {len(records)} records hợp lệ, load embedder...")
            embedder._load()
            
            embs = await embedder.encode(texts)
            
            result = await srag._store.add_precomputed_batch(
                records, embs, dedupe_key=f"post_{run_id}_{batch_idx}"
            )
            
            if result == "ok":
                stats["ok"] += len(records)
                log.info(f"[posts] batch {batch_num}: ✅ {len(records)} added")
            else:
                stats["error"] += len(records)
                log.warning(f"[posts] batch {batch_num}: ⚠️ {result}")
            
            embedder.unload()
            _clear_vram()
            await asyncio.sleep(0.5)
            
        except Exception as e:
            log.error(f"[posts] batch {batch_num} lỗi: {e}", exc_info=True)
            stats["error"] += len(batch)
            embedder.unload()
            _clear_vram()
    
    return stats


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: Comments (batch 10)
# ═══════════════════════════════════════════════════════════════════════════════

async def _ingest_comments_phase(
    business_id: str,
    comments: list,
    run_id: str,
) -> dict:
    stats = {"ok": 0, "error": 0}
    
    if not comments:
        log.info("[comments] không có comment nào")
        return stats
    
    log.info(f"[comments] {len(comments)} comments, batch 10")
    
    crag = CommentRAG()
    embedder = get_embedder()
    BATCH_SIZE = 10
    
    for batch_idx in range(0, len(comments), BATCH_SIZE):
        batch = comments[batch_idx:batch_idx + BATCH_SIZE]
        batch_num = batch_idx // BATCH_SIZE + 1
        
        try:
            records = []
            texts = []
            
            for i, cmt in enumerate(batch):
                comment_text = cmt.get("comment", "").strip() if isinstance(cmt, dict) else ""
                author = cmt.get("author", "Ẩn danh") if isinstance(cmt, dict) else "Ẩn danh"
                
                if not comment_text:
                    continue
                
                formatted = f"{author}: {comment_text}"
                texts.append(formatted)
                records.append({
                    "text": formatted,
                    "chunk_type": "comment",
                    "chunk_id": f"cmt_{run_id}_{batch_idx}_{i}",
                    "business_id": business_id,
                    "source_id": f"research_cmt_{run_id}_{batch_idx}_{i}",
                    "source_type": "comment",
                })
            
            if not records:
                continue
            
            log.info(f"[comments] batch {batch_num}: load embedder...")
            embedder._load()
            
            embs = await embedder.encode(texts)
            
            result = await crag._store.add_precomputed_batch(
                records, embs, dedupe_key=f"cmt_{run_id}_{batch_idx}"
            )
            
            if result == "ok":
                stats["ok"] += len(records)
                log.info(f"[comments] batch {batch_num}: ✅ {len(records)} added")
            else:
                stats["error"] += len(records)
                log.warning(f"[comments] batch {batch_num}: ⚠️ {result}")
            
            embedder.unload()
            _clear_vram()
            await asyncio.sleep(0.5)
            
        except Exception as e:
            log.error(f"[comments] batch {batch_num} lỗi: {e}")
            stats["error"] += len(batch)
            embedder.unload()
            _clear_vram()
    
    return stats


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: Images (model KHÁC, batch 2)
# ═══════════════════════════════════════════════════════════════════════════════

async def _ingest_images_phase(
    business_id: str,
    photo_urls: list,
) -> dict:
    stats = {"ok": 0, "error": 0}
    
    if not photo_urls:
        log.info("[images] không có ảnh nào")
        return stats
    
    log.info(f"[images] {len(photo_urls)} ảnh, batch 2, model riêng")
    
    try:
        from aiohttp import ClientSession
        from PIL import Image
        from io import BytesIO
        import torch
        
        _clear_vram()
        await asyncio.sleep(1)
        
        # Load model image riêng (KHÔNG dùng get_embedder/bge-m3)
        log.info("[images] loading image model...")
        from sentence_transformers import SentenceTransformer
        
        img_model_name = "clip-ViT-B-32"
        img_model = SentenceTransformer(img_model_name)
        
        irag = ImageRAG(None)
        
        urls = []
        for ph in photo_urls:
            if isinstance(ph, dict):
                url = ph.get("value") or ph.get("url")
            else:
                url = str(ph) if ph else None
            
            if url and isinstance(url, str):
                urls.append(url)
        
        if not urls:
            img_model = None
            _clear_vram()
            return stats
        
        BATCH_SIZE = 2
        
        for batch_idx in range(0, len(urls), BATCH_SIZE):
            batch_urls = urls[batch_idx:batch_idx + BATCH_SIZE]
            images = []
            
            async with ClientSession() as session:
                for url in batch_urls:
                    try:
                        async with session.get(url, timeout=10) as resp:
                            if resp.status == 200:
                                data = await resp.read()
                                img = Image.open(BytesIO(data))
                                images.append((img, f"img_{batch_idx}_{len(images)}", {}))
                    except Exception as e:
                        log.debug(f"[img] download lỗi: {url}")
                        stats["error"] += 1
            
            if images:
                try:
                    batch_results = await irag.add_batch(images)
                    for r in batch_results:
                        if r == "ok":
                            stats["ok"] += 1
                        else:
                            stats["error"] += 1
                except Exception as e:
                    log.warning(f"[img] batch lỗi: {e}")
                    stats["error"] += len(images)
            
            await asyncio.sleep(0.5)
        
        log.info("[images] unloading image model...")
        img_model = None
        _clear_vram()
        await asyncio.sleep(1)
        
        return stats
        
    except Exception as e:
        log.error(f"[images] phase lỗi: {e}")
        _clear_vram()
        return stats