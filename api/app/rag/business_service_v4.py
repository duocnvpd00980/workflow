from __future__ import annotations

import logging
import re
from typing import Any, Optional
from urllib.parse import urljoin, urlparse
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.loader import DocumentLoader
from app.rag.models import DocumentPage
from app.rag.service import RAG

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("business_crawler_v5")


# ═══════════════════════════════════════════════════════════════════════════════
# I. PYDANTIC SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class BrandIdentity(BaseModel):
    brand_name: Optional[str] = None
    description: Optional[str] = None
    taglines: list[str] = Field(default_factory=list)
    mission: Optional[str] = None
    vision: Optional[str] = None
    story: Optional[str] = None
    tone_keywords: list[str] = Field(default_factory=list)
    main_products: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    partners: list[str] = Field(default_factory=list)


class VisualIdentity(BaseModel):
    logos: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)


class ContactDetails(BaseModel):
    phones: list[str] = Field(default_factory=list)
    addresses: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    business_hours: list[str] = Field(default_factory=list)
    social_links: dict[str, list[str]] = Field(default_factory=dict)
    ecommerce_links: list[str] = Field(default_factory=list)


class ExtractedData(BaseModel):
    source_url: str
    crawled_at: str
    brand_identity: BrandIdentity
    visual_identity: VisualIdentity
    contact_details: ContactDetails
    nav_urls: list[dict[str, str]] = Field(default_factory=list)
    rag_chunks: dict[str, str] = Field(default_factory=dict)
    chunk_quality: dict[str, str] = Field(default_factory=dict)
    raw_stats: dict[str, Any] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# II. REGEX ENGINE — V5 (Universal)
# ═══════════════════════════════════════════════════════════════════════════════

# ── 2.1 SĐT VIỆT NAM — V5 FIX ──
# BUG V4: (1) capturing group khiến findall trả về group thay vì full match
#          (2) pattern 4+3+3 vỡ với separator: '0901.234.567' → chỉ match 8 chars
# FIX V5: non-capturing groups + explicit 4-digit-prefix grouping
_PHONE_RE = re.compile(
    # Mobile 10 digits: 03x/05x/07x/08x/09x — flat + 4.3.3 (dot/space/dash)
    r'(?<!\d)(?:\+?84[\s.\-]?|0)(?:3[2-9]|5[689]|7[06-9]|8[1-689]|9[0-46-9])'
    r'(?:\d[\s.\-]\d{3}[\s.\-]\d{3}|\d{7}|\d{4}[\s.\-]\d{3}|\d{3}[\s.\-]\d{4})(?!\d)'
    # Landline 02x: 028.xxxx.xxxx (11 digits total)
    r'|\b02[1-9][\s.\-]?\d{4}[\s.\-]?\d{4}\b'
    # Hotline 1800/1900: 8 digits
    r'|\b1[89]00[\s.\-]?\d{4,6}\b',
    re.IGNORECASE,
)

# ── 2.2 Zalo OA — V5 FIX ──
# BUG V4: (1) chỉ match 15-16 digits, OA thật thường 18-19
#          (2) bỏ qua hoàn toàn data-oaid widget embed (dạng phổ biến nhất)
# FIX V5: bắt cả data-oaid attribute + URL, 15-19 digits
_ZALO_OA_RE = re.compile(
    r'data-oaid=["\'](\d{15,19})["\']'  # Widget embed: <div data-oaid="579745...">
    r'|zalo\.me/(\d{15,19})\b',          # URL-based OA ID
    re.IGNORECASE,
)

# Zalo link bằng SĐT (không phải OA): xử lý riêng
_ZALO_PHONE_LINK_RE = re.compile(r'zalo\.me/(0\d{9})\b', re.IGNORECASE)

# ── 2.3 Email ──
_EMAIL_RE = re.compile(r'([\w.\-+]+@[\w.\-]+\.\w{2,})', re.IGNORECASE)

# ── 2.4 Giờ mở cửa ──
_HOURS_RE = re.compile(
    r'(?:giờ\s*mở\s*cửa|giờ\s*làm\s*việc|mở\s*cửa|opening\s*hours|business\s*hours|thứ\s*[2-7]|t[2-7]\s*[-–])'
    r'[^\n:：]{0,30}[:\s：]+([^\n]{5,120})'
    r'|(\d{1,2}[h:]\d{0,2}\s*[-–]\s*\d{1,2}[h:]\d{0,2}(?:\s*(?:hàng ngày|all day|everyday|thứ\s*[2-7]|t[2-7])[^\n]{0,40})?)'
    r'|(\d{1,2}\s*giờ\s*[-–]\s*\d{1,2}\s*giờ)',
    re.IGNORECASE,
)

# ── 2.5 Logo — V5 FIX ──
# BUG V4: chỉ match HTML src/href/alt, không match markdown image syntax
# FIX V5: thêm markdown patterns + CDN URL patterns (universal, không chỉ Shopify)
_LOGO_RE = re.compile(
    # HTML: src="...logo..." or alt="...logo..." then src
    r'src=["\']([^"\'>\s]*(?:logo|brand|logotype)[^"\'>\s]*)["\']'
    r'|href=["\']([^"\'>\s]*(?:favicon|logo|brand)[^"\'>\s]*)["\']'
    r'|alt=["\']([^"\']*(?:logo|brand|site)[^"\']*)["\'][^>]*src=["\']([^"\'>\s]+)["\']'
    r'|class=["\'][^"\']*(?:logo|brand|site-logo|navbar-brand)[^"\']*["\'][^>]*src=["\']([^"\'>\s]+)["\']'
    # CDN patterns (Shopify, WooCommerce, custom CDN)
    r'|src=["\']([^"\'>\s]*cdn[^"\'>\s]*(?:logo|brand)[^"\'>\s]*)["\']'
    # Markdown: ![Logo text](url) — V5 NEW
    r'|!\[([^\]]*(?:logo|brand|site)[^\]]*)\]\(((?:https?:)?//[^\s)]+)\)'
    # Markdown: any image whose URL contains logo/brand — V5 NEW
    r'|!\[[^\]]*\]\(((?:https?:)?//[^\s)]*(?:logo|brand|logotype)[^\s)]*)\)'
    # Protocol-relative CDN image in markdown — V5 NEW
    r'|!\[[^\]]*\]\((//[^\s)]+\.(?:png|svg|webp|jpg)(?:\?[^\s)]*)?)\)',
    re.IGNORECASE,
)

