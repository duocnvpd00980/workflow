"""Hotel Service — crawl + extract + embed + search phòng khách sạn.

Hoàn toàn độc lập — không phụ thuộc DocumentLoader hay bất kỳ RAG loader nào.
"""

from __future__ import annotations

import asyncio
import logging
import re
import json
from typing import Optional

import faiss
import numpy as np
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.models import HotelRoom
from app.rag.service import Embedder
from app.config import get_settings

_s = get_settings()

log = logging.getLogger("hotel")

HOTEL_PERSIST_DIR = Path(__file__).parent.parent.parent / "rag_storage" / "hotel"
HOTEL_DIM = 1024  # BGE-M3
_EXCESS_NEWLINE_RE = re.compile(r"\n{3,}")


# ── Web Crawler ───────────────────────────────────────────────────────────────

async def _fetch_page(url: str, max_retries: int = 3) -> str:
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
    except ImportError:
        raise ImportError("Cài đặt: pip install crawl4ai && crawl4ai-setup")

    browser_cfg = BrowserConfig(headless=True, verbose=False)
    run_cfg = CrawlerRunConfig(
        # Bỏ PruningContentFilter — để LLM đọc toàn bộ, tránh cắt mất amenities/description
        markdown_generator=DefaultMarkdownGenerator(),
        wait_until="networkidle",
        page_timeout=30_000,
        cache_mode="bypass",
    )

    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                result = await crawler.arun(url=url, config=run_cfg)

            if not result.success:
                raise ValueError(f"crawl4ai thất bại: {result.error_message}")

            text = (
                (result.markdown.fit_markdown or "").strip()
                or (result.markdown.raw_markdown or "").strip()
            )

            if not text:
                raise ValueError("Không trích xuất được nội dung từ URL.")

            lines = [line.strip() for line in text.split("\n")]
            text = _EXCESS_NEWLINE_RE.sub("\n\n", "\n".join(lines)).strip()

            log.info("[hotel_fetch] OK url=%s, len=%d", url, len(text))
            return text

        except Exception as exc:
            last_exc = exc
            log.warning("[hotel_fetch] lần %d/%d thất bại: %s — %s",
                        attempt + 1, max_retries, url, exc)
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)

    raise ValueError(f"Không thể crawl URL sau {max_retries} lần thử: {url}") from last_exc


# ── Groq Extractor ────────────────────────────────────────────────────────────

EXTRACT_PROMPT = """Bạn là AI chuyên phân tích trang web khách sạn.
Từ nội dung dưới đây, hãy liệt kê các phòng khách sạn tìm được.

Mỗi phòng viết theo định dạng sau:

--- PHÒNG ---
Tên: <tên phòng>
Loại: <standard|deluxe|vip|suite>
Giường: <single|double|twin|king>
Sức chứa: <số người>
Diện tích: <m²>
Giá: <số tiền> <VND|USD>/đêm
Tiện nghi: <wifi, ac, tv, ...>
Mô tả: <mô tả ngắn>
Ảnh: <url1>, <url2>
---

Nếu một trường không có thông tin thì bỏ qua dòng đó.
Nếu không tìm thấy phòng nào thì viết: KHÔNG TÌM THẤY PHÒNG.
Nội dung:
"""

ALIAS_PROMPT = """Bạn là AI hỗ trợ tìm kiếm khách sạn.
Cho tên phòng và thông tin sau, hãy sinh ra các cách gọi tiếng Việt tự nhiên mà khách hàng hay dùng khi tìm kiếm.

Tên phòng: {name}
Loại: {room_type}
Giường: {bed_type}
Sức chứa: {capacity} người
Tiện nghi: {amenities}

Yêu cầu:
- Liệt kê 4-6 cách gọi ngắn gọn, tự nhiên
- Mỗi alias một dòng, không đánh số, không giải thích
- Dùng tiếng Việt thuần, tránh lặp lại tên gốc

Ví dụ output:
phòng đôi tiêu chuẩn
phòng 2 giường
phòng đôi có wifi
phòng standard 2 người
"""


def _parse_rooms(raw: str) -> list[dict]:
    rooms = []
    for block in re.split(r"---\s*PHÒNG\s*---", raw):
        block = block.strip().strip("---").strip()
        if not block or "KHÔNG TÌM THẤY" in block:
            continue

        def _get(label: str) -> str | None:
            m = re.search(rf"^{label}:\s*(.+)$", block, re.MULTILINE)
            return m.group(1).strip() if m else None

        name = _get("Tên")
        if not name:
            continue

        price: float | None = None
        currency = "VND"
        raw_price = _get("Giá")
        if raw_price:
            m = re.search(r"([\d,\.]+)", raw_price)
            if m:
                price = float(m.group(1).replace(",", ""))
            currency = "USD" if "USD" in raw_price.upper() else "VND"

        area: float | None = None
        raw_area = _get("Diện tích")
        if raw_area:
            m = re.search(r"([\d,\.]+)", raw_area)
            if m:
                area = float(m.group(1).replace(",", ""))

        capacity: int | None = None
        raw_cap = _get("Sức chứa")
        if raw_cap:
            m = re.search(r"\d+", raw_cap)
            if m:
                capacity = int(m.group())

        amenities: list[str] = []
        raw_am = _get("Tiện nghi")
        if raw_am:
            amenities = [a.strip() for a in re.split(r"[,;]", raw_am) if a.strip()]

        image_urls: list[str] = []
        raw_img = _get("Ảnh")
        if raw_img:
            image_urls = [u.strip() for u in re.split(r"[,;]", raw_img) if u.strip()]

        rooms.append({
            "name":            name,
            "room_type":       _get("Loại"),
            "bed_type":        _get("Giường"),
            "capacity":        capacity,
            "area_sqm":        area,
            "price_per_night": price,
            "currency":        currency,
            "description":     _get("Mô tả"),
            "amenities":       amenities,
            "image_urls":      image_urls,
        })

    log.info("[parse_rooms] parsed %d rooms", len(rooms))
    return rooms


