# ── CELL 5: Sync vào business_service.py — copy toàn bộ cell này ─────────────
"""BusinessCrawler v2 — khai thác header/nav/footer/contact cho brand RAG."""
from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.loader import DocumentLoader
from app.rag.models import DocumentPage
from app.rag.service import RAG

log = logging.getLogger(__name__)

# ── Regex contact ─────────────────────────────────────────────────────────────
_PHONE_RE     = re.compile(r"tel:([\d\s\-\+\.]+)", re.IGNORECASE)
_ZALO_RE      = re.compile(r"zalo\.me/([^\s\)\"]+)", re.IGNORECASE)
_EMAIL_RE     = re.compile(r"mailto:([^\s\)\"]+)", re.IGNORECASE)
_FB_RE        = re.compile(r"facebook\.com/([^\s\)\"]+)", re.IGNORECASE)
_TIKTOK_RE    = re.compile(r"tiktok\.com/@([^\s\)\"]+)", re.IGNORECASE)
_INSTAGRAM_RE = re.compile(r"instagram\.com/([^\s\)\"]+)", re.IGNORECASE)
_ADDRESS_RE   = re.compile(
    r"(số\s+\d+.{5,80}(?:đường|phố|quận|huyện|tp\.|thành phố)[^,\n]{0,60})",
    re.IGNORECASE,
)
_HOURS_RE = re.compile(
    r"(\d{1,2}[h:]\d{0,2}\s*[-–]\s*\d{1,2}[h:]\d{0,2})",
    re.IGNORECASE,
)

# ── Regex cấu trúc markdown ───────────────────────────────────────────────────
_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_H2_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)

# Bắt [label](url) và [label](url "title") — chỉ lấy url, bỏ title attribute
_MD_LINK_RE = re.compile(
    r'\[([^\]]+)\]\(((?:/[^\s\)\"]*|https?://[^\s\)\"]*))(?:\s+"[^"]*")?\)',
    re.IGNORECASE,
)

# Tagline — chỉ lấy dòng text thuần, không chứa markdown link
_TAGLINE_SAFE_RE = re.compile(
    r'^(?!.*\]\()'
    r'.*(chuyên|cung cấp|được thành lập|với hơn|hệ thống|chuỗi).{20,200}$',
    re.IGNORECASE | re.MULTILINE,
)

# Nav skip — path UI không có giá trị brand
_NAV_SKIP_RE = re.compile(
    r'/(login|signin|logout|checkout|cart|account|search'
    r'|order|password|register|wishlist|compare)(/|$)',
    re.IGNORECASE,
)
_NAV_SKIP_LABELS = {"đọc tiếp", "xem thêm", "xem tất cả", "tài khoản", "gọi ngay", "chat"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_md_text(text: str) -> str:
    """Bỏ markdown link syntax, giữ lại text thuần."""
    return re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text).strip()


def _extract_contact(raw: str, base_url: str) -> dict[str, Any]:
    contact: dict[str, Any] = {}
    phones = _PHONE_RE.findall(raw)
    if phones:
        contact["phones"] = [p.strip() for p in phones]
    zalos = _ZALO_RE.findall(raw)
    if zalos:
        contact["zalo_ids"] = zalos
    emails = _EMAIL_RE.findall(raw)
    if emails:
        contact["emails"] = emails
    fb = _FB_RE.findall(raw)
    if fb:
        contact["facebook"] = [f"https://facebook.com/{h}" for h in fb]
    tiktok = _TIKTOK_RE.findall(raw)
    if tiktok:
        contact["tiktok"] = [f"https://tiktok.com/@{h}" for h in tiktok]
    ig = _INSTAGRAM_RE.findall(raw)
    if ig:
        contact["instagram"] = [f"https://instagram.com/{h}" for h in ig]
    addresses = _ADDRESS_RE.findall(raw)
    if addresses:
        contact["addresses"] = addresses[:3]
    hours = _HOURS_RE.findall(raw)
    if hours:
        contact["business_hours"] = list(set(hours))
    return contact


def _extract_nav_urls(raw: str, base_url: str) -> list[dict[str, str]]:
    domain = urlparse(base_url).netloc
    seen: set[str] = set()
    nav_urls: list[dict[str, str]] = []
    for label, href in _MD_LINK_RE.findall(raw):
        full = urljoin(base_url, href) if href.startswith("/") else href
        if urlparse(full).netloc != domain:
            continue
        if _NAV_SKIP_RE.search(full):
            continue
        if label.strip().lower() in _NAV_SKIP_LABELS:
            continue
        if full in seen:
            continue
        seen.add(full)
        nav_urls.append({"url": full, "label": label.strip()})
    return nav_urls


def _extract_brand_identity(raw: str, url: str) -> dict[str, Any]:
    identity: dict[str, Any] = {}
    m = _H1_RE.search(raw)
    if m:
        h1_raw = _clean_md_text(m.group(1))
        parts = re.split(r'\s[-–]\s', h1_raw, maxsplit=1)
        brand_name = parts[0].strip()
        if len(brand_name) > 60:
            short = re.split(r'[,.]', brand_name)[0].strip()
            brand_name = short if len(short) > 3 else brand_name[:60]
        identity["brand_name"] = brand_name
        if len(parts) > 1:
            identity["description"] = parts[1].strip()
    taglines = _TAGLINE_SAFE_RE.findall(raw)
    clean_taglines = []
    for t in taglines:
        cleaned = _clean_md_text(t).strip()
        if 20 < len(cleaned) < 300 and "](" not in cleaned:
            clean_taglines.append(cleaned)
    if clean_taglines:
        identity["taglines"] = clean_taglines[:3]
    return identity