# ── 2.6 Màu sắc — V5 ──
# NOTE: Tailwind classes bị strip bởi markdown loader → phải chạy trên HTML
# _extract_visual_identity nhận thêm html_source để xử lý đúng
_COLOR_RE = re.compile(
    # CSS inline: color: #xxx or background-color: #xxx
    r'(?:background(?:-color)?|color)\s*:\s*([#][0-9a-fA-F]{3,6}|rgb\(\d+,\s*\d+,\s*\d+\))'
    # CSS variable value
    r'|--[\w-]*(?:primary|brand|theme|main|accent|color)[^:：]*[:\s]+([#][0-9a-fA-F]{3,6})'
    # Tailwind arbitrary: bg-[#xxx]
    r'|\[([#][0-9a-fA-F]{3,6})\]'
    # Tailwind semantic classes (from HTML)
    r'|\b(bg|text|border)-(?:green|blue|orange|red|yellow|purple|pink|indigo|teal|cyan|emerald|lime|rose|amber|sky|violet)(?:-\d{2,3})?\b'
    # Named colors in CSS
    r'|(?:background-color|color)[:\s]+(green|blue|orange|red|yellow|brown|purple|pink|black|white|gray)\b',
    re.IGNORECASE,
)

# ── 2.7 Tone of Voice ──
_TONE_RE = re.compile(
    r'\b(chuyên nghiệp|tận tâm|uy tín|chất lượng|hàng đầu|giá rẻ|tiết kiệm|'
    r'sang trọng|đẳng cấp|thân thiện|gần gũi|trẻ trung|năng động|đáng tin cậy|'
    r'hiện đại|truyền thống|an toàn|bền vững|tiện lợi|nhanh chóng|'
    r'professional|trusted|reliable|quality|affordable|premium|innovative)\b',
    re.IGNORECASE,
)

# ── 2.8 Tagline — V5 FIX ──
# BUG V4: keyword list quá hẹp (chỉ VN agri keywords) → miss hero text phổ thông
# FIX V5: pass 1 keyword-based (high confidence) + pass 2 H2 structural fallback
_TAGLINE_KEYWORD_RE = re.compile(
    r'^(?![\s*•\-–\d])(?!.*https?://)(?!.*\]\().{10,80}'
    r'(?:nông nghiệp|phố|vườn|xanh|sạch|tươi|chất lượng|uy tín|hàng đầu|số 1|'
    r'tốt nhất|vì bạn|vì khách hàng|đồng hành|cùng bạn|mỗi ngày|tận tâm|'
    r'chuyên nghiệp|đẳng cấp|khác biệt|hoàn hảo|trọn vẹn|'
    r'giải pháp|công nghệ|dịch vụ|thương hiệu|tin tưởng|uy tín).{0,30}$',
    re.IGNORECASE | re.MULTILINE,
)

# ── 2.9 Chứng nhận ──
_CERT_RE = re.compile(
    r'(?:chứng\s*nhận|giải\s*thưởng|đạt\s*chuẩn|certified|award|được\s*công\s*nhận)[^\n:：]{0,20}[:\s：]+([^\n]{10,200})'
    r'|(?:ISO\s*\d{4,5}|HACCP|GMP|FDA|CE\s*Mark|Top\s*\d+\s*thương\s*hiệu|'
    r'Giải\s*(?:thưởng|nhất|nhì|ba|vàng|bạc|đồng)|OCOP\s*\d|VietGAP|GlobalGAP)[^\n]{0,100}',
    re.IGNORECASE,
)

# ── 2.10 Đối tác ──
_PARTNER_RE = re.compile(
    r'(?:đối\s*tác|khách\s*hàng\s*tiêu\s*biểu|partner|client|thương\s*hiệu\s*liên\s*kết)[^\n:：]{0,20}[:\s：]+([^\n]{20,300})',
    re.IGNORECASE,
)

# ── 2.11 Địa chỉ — Universal VN ──
# Pass 1: keyword-triggered (có "địa chỉ:", "văn phòng:", ...)
_ADDRESS_KEYWORD_RE = re.compile(
    r'(?:địa\s*chỉ|văn\s*phòng|chi\s*nhánh|cửa\s*hàng|showroom|kho\s*hàng|trụ\s*sở|office|store\s*address)[^\n:：]{0,20}[:\s：]+([^\n]{15,200})',
    re.IGNORECASE,
)
# Pass 2: structural — số nhà + đường/phố + quận/tỉnh (không cần keyword trigger)
_ADDRESS_STRUCTURAL_RE = re.compile(
    r'(?:số\s*)?\d+[^,\n]{0,60}'
    r'(?:đường|phố|ngõ|ngách|khu\s*phố|ấp|thôn|quốc\s*lộ|ql\.?|tỉnh\s*lộ|tl\.?)\s*[^\n,]{0,60}[,\s]+'
    r'(?:phường|xã|thị\s*trấn)\s*[^\n,]{0,40}[,\s]+'
    r'(?:quận|huyện|thị\s*xã|thành\s*phố|tp\.?|tỉnh)\s*[^\n,]{0,50}',
    re.IGNORECASE,
)

# ── 2.12 E-commerce ──
_ECOM_RE = re.compile(
    r'(shopee\.vn/[^\s\)\"\'>]+|lazada\.vn/[^\s\)\"\'>]+|tiki\.vn/[^\s\)\"\'>]+|'
    r'tiktok\.com/[^\s\)\"\'>]+/shop|sendo\.vn/[^\s\)\"\'>]+)',
    re.IGNORECASE,
)

# ── 2.13 Markdown & Navigation ──
_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_H2_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_H2_SHORT_RE = re.compile(r"^##\s+(.{10,70})$", re.MULTILINE)  # V5: tagline fallback
_MD_LINK_RE = re.compile(
    r'\[([^\]]+)\]\(((?:/[^\s\)\"]*|https?://[^\s\)\"]*))(?:\s+"[^"]*")?\)',
    re.IGNORECASE,
)

_SKIP_SCHEME_RE = re.compile(r'^(javascript|tel|mailto|zalo|sms|whatsapp):', re.IGNORECASE)


