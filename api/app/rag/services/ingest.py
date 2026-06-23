"""
app/rag/services/ingest.py
RAG ingestion - Load/Unload embedder per phase (VRAM 4GB optimization).

Flow:
1. Load embedder → Keywords (max 50 batch) → Unload
2. Load embedder → Posts (max 10 batch) → Unload
3. Load embedder → Comments (max 30 batch) → Unload
4. Images (skip or lightweight)
"""

import asyncio
import logging
import numpy as np
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.research.models import ResearchResult
from app.rag.services.keyword import KeywordRAG
from app.rag.services.comment import CommentRAG
from app.rag.services.social import SocialPostRAG
from app.rag.services.image_rag import ImageRAG
from app.rag.services.embedder import get_embedder

log = logging.getLogger("rag.ingest")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN: Trigger RAG Ingestion
# ═══════════════════════════════════════════════════════════════════════════════

async def trigger_rag_ingestion(db: AsyncSession, business_id: str) -> dict:
    """
    Ingest research result → RAG (tuần tự, load/unload per phase).
    
    Phases:
    1. Keywords (max 50/batch) → Unload
    2. Posts (max 10/batch) → Unload
    3. Comments (max 30/batch) → Unload
    4. Images (optional, skip)
    
    Return: {
        "status": "ok" | "error",
        "keywords": {"ok": int, "error": int},
        "posts": {"ok": int, "error": int},
        "comments": {"ok": int, "error": int},
        "images": {"ok": int, "error": int},
    }
    """
    try:
        stmt = select(ResearchResult).where(
            ResearchResult.business_id == business_id
        )
        result = await db.execute(stmt)
        research = result.scalar_one_or_none()
        
        if not research:
            log.warning(f"[rag] ResearchResult not found: {business_id}")
            return {"status": "error", "error": "ResearchResult not found"}
        
        log.info(f"[rag] START ingestion: {business_id}")
        
        stats = {
            "status": "ok",
            "keywords": {"ok": 0, "error": 0},
            "posts": {"ok": 0, "error": 0},
            "comments": {"ok": 0, "error": 0},
            "images": {"ok": 0, "error": 0},
        }
        
        try:
            # Phase 1: Keywords (Load → Ingest → Unload)
            log.info("[rag] PHASE 1: Keywords")
            kw_stats = await _ingest_keywords_phase(
                business_id,
                research.suggestions_tagged or {},
                research.serp_data.get("content_angle", []) if research.serp_data else []
            )
            stats["keywords"] = kw_stats
            log.info(f"[rag] keywords done: {kw_stats}")
            
            # Phase 2: Posts (Load → Ingest → Unload)
            log.info("[rag] PHASE 2: Posts")
            post_stats = await _ingest_posts_phase(
                business_id,
                research.fb_data.get("posts", []) if research.fb_data else []
            )
            stats["posts"] = post_stats
            log.info(f"[rag] posts done: {post_stats}")
            
            # Phase 3: Comments (Load → Ingest → Unload)
            log.info("[rag] PHASE 3: Comments")
            cmt_stats = await _ingest_comments_phase(
                business_id,
                research.fb_data.get("comments", []) if research.fb_data else []
            )
            stats["comments"] = cmt_stats
            log.info(f"[rag] comments done: {cmt_stats}")
            
            # Priority 4: Images (nặng nhất, optional)
            log.info("[rag] PHASE 3: Comments")
            img_stats = await _ingest_images(
                    business_id,
                    research.fb_data.get("photo", []) if research.fb_data else []
                )
            stats["images"] = img_stats
            log.info(f"[rag] images done: {img_stats}")
            
            log.info(f"[rag] ✅ DONE ingestion: {business_id} | {stats}")
            return stats

            
        except Exception as e:
            log.error(f"[rag] ingestion phase error: {e}", exc_info=True)
            stats["status"] = "error"
            stats["error"] = str(e)
        
        log.info(f"[rag] ✅ DONE ingestion: {business_id}")
        return stats
        
    except Exception as e:
        log.error(f"[rag] ❌ ingestion error: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: Keywords (Max 50/batch)
# ═══════════════════════════════════════════════════════════════════════════════

async def _ingest_keywords_phase(
    business_id: str,
    suggestions_tagged: dict,
    content_angles: list,
) -> dict:
    """Phase 1: Keywords - Load → Batch embed → Add → Unload."""
    stats = {"ok": 0, "error": 0}
    
    try:
        # Flatten + Dedupe keywords
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
            log.info("[keywords] no keywords to ingest")
            return stats
        
        log.info(f"[keywords] ingesting {len(unique_kw)} keywords (max 50/batch)")
        
        krag = KeywordRAG()
        embedder = get_embedder()
        
        BATCH_SIZE = 50
        batch_count = 0
        
        for batch_idx in range(0, len(unique_kw), BATCH_SIZE):
            batch = unique_kw[batch_idx:batch_idx + BATCH_SIZE]
            batch_count += 1
            
            try:
                # Load embedder
                log.info(f"[keywords] batch {batch_count}: loading embedder...")
                embedder._load()
                
                # Encode batch
                log.info(f"[keywords] batch {batch_count}: encoding {len(batch)} keywords...")
                embs = await embedder.encode(batch)
                
                # Build records
                records = []
                for i, kw in enumerate(batch):
                    records.append({
                        "text": kw,
                        "chunk_type": "keyword",
                        "chunk_id": f"kw_{batch_idx}_{i}",
                        "business_id": business_id,
                        "source_id": f"research_kw_{hash(kw)}",
                        "source_type": "keyword",
                    })
                
                # Add precomputed batch
                log.info(f"[keywords] batch {batch_count}: adding to FAISS...")
                result = await krag._store.add_precomputed_batch(
                    records, embs, dedupe_key=f"kw_batch_{batch_idx}"
                )
                
                if result == "ok":
                    stats["ok"] += len(records)
                    log.info(f"[keywords] batch {batch_count}: ✅ {len(records)} added")
                else:
                    log.warning(f"[keywords] batch {batch_count}: {result}")
                
                # Unload embedder
                log.info(f"[keywords] batch {batch_count}: unloading embedder...")
                embedder._model = None
                embedder._tokenizer = None
                import gc
                gc.collect()
                
                # Small delay to ensure cleanup
                await asyncio.sleep(0.5)
                
            except Exception as e:
                log.error(f"[keywords] batch {batch_count} failed: {e}")
                stats["error"] += len(batch)
                embedder._model = None  # Force cleanup
        
        return stats
        
    except Exception as e:
        log.error(f"[keywords] phase error: {e}")
        return stats


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: Posts (Max 10/batch)
# ═══════════════════════════════════════════════════════════════════════════════

async def _ingest_posts_phase(
    business_id: str,
    posts: list,
) -> dict:
    """Phase 2: Posts - Load → Batch embed → Add → Unload."""
    stats = {"ok": 0, "error": 0}
    
    try:
        if not posts:
            log.info("[posts] no posts to ingest")
            return stats
        
        log.info(f"[posts] ingesting {len(posts)} posts (max 10/batch)")
        
        srag = SocialPostRAG()
        embedder = get_embedder()
        
        BATCH_SIZE = 10
        batch_count = 0
        
        for batch_idx in range(0, len(posts), BATCH_SIZE):
            batch = posts[batch_idx:batch_idx + BATCH_SIZE]
            batch_count += 1
            
            try:
                # Prepare texts
                records = []
                texts = []
                
                for i, post_text in enumerate(batch):
                    if not post_text or not post_text.strip():
                        continue
                    
                    lines = post_text.strip().split("\n", 1)
                    title = lines[0][:100]
                    body = lines[1] if len(lines) > 1 else ""
                    full_text = f"{title} {body}".strip()
                    
                    texts.append(full_text)
                    records.append({
                        "text": full_text,
                        "chunk_type": "post",
                        "chunk_id": f"post_{batch_idx}_{i}",
                        "business_id": business_id,
                        "source_id": f"research_post_{batch_idx}_{i}",
                        "source_type": "social",
                    })
                
                if not records:
                    continue
                
                # Load embedder
                log.info(f"[posts] batch {batch_count}: loading embedder...")
                embedder._load()
                
                # Encode batch
                log.info(f"[posts] batch {batch_count}: encoding {len(records)} posts...")
                embs = await embedder.encode(texts)
                
                # Add precomputed batch
                log.info(f"[posts] batch {batch_count}: adding to FAISS...")
                result = await srag._store.add_precomputed_batch(
                    records, embs, dedupe_key=f"post_batch_{batch_idx}"
                )
                
                if result == "ok":
                    stats["ok"] += len(records)
                    log.info(f"[posts] batch {batch_count}: ✅ {len(records)} added")
                else:
                    log.warning(f"[posts] batch {batch_count}: {result}")
                
                # Unload embedder
                log.info(f"[posts] batch {batch_count}: unloading embedder...")
                embedder._model = None
                embedder._tokenizer = None
                import gc
                gc.collect()
                await asyncio.sleep(0.5)
                
            except Exception as e:
                log.error(f"[posts] batch {batch_count} failed: {e}")
                stats["error"] += len(batch)
                embedder._model = None
        
        return stats
        
    except Exception as e:
        log.error(f"[posts] phase error: {e}")
        return stats


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: Comments (Max 30/batch)
# ═══════════════════════════════════════════════════════════════════════════════

async def _ingest_comments_phase(
    business_id: str,
    comments: list,
) -> dict:
    """Phase 3: Comments - Load → Batch embed → Add → Unload."""
    stats = {"ok": 0, "error": 0}
    
    try:
        if not comments:
            log.info("[comments] no comments to ingest")
            return stats
        
        log.info(f"[comments] ingesting {len(comments)} comments (max 30/batch)")
        
        crag = CommentRAG()
        embedder = get_embedder()
        
        BATCH_SIZE = 30
        batch_count = 0
        
        for batch_idx in range(0, len(comments), BATCH_SIZE):
            batch = comments[batch_idx:batch_idx + BATCH_SIZE]
            batch_count += 1
            
            try:
                # Prepare texts
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
                        "chunk_id": f"cmt_{batch_idx}_{i}",
                        "business_id": business_id,
                        "source_id": f"research_cmt_{batch_idx}_{i}",
                        "source_type": "comment",
                    })
                
                if not records:
                    continue
                
                # Load embedder
                log.info(f"[comments] batch {batch_count}: loading embedder...")
                embedder._load()
                
                # Encode batch
                log.info(f"[comments] batch {batch_count}: encoding {len(records)} comments...")
                embs = await embedder.encode(texts)
                
                # Add precomputed batch
                log.info(f"[comments] batch {batch_count}: adding to FAISS...")
                result = await crag._store.add_precomputed_batch(
                    records, embs, dedupe_key=f"cmt_batch_{batch_idx}"
                )
                
                if result == "ok":
                    stats["ok"] += len(records)
                    log.info(f"[comments] batch {batch_count}: ✅ {len(records)} added")
                else:
                    log.warning(f"[comments] batch {batch_count}: {result}")
                
                # Unload embedder
                log.info(f"[comments] batch {batch_count}: unloading embedder...")
                embedder._model = None
                embedder._tokenizer = None
                import gc
                gc.collect()
                await asyncio.sleep(0.5)
                
            except Exception as e:
                log.error(f"[comments] batch {batch_count} failed: {e}")
                stats["error"] += len(batch)
                embedder._model = None
        
        return stats
        
    except Exception as e:
        log.error(f"[comments] phase error: {e}")
        return stats
    