def _extract_title(raw: str, url: str) -> str:
    m = _H1_RE.search(raw)
    if m:
        h1 = _clean_md_text(m.group(1))
        parts = re.split(r'\s[-–]\s', h1, maxsplit=1)
        title = parts[0].strip()
        if len(title) > 3:
            return title[:200]
    m = re.search(r"https?://(?:www\.)?([^/]+)", url)
    return m.group(1) if m else url[:200]


def _compose_brand_text(
    raw: str,
    contact: dict[str, Any],
    identity: dict[str, Any],
    nav_urls: list[dict[str, str]],
    url: str,
) -> str:
    sections: list[str] = []
    if identity.get("brand_name"):
        sections.append(f"Tên thương hiệu: {identity['brand_name']}")
    if identity.get("description"):
        sections.append(f"Mô tả: {identity['description']}")
    if identity.get("taglines"):
        sections.append("Slogan: " + " | ".join(identity["taglines"]))
    if contact.get("phones"):
        sections.append("Điện thoại: " + ", ".join(contact["phones"]))
    if contact.get("zalo_ids"):
        sections.append("Zalo: " + ", ".join(contact["zalo_ids"]))
    if contact.get("emails"):
        sections.append("Email: " + ", ".join(contact["emails"]))
    if contact.get("addresses"):
        sections.append("Địa chỉ: " + " | ".join(contact["addresses"]))
    if contact.get("business_hours"):
        sections.append("Giờ làm việc: " + ", ".join(contact["business_hours"]))
    if contact.get("facebook"):
        sections.append("Facebook: " + ", ".join(contact["facebook"]))
    if contact.get("tiktok"):
        sections.append("TikTok: " + ", ".join(contact["tiktok"]))
    if contact.get("instagram"):
        sections.append("Instagram: " + ", ".join(contact["instagram"]))
    if nav_urls:
        collections = [n for n in nav_urls if "/collections/" in n["url"]]
        blogs       = [n for n in nav_urls if "/blogs/" in n["url"] and "tin-tuc" not in n["url"]]
        posts       = [n for n in nav_urls if "/blogs/tin-tuc" in n["url"]]
        others      = [n for n in nav_urls if n not in collections + blogs + posts]
        if collections:
            sections.append("Danh mục sản phẩm:\n" + "\n".join(
                f"- {n['label']}: {n['url']}" for n in collections
            ))
        if blogs:
            sections.append("Chuyên mục blog:\n" + "\n".join(
                f"- {n['label']}: {n['url']}" for n in blogs
            ))
        if posts:
            sections.append("Bài viết nổi bật:\n" + "\n".join(
                f"- {n['label']}: {n['url']}" for n in posts[:5]
            ))
        if others:
            sections.append("Trang khác:\n" + "\n".join(
                f"- {n['label']}: {n['url']}" for n in others
            ))
    sections.append(f"Website: {url}")
    return "\n\n".join(sections)


# ── BusinessCrawler ───────────────────────────────────────────────────────────

class BusinessCrawler:
    """
    Crawl homepage brand:
    1. Parse header → nav URLs (sitemap thực tế)
    2. Parse footer → contact (phone, zalo, email, address, social)
    3. Parse body  → brand identity (name, description, tagline)
    4. Compose structured text → ingest RAG
    5. Lưu DocumentPage với extracted đầy đủ
    """

    def __init__(self, rag: RAG, loader: DocumentLoader, db: AsyncSession) -> None:
        self._rag    = rag
        self._loader = loader
        self._db     = db

    async def crawl_business(
        self,
        url: str,
        document_type: str,
        document_id: int,
    ) -> int:
        # 1. Crawl raw markdown
        loaded = self._loader.load_web(url, document_type=document_type)
        raw    = loaded.text

        # 2. Khai thác toàn bộ
        contact    = _extract_contact(raw, url)
        identity   = _extract_brand_identity(raw, url)
        nav_urls   = _extract_nav_urls(raw, url)
        title      = _extract_title(raw, url)
        brand_text = _compose_brand_text(raw, contact, identity, nav_urls, url)

        if not brand_text.strip():
            log.warning("[BusinessCrawler] Không khai thác được nội dung: %s", url)
            return 0

        # 3. Ingest vào RAG
        await self._rag.add(brand_text, **loaded.metadata)

        # 4. Lưu DocumentPage
        page = DocumentPage(
            document_id=document_id,
            url=url,
            title=title,
            content=brand_text,
            extracted={
                "source_url": url,
                "word_count": len(brand_text.split()),
                "contact":    contact,
                "identity":   identity,
                "nav_urls":   nav_urls[:30],
            },
        )
        self._db.add(page)
        await self._db.commit()
        await self._db.refresh(page)

        log.info(
            "[BusinessCrawler] page_id=%d title=%r contact=%s nav=%d words=%d",
            page.id, title, list(contact.keys()),
            len(nav_urls), len(brand_text.split()),
        )
        return 1