# ═══════════════════════════════════════════════════════════════════════════════
# III. SCORING TABLES — Universal (không chỉ Shopify)
# ═══════════════════════════════════════════════════════════════════════════════

_PATH_SCORES: list[tuple[int, re.Pattern[str]]] = [
    # Contact pages — highest priority
    (+35, re.compile(r'/(lien-he|contact|he-thong-cua-hang|stores|address|map|chi-nhanh|dia-chi|find-us|locations?)(/|$)', re.IGNORECASE)),
    # About/brand pages
    (+25, re.compile(r'/(about|gioi-thieu|brand|company|story|ve-chung-toi|about-us|who-we-are|introduce)(/|$)', re.IGNORECASE)),
    # Product/service pages
    (+10, re.compile(r'/(san-pham|dich-vu|products?|services?|solutions?|collections?)(/|$)', re.IGNORECASE)),
    # Blog — low value but crawlable
    (+2,  re.compile(r'/(blog|news|kinh-nghiem|articles?|tin-tuc|posts?)(/|$)', re.IGNORECASE)),
    # Blacklist — hard exclude
    (-20, re.compile(r'/(checkout|account|cart|search|login|sign-?in|register|wishlist|'
                     r'gio-hang|don-hang|thanh-toan|my-account|forgot-password|reset)(/|$)', re.IGNORECASE)),
]

_LABEL_SCORES: list[tuple[int, re.Pattern[str]]] = [
    (+20, re.compile(r'liên\s*hệ|contact|địa\s*chỉ|cửa\s*hàng|hotline|chi\s*nhánh|find\s*us|locate\s*us', re.IGNORECASE)),
    (+15, re.compile(r'giới\s*thiệu|về\s*chúng\s*tôi|câu\s*chuyện|about\s*us|thương\s*hiệu|our\s*story', re.IGNORECASE)),
    (+5,  re.compile(r'sản\s*phẩm|dịch\s*vụ|products?|services?|collections?', re.IGNORECASE)),
]

_MIN_SCORE = 5   # V5: tăng từ 1 → 5 để lọc blog spam
_BLACKLIST_SCORE = -100


# ═══════════════════════════════════════════════════════════════════════════════
# IV. CORE HELPER FUNCTIONS — V5
# ═══════════════════════════════════════════════════════════════════════════════

def _clean_md_text(text: str) -> str:
    """Strip markdown link syntax, keep label text."""
    return re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text).strip()


def _clean_url_from_text(text: str) -> str:
    """Remove URLs from extracted text."""
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'//\S+', '', text)
    text = re.sub(r'[")\]]+$', '', text)
    return text.strip()


def _score_url(href: str, label: str) -> int:
    if _SKIP_SCHEME_RE.match(href):
        return _BLACKLIST_SCORE
    score = 0
    for delta, pattern in _PATH_SCORES:
        if pattern.search(href):
            score += delta
    for delta, pattern in _LABEL_SCORES:
        if pattern.search(label):
            score += delta
    return score


def _validate_phone(phone: str) -> Optional[str]:
    """Validate Vietnamese phone number.
    
    V5 FIX: min digits từ 9 → 8 để support 1800xxxx (hotline 8 digits).
    """
    digits = re.sub(r'\D', '', phone)
    if len(digits) < 8 or len(digits) > 12:
        return None
    if len(set(digits)) <= 2:
        return None
    # Loại số rác: toàn 0 hoặc lặp lại
    if digits == digits[0] * len(digits):
        return None
    return phone.strip()


def _validate_zalo_oa(zalo_id: str) -> Optional[str]:
    """Validate Zalo OA ID.
    
    V5 FIX: range từ 15-16 → 15-19 digits (OA thật thường 18-19).
    """
    digits = re.sub(r'\D', '', zalo_id)
    if 15 <= len(digits) <= 19 and digits.isdigit():
        return digits
    return None


def _is_valid_address(text: str) -> bool:
    """Validate Vietnamese address — cần có số + (đường HOẶC quận)."""
    text_lower = text.lower()
    has_number = bool(re.search(r'\d+', text))
    has_street = any(k in text_lower for k in [
        "đường", "phố", "ngõ", "ngách", "khu phố", "ấp", "xã", "phường",
        "thôn", "quốc lộ", "ql.", "tỉnh lộ", "tl.", "street", "road", "ave",
    ])
    has_district = any(k in text_lower for k in [
        "quận", "huyện", "tp.", "thành phố", "tỉnh", "district", "province",
    ])
    return has_number and (has_street or has_district) and 10 < len(text) < 250


def _is_generic_product_label(label: str) -> bool:
    """Labels quá chung → skip khi extract main_products."""
    generic = [
        "sản phẩm bán chạy", "sản phẩm", "tất cả sản phẩm", "products",
        "best sellers", "new arrivals", "sale", "khuyến mãi", "all products",
        "bộ sưu tập", "collections", "danh mục", "categories", "featured",
        "nổi bật", "mới nhất", "hot", "trending",
    ]
    label_lower = label.lower().strip()
    return any(g == label_lower or label_lower.startswith(g) for g in generic)


def _detect_platform(homepage_raw: str, homepage_html: Optional[str]) -> str:
    """Detect website platform để tune extraction strategy."""
    source = homepage_html or homepage_raw
    if "cdn.shopify.com" in source or "shopify" in source.lower():
        return "shopify"
    if "wp-content" in source or "wordpress" in source.lower():
        return "wordpress"
    if "woocommerce" in source.lower():
        return "woocommerce"
    if "webflow" in source.lower():
        return "webflow"
    if "haravan" in source.lower():
        return "haravan"
    if "sapo" in source.lower():
        return "sapo"
    return "generic"


def _discover_brand_urls(
    raw: str,
    base_url: str,
    top_n: int = 10,
    platform: str = "generic",
) -> tuple[list[str], list[str]]:
    """Discover internal brand URLs + social links.
    
    V5: top_n tăng 8 → 10, platform-aware path detection.
    """
    domain = urlparse(base_url).netloc
    scored: dict[str, int] = {}
    social_links: set[str] = set()

    candidates: list[tuple[str, str]] = []
    candidates.extend(_MD_LINK_RE.findall(raw))

    for href in re.compile(r'href=["\']([^"\'>\s]+)["\']', re.IGNORECASE).findall(raw):
        candidates.append(("", href))

    # Social links từ class attributes
    for match in re.compile(
        r'<a[^>]*class=["\'][^"\']*(?:social|facebook|zalo|tiktok|youtube|instagram)[^"\']*["\'][^>]*href=["\']([^"\']+)["\']',
        re.IGNORECASE,
    ).findall(raw):
        candidates.append(("social", match))

    for label, href in candidates:
        href = href.strip()
        if not href or _SKIP_SCHEME_RE.match(href):
            continue
        full = (
            urljoin(base_url, href)
            if href.startswith(("/?", "./", "../", "/")) or not href.startswith("http")
            else href
        )
        parsed = urlparse(full)

        if parsed.netloc != domain:
            if any(soc in parsed.netloc for soc in [
                "facebook.com", "fb.com", "zalo.me", "tiktok.com",
                "youtube.com", "instagram.com", "linkedin.com", "twitter.com", "x.com",
            ]):
                social_links.add(full)
            continue

        if full.rstrip("/") == base_url.rstrip("/"):
            continue

        s = _score_url(full, label)
        if s >= _MIN_SCORE:
            if full not in scored or scored[full] < s:
                scored[full] = s

    qualified = [url for url, _ in sorted(scored.items(), key=lambda x: x[1], reverse=True)]
    return qualified[:top_n], list(social_links)[:8]


def _extract_contact(
    raw: str,
    html: Optional[str],
    base_url: str,
    nav_urls: list[dict[str, str]],
) -> ContactDetails:
    """Extract contact details.
    
    V5: phones fix (full match), zalo fix (data-oaid + 15-19 digits),
        address dual-pass, html fallback.
    """
    contact = ContactDetails()
    # Chạy trên cả raw + html nếu có (tránh mất data khi markdown strip)
    sources = [raw]
    if html:
        sources.append(html)
    full_source = "\n\n".join(sources)

    # 1. SĐT — V5: _PHONE_RE trả về full match (non-capturing groups)
    phones_found: list[str] = []
    for p in _PHONE_RE.findall(full_source):
        validated = _validate_phone(p)
        if validated:
            phones_found.append(validated)

    # Zalo phone-link: zalo.me/0901234567
    for p in _ZALO_PHONE_LINK_RE.findall(full_source):
        validated = _validate_phone(p)
        if validated and validated not in phones_found:
            phones_found.append(validated)

    if phones_found:
        contact.phones = list(dict.fromkeys(phones_found))

    # 2. Zalo OA — V5: data-oaid + URL + 15-19 digits
    zalo_ids = _ZALO_OA_RE.findall(full_source)
    for match in zalo_ids:
        # findall trả về tuple (group1, group2) vì có 2 capturing groups
        zid = next((x for x in match if x), None) if isinstance(match, tuple) else match
        if zid:
            validated = _validate_zalo_oa(zid)
            if validated:
                zalo_url = f"https://zalo.me/{validated}"
                contact.social_links.setdefault("zalo", []).append(zalo_url)

    # 3. Địa chỉ — V5: dual-pass (keyword + structural)
    addresses_found: list[str] = []

    # Pass 1: keyword-triggered
    for match in _ADDRESS_KEYWORD_RE.findall(full_source):
        addr_text = match if isinstance(match, str) else next((x for x in match if x), "")
        if addr_text:
            clean = _clean_md_text(_clean_url_from_text(addr_text))
            if _is_valid_address(clean):
                addresses_found.append(clean)

    # Pass 2: structural (không cần keyword, tìm pattern địa chỉ VN chuẩn)
    for match in _ADDRESS_STRUCTURAL_RE.findall(full_source):
        addr_text = match if isinstance(match, str) else next((x for x in match if x), "")
        if addr_text:
            clean = _clean_md_text(_clean_url_from_text(addr_text))
            if _is_valid_address(clean) and clean not in addresses_found:
                addresses_found.append(clean)

    if addresses_found:
        contact.addresses = list(dict.fromkeys(addresses_found))[:10]

    # 4. Email
    emails = _EMAIL_RE.findall(full_source)
    if emails:
        contact.emails = list(dict.fromkeys([
            e.strip() for e in emails
            if not any(x in e.lower() for x in [
                ".png", ".gif", ".jpg", ".jpeg", ".svg",
                "example.com", "test.com", "noreply", "no-reply",
                "domain.com", "youremail",
            ])
        ]))[:5]

    # 5. Giờ mở cửa
    hours_raw = _HOURS_RE.findall(full_source)
    if hours_raw:
        clean_hours = []
        for h in hours_raw:
            hour_str = next((x for x in h if x), None) if isinstance(h, tuple) else h
            if hour_str and len(hour_str.strip()) > 3:
                clean_hours.append(_clean_md_text(hour_str.strip()))
        if clean_hours:
            contact.business_hours = list(dict.fromkeys(clean_hours))[:4]

    # 6. Facebook
    fbs = re.compile(r'(?:https?://)?(?:www\.)?facebook\.com/(?!sharer|share|dialog|login|events|groups|photo|video)([a-zA-Z0-9._\-]{3,})', re.IGNORECASE).findall(full_source)
    if fbs:
        cleaned_fbs = [f"https://facebook.com/{f.strip('/')}" for f in fbs]
        contact.social_links["facebook"] = list(dict.fromkeys(cleaned_fbs))[:3]

    # 7. TikTok
    tiktoks = re.compile(r'tiktok\.com/@[a-zA-Z0-9._\-]+', re.IGNORECASE).findall(full_source)
    if tiktoks:
        cleaned = [f"https://{t}" if not t.startswith("http") else t for t in tiktoks]
        contact.social_links["tiktok"] = list(dict.fromkeys(cleaned))[:2]

    # 8. YouTube
    youtubes = re.compile(r'youtube\.com/(?:channel/|c/|@)[a-zA-Z0-9._\-]+', re.IGNORECASE).findall(full_source)
    if youtubes:
        cleaned = [f"https://{y}" if not y.startswith("http") else y for y in youtubes]
        contact.social_links["youtube"] = list(dict.fromkeys(cleaned))[:2]

    # 9. Instagram
    instagrams = re.compile(r'instagram\.com/[a-zA-Z0-9._\-]+', re.IGNORECASE).findall(full_source)
    if instagrams:
        cleaned = [f"https://{i}" if not i.startswith("http") else i for i in instagrams]
        contact.social_links["instagram"] = list(dict.fromkeys(cleaned))[:2]

    # 10. E-commerce
    ecoms = _ECOM_RE.findall(full_source)
    if ecoms:
        contact.ecommerce_links = list(dict.fromkeys([
            f"https://{e}" if not e.startswith("http") else e for e in ecoms
        ]))

    return contact


def _extract_nav_urls(raw: str, base_url: str) -> list[dict[str, str]]:
    """Extract navigation URLs from markdown.
    
    V5: _MIN_SCORE tăng lên 5 nên blog spam bị filter tự động.
    """
    domain = urlparse(base_url).netloc
    seen: set[str] = set()
    nav_urls: list[dict[str, str]] = []

    for label, href in _MD_LINK_RE.findall(raw):
        full = (
            urljoin(base_url, href)
            if href.startswith(("/?", "./", "../", "/")) or not href.startswith("http")
            else href
        )
        if urlparse(full).netloc != domain or full in seen:
            continue
        if _score_url(full, label) < 0:
            continue
        seen.add(full)
        nav_urls.append({"url": full, "label": label.strip()})

    return nav_urls


def _extract_brand_identity(
    pages_for_db: list[dict[str, Any]],
    homepage_raw: str,
    homepage_html: Optional[str] = None,
    nav_urls: Optional[list[dict[str, str]]] = None,
    platform: str = "generic",
) -> BrandIdentity:
    """Extract brand identity.
    
    V5: tagline dual-pass, product extraction platform-aware.
    """
    pages_raw = [homepage_raw] + [p["raw"] for p in pages_for_db]
    full_text = "\n\n".join(pages_raw)
    source_for_meta = homepage_html if homepage_html is not None else homepage_raw

    identity = BrandIdentity()

    # ── 1. Brand Name ──
    brand_name: Optional[str] = None
    description: Optional[str] = None

    # H1 từ markdown
    m = _H1_RE.search(homepage_raw)
    if m:
        h1_raw = _clean_md_text(m.group(1))
        parts = re.split(r'\s*[-–|:,]\s*', h1_raw, maxsplit=1)
        brand_name = parts[0].strip()
        if len(parts) > 1:
            description = parts[1].strip()

    # Nếu H1 là generic → dùng og:site_name
    generic_h1 = {"trang chủ", "home", "welcome", "trang chu", "", "index"}
    if not brand_name or len(brand_name) < 2 or brand_name.lower() in generic_h1:
        site_name = re.search(
            r'<meta[^>]*(?:og:site_name|name=["\']application-name["\'])[^>]*content=["\']([^"\']{2,80})["\']',
            source_for_meta, re.IGNORECASE,
        )
        if site_name:
            brand_name = site_name.group(1).strip()

    # Fallback: <title>
    if not brand_name or len(brand_name) < 2:
        title_match = re.search(r'<title>([^<]{2,100})</title>', source_for_meta, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            brand_name = re.split(r'\s*[|\-–]\s*', title)[0].strip()

    # Description từ meta
    if not description or len(description) < 10:
        for meta_pattern in [
            r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']{20,400})["\']',
            r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']{20,400})["\']',
        ]:
            meta_desc = re.search(meta_pattern, source_for_meta, re.IGNORECASE)
            if meta_desc:
                desc = meta_desc.group(1).strip()
                if 20 < len(desc) < 400:
                    description = desc
                    break

    identity.brand_name = brand_name
    identity.description = description

    # ── 2. Tagline — V5: dual-pass ──
    taglines: list[str] = []

    # Pass 1: keyword-based (high confidence)
    kw_matches = _TAGLINE_KEYWORD_RE.findall(homepage_raw)
    for t in kw_matches:
        clean = _clean_md_text(_clean_url_from_text(t)).strip()
        if clean and not clean.startswith(('*', '-', '•', '–')):
            if 10 < len(clean) < 80 and clean not in {brand_name, description}:
                taglines.append(clean)

    # Pass 2: H2 structural fallback (nếu pass 1 empty)
    if not taglines:
        h2s = _H2_SHORT_RE.findall(homepage_raw)
        for h in h2s[:5]:
            clean = _clean_md_text(_clean_url_from_text(h)).strip()
            if (
                clean
                and not _is_generic_product_label(clean)
                and clean not in {brand_name, description}
                and 10 < len(clean) < 80
                and not re.match(r'^\d', clean)  # không bắt đầu bằng số
            ):
                taglines.append(clean)

    identity.taglines = list(dict.fromkeys(taglines))[:3]

    # ── 3. Mission / Vision / Story ──
    _MISSION_RE = re.compile(
        r'(?:sứ\s*mệnh|mission|mục\s*tiêu\s*của\s*chúng\s*tôi)[^\n:：]{0,30}[:\s：]+([^\n]{30,500})',
        re.IGNORECASE,
    )
    _VISION_RE = re.compile(
        r'(?:tầm\s*nhìn|vision|định\s*hướng\s*phát\s*triển)[^\n:：]{0,30}[:\s：]+([^\n]{30,500})',
        re.IGNORECASE,
    )
    _STORY_RE = re.compile(
        r'(?:câu\s*chuyện|thành\s*lập|lịch\s*sử|hành\s*trình|story|founded?|established?|since\s*\d{4})[^\n:：]{0,30}[:\s：]*((?:[^\n]+\n?){1,10})',
        re.IGNORECASE,
    )

    m = _MISSION_RE.search(full_text)
    if m:
        identity.mission = _clean_md_text(m.group(1)).strip()

    m = _VISION_RE.search(full_text)
    if m:
        identity.vision = _clean_md_text(m.group(1)).strip()

    m = _STORY_RE.search(full_text)
    if m:
        identity.story = _clean_md_text(m.group(1)).strip()[:500]

    # ── 4. Tone of Voice ──
    tones = _TONE_RE.findall(full_text)
    if tones:
        identity.tone_keywords = list(dict.fromkeys([t.lower() for t in tones]))[:8]

    # ── 5. Main Products — V5: platform-aware URL patterns ──
    if nav_urls:
        # Product URL patterns by platform
        product_url_patterns = [
            "/collections/",   # Shopify
            "/products/",      # Shopify, generic
            "/san-pham/",      # Generic VN
            "/dich-vu/",       # Service businesses
            "/danh-muc/",      # Generic VN category
            "/category/",      # WordPress/WooCommerce
            "/categories/",
            "/product-category/",  # WooCommerce
            "?cat=",           # WordPress
        ]

        products_from_nav = []
        for nav in nav_urls:
            label = nav["label"].strip()
            href = nav["url"].lower()

            is_product_url = any(pk in href for pk in product_url_patterns)
            is_not_generic = not _is_generic_product_label(label)

            if is_product_url and is_not_generic:
                clean_label = _clean_md_text(label)
                if 2 < len(clean_label) < 60:
                    products_from_nav.append(clean_label)

        # Fallback: extract từ text nếu nav không có
        if not products_from_nav:
            _PRODUCT_SECTION_RE = re.compile(
                r'(?:sản\s*phẩm\s*(?:chính|của\s*chúng\s*tôi|nổi\s*bật)|'
                r'products?\s*(?:we\s*offer|overview)|dịch\s*vụ\s*(?:của|chúng\s*tôi))'
                r'[^\n]{0,50}\n((?:[^\n]+\n?){3,15})',
                re.IGNORECASE,
            )
            m = _PRODUCT_SECTION_RE.search(full_text)
            if m:
                lines = [
                    _clean_md_text(l.strip().lstrip('*-•–123456789. '))
                    for l in m.group(1).splitlines()
                    if l.strip() and len(l.strip()) > 3
                ]
                products_from_nav = [l for l in lines if not _is_generic_product_label(l)][:8]

        if products_from_nav:
            identity.main_products = list(dict.fromkeys(products_from_nav))[:8]

    # ── 6. Certifications ──
    cert_sections = re.split(
        r'(?:chứng\s*nhận|giải\s*thưởng|đối\s*tác|thành\s*tích)',
        full_text, flags=re.IGNORECASE,
    )[-2:]
    cert_text = "\n".join(cert_sections)
    certs = _CERT_RE.findall(cert_text)
    if certs:
        clean_certs = []
        for c in certs:
            if isinstance(c, tuple):
                c = next((x for x in c if x), "")
            if c and len(c.strip()) > 5:
                clean_c = _clean_md_text(_clean_url_from_text(c)).strip()
                if 10 < len(clean_c) < 200 and "blog" not in clean_c.lower():
                    clean_certs.append(clean_c)
        identity.certifications = list(dict.fromkeys(clean_certs))[:5]

    # ── 7. Partners ──
    partner_sections = re.split(
        r'(?:đối\s*tác|khách\s*hàng\s*tiêu\s*biểu|partner)',
        full_text, flags=re.IGNORECASE,
    )[-2:]
    partner_text = "\n".join(partner_sections)
    partners = _PARTNER_RE.findall(partner_text)
    if partners:
        clean_partners = []
        for p in partners:
            if isinstance(p, tuple):
                p = next((x for x in p if x), "")
            if p and len(p.strip()) > 3:
                clean_p = _clean_md_text(_clean_url_from_text(p)).strip()
                if len(clean_p) > 3:
                    clean_partners.append(clean_p)
        identity.partners = list(dict.fromkeys(clean_partners))[:10]

    return identity


def _extract_visual_identity(
    source: str,
    html_source: Optional[str] = None,
) -> VisualIdentity:
    """Extract logos and colors.
    
    V5 FIX:
    - Logo: chạy trên cả HTML lẫn markdown (thêm markdown patterns vào _LOGO_RE)
    - Colors: ưu tiên HTML source (Tailwind bị strip trong markdown)
    """
    visual = VisualIdentity()

    # ── Logo: chạy trên HTML trước, rồi markdown ──
    logo_sources = []
    if html_source:
        logo_sources.append(html_source)
    logo_sources.append(source)

    detected_logos: list[str] = []
    seen_logos: set[str] = set()

    for logo_src in logo_sources:
        for match in _LOGO_RE.findall(logo_src):
            candidates = [match] if isinstance(match, str) else list(match)
            for group in candidates:
                if group and group.strip() and group not in seen_logos:
                    url_or_path = group.strip()
                    # Chỉ lấy URL thật, không lấy alt text
                    if (
                        url_or_path.startswith(("http", "/", "data:", "//"))
                        and "." in url_or_path.split("/")[-1]
                        and len(url_or_path) < 500
                    ):
                        detected_logos.append(url_or_path)
                        seen_logos.add(url_or_path)

    visual.logos = detected_logos[:5]

    # ── Colors: ưu tiên HTML (Tailwind không tồn tại trong markdown) ──
    color_source = html_source if html_source else source
    detected_colors = _COLOR_RE.findall(color_source)
    if detected_colors:
        clean_colors: list[str] = []
        for c in detected_colors:
            val = next((x for x in c if x), None) if isinstance(c, tuple) else c
            if val and val.strip() and len(val.strip()) > 1:
                clean_colors.append(val.strip().lower())
        visual.colors = list(dict.fromkeys(clean_colors))[:8]

    return visual


# ═══════════════════════════════════════════════════════════════════════════════
# V. RAG CHUNKING — V5 với Granular Quality
# ═══════════════════════════════════════════════════════════════════════════════

def _compose_rag_chunks(
    identity: BrandIdentity,
    contact: ContactDetails,
    visual: VisualIdentity,
) -> tuple[dict[str, str], dict[str, str]]:
    chunks: dict[str, str] = {}
    quality: dict[str, str] = {}

    # ── Chunk 1: Brand Core ──
    core_lines = []
    if identity.brand_name:
        core_lines.append(f"Tên thương hiệu: {identity.brand_name}")
    if identity.description:
        core_lines.append(f"Lĩnh vực: {identity.description}")
    if identity.taglines:
        core_lines.append(f"Slogan: {' | '.join(identity.taglines)}")
    if identity.tone_keywords:
        core_lines.append(f"Giọng điệu: {', '.join(identity.tone_keywords)}")
    if identity.main_products:
        core_lines.append(f"Sản phẩm/dịch vụ chính:\n- " + "\n- ".join(identity.main_products))

    chunks["brand_core"] = "\n".join(core_lines)
    has_name = bool(identity.brand_name)
    has_desc = bool(identity.description)
    has_products = bool(identity.main_products)
    if has_name and has_desc and has_products:
        quality["brand_core"] = "very_high"
    elif has_name and has_desc:
        quality["brand_core"] = "high"
    elif has_name:
        quality["brand_core"] = "medium"
    else:
        quality["brand_core"] = "low"

    # ── Chunk 2: Story & Values ──
    story_lines = []
    if identity.mission:
        story_lines.append(f"Sứ mệnh: {identity.mission}")
    if identity.vision:
        story_lines.append(f"Tầm nhìn: {identity.vision}")
    if identity.story:
        story_lines.append(f"Câu chuyện: {identity.story}")
    if identity.certifications:
        story_lines.append(f"Chứng nhận: {', '.join(identity.certifications)}")
    if identity.partners:
        story_lines.append(f"Đối tác: {', '.join(identity.partners[:5])}")

    chunks["brand_story"] = "\n".join(story_lines)
    has_story = any([identity.mission, identity.vision, identity.story])
    has_social_proof = bool(identity.certifications or identity.partners)
    if has_story and has_social_proof:
        quality["brand_story"] = "high"
    elif has_story:
        quality["brand_story"] = "medium"
    else:
        quality["brand_story"] = "low"

    # ── Chunk 3: Visual ──
    visual_lines = []
    if visual.logos:
        visual_lines.append(f"Logo: {', '.join(visual.logos[:3])}")
    if visual.colors:
        visual_lines.append(f"Màu sắc nhận diện: {', '.join(visual.colors)}")

    chunks["brand_visual"] = "\n".join(visual_lines)
    quality["brand_visual"] = "high" if visual.logos else ("medium" if visual.colors else "low")

    # ── Chunk 4: Contact & CTA ──
    cta_lines = []
    if contact.phones:
        cta_lines.append(f"Hotline/SĐT: {', '.join(contact.phones[:4])}")
    if contact.business_hours:
        cta_lines.append(f"Giờ mở cửa: {' | '.join(contact.business_hours)}")
    if contact.addresses:
        cta_lines.append(
            f"Địa chỉ ({len(contact.addresses)} chi nhánh):\n- " + "\n- ".join(contact.addresses[:5])
        )
    if contact.emails:
        cta_lines.append(f"Email: {', '.join(contact.emails[:2])}")
    if contact.ecommerce_links:
        cta_lines.append(f"Mua online: {' | '.join(contact.ecommerce_links[:3])}")

    chunks["contact_cta"] = "\n".join(cta_lines)
    has_phone = bool(contact.phones)
    has_address = bool(contact.addresses)
    if has_phone and has_address:
        quality["contact_cta"] = "high"
    elif has_phone or has_address:
        quality["contact_cta"] = "medium"
    else:
        quality["contact_cta"] = "low"

    # ── Chunk 5: Social ──
    social_lines = []
    for platform, links in contact.social_links.items():
        if links:
            social_lines.append(f"{platform.capitalize()}: {', '.join(links[:2])}")

    chunks["social_channels"] = "\n".join(social_lines)
    platform_count = len(contact.social_links)
    if platform_count >= 3:
        quality["social_channels"] = "high"
    elif platform_count >= 1:
        quality["social_channels"] = "medium"
    else:
        quality["social_channels"] = "low"

    return chunks, quality


# ═══════════════════════════════════════════════════════════════════════════════
# VI. BUSINESS CRAWLER SERVICE — V5
# ═══════════════════════════════════════════════════════════════════════════════

# Fallback paths phổ biến — platform-agnostic, bao phủ rộng
_FALLBACK_PATHS = [
    # Contact (highest value)
    "/lien-he", "/contact", "/contact-us", "/contacts",
    "/pages/lien-he", "/pages/contact", "/pages/contact-us",  # Shopify
    "/dia-chi", "/he-thong-cua-hang", "/chi-nhanh", "/stores", "/locations",
    # About
    "/about", "/about-us", "/gioi-thieu", "/ve-chung-toi",
    "/pages/about", "/pages/gioi-thieu",                       # Shopify
    "/introduce", "/company", "/our-story",
    # Products/Services
    "/san-pham", "/products", "/dich-vu", "/services",
    "/collections", "/shop",                                    # Shopify/WooCommerce
    "/danh-muc", "/categories",
]

_RETRY_MAX = 3


class BusinessCrawler:
    def __init__(self, rag: RAG, loader: DocumentLoader, db: AsyncSession) -> None:
        self._rag = rag
        self._loader = loader
        self._db = db

    async def crawl_business(self, url: str, document_type: str, document_id: int) -> int:
        log.info("[BusinessCrawlerV5] Bắt đầu crawl: %s", url)

        # ── 1. Load homepage ──
        homepage = await self._load_with_retry(url, document_type)
        if not homepage:
            log.error("[BusinessCrawlerV5] Không thể load homepage: %s", url)
            return 0

        homepage_raw, homepage_html = self._normalize_loader_result(homepage)

        if len(homepage_raw.strip()) < 200:
            log.warning(
                "[BusinessCrawlerV5] Homepage quá ít text (%d chars). "
                "Có thể JS-rendered — cần Playwright/Selenium.",
                len(homepage_raw.strip()),
            )

        # ── 2. Detect platform ──
        platform = _detect_platform(homepage_raw, homepage_html)
        log.info("[BusinessCrawlerV5] Platform detected: %s", platform)

        # ── 3. Extract nav URLs ──
        nav_urls = _extract_nav_urls(homepage_raw, url)
        log.info("[BusinessCrawlerV5] Nav URLs: %d", len(nav_urls))

        # ── 4. Discover brand URLs ──
        discovered_internal, social_links = _discover_brand_urls(
            homepage_raw, url, top_n=10, platform=platform,
        )

        brand_urls: list[str] = [url]
        for b_url in discovered_internal:
            if b_url.rstrip("/") != url.rstrip("/"):
                brand_urls.append(b_url)

        # Nếu chưa có đủ pages → thêm fallback paths
        if len(brand_urls) <= 2:
            base = url.rstrip("/")
            for path in _FALLBACK_PATHS:
                candidate = base + path
                if candidate not in brand_urls:
                    brand_urls.append(candidate)

        log.info("[BusinessCrawlerV5] Tổng %d brand URLs sẽ crawl", len(brand_urls))

        # ── 5. Crawl sub-pages ──
        pages_for_db: list[dict[str, Any]] = []
        base_domain = urlparse(url).netloc

        for brand_url in brand_urls[1:]:
            if urlparse(brand_url).netloc != base_domain:
                log.debug("[BusinessCrawlerV5] Skip ngoài domain: %s", brand_url)
                continue

            loaded = await self._load_with_retry(brand_url, document_type)
            if loaded:
                raw, _ = self._normalize_loader_result(loaded)
                char_count = len(raw.strip())
                if char_count > 100:
                    pages_for_db.append({"url": brand_url, "raw": raw})
                    log.info("[BusinessCrawlerV5] ✓ %s (%d chars)", brand_url, char_count)
                else:
                    log.warning("[BusinessCrawlerV5] Trang rỗng/404: %s (%d chars)", brand_url, char_count)
            else:
                log.warning("[BusinessCrawlerV5] Load failed: %s", brand_url)

        log.info(
            "[BusinessCrawlerV5] Crawl xong: %d/%d subpages thành công",
            len(pages_for_db), len(brand_urls) - 1,
        )

        # ── 6. Extract data ──
        aggregated_raw = homepage_raw + "\n\n" + "\n\n".join([p["raw"] for p in pages_for_db])

        identity = _extract_brand_identity(
            pages_for_db, homepage_raw, homepage_html,
            nav_urls=nav_urls, platform=platform,
        )
        # V5: truyền html_source vào visual extraction
        visual = _extract_visual_identity(homepage_html or homepage_raw, html_source=homepage_html)
        # V5: truyền html vào contact extraction (tránh mất data khi markdown strip)
        contact = _extract_contact(aggregated_raw, homepage_html, url, nav_urls)

        # Merge social links từ discovery
        for link in social_links:
            parsed_link = urlparse(link)
            if "facebook.com" in parsed_link.netloc:
                contact.social_links.setdefault("facebook", []).append(link)
            elif "zalo.me" in parsed_link.netloc:
                zid_match = re.search(r'zalo\.me/(\d{15,19})\b', link)
                if zid_match and _validate_zalo_oa(zid_match.group(1)):
                    contact.social_links.setdefault("zalo", []).append(link)
            elif "tiktok.com" in parsed_link.netloc:
                contact.social_links.setdefault("tiktok", []).append(link)
            elif "youtube.com" in parsed_link.netloc:
                contact.social_links.setdefault("youtube", []).append(link)
            elif "instagram.com" in parsed_link.netloc:
                contact.social_links.setdefault("instagram", []).append(link)

        # Deduplicate social links
        for platform_key in contact.social_links:
            contact.social_links[platform_key] = list(dict.fromkeys(
                contact.social_links[platform_key]
            ))[:3]

        # ── 7. Compose RAG chunks ──
        rag_chunks, chunk_quality = _compose_rag_chunks(identity, contact, visual)
        full_rag_text = "\n\n".join([
            f"=== {k.upper().replace('_', ' ')} ===\n{v}"
            for k, v in rag_chunks.items() if v.strip()
        ])

        if not full_rag_text.strip():
            full_rag_text = f"Tên thương hiệu: {identity.brand_name or url}\nURL nguồn: {url}"

        # ── 8. Save to Vector DB ──
        for chunk_name, chunk_text in rag_chunks.items():
            if chunk_text.strip():
                metadata = {
                    "chunk_type": chunk_name,
                    "brand_name": identity.brand_name,
                    "source_url": url,
                    "document_id": document_id,
                    "quality": chunk_quality.get(chunk_name, "unknown"),
                    "platform": platform,
                }
                await self._rag.add(chunk_text, **metadata)

        # ── 9. Save to PostgreSQL ──
        extracted_data = ExtractedData(
            source_url=url,
            crawled_at=datetime.utcnow().isoformat(),
            brand_identity=identity,
            visual_identity=visual,
            contact_details=contact,
            nav_urls=nav_urls,
            rag_chunks=rag_chunks,
            chunk_quality=chunk_quality,
            raw_stats={
                "pages_crawled": len(pages_for_db) + 1,
                "total_chars": len(aggregated_raw),
                "homepage_chars": len(homepage_raw),
                "subpage_count": len(pages_for_db),
                "platform": platform,
                "has_html": homepage_html is not None,
            },
        )

        combined_content = homepage_raw + "\n\n---\n\n" + "\n\n---\n\n".join(
            f"[{p['url']}]\n{p['raw']}" for p in pages_for_db
        )

        page = DocumentPage(
            document_id=document_id,
            url=url,
            title=identity.brand_name or url,
            content=combined_content,
            extracted=extracted_data.model_dump(mode="json"),
        )

        self._db.add(page)
        await self._db.commit()
        await self._db.refresh(page)

        log.info(
            "[BusinessCrawlerV5] ✅ HOÀN THÀNH — page_id=%s brand=%r platform=%s quality=%s",
            page.id, identity.brand_name, platform, chunk_quality,
        )
        return 1

    async def _load_with_retry(self, url: str, document_type: str) -> Any:
        """Load URL với retry logic."""
        for attempt in range(_RETRY_MAX):
            try:
                return self._loader.load_web(url, document_type=document_type)
            except Exception as e:
                log.warning(
                    "[BusinessCrawlerV5] Retry %d/%d: %s — %s",
                    attempt + 1, _RETRY_MAX, url, e,
                )
                if attempt == _RETRY_MAX - 1:
                    return None
        return None

    def _normalize_loader_result(self, result: Any) -> tuple[str, Optional[str]]:
        """Normalize loader output → (markdown_text, html_or_None).
        
        Supports: str, dict{text, html}, object with .text/.raw_html attrs.
        """
        if isinstance(result, str):
            return result, None
        if isinstance(result, dict):
            return result.get("text", str(result)), result.get("html") or result.get("raw_html")
        raw = getattr(result, "text", str(result))
        html = getattr(result, "raw_html", getattr(result, "html", None))
        return raw, html