"""Migration: rag_storage cũ (RAG ZERO v3.1 — 1 store gộp chung) -> rag_core mới
(3 store riêng: keyword / comment / social).

Old storage:
    rag_storage/data.json   -> {"texts": [...], "metas": [...], "corpus": [...], "hashes": [...]}
    rag_storage/faiss.index -> FAISS IndexFlatIP, dim=1024, cùng model bge-m3

Vì model embedding KHÔNG đổi (vẫn BAAI/bge-m3, dim 1024), script này TÁI SỬ DỤNG
trực tiếp vector cũ trong faiss.index — không re-embed — để di chuyển nhanh và
không lệch không gian vector.

Vì schema metadata cũ là dict tự do (do caller cũ tự đặt field), script không thể
tự suy luận loại RAG (keyword/comment/social) một cách chắc chắn. Mặc định dùng
`classify_record()` dưới đây — CHỈNH LẠI hàm này theo field thực tế trong
metadata cũ của bạn trước khi chạy migrate cho production.

Chạy:
    python -m rag_core.migrate_legacy --old-dir /path/to/old/rag_storage
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Optional

import faiss
import numpy as np

from .comment import CommentRAG
from .keyword import KeywordRAG
from .social import SocialPostRAG

log = logging.getLogger("rag.migrate")
logging.basicConfig(level=logging.INFO)


def classify_record(meta: Dict) -> Optional[str]:
    """Suy luận loại RAG từ metadata cũ. CHỈNH LẠI theo dữ liệu thực tế.

    Trả về "keyword" | "comment" | "social" | None (None = bỏ qua, không migrate).
    """
    # Ưu tiên 1: nếu metadata cũ đã có field đánh dấu loại sẵn.
    explicit = (meta.get("rag_type") or meta.get("type") or meta.get("category") or "").lower()
    if explicit in ("keyword", "comment", "social", "social_post"):
        return "social" if explicit == "social_post" else explicit

    # Ưu tiên 2: heuristic theo field đặc trưng (chỉnh theo schema thật của bạn).
    if any(k in meta for k in ("keyword", "search_volume", "seo_intent")):
        return "keyword"
    if any(k in meta for k in ("comment_id", "rating", "sentiment")):
        return "comment"
    if any(k in meta for k in ("post_id", "cta", "hook", "platform")):
        return "social"

    return None  # không xác định -> bỏ qua, tránh migrate sai loại


def _social_fields(text: str, meta: Dict) -> Dict[str, str]:
    """Cố gắng tách title/body/cta từ record cũ. Nếu cũ không tách sẵn,
    toàn bộ text được coi là 'body' (script sẽ tự thêm 1 chunk loại 'body').
    """
    return {
        "title": meta.get("title", ""),
        "body": meta.get("body", text),
        "cta": meta.get("cta", ""),
    }


async def migrate(old_dir: Path):
    data_path = old_dir / "data.json"
    index_path = old_dir / "faiss.index"
    if not (data_path.exists() and index_path.exists()):
        log.error(f"Không tìm thấy {data_path} hoặc {index_path}")
        return

    with open(data_path, encoding="utf-8") as f:
        old = json.load(f)
    old_texts = old["texts"]
    old_metas = old["metas"]
    old_index = faiss.read_index(str(index_path))

    if old_index.ntotal != len(old_texts):
        log.warning(
            f"Số vector trong faiss.index ({old_index.ntotal}) khác số text "
            f"({len(old_texts)}) — có thể storage cũ không đồng bộ."
        )

    old_vectors = old_index.reconstruct_n(0, old_index.ntotal)  # (n, dim), đã normalize sẵn

    keyword_rag = KeywordRAG()
    comment_rag = CommentRAG()
    social_rag = SocialPostRAG()

    counters = {"keyword": 0, "comment": 0, "social": 0, "skipped": 0}

    for i, (text, meta) in enumerate(zip(old_texts, old_metas)):
        rag_type = classify_record(meta)
        business_id = meta.get("business_id", "unknown")
        source_id = meta.get("source_id", f"legacy-{i}")
        vec = old_vectors[i : i + 1]

        if rag_type == "keyword":
            dkey = f"legacy-keyword-{source_id}"
            records = [
                {
                    "text": text,
                    "chunk_type": "keyword",
                    "chunk_id": f"{dkey}_0",
                    "business_id": business_id,
                    "source_id": source_id,
                    "source_type": "keyword",
                }
            ]
            res = await keyword_rag._store.add_precomputed_batch(records, vec, dkey)
            counters["keyword"] += res == "ok"

        elif rag_type == "comment":
            dkey = f"legacy-comment-{source_id}"
            records = [
                {
                    "text": text,
                    "chunk_type": "comment",
                    "chunk_id": f"{dkey}_0",
                    "business_id": business_id,
                    "source_id": source_id,
                    "source_type": "comment",
                }
            ]
            res = await comment_rag._store.add_precomputed_batch(records, vec, dkey)
            counters["comment"] += res == "ok"

        elif rag_type == "social":
            dkey = f"legacy-social-{source_id}"
            fields = _social_fields(text, meta)
            chunk_type = "title" if fields["title"] == text else "body"
            records = [
                {
                    "text": text,
                    "chunk_type": chunk_type,
                    "chunk_id": f"{dkey}_0",
                    "business_id": business_id,
                    "source_id": source_id,
                    "source_type": "social",
                }
            ]
            # Lưu ý: record cũ thường KHÔNG có sẵn 3-6 chunk/post tách title/body/cta.
            # Ta giữ nguyên 1 vector cũ -> 1 chunk (không re-embed) để tái sử dụng,
            # phần social post mới thêm sau này sẽ tự được chunk đúng chuẩn 3-6.
            res = await social_rag._store.add_precomputed_batch(records, vec, dkey)
            counters["social"] += res == "ok"

        else:
            counters["skipped"] += 1

    log.info(f"[migrate] done: {counters}")


def main():
    parser = argparse.ArgumentParser(description="Migrate RAG ZERO v3.1 -> rag_core mới")
    parser.add_argument("--old-dir", required=True, help="Đường dẫn thư mục rag_storage cũ")
    args = parser.parse_args()
    asyncio.run(migrate(Path(args.old_dir)))


if __name__ == "__main__":
    main()
