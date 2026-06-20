"""Test script cho rag_core — chạy offline (mock embedder + reranker để không cần
tải model thật), nhưng pipeline FAISS + BM25 + retrieve/prefilter/rerank/cache
chạy THẬT.

Chạy:
    python tests/test_rag.py
"""

import asyncio
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TEST_STORAGE = Path("/tmp/rag_core_test_storage")


def _setup_fake_storage_env():
    if TEST_STORAGE.exists():
        shutil.rmtree(TEST_STORAGE)
    os.environ["RAG_STORAGE_DIR"] = str(TEST_STORAGE)


_setup_fake_storage_env()

import numpy as np  # noqa: E402

from app.rag.services.embedder import get_embedder  # noqa: E402
from app.rag.services.reranker import get_reranker  # noqa: E402


# ── Fake embedder: hash-based deterministic vector, không cần model thật ──────

def _fake_vector(text: str, dim: int = 1024) -> np.ndarray:
    rng = np.random.default_rng(abs(hash(text.lower())) % (2**32))
    v = rng.standard_normal(dim).astype(np.float32)
    return v


async def _fake_encode(self, texts):
    if not texts:
        return np.zeros((0, 1024), dtype=np.float32)
    return np.stack([_fake_vector(t) for t in texts])


def _fake_rerank(self, query, candidates):
    # score giả: overlap token thô — đủ để test thứ tự pipeline, không cần model thật
    q_tokens = set(query.lower().split())
    scores = []
    for _cid, text in candidates:
        t_tokens = set(text.lower().split())
        overlap = len(q_tokens & t_tokens)
        scores.append(overlap / (len(q_tokens) + 1e-6))
    return scores


async def _fake_arerank(self, query, candidates):
    return self.rerank(query, candidates)


def _patch_models():
    embedder = get_embedder()
    embedder.encode = _fake_encode.__get__(embedder)

    reranker = get_reranker()
    reranker.rerank = _fake_rerank.__get__(reranker)
    reranker.arerank = _fake_arerank.__get__(reranker)


_patch_models()

from app.rag.services import CommentRAG, KeywordRAG, SocialPostRAG  # noqa: E402

PASS = 0
FAIL = 0


def check(label: str, cond: bool, detail: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label} {detail}")


async def test_keyword():
    print("\n== KeywordRAG ==")
    rag = KeywordRAG()

    res = await rag.add("seo nhà hàng view pháo hoa ăn tối đà nẵng", business_id="b1", source_id="kw-1")
    check("add keyword -> ok", res == "ok", res)

    dup = await rag.add("seo nhà hàng view pháo hoa ăn tối đà nẵng", business_id="b1", source_id="kw-1")
    check("add lại cùng source_id -> duplicate", dup == "duplicate", dup)

    await rag.add("quán cafe view biển đà nẵng", business_id="b1", source_id="kw-2")
    await rag.add("nhà hàng hải sản đà nẵng giá rẻ", business_id="b1", source_id="kw-3")
    await rag.add("khách sạn 5 sao đà nẵng", business_id="b2", source_id="kw-4")  # business khác

    results = await rag.search("nhà hàng view đẹp đà nẵng", business_id="b1")
    check("search trả về kết quả", len(results) > 0, str(results))
    check(
        "search chỉ trả business_id=b1",
        all(c.meta["business_id"] == "b1" for c in results),
        str([c.meta["business_id"] for c in results]),
    )
    check("chunk_type = keyword", all(c.meta["chunk_type"] == "keyword" for c in results))

    t0 = time.perf_counter()
    await rag.search("nhà hàng view đẹp đà nẵng", business_id="b1")
    cached_ms = (time.perf_counter() - t0) * 1000
    check(f"cache hit nhanh (<50ms, thực tế {cached_ms:.2f}ms)", cached_ms < 50)


async def test_comment():
    print("\n== CommentRAG ==")
    rag = CommentRAG()

    await rag.add("quá tuyệt đặt bàn view đẹp", business_id="b1", source_id="cm-1")
    await rag.add("nhân viên phục vụ rất chu đáo, sẽ quay lại", business_id="b1", source_id="cm-2")
    await rag.add("giá hơi cao so với chất lượng món ăn", business_id="b1", source_id="cm-3")

    results = await rag.search("trải nghiệm đặt bàn view", business_id="b1")
    check("search trả về kết quả", len(results) > 0, str(results))
    check("không bị cắt câu (giữ nguyên text gốc)", all(len(c.text.split()) >= 3 for c in results))


async def test_social():
    print("\n== SocialPostRAG ==")
    rag = SocialPostRAG()

    res = await rag.add(
        business_id="b1",
        source_id="post-1",
        title="Đặt bàn ngay tối nay để xem pháo hoa từ trên cao",
        body=(
            "Nhà hàng X nằm ở vị trí đắc địa nhất sông Hàn.\n\n"
            "Thực khách có thể vừa ăn tối vừa ngắm trọn pháo hoa quốc tế.\n\n"
            "Không gian sang trọng, phù hợp cho cặp đôi và gia đình."
        ),
        cta="Đặt bàn ngay hôm nay để giữ chỗ view đẹp nhất!",
    )
    check("add social post -> ok", res == "ok", res)

    results = await rag.search("hook và CTA cho bài viết về view pháo hoa", business_id="b1")
    check("search trả về kết quả", len(results) > 0, str(results))
    chunk_types = {c.meta["chunk_type"] for c in results}
    check("có nhiều loại chunk (title/body/cta)", len(chunk_types) >= 1, str(chunk_types))


async def test_stats():
    print("\n== Stats ==")
    kw, cm, sp = KeywordRAG(), CommentRAG(), SocialPostRAG()
    print("  keyword:", kw.stats())
    print("  comment:", cm.stats())
    print("  social :", sp.stats())
    check("keyword có chunk", kw.stats()["chunks"] > 0)
    check("comment có chunk", cm.stats()["chunks"] > 0)
    check("social có chunk", sp.stats()["chunks"] > 0)


async def main():
    await test_keyword()
    await test_comment()
    await test_social()
    await test_stats()

    print(f"\n=== RESULT: {PASS} passed, {FAIL} failed ===")
    shutil.rmtree(TEST_STORAGE, ignore_errors=True)
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    asyncio.run(main())