def _parse_aliases(raw: str) -> list[str]:
    """Parse danh sách alias — mỗi dòng là một alias, bỏ dòng trống."""
    return [
        line.strip()
        for line in raw.strip().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


class GroqExtractor:
    def __init__(self):
        from groq import Groq
        self._client = Groq(api_key=_s.GROQ_API_KEY)
        self._model = _s.GROQ_MODEL

    async def extract(self, content: str) -> list[dict]:
        if not content or len(content.strip()) < 50:
            log.warning("[groq_extract] content quá ngắn (%d chars), skip", len(content))
            return []

        loop = asyncio.get_running_loop()

        def _run():
            truncated = content[:8000]
            log.info("[groq_extract] gửi %d chars, model=%s", len(truncated), self._model)

            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": "Bạn là AI chuyên phân tích trang web khách sạn. Hãy liệt kê thông tin phòng theo đúng định dạng được yêu cầu.",
                    },
                    {"role": "user", "content": EXTRACT_PROMPT + truncated},
                ],
                temperature=0.1,
                max_tokens=2048,
            )

            raw = resp.choices[0].message.content or ""
            finish_reason = resp.choices[0].finish_reason
            log.info("[groq_extract] finish_reason=%s, raw_len=%d, preview=%.200s",
                     finish_reason, len(raw), raw)

            if not raw.strip():
                log.error("[groq_extract] Groq trả về rỗng, finish_reason=%s", finish_reason)
                return []

            return _parse_rooms(raw)

        try:
            return await loop.run_in_executor(None, _run)
        except Exception as e:
            log.error("[groq_extract] %s: %s", type(e).__name__, e)
            return []

    async def generate_aliases(self, room: dict) -> list[str]:
        """Sinh alias tiếng Việt cho một phòng — chạy sau extract."""
        loop = asyncio.get_running_loop()

        def _run():
            prompt = ALIAS_PROMPT.format(
                name=room.get("name", ""),
                room_type=room.get("room_type") or "không rõ",
                bed_type=room.get("bed_type") or "không rõ",
                capacity=room.get("capacity") or "không rõ",
                amenities=", ".join(room.get("amenities") or []) or "không rõ",
            )
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,  # cao hơn chút để alias đa dạng
                max_tokens=256,
            )
            raw = resp.choices[0].message.content or ""
            aliases = _parse_aliases(raw)
            log.info("[groq_alias] %s → %s", room.get("name"), aliases)
            return aliases

        try:
            return await loop.run_in_executor(None, _run)
        except Exception as e:
            log.error("[groq_alias] %s: %s", type(e).__name__, e)
            return []


# ── Hotel Vector Store ────────────────────────────────────────────────────────

class HotelVectorStore:
    def __init__(self, embedder: Embedder):
        self._embed = embedder
        self._idx = faiss.IndexFlatIP(HOTEL_DIM)
        self._room_ids: list[int] = []
        HOTEL_PERSIST_DIR.mkdir(parents=True, exist_ok=True)

    async def add(self, room_id: int, text: str):
        embs = await self._embed.encode([text])
        v = np.array(embs, dtype=np.float32)
        faiss.normalize_L2(v)
        self._idx.add(v)
        self._room_ids.append(room_id)
        self._save()
        log.info("[hotel_vec] added room_id=%d", room_id)

    async def search(self, query: str, k: int = 20) -> list[int]:
        if not self._idx.ntotal:
            return []
        embs = await self._embed.encode([query])
        v = np.array(embs, dtype=np.float32)
        faiss.normalize_L2(v)
        scores, ids = self._idx.search(v, k)
        return [
            self._room_ids[i]
            for s, i in zip(scores[0], ids[0])
            if i >= 0 and s > 0
        ]

    def remove(self, room_id: int):
        """FAISS FlatIP không support remove — rebuild index."""
        if room_id not in self._room_ids:
            return
        idx = self._room_ids.index(room_id)
        self._room_ids.pop(idx)
        vectors = faiss.rev_swig_ptr(self._idx.get_xb(), self._idx.ntotal * HOTEL_DIM)
        vectors = vectors.reshape(self._idx.ntotal, HOTEL_DIM)
        vectors = np.delete(vectors, idx, axis=0)
        self._idx = faiss.IndexFlatIP(HOTEL_DIM)
        if len(vectors):
            self._idx.add(vectors.astype(np.float32))
        self._save()

    def _save(self):
        dp = HOTEL_PERSIST_DIR / "data.json"
        fp = HOTEL_PERSIST_DIR / "faiss.index"
        try:
            tmp_d = dp.with_suffix(".tmp")
            tmp_f = fp.with_suffix(".tmp")
            tmp_d.write_text(json.dumps({"room_ids": self._room_ids}))
            tmp_d.replace(dp)
            faiss.write_index(self._idx, str(tmp_f))
            tmp_f.replace(fp)
        except Exception as e:
            log.error("[hotel_vec_save] %s", e)

    def _load(self):
        dp = HOTEL_PERSIST_DIR / "data.json"
        fp = HOTEL_PERSIST_DIR / "faiss.index"
        if not (dp.exists() and fp.exists()):
            return
        try:
            d = json.loads(dp.read_text())
            self._room_ids = d["room_ids"]
            self._idx = faiss.read_index(str(fp))
            log.info("[hotel_vec] loaded %d rooms", len(self._room_ids))
        except Exception as e:
            log.warning("[hotel_vec] corrupt, fresh start: %s", e)
            self._room_ids = []
            self._idx = faiss.IndexFlatIP(HOTEL_DIM)


# ── Hotel Service ─────────────────────────────────────────────────────────────

class HotelService:
    def __init__(self):
        self._embedder = Embedder()
        self._vec: Optional[HotelVectorStore] = None
        self._extractor = GroqExtractor()

    def _lazy_init(self):
        if self._vec is None:
            self._vec = HotelVectorStore(self._embedder)
            self._vec._load()

    @staticmethod
    def _slug(name: str) -> str:
        s = name.lower().strip()
        s = re.sub(r"[^\w\s-]", "", s)
        s = re.sub(r"\s+", "-", s)
        return s[:200]

    async def crawl(self, url: str, db: AsyncSession) -> list[HotelRoom]:
        self._lazy_init()

        content = await _fetch_page(url)

        if not content:
            log.warning("[hotel_crawl] empty content: %s", url)
            return []

        rooms_data = await self._extractor.extract(content)
        if not rooms_data:
            log.warning("[hotel_crawl] no rooms extracted: %s", url)
            return []

        saved = []
        for data in rooms_data:
            name = data.get("name", "").strip()
            if not name:
                continue

            slug = self._slug(name)

            existing = await db.execute(
                select(HotelRoom).where(HotelRoom.slug == slug)
            )
            if existing.scalar_one_or_none():
                log.info("[hotel_crawl] duplicate: %s", slug)
                continue

            # Sinh aliases tiếng Việt — fallback về [] nếu lỗi
            aliases = await self._extractor.generate_aliases(data)

            room = HotelRoom(
                name=name,
                slug=slug,
                source_url=url,
                room_type=data.get("room_type"),
                bed_type=data.get("bed_type"),
                capacity=data.get("capacity"),
                area_sqm=data.get("area_sqm"),
                price_per_night=data.get("price_per_night"),
                currency=data.get("currency", "VND"),
                description=data.get("description"),
                amenities=data.get("amenities", []),
                image_urls=data.get("image_urls", []),
                aliases=aliases,
                status="active",
            )
            db.add(room)
            await db.flush()

            await self._vec.add(room.id, room.embed_text())
            saved.append(room)

        await db.commit()
        log.info("[hotel_crawl] saved %d rooms from %s", len(saved), url)
        return saved

    async def search(
        self,
        query: str,
        db: AsyncSession,
        k: int = 5,
        room_type: Optional[str] = None,
        max_price: Optional[float] = None,
        min_capacity: Optional[int] = None,
    ) -> list[HotelRoom]:
        self._lazy_init()

        room_ids = await self._vec.search(query, k=20)
        if not room_ids:
            return []

        rows = await db.execute(
            select(HotelRoom).where(
                HotelRoom.id.in_(room_ids),
                HotelRoom.status == "active",
            )
        )
        rooms = list(rows.scalars())

        if room_type:
            rooms = [r for r in rooms if r.room_type == room_type]
        if max_price is not None:
            rooms = [r for r in rooms if r.price_per_night and r.price_per_night <= max_price]
        if min_capacity is not None:
            rooms = [r for r in rooms if r.capacity and r.capacity >= min_capacity]

        id_order = {rid: i for i, rid in enumerate(room_ids)}
        rooms.sort(key=lambda r: id_order.get(r.id, 999))

        return rooms[:k]

    async def delete(self, room_id: int, db: AsyncSession) -> bool:
        self._lazy_init()
        room = await db.get(HotelRoom, room_id)
        if not room:
            return False
        await db.delete(room)
        await db.commit()
        self._vec.remove(room_id)
        return True

    def stats(self) -> dict:
        self._lazy_init()
        return {
            "total_vectors": self._vec._idx.ntotal,
            "total_rooms": len(self._vec._room_ids),
        }