"""Image RAG — Florence-2 caption + BGE-M3 embed, text→image search."""

import asyncio
import hashlib
import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import List, Optional, Set, Tuple, Dict

import faiss
import numpy as np
import torch

log = logging.getLogger("rag")

# ── Config ────────────────────────────────────────────────────────────────────

IMAGE_PERSIST_DIR = Path(__file__).parent.parent.parent / "rag_storage" / "image"
# CAPTION_MODEL = "/home/duoc/models/florence-2-large"
CAPTION_MODEL = "/home/duoc/models/florence-2-base"
ENABLE_IMAGE_CAPTION = True

# Dùng chung BGE-M3 DIM=1024 thay vì SigLIP 768
IMAGE_DIM = 1024

# Caption bị coi là rác nếu quá ngắn hoặc quá mơ hồ
_MIN_CAPTION_LEN = 25
_TRASH_RE = re.compile(
    r"^(a\s+)?(photo|image|picture|photograph|img|drawing|illustration)"
    r"(\s+of\s+.{0,10})?\.?$",
    re.IGNORECASE,
)

_STRIP_PREFIXES = [
    "The image shows ",
    "The image depicts ",
    "This image shows ",
    "This image depicts ",
    "In this image, ",
    "The picture shows ",
]


def _is_trash(caption: str) -> bool:
    if not caption or len(caption.strip()) < _MIN_CAPTION_LEN:
        return True
    return bool(_TRASH_RE.match(caption.strip()))


def _clean_caption(caption: str) -> str:
    """Bỏ prefix thừa để embedding chính xác hơn."""
    caption = caption.strip()
    for prefix in _STRIP_PREFIXES:
        if caption.startswith(prefix):
            caption = caption[len(prefix):]
            caption = caption[0].upper() + caption[1:]
            break
    # Bỏ trailing artifacts như "=-" hay "=--"
    caption = re.sub(r"\s*=[-=]+\s*$", "", caption).strip()
    return caption


# ── ImageCaptioner ────────────────────────────────────────────────────────────

class ImageCaptioner:
    """
    Florence-2: sinh caption chi tiết từ ảnh.

    Load/unload GPU theo từng lô để tránh OOM khi dùng chung GPU với BGE-M3.
    """

    def __init__(self):
        self._processor = None
        self._model = None

    def _load(self):
        if self._model is not None:
            return
        from transformers import AutoProcessor, AutoModelForCausalLM

        log.info(f"[caption] loading {CAPTION_MODEL}...")
        self._processor = AutoProcessor.from_pretrained(
            CAPTION_MODEL,
            trust_remote_code=True,
            local_files_only=True,
            attn_implementation="eager",
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            CAPTION_MODEL,
            trust_remote_code=True,
            local_files_only=True,
            attn_implementation="eager",
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        )
        if torch.cuda.is_available():
            self._model = self._model.cuda()
        self._model.eval()
        log.info("[caption] loaded")

    def _unload(self):
        """Giải phóng VRAM sau khi xong lô."""
        if self._model is None:
            return
        self._model.cpu()
        del self._model
        del self._processor
        self._model = None
        self._processor = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        log.info("[caption] unloaded, VRAM freed")

    def _run_caption(self, image: "Image.Image") -> str:
        """Chạy inference đồng bộ — gọi trong thread executor."""
        prompt = "<MORE_DETAILED_CAPTION>"
        image_size = image.size
        inputs = self._processor(text=prompt, images=image, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = {
                k: v.cuda().half() if v.dtype == torch.float32 else v.cuda()
                for k, v in inputs.items()
            }
        with torch.no_grad():
            generated_ids = self._model.generate(
                **inputs,
                max_new_tokens=128,
                do_sample=False,
                num_beams=1,
                use_cache=False,
            )
        result = self._processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        parsed = self._processor.post_process_generation(
            result, task=prompt, image_size=image_size
        )
        return _clean_caption(parsed.get(prompt, ""))

    async def caption(self, image: "Image.Image") -> str:
        """Caption 1 ảnh — load trước, unload sau."""
        self._load()
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, self._run_caption, image)
        finally:
            self._unload()

    async def caption_batch(self, images: List["Image.Image"]) -> List[str]:
        """
        Caption nhiều ảnh trong 1 lô.
        Load Florence-2 1 lần → caption tất cả → unload.
        Hiệu quả hơn caption() từng ảnh khi xử lý lô lớn.
        """
        self._load()
        loop = asyncio.get_running_loop()
        try:
            results = []
            for image in images:
                try:
                    caption = await loop.run_in_executor(None, self._run_caption, image)
                    results.append(caption)
                except Exception as e:
                    log.warning(f"[caption] failed for 1 image: {e}")
                    results.append("")
            return results
        finally:
            self._unload()


# ── ImageStore ────────────────────────────────────────────────────────────────

class ImageStore:
    """
    Lưu trữ và tìm kiếm ảnh bằng cách embed caption qua BGE-M3.

    Thay vì embed ảnh trực tiếp (SigLIP), ta embed caption text → vector 1024d.
    Tìm kiếm text→ảnh sẽ là text↔text match, chính xác hơn nhiều.
    """

    def __init__(self, embedder):
        self._embed = embedder
        self._idx = faiss.IndexFlatIP(IMAGE_DIM)
        self._ids: List[str] = []
        self._metas: List[dict] = []
        self._hashes: Set[str] = set()
        self._lock = asyncio.Lock()
        IMAGE_PERSIST_DIR.mkdir(parents=True, exist_ok=True)

    def _make_hash(self, image_id: str) -> str:
        return hashlib.sha256(image_id.encode()).hexdigest()[:16]

    async def add(self, image_id: str, caption: str, **meta) -> str:
        """Thêm 1 ảnh — embed caption → lưu FAISS."""
        h = self._make_hash(image_id)
        if h in self._hashes:
            return "duplicate"

        async with self._lock:
            if h in self._hashes:
                return "duplicate"

            embs = await self._embed.encode([caption])
            emb = np.array(embs, dtype=np.float32)
            faiss.normalize_L2(emb)
            self._idx.add(emb)

            self._ids.append(image_id)
            self._metas.append({"image_id": image_id, "caption": caption, **meta})
            self._hashes.add(h)
            await self._save()
            log.info(f"[image_add] {image_id} | {caption[:60]}...")
            return "ok"

    async def add_batch(self, items: List[Tuple[str, str, dict]]) -> List[str]:
        """
        Thêm nhiều ảnh — embed tất cả caption 1 lần (batch) → lưu FAISS.
        items: list of (image_id, caption, meta)
        """
        # Lọc duplicate trước
        valid = []
        results: Dict[str, str] = {}
        for image_id, caption, meta in items:
            h = self._make_hash(image_id)
            if h in self._hashes:
                results[image_id] = "duplicate"
            else:
                valid.append((image_id, caption, meta, h))

        if not valid:
            return [results.get(iid, "duplicate") for iid, _, _ in items]

        # Batch embed tất cả caption 1 lần — BGE-M3 nhanh hơn nhiều
        captions = [cap for _, cap, _, _ in valid]
        embs = await self._embed.encode(captions)
        embs = np.array(embs, dtype=np.float32)
        faiss.normalize_L2(embs)

        async with self._lock:
            self._idx.add(embs)
            for i, (image_id, caption, meta, h) in enumerate(valid):
                self._ids.append(image_id)
                self._metas.append({"image_id": image_id, "caption": caption, **meta})
                self._hashes.add(h)
                results[image_id] = "ok"
                log.info(f"[image_add] {image_id} | {caption[:60]}...")

        await self._save()
        log.info(f"[batch_add] {len(valid)} added")
        return [results.get(iid, "ok") for iid, _, _ in items]

    async def search_by_text(self, text: str, k: int = 5) -> List[dict]:
        """Tìm ảnh bằng text query — text↔text match qua BGE-M3."""
        if not self._idx.ntotal:
            return []

        embs = await self._embed.encode([text])
        v = np.array(embs, dtype=np.float32)
        faiss.normalize_L2(v)
        scores, ids = self._idx.search(v, k)

        return [
            {"image_id": self._ids[i], "score": float(s), "meta": self._metas[i]}
            for s, i in zip(scores[0], ids[0])
            if i >= 0 and s > 0
        ]

    def stats(self) -> dict:
        return {"images": len(self._ids), "faiss_vectors": self._idx.ntotal}

    # ── Persist ──────────────────────────────────────────────────────────────

    def _save_sync(self):
        data = {"ids": self._ids, "metas": self._metas, "hashes": list(self._hashes)}
        tmp = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=IMAGE_PERSIST_DIR, delete=False, suffix=".tmp"
        )
        try:
            json.dump(data, tmp, ensure_ascii=False)
            tmp.close()
            os.replace(tmp.name, IMAGE_PERSIST_DIR / "data.json")
        except Exception:
            os.unlink(tmp.name)
            raise

        tmp_idx = tempfile.NamedTemporaryFile(dir=IMAGE_PERSIST_DIR, delete=False, suffix=".tmp")
        try:
            tmp_idx.close()
            faiss.write_index(self._idx, tmp_idx.name)
            os.replace(tmp_idx.name, IMAGE_PERSIST_DIR / "faiss.index")
        except Exception:
            os.path.exists(tmp_idx.name) and os.unlink(tmp_idx.name)
            raise

    async def _save(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._save_sync)

    def _load(self):
        dp = IMAGE_PERSIST_DIR / "data.json"
        fp = IMAGE_PERSIST_DIR / "faiss.index"
        if not (dp.exists() and fp.exists()):
            return
        try:
            with open(dp, encoding="utf-8") as f:
                d = json.load(f)
            self._ids = d["ids"]
            self._metas = d["metas"]
            self._hashes = set(d["hashes"])
            self._idx = faiss.read_index(str(fp))
            log.info(f"[image_load] {len(self._ids)} images restored")
        except Exception as e:
            log.warning(f"[image_load] corrupt, starting fresh: {e}")
            self._ids, self._metas, self._hashes = [], [], set()
            self._idx = faiss.IndexFlatIP(IMAGE_DIM)


# ── ImageRAG ──────────────────────────────────────────────────────────────────

class ImageRAG:
    """
    Pipeline add đơn:
        add(image) → Florence-2 caption → lọc rác → BGE-M3 embed → FAISS

    Pipeline add lô (khuyến nghị cho 10-100 ảnh):
        add_batch(images):
            Bước 1 — Florence-2 load GPU → caption tất cả → unload GPU
            Bước 2 — BGE-M3 load GPU → batch embed tất cả caption → unload GPU
            Bước 3 — FAISS lưu vectors

    Pipeline search:
        search_by_text(query) → BGE-M3 embed query → FAISS → ảnh khớp nhất
    """

    def __init__(self, embedder):
        """embedder: instance Embedder (BGE-M3) từ rag.py — dùng chung."""
        self._embed = embedder
        self._captioner = ImageCaptioner() if ENABLE_IMAGE_CAPTION else None
        self._store: Optional[ImageStore] = None

    async def _lazy_init(self):
        if self._store is None:
            self._store = ImageStore(self._embed)
            self._store._load()

    # ── Add đơn ──────────────────────────────────────────────────────────────

    async def add(self, image: "Image.Image", image_id: str, **meta) -> str:
        """
        Thêm 1 ảnh. Phù hợp khi thêm lẻ tẻ.
        Florence-2 load → caption → unload mỗi lần gọi.
        Trả về: "ok" | "duplicate" | "rejected"
        """
        await self._lazy_init()

        if not self._captioner:
            log.warning("[image_rag] captioner disabled")
            return "rejected"

        try:
            caption = await self._captioner.caption(image)  # load + unload bên trong
        except Exception as e:
            log.warning(f"[caption] failed for {image_id}: {e}")
            return "rejected"

        if _is_trash(caption):
            log.info(f"[image_rag] rejected: {image_id} | '{caption}'")
            return "rejected"

        return await self._store.add(image_id, caption, **meta)

    # ── Add lô ───────────────────────────────────────────────────────────────

    async def add_batch(
        self,
        images: List[Tuple["Image.Image", str, dict]],
    ) -> List[str]:
        """
        Thêm lô ảnh (10-100 hình). Hiệu quả hơn add() từng cái.

        images: list of (image, image_id, meta_dict)

        Flow:
            Bước 1: Florence-2 load GPU → caption tất cả → unload GPU
            Bước 2: BGE-M3 embed batch caption (1 lần) → lưu FAISS
        """
        await self._lazy_init()

        if not self._captioner:
            log.warning("[image_rag] captioner disabled")
            return ["rejected"] * len(images)

        # Bước 1: Caption toàn bộ lô — Florence-2 load 1 lần → unload sau
        log.info(f"[batch] captioning {len(images)} images...")
        raw_images = [img for img, _, _ in images]
        captions = await self._captioner.caption_batch(raw_images)  # load+unload bên trong

        # Lọc rác + chuẩn bị items hợp lệ
        store_items: List[Tuple[str, str, dict]] = []
        pre_results: Dict[str, str] = {}

        for (image, image_id, meta), caption in zip(images, captions):
            if _is_trash(caption):
                log.info(f"[batch] rejected: {image_id} | '{caption}'")
                pre_results[image_id] = "rejected"
            else:
                store_items.append((image_id, caption, meta))

        if not store_items:
            log.info("[batch] all images rejected as trash")
            return [pre_results.get(iid, "rejected") for _, iid, _ in images]

        # Bước 2: BGE-M3 batch embed + lưu FAISS
        log.info(f"[batch] embedding {len(store_items)} captions...")
        batch_results = await self._store.add_batch(store_items)

        # Gộp kết quả theo thứ tự ban đầu
        batch_map = {iid: r for (iid, _, _), r in zip(store_items, batch_results)}
        return [
            pre_results.get(image_id) or batch_map.get(image_id, "rejected")
            for _, image_id, _ in images
        ]

    # ── Search ────────────────────────────────────────────────────────────────

    async def search_by_text(self, text: str, k: int = 5) -> List[dict]:
        """Tìm ảnh bằng text query."""
        await self._lazy_init()
        return await self._store.search_by_text(text, k)

    def stats(self) -> dict:
        return self._store.stats() if self._store else {"images": 0, "faiss_vectors": 0}