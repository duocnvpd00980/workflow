"""
app/rag/services/ingest.py
RAG ingestion - VRAM 4GB, tối ưu tốc độ, tích hợp ImageRAG.
"""

import asyncio
import gc
import logging
import os
import time
import numpy as np
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from PIL import Image
from io import BytesIO
from aiohttp import ClientSession
from app.research.models import ResearchResult, FbPost, FbComment, FbPhoto
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
    1. Keywords (batch 10) — load 1 lần, nhiều batch, unload cuối
    2. Posts (batch 5) — load 1 lần, nhiều batch, unload cuối
    3. Comments (batch 10) — load 1 lần, nhiều batch, unload cuối
    4. Images (ImageRAG: Florence-2 caption + BGE-M3 embed, batch 2)
    """
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
            "photos": {"ok": 0, "error": 0},
        }
        
        # ═════════════════════════════════════════════════════════════════
        # PHASE 1: Keywords (batch 10, load 1 lần)
        # ════════════════════════════════════
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
        # PHASE 2: Posts (batch 5, load 1 lần)
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
        # PHASE 3: Comments (batch 10, load 1 lần)
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
        # PHASE 4: Images (ImageRAG — Florence-2 + BGE-M3, batch 2)
        # ═════════════════════════════════════════════════════════════════
        log.info("[rag] === PHASE 4: Images ===")
        
        # Lấy photo URLs từ bảng FbPhoto (mới tạo)
        photo_stmt = select(FbPhoto).where(FbPhoto.business_id == business_id)
        photo_result = await db.execute(photo_stmt)
        photo_urls = [p.url for p in photo_result.scalars().all() if p.url]
        
        log.info(f"[images] tìm thấy {len(photo_urls)} ảnh từ DB")
        
        img_stats = await _ingest_images_phase(business_id, photo_urls)
        stats["images"] = img_stats
        log.info(f"[rag] Images xong: {img_stats}")
        
        _clear_vram()
        
        log.info(f"[rag] ✅ DONE: {business_id} | {stats}")
        return stats

    except Exception as e:
        log.error(f"[rag] ❌ error: {e}", exc_info=True)
        _clear_vram()
        return {"status": "error", "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: Keywords (batch 10, load 1 lần mỗi phase)
# ═══════════════════════════════════════════════════════════════════════════════

async def _ingest_keywords_phase(
    business_id: str,
    suggestions_tagged: dict,
    content_angles: list,
    run_id: str,
) -> dict:
    stats = {"ok": 0, "error": 0}
    
    try:
        # Flatten keywords
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
        
        # Load embedder 1 lần đầu phase
        log.info("[keywords] load embedder 1 lần...")
        embedder._load()
        
        try:
            for batch_idx in range(0, len(unique_kw), BATCH_SIZE):
                batch = unique_kw[batch_idx:batch_idx + BATCH_SIZE]
                batch_num = batch_idx // BATCH_SIZE + 1
                
                try:
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
                    
                except Exception as e:
                    log.error(f"[keywords] batch {batch_num} lỗi: {e}")
                    stats["error"] += len(batch)
        
        finally:
            # Unload 1 lần cuối phase
            embedder.unload()
            _clear_vram()
            log.info("[keywords] unload xong")
        
        return stats
        
    except Exception as e:
        log.error(f"[keywords] phase lỗi: {e}")
        return stats


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: Posts (batch 5, load 1 lần mỗi phase)
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
    
    # Load embedder 1 lần đầu phase
    log.info("[posts] load embedder 1 lần...")
    embedder._load()
    
    try:
        for batch_idx in range(0, len(posts), BATCH_SIZE):
            batch = posts[batch_idx:batch_idx + BATCH_SIZE]
            batch_num = batch_idx // BATCH_SIZE + 1
            
            try:
                records = []
                texts = []
                
                for i, post_text in enumerate(batch):
                    if not post_text:
                        continue
                    
                    text = str(post_text).strip()
                    if not text:
                        continue
                    
                    lines = text.split("\n", 1)
                    title = lines[0][:100] if lines[0] else ""
                    body = lines[1] if len(lines) > 1 else ""
                    full_text = f"{title} {body}".strip()
                    
                    if not full_text:
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
                
            except Exception as e:
                log.error(f"[posts] batch {batch_num} lỗi: {e}", exc_info=True)
                stats["error"] += len(batch)
    
    finally:
        # Unload 1 lần cuối phase
        embedder.unload()
        _clear_vram()
        log.info("[posts] unload xong")
    
    return stats


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: Comments (batch 10, load 1 lần mỗi phase)
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
    
    # Load embedder 1 lần đầu phase
    log.info("[comments] load embedder 1 lần...")
    embedder._load()
    
    try:
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
                
            except Exception as e:
                log.error(f"[comments] batch {batch_num} lỗi: {e}")
                stats["error"] += len(batch)
    
    finally:
        # Unload 1 lần cuối phase
        embedder.unload()
        _clear_vram()
        log.info("[comments] unload xong")
    
    return stats


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: Images (ImageRAG — Florence-2 caption + BGE-M3 embed)
# ═══════════════════════════════════════════════════════════════════════════════

async def _ingest_images_phase(
    business_id: str,
    photo_urls: list,
) -> dict:
    """
    Images: dùng ImageRAG với Florence-2 caption + BGE-M3 embed.
    Flow: download ảnh → ImageRAG.add_batch() → tự động caption + embed + lưu FAISS
    """
    stats = {"ok": 0, "error": 0}
    
    if not photo_urls:
        log.info("[images] không có ảnh nào")
        return stats
    
    # Extract URLs
    urls = []
    for ph in photo_urls:
        if isinstance(ph, dict):
            url = ph.get("value") or ph.get("url") or ph.get("src")
        else:
            url = str(ph) if ph else None
        
        if url and isinstance(url, str) and url.startswith(("http://", "https://")):
            urls.append(url)
    
    if not urls:
        log.info("[images] không có URL hợp lệ")
        return stats
    
    log.info(f"[images] {len(urls)} ảnh, download & process...")
    
    # Dọn VRAM trước khi load Florence-2
    _clear_vram()
    await asyncio.sleep(1)
    
    # Download ảnh
    images: List[Tuple[Image.Image, str, dict]] = []
    
    async with ClientSession() as session:
        for i, url in enumerate(urls):
            try:
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        img = Image.open(BytesIO(data))
                        # Convert sang RGB nếu cần
                        if img.mode != "RGB":
                            img = img.convert("RGB")
                        
                        image_id = f"{business_id}_img_{i}"
                        meta = {"url": url, "business_id": business_id, "index": i}
                        images.append((img, image_id, meta))
                        log.info(f"[images] downloaded: {url[:60]}...")
                    else:
                        log.warning(f"[images] HTTP {resp.status}: {url[:60]}...")
                        stats["error"] += 1
            except Exception as e:
                log.warning(f"[images] download lỗi: {url[:60]}... | {e}")
                stats["error"] += 1
    
    if not images:
        log.info("[images] không tải được ảnh nào")
        return stats
    
    log.info(f"[images] đã tải {len(images)} ảnh, bắt đầu ImageRAG...")
    
    try:
        # Khởi tạo ImageRAG với embedder BGE-M3
        embedder = get_embedder()
        irag = ImageRAG(embedder)
        
        # ImageRAG.add_batch tự động: Florence-2 load → caption all → unload → BGE-M3 embed → FAISS
        batch_results = await irag.add_batch(images)
        
        for r in batch_results:
            if r == "ok":
                stats["ok"] += 1
            elif r == "duplicate":
                stats["error"] += 1  # Hoặc không tính lỗi nếu muốn
            elif r == "rejected":
                stats["error"] += 1
            else:
                stats["error"] += 1
        
        log.info(f"[images] ImageRAG xong: ok={stats['ok']}, error={stats['error']}")
        
    except Exception as e:
        log.error(f"[images] ImageRAG lỗi: {e}", exc_info=True)
        stats["error"] += len(images)
    
    finally:
        # Dọn VRAM sau khi xong
        _clear_vram()
        await asyncio.sleep(1)
    
    return stats