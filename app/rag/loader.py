"""DocumentLoaderService v2.2 — Production-grade document loader cho RAG ZERO v2.1.

Fixes so với v2.1:
- load_web: retry đúng khi fetch trả None (không exception)
- _iter_files: gọi _should_skip để bỏ hidden/venv/cache dirs
- load_directory: dùng _should_skip nhất quán
- Bỏ target_language="vi" trong trafilatura (tránh lọc nhầm content tiếng Anh xen kẽ)
- source_id nhất quán: dùng file_name hoặc URL để RAG dedup đúng
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from time import sleep
from typing import Dict, Iterator, List

import trafilatura

logger = logging.getLogger(__name__)


@dataclass
class LoadedDocument:
    """Đại diện cho một tài liệu đã tải — text + metadata."""

    text: str
    metadata: Dict = field(default_factory=dict)


class DocumentLoader:
    """
    Dịch vụ tải tài liệu chuẩn hóa cho RAG ZERO v2.1.
    Hỗ trợ: web, PDF, DOCX, XLSX, TXT, CSV, Markdown.
    Không phụ thuộc llama-index.
    """

    SUPPORTED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt", ".csv", ".xlsx", ".md"]
    MAX_FILE_SIZE_MB: int = 50

    # Patterns thư mục/file nên bỏ qua
    _SKIP_PATTERNS = (
        "/.git/",
        "/.venv/",
        "/venv/",
        "/node_modules/",
        "/__pycache__/",
        "/dist/",
        "/build/",
    )
    _SKIP_PREFIXES = (".", "~")

    _EXCESS_NEWLINE_RE: re.Pattern = re.compile(r"\n{3,}")

    def __init__(
        self,
        request_timeout_seconds: int = 15,
        max_retries: int = 3,
    ) -> None:
        self._timeout = request_timeout_seconds
        self._max_retries = max_retries

    # ── Text Cleaning ─────────────────────────────────────────────────────────

    def _clean_text(self, raw: str) -> str:
        """Chuẩn hoá whitespace, giữ ranh giới đoạn văn."""
        if not raw:
            return ""
        lines = [line.strip() for line in raw.split("\n")]
        joined = "\n".join(lines)
        return self._EXCESS_NEWLINE_RE.sub("\n\n", joined).strip()

    # ── Web Loading ───────────────────────────────────────────────────────────

    def load_web(self, url: str) -> LoadedDocument:
        """
        Tải và trích xuất nội dung từ URL với retry + exponential backoff.
        Retry cả khi fetch trả None (không chỉ khi có exception).
        """
        downloaded = None
        last_exc: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                downloaded = trafilatura.fetch_url(url)
                if downloaded:
                    break
                # Fetch thành công nhưng không có content → thử lại
                logger.warning(
                    "[Loader] fetch_url trả None lần %d/%d: %s",
                    attempt + 1,
                    self._max_retries,
                    url,
                )
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "[Loader] fetch_url exception lần %d/%d: %s — %s",
                    attempt + 1,
                    self._max_retries,
                    url,
                    exc,
                )

            if attempt < self._max_retries - 1:
                sleep(2**attempt)  # 1s → 2s → 4s

        if not downloaded:
            raise ValueError(
                f"Không thể tải URL sau {self._max_retries} lần thử: {url}"
            ) from last_exc

        # Trích xuất nội dung — không ép target_language để tránh lọc nhầm
        extracted = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
        )

        if not extracted:
            raise ValueError(f"Không trích xuất được nội dung từ URL: {url}")

        return LoadedDocument(
            text=self._clean_text(extracted),
            metadata={
                "source_id": url,
                "source_url": url,
                "document_type": "web_page",
            },
        )

    # ── File Reading (by type) ────────────────────────────────────────────────

    def _check_file_size(self, path: Path) -> None:
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > self.MAX_FILE_SIZE_MB:
            raise ValueError(
                f"File {path.name} ({size_mb:.1f} MB) vượt giới hạn {self.MAX_FILE_SIZE_MB} MB"
            )

    def _read_pdf(self, path: Path) -> str:
        try:
            import fitz
        except ImportError:
            raise ImportError("uv add pymupdf")

        doc = fitz.open(str(path))
        pages = []
        for page in doc:
            # Thử lấy text thường trước
            text = page.get_text("text")
            if text.strip():
                pages.append(text)
                continue
            # Thử lấy theo blocks (tốt hơn cho bảng/cột)
            blocks = page.get_text("blocks")
            block_text = "\n".join(b[4] for b in blocks if b[4].strip())
            if block_text.strip():
                pages.append(block_text)
                continue
            # Scan ảnh → OCR
            try:
                import pytesseract
                from PIL import Image
                import io
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_text = pytesseract.image_to_string(img, lang="vie+eng")
                if ocr_text.strip():
                    pages.append(ocr_text)
                    logger.info("[Loader] Page %d OCR thành công", page.number + 1)
            except Exception as e:
                logger.warning("[Loader] OCR page %d thất bại: %s", page.number + 1, e)

        if not pages:
            raise ValueError(f"Không đọc được nội dung (kể cả OCR): {path.name}")

        return "\n\n".join(pages)

    def _read_docx(self, path: Path) -> str:
        try:
            from docx import Document
        except ImportError:
            raise ImportError("Cài đặt: pip install python-docx")

        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    def _read_xlsx(self, path: Path) -> str:
        try:
            from openpyxl import load_workbook
        except ImportError:
            raise ImportError("Cài đặt: pip install openpyxl")

        wb = load_workbook(str(path), data_only=True)
        rows: List[str] = []
        for sheet in wb.worksheets:
            for row in sheet.iter_rows(values_only=True):
                row_text = " | ".join(str(c) for c in row if c is not None)
                if row_text.strip():
                    rows.append(row_text)
        return "\n".join(rows)

    def _read_txt(self, path: Path) -> str:
        for enc in ("utf-8", "utf-16", "cp1252", "iso-8859-1"):
            try:
                return path.read_text(encoding=enc)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Không thể decode file: {path}")

    _READERS = {
        ".pdf": _read_pdf,
        ".docx": _read_docx,
        ".xlsx": _read_xlsx,
        ".txt": _read_txt,
        ".csv": _read_txt,
        ".md": _read_txt,
    }

    def _read_file(self, path: Path) -> str:
        reader = self._READERS.get(path.suffix.lower())
        if not reader:
            raise ValueError(f"Không có reader cho định dạng: {path.suffix}")
        return reader(self, path)

    # ── Single File Loading ───────────────────────────────────────────────────

    def load_file(self, path: str) -> List[LoadedDocument]:
        """Đọc một file, trả về list (để đồng nhất interface với load_directory)."""
        file_path = Path(path)

        if not file_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file: {path}")
        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Định dạng '{file_path.suffix}' không được hỗ trợ. "
                f"Chấp nhận: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

        self._check_file_size(file_path)
        raw = self._read_file(file_path)
        cleaned = self._clean_text(raw)

        if not cleaned:
            raise ValueError(f"Không trích xuất được nội dung từ: {file_path.name}")

        return [
            LoadedDocument(
                text=cleaned,
                metadata=self._file_metadata(file_path),
            )
        ]

    def _file_metadata(self, path: Path) -> Dict:
        return {
            "source_id": path.name,          # dùng làm key dedup trong RAG Store
            "file_name": path.name,
            "file_extension": path.suffix.lower().lstrip("."),
            "file_size_bytes": path.stat().st_size,
            "absolute_path": str(path.resolve()),
            "document_type": "file",
        }

    # ── Directory Loading ─────────────────────────────────────────────────────

    def _should_skip(self, path: Path) -> bool:
        """Trả True nếu path thuộc hidden dir, venv, cache, v.v."""
        posix = path.as_posix()
        if any(pat in posix for pat in self._SKIP_PATTERNS):
            return True
        # File/dir bắt đầu bằng '.' hoặc '~'
        if any(part.startswith(self._SKIP_PREFIXES) for part in path.parts):
            return True
        return False

    def _iter_files(self, dir_path: Path) -> Iterator[Path]:
        for file_path in dir_path.rglob("*"):
            if (
                file_path.is_file()
                and not self._should_skip(file_path)
                and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS
            ):
                yield file_path

    def load_directory(self, path: str) -> List[LoadedDocument]:
        """
        Quét đệ quy thư mục.
        Bỏ qua hidden dirs, venv, cache, file lỗi.
        """
        dir_path = Path(path)
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Không phải thư mục: {path}")

        docs: List[LoadedDocument] = []

        for file_path in self._iter_files(dir_path):
            try:
                self._check_file_size(file_path)
                raw = self._read_file(file_path)
                cleaned = self._clean_text(raw)
                if cleaned:
                    docs.append(
                        LoadedDocument(
                            text=cleaned,
                            metadata=self._file_metadata(file_path),
                        )
                    )
            except Exception as exc:
                logger.warning("[Loader] Bỏ qua %s: %s", file_path, exc)

        logger.info("[Loader] Nạp %d tài liệu từ %s", len(docs), path)
        return docs