async def _ingest_images(
    business_id: str,
    photo_urls: list,
) -> dict:
    """Priority 4: Images → ImageRAG (optional, GPU-dependent)."""
    stats = {"ok": 0, "error": 0}
    
    if not photo_urls:
        return stats
    
    try:
        from aiohttp import ClientSession
        from PIL import Image
        from io import BytesIO
        
        embedder = get_embedder()
        irag = ImageRAG(embedder)
        
        # Extract URLs
        urls = []
        for ph in photo_urls:
            if isinstance(ph, dict):
                url = ph.get("value") or ph.get("url")
            else:
                url = str(ph) if ph else None
            
            if url and isinstance(url, str):
                urls.append(url)
        
        if not urls:
            return stats
        
        # Download images (batch 3)
        images = []
        async with ClientSession() as session:
            for url in urls[:5]:  # Limit 5 images
                try:
                    async with session.get(url, timeout=10) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            img = Image.open(BytesIO(data))
                            images.append((img, f"research_img_{len(images)}", {}))
                except Exception as e:
                    log.debug(f"[img] download failed: {url}")
        
        # Add batch
        if images:
            try:
                batch_results = await irag.add_batch(images)
                for r in batch_results:
                    if r == "ok":
                        stats["ok"] += 1
                    else:
                        stats["error"] += 1
            except Exception as e:
                log.warning(f"[img] batch add failed: {e}")
                stats["error"] += len(images)
        
        return stats
    except Exception as e:
        log.error(f"[images] error: {e}")
        return stats