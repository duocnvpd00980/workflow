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
# II. REGEX ENGINE — V5 FIXES
# ═══════════════════════════════════════════════════════════════════════════════

# ── 2.1 SĐT VIỆT NAM ──
_PHONE_RE = re.compile(
    r'(?:\+?84[\s.]?|0)(3[2-9]|5[689]|7[06-9]|8[1-689]|9[0-46-9])[\s.]?\d{3}[\s.]?\d{3}'
    r'|\b1[89]00\d{4,6}\b'
    r'|\b02[1-9]\d{7,8}\b',
    re.IGNORECASE,
)

# Zalo OA — Anh Minh + Chị Ngọc: Bắt MỌI định dạng, strict validation
_ZALO_RE = re.compile(
    r'(?:https?://)?(?:www\.)?zalo\.me/(\d{10,20})',  # Bắt cả có/không protocol
    re.IGNORECASE,
)

# ── 2.2 Email ──
_EMAIL_RE = re.compile(r'([\w.-]+@[\w.-]+\.\w+)', re.IGNORECASE)

# ── 2.3 Giờ mở cửa ──
_HOURS_RE = re.compile(
    r'(?:giờ\s*mở\s*cửa|giờ\s*làm\s*việc|mở\s*cửa|opening\s*hours|business\s*hours)[^\n:：]{0,20}[:\s：]+([^\n]{5,100})'
    r'|(\d{1,2}[h:]\d{0,2}\s*[-–]\s*\d{1,2}[h:]\d{0,2})'
    r'|(\d{1,2}\s*giờ\s*[-–]\s*\d{1,2}\s*giờ)',
    re.IGNORECASE,
)

# ── 2.4 Logo — Anh Đức: Bắt cả Shopify CDN, alt text, header img
_LOGO_RE = re.compile(
    r'src=["\']([^"\'>\s]*(?:logo|brand)[^"\'>\s]*)["\']'
    r'|href=["\']([^"\'>\s]*(?:favicon|logo|brand)[^"\'>\s]*)["\']'
    r'|alt=["\']([^"\']*(?:logo|brand|site)[^"\']*)["\'][^>]*src=["\']([^"\'>\s]+)["\']'
    r'|class=["\'][^"\']*(?:logo|brand|site-logo|header__logo)[^"\']*["\'][^>]*src=["\']([^"\'>\s]+)["\']'
    r'|<img[^>]*src=["\']([^"\']+)["\'][^>]*alt=["\']([^"\']*(?:logo|brand|site|trang chủ)[^"\']*)["\']'
    r'|<header[^>]*>.*?<img[^>]*src=["\']([^"\'>\s]+)["\']'  # First img in header
    r'|(?<=!\[)[^\]]*(?=\]\(([^)]*(?:logo|brand)[^)]*)\))',
    re.IGNORECASE | re.DOTALL,
)

# ── 2.5 Màu sắc — Anh Đức: Bắt cả class generic + inline style
_COLOR_RE = re.compile(
    r'(?:background-color|color|bg-|text-)[:\s]*([#][0-9a-fA-F]{3,6}|green|blue|orange|red|yellow|brown|purple|pink)'
    r'|var\(--[\w-]*(?:primary|brand|theme|main|accent)[^)]*\):\s*([#][0-9a-fA-F]{3,6})'
    r'|\[([#][0-9a-fA-F]{3,6})\]'
    r'|\b(bg|text|border)-(green|blue|orange|red|yellow|purple|pink|indigo|teal|cyan|emerald|lime)(?:-\d{2,3})?\b'
    r'|style=["\'][^"\']*(?:color|background)[:\s]*([#][0-9a-fA-F]{3,6})[^"\']*["\']',
    re.IGNORECASE,
)

# ── 2.6 Tone of Voice ──
_TONE_RE = re.compile(
    r'\b(chuyên nghiệp|tận tâm|uy tín|chất lượng|hàng đầu|giá rẻ|tiết kiệm|'
    r'sang trọng|đẳng cấp|thân thiện|gần gũi|trẻ trung|năng động|đáng tin cậy|'
    r'hiện đại|truyền thống|an toàn|bền vững|tiện lợi|nhanh chóng)\b',
    re.IGNORECASE,
)

# ── 2.7 Tagline — Ms. Hương: Generic hơn, không yêu cầu từ khóa đặc biệt
_TAGLINE_RE = re.compile(
    r'^(?![\s*•\-–\d])(?!.*https?://)(?!.*\]\().{10,60}$',  # Câu ngắn, không list item
    re.MULTILINE,
)

# ── 2.8 Chứng nhận ──
_CERT_RE = re.compile(
    r'(?:chứng\s*nhận|giải\s*thưởng|đạt\s*chuẩn|certified|award|được\s*công\s*nhận)[^\n:：]{0,20}[:\s：]+([^\n]{10,200})'
    r'|(?:ISO\s*\d{4,5}|HACCP|GMP|FDA|CE\s*Mark|Top\s*\d+\s*thương\s*hiệu|'
    r'Giải\s*(?:thưởng|nhất|nhì|ba|vàng|bạc|đồng))[^\n]{0,100}',
    re.IGNORECASE,
)

# ── 2.9 Đối tác ──
_PARTNER_RE = re.compile(
    r'(?:đối\s*tác|khách\s*hàng\s*tiêu\s*biểu|partner|client|thương\s*hiệu\s*liên\s*kết)[^\n:：]{0,20}[:\s：]+([^\n]{20,300})',
    re.IGNORECASE,
)

# ── 2.10 Địa chỉ ──
_ADDRESS_RE = re.compile(
    r'(?:địa\s*chỉ|văn\s*phòng|chi\s*nhánh|cửa\s*hàng|showroom|kho\s*hàng|trụ\s*sở)[^\n:：]{0,15}[:\s：]+([^\n]{15,200})'
    r'|(?:số\s*\d+[^,]{0,50}(?:đường|phố|ngõ|ngách|khu\s*phố|ấp|xã|phường|thôn|quốc\s*lộ|ql\.?)[^,]{0,100}'
    r'(?:quận|huyện|thành\s*phố|tỉnh|tp\.?)[^,]{0,50})',
    re.IGNORECASE,
)

# ── 2.11 E-commerce ──
_ECOM_RE = re.compile(
    r'(shopee\.vn/[^\s\)\"\'>]+|lazada\.vn/[^\s\)\"\'>]+|tiki\.vn/[^\s\)\"\'>]+|'
    r'tiktok\.com/[^\s\)\"\'>]+/shop|sendo\.vn/[^\s\)\"\'>]+)',
    re.IGNORECASE,
)

# ── 2.12 Social links từ HTML — Chị Ngọc: Broader, bắt cả SVG icons
_SOCIAL_HTML_RE = re.compile(
    r'<a[^>]*href=["\']([^"\']*(?:facebook\.com|fb\.com|zalo\.me|tiktok\.com|'
    r'instagram\.com|youtube\.com|linkedin\.com)[^"\']*)["\']',
    re.IGNORECASE,
)

# ── 2.13 Markdown & Navigation ──
_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_MD_LINK_RE = re.compile(
    r'\[([^\]]+)\]\(((?:/[^\s\)\"]*|https?://[^\s\)\"]*))(?:\s+"[^"]*")?\)',
    re.IGNORECASE,
)

_SKIP_SCHEME_RE = re.compile(r'^(javascript|tel|mailto|zalo|sms|whatsapp):', re.IGNORECASE)


# ═══════════════════════════════════════════════════════════════════════════════
# III. SCORING TABLES
# ═══════════════════════════════════════════════════════════════════════════════

_PATH_SCORES: list[tuple[int, re.Pattern[str]]] = [
    (+50, re.compile(r'(lien-he|contact|he-thong-cua-hang|stores|address|map|chi-nhanh|cuahang)', re.IGNORECASE)),  # Ưu tiên tuyệt đối
    (+30, re.compile(r'(about|gioi-thieu|brand|company|story|ve-chung-toi)', re.IGNORECASE)),
    (+10, re.compile(r'(san-pham|dich-vu|products|services|solutions)', re.IGNORECASE)),
    (+2,  re.compile(r'/(blog|news|kinh-nghiem|articles?|tin-tuc)(/|$)', re.IGNORECASE)),
    (-20, re.compile(r'/(checkout|account|cart|search|login|sign-?in|register|wishlist|gio-hang|don-hang|thanh-toan)(/|$)', re.IGNORECASE)),
]

_LABEL_SCORES: list[tuple[int, re.Pattern[str]]] = [
    (+20, re.compile(r'liên\s*hệ|contact|địa\s*chỉ|cửa\s*hàng|hotline|chi\s*nhánh', re.IGNORECASE)),
    (+15, re.compile(r'giới\s*thiệu|về\s*chúng\s*tôi|câu\s*chuyện|about\s*us|thương\s*hiệu', re.IGNORECASE)),
    (+5,  re.compile(r'sản\s*phẩm|dịch\s*vụ|products|services', re.IGNORECASE)),
]

_MIN_SCORE = 1
_BLACKLIST_SCORE = -100


# ═══════════════════════════════════════════════════════════════════════════════
# IV. CORE HELPER FUNCTIONS — V5 FIXES
# ═══════════════════════════════════════════════════════════════════════════════

def _clean_md_text(text: str) -> str:
    return re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text).strip()


def _clean_url_from_text(text: str) -> str:
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
    digits = re.sub(r'\D', '', phone)
    if len(digits) < 9 or len(digits) > 11:
        return None
    if len(set(digits)) <= 2:
        return None
    return phone.strip()


def _validate_zalo_oa(zalo_id: str) -> Optional[str]:
    """Chị Ngọc — Zalo OA: 10-16 số, thường 15-16."""
    digits = re.sub(r'\D', '', zalo_id)
    if 10 <= len(digits) <= 16 and digits.isdigit():
        # Zalo OA thường không bắt đầu bằng 0
        if not digits.startswith('0'):
            return digits
        # Hoặc nếu bắt đầu bằng 0 thì phải là SĐT VN hợp lệ
        if len(digits) == 10 and digits.startswith('0'):
            return digits
    return None


def _is_valid_address(text: str) -> bool:
    text_lower = text.lower()
    has_number = bool(re.search(r'\d+', text))
    has_street = any(k in text_lower for k in ["đường", "phố", "ngõ", "ngách", "khu phố", "ấp", "xã", "phường", "thôn", "quốc lộ", "ql."])
    has_district = any(k in text_lower for k in ["quận", "huyện", "tp.", "thành phố", "tỉnh"])
    return has_number and (has_street or has_district) and 15 < len(text) < 200


def _is_generic_product_label(label: str) -> bool:
    generic = [
        "sản phẩm bán chạy", "sản phẩm", "tất cả sản phẩm", "products", 
        "best sellers", "new arrivals", "sale", "khuyến mãi", "all products",
        "bộ sưu tập", "collections", "danh mục", "categories", "shop all"
    ]
    return any(g in label.lower() for g in generic)


def _discover_brand_urls(raw: str, base_url: str, top_n: int = 8) -> tuple[list[str], list[str]]:
    domain = urlparse(base_url).netloc
    scored: dict[str, int] = {}
    social_links: set[str] = set()

    candidates: list[tuple[str, str]] = []
    candidates.extend(_MD_LINK_RE.findall(raw))
    
    for href in re.compile(r'href=["\']([^"\'>\s]+)["\']', re.IGNORECASE).findall(raw):
        candidates.append(("", href))

    for label, href in candidates:
        href = href.strip()
        if not href or _SKIP_SCHEME_RE.match(href):
            continue
        full = urljoin(base_url, href) if href.startswith(("/?", "./", "../")) or not href.startswith("http") else href
        parsed = urlparse(full)

        if parsed.netloc != domain:
            if any(soc in parsed.netloc for soc in ["facebook.com", "fb.com", "zalo.me", "tiktok.com", "youtube.com", "instagram.com", "linkedin.com"]):
                social_links.add(full)
            continue

        if full.rstrip("/") == base_url.rstrip("/"):
            continue

        s = _score_url(full, label)
        if s >= _MIN_SCORE:
            if full not in scored or scored[full] < s:
                scored[full] = s

    qualified = [url for url, s in sorted(scored.items(), key=lambda x: x[1], reverse=True)]
    return qualified[:top_n], list(social_links)[:5]


def _extract_social_from_html(html: str) -> dict[str, list[str]]:
    """Chị Ngọc — Bắt social links từ HTML gốc (SVG icons, etc)."""
    social: dict[str, list[str]] = {}
    if not html:
        return social
    
    matches = _SOCIAL_HTML_RE.findall(html)
    for url in matches:
        url = url.strip()
        if "facebook.com" in url or "fb.com" in url:
            social.setdefault("facebook", []).append(url)
        elif "zalo.me" in url:
            zid_match = re.search(r'zalo\.me/(\d+)', url)
            if zid_match:
                zid = _validate_zalo_oa(zid_match.group(1))
                if zid:
                    social.setdefault("zalo", []).append(f"https://zalo.me/{zid}")
        elif "tiktok.com" in url:
            social.setdefault("tiktok", []).append(url)
        elif "instagram.com" in url:
            social.setdefault("instagram", []).append(url)
        elif "youtube.com" in url:
            social.setdefault("youtube", []).append(url)
    
    # Deduplicate
    for platform in social:
        social[platform] = list(dict.fromkeys(social[platform]))[:3]
    
    return social


def _extract_contact(raw: str, base_url: str, html: Optional[str] = None) -> ContactDetails:
    """Anh Minh + Chị Ngọc — Contact với social recovery từ HTML."""
    contact = ContactDetails()

    # 1. SĐT truyền thống
    raw_phones = _PHONE_RE.findall(raw)
    phones_found = []
    for p in raw_phones:
        if isinstance(p, tuple):
            p = next((x for x in p if x), None)
        if p:
            validated = _validate_phone(p.strip())
            if validated:
                phones_found.append(validated)

    # 2. Zalo OA — Bắt MỌI định dạng
    zalo_matches = _ZALO_RE.findall(raw)
    zalo_ids_found = []
    for zid in zalo_matches:
        validated = _validate_zalo_oa(zid)
        if validated:
            zalo_ids_found.append(validated)
            # Coi Zalo OA ID là phone nếu không có phone truyền thống
            if validated not in phones_found:
                phones_found.append(validated)
    
    if phones_found:
        contact.phones = list(dict.fromkeys(phones_found))

    if zalo_ids_found:
        contact.social_links["zalo"] = list(dict.fromkeys([
            f"https://zalo.me/{zid}" for zid in zalo_ids_found
        ]))

    # 3. Social từ HTML — Chị Ngọc
    if html:
        html_social = _extract_social_from_html(html)
        for platform, links in html_social.items():
            if platform not in contact.social_links:
                contact.social_links[platform] = links
            else:
                # Merge và deduplicate
                existing = set(contact.social_links[platform])
                for link in links:
                    if link not in existing:
                        contact.social_links[platform].append(link)

    # 4. Địa chỉ
    addresses_found = []
    addr_matches = _ADDRESS_RE.findall(raw)
    for match in addr_matches:
        if isinstance(match, tuple):
            addr_text = next((x for x in match if x), "")
        else:
            addr_text = match
        if addr_text:
            clean = _clean_md_text(_clean_url_from_text(addr_text))
            if _is_valid_address(clean):
                addresses_found.append(clean)
    
    if addresses_found:
        contact.addresses = list(dict.fromkeys(addresses_found))

    # 5. Email
    emails = _EMAIL_RE.findall(raw)
    if emails:
        contact.emails = list(dict.fromkeys([
            e.strip() for e in emails 
            if not any(x in e.lower() for x in ["png", "gif", "jpg", "jpeg", "example.com", "test.com", "noreply"])
        ]))

    # 6. Giờ mở cửa
    hours = _HOURS_RE.findall(raw)
    if hours:
        clean_hours = []
        for h in hours:
            if isinstance(h, tuple):
                hour_str = next((x for x in h if x), None)
            else:
                hour_str = h
            if hour_str and len(hour_str.strip()) > 3:
                clean_hours.append(_clean_md_text(hour_str.strip()))
        if clean_hours:
            contact.business_hours = list(dict.fromkeys(clean_hours))[:3]

    # 7. E-commerce
    ecoms = _ECOM_RE.findall(raw)
    if ecoms:
        contact.ecommerce_links = list(dict.fromkeys([
            f"https://{e}" if not e.startswith("http") else e for e in ecoms
        ]))

    return contact


def _extract_nav_urls(raw: str, base_url: str) -> list[dict[str, str]]:
    domain = urlparse(base_url).netloc
    seen: set[str] = set()
    nav_urls: list[dict[str, str]] = []

    for label, href in _MD_LINK_RE.findall(raw):
        full = urljoin(base_url, href) if href.startswith(("/?", "./", "../")) or not href.startswith("http") else href
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
    nav_urls: Optional[list[dict[str, str]]] = None
) -> BrandIdentity:
    pages_raw = [homepage_raw] + [p["raw"] for p in pages_for_db]
    full_text = "\n\n".join(pages_raw)
    source_for_visual = homepage_html if homepage_html is not None else homepage_raw

    identity = BrandIdentity()

    # 1. Brand Name
    brand_name = None
    description = None

    m = _H1_RE.search(homepage_raw)
    if m:
        h1_raw = _clean_md_text(m.group(1))
        parts = re.split(r'\s*[-–|:,]\s*', h1_raw, maxsplit=1)
        brand_name = parts[0].strip()
        if len(parts) > 1:
            description = parts[1].strip()

    if not brand_name or len(brand_name) < 2 or brand_name.lower() in ["trang chủ", "home", "welcome", ""]:
        site_name = re.search(r'<meta[^>]*og:site_name[^>]*content=["\']([^"\']+)["\']', source_for_visual, re.IGNORECASE)
        if site_name:
            brand_name = site_name.group(1).strip()

    if not brand_name or len(brand_name) < 2:
        title_match = re.search(r'<title>([^<]{2,100})</title>', source_for_visual, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            brand_name = re.split(r'\s*[|\-–]\s*', title)[0].strip()

    if not description or len(description) < 10:
        meta_desc = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', source_for_visual, re.IGNORECASE)
        if not meta_desc:
            meta_desc = re.search(r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', source_for_visual, re.IGNORECASE)
        if meta_desc:
            desc = meta_desc.group(1).strip()
            if 20 < len(desc) < 300:
                description = desc

    identity.brand_name = brand_name
    identity.description = description

    # 2. Tagline — Ms. Hương: Generic, nhưng filter kỹ
    taglines = _TAGLINE_RE.findall(homepage_raw)
    if taglines:
        clean_taglines = []
        for t in taglines:
            clean = _clean_md_text(_clean_url_from_text(t)).strip()
            if clean and not clean.startswith(('*', '-', '•', '–', '#')):
                if 10 < len(clean) < 60 and clean not in [brand_name, description]:
                    # Không lấy nếu là tên product category
                    if not any(cat in clean.lower() for cat in ["đất sạch", "phân bón", "thuốc trừ sâu", "chăm sóc"]):
                        clean_taglines.append(clean)
        identity.taglines = list(dict.fromkeys(clean_taglines))[:3]
    
    # Fallback: dùng first sentence của description
    if not identity.taglines and description:
        first_sentence = description.split('.')[0].strip()
        if 10 < len(first_sentence) < 80:
            identity.taglines = [first_sentence]

    # 3. Mission/Vision/Story
    _MISSION_RE = re.compile(r'(?:sứ\s*mệnh|mission)[^\n:：]{0,20}[:\s：]+([^\n]{30,400})', re.IGNORECASE)
    _VISION_RE = re.compile(r'(?:tầm\s*nhìn|vision)[^\n:：]{0,20}[:\s：]+([^\n]{30,400})', re.IGNORECASE)
    _STORY_RE = re.compile(r'(?:câu\s*chuyện|thành\s*lập|lịch\s*sử|story|founded?|established?)[^\n:：]{0,20}[:\s：]*((?:[^\n]+\n?){1,8})', re.IGNORECASE)

    m = _MISSION_RE.search(full_text)
    if m:
        identity.mission = _clean_md_text(m.group(1)).strip()

    m = _VISION_RE.search(full_text)
    if m:
        identity.vision = _clean_md_text(m.group(1)).strip()

    m = _STORY_RE.search(full_text)
    if m:
        identity.story = _clean_md_text(m.group(1)).strip()

    # 4. Tone of Voice
    tones = _TONE_RE.findall(full_text)
    if tones:
        identity.tone_keywords = list(dict.fromkeys([t.lower() for t in tones]))[:8]

    # 5. Main Products
    if nav_urls:
        products_from_nav = []
        for nav in nav_urls:
            label = nav["label"].strip()
            href = nav["url"].lower()
            
            is_product_url = any(pk in href for pk in ["/collections/", "/products/", "/san-pham/"])
            is_not_generic = not _is_generic_product_label(label)
            
            if is_product_url and is_not_generic:
                clean_label = _clean_md_text(label)
                if 3 < len(clean_label) < 50:
                    products_from_nav.append(clean_label)
        
        if products_from_nav:
            identity.main_products = list(dict.fromkeys(products_from_nav))[:8]

    # 6. Certifications
    cert_sections = re.split(r'(?:chứng\s*nhận|giải\s*thưởng|đối\s*tác|thành\s*tích)', full_text, flags=re.IGNORECASE)[-2:]
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

    # 7. Partners
    partner_sections = re.split(r'(?:đối\s*tác|khách\s*hàng\s*tiêu\s*biểu|partner)', full_text, flags=re.IGNORECASE)[-2:]
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


def _extract_visual_identity(source: str) -> VisualIdentity:
    visual = VisualIdentity()

    detected_logos = []
    for match in _LOGO_RE.findall(source):
        if isinstance(match, tuple):
            for group in match:
                if group and group.strip():
                    detected_logos.append(group.strip())
        elif isinstance(match, str) and match.strip():
            detected_logos.append(match.strip())

    if detected_logos:
        valid_logos = []
        for logo in detected_logos:
            if logo.startswith(("http", "/", "data:", "https:")) or "." in logo:
                if len(logo) < 1000 and not logo.endswith((".js", ".css")):
                    valid_logos.append(logo)
        visual.logos = list(dict.fromkeys(valid_logos))[:5]

    detected_colors = _COLOR_RE.findall(source)
    if detected_colors:
        clean_colors = []
        for c in detected_colors:
            if isinstance(c, tuple):
                c = next((x for x in c if x), None)
            if c and c.strip():
                clean_colors.append(c.strip().lower())
        # Lọc trùng và lấy hex优先
        hex_colors = [c for c in clean_colors if c.startswith('#')]
        name_colors = [c for c in clean_colors if not c.startswith('#')]
        visual.colors = list(dict.fromkeys(hex_colors + name_colors))[:8]

    return visual


# ═══════════════════════════════════════════════════════════════════════════════
# V. RAG CHUNKING — V5
# ═══════════════════════════════════════════════════════════════════════════════

def _compose_rag_chunks(
    identity: BrandIdentity, 
    contact: ContactDetails, 
    visual: VisualIdentity
) -> tuple[dict[str, str], dict[str, str]]:
    chunks: dict[str, str] = {}
    quality: dict[str, str] = {}

    # Chunk 1: Brand Core
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
        core_lines.append(f"Sản phẩm chính:\n- " + "\n- ".join(identity.main_products))
    
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

    # Chunk 2: Story & Values
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

    # Chunk 3: Visual
    visual_lines = []
    if visual.logos:
        visual_lines.append(f"Logo: {', '.join(visual.logos[:3])}")
    if visual.colors:
        visual_lines.append(f"Màu sắc: {', '.join(visual.colors)}")
    
    chunks["brand_visual"] = "\n".join(visual_lines)
    quality["brand_visual"] = "high" if visual.logos else "low"

    # Chunk 4: Contact & CTA
    cta_lines = []
    if contact.phones:
        cta_lines.append(f"Hotline: {', '.join(contact.phones[:3])}")
    if contact.business_hours:
        cta_lines.append(f"Giờ mở cửa: {' | '.join(contact.business_hours)}")
    if contact.addresses:
        cta_lines.append(f"Địa chỉ ({len(contact.addresses)} chi nhánh):\n- " + "\n- ".join(contact.addresses[:5]))
    if contact.emails:
        cta_lines.append(f"Email: {', '.join(contact.emails[:2])}")
    if contact.ecommerce_links:
        cta_lines.append(f"Mua online: {' | '.join(contact.ecommerce_links[:3])}")
    
    chunks["contact_cta"] = "\n".join(cta_lines)
    has_phone = bool(contact.phones)
    has_address = bool(contact.addresses)
    has_social = bool(contact.social_links)
    if has_phone and has_address:
        quality["contact_cta"] = "high"
    elif has_phone:
        quality["contact_cta"] = "medium"
    elif has_social:
        quality["contact_cta"] = "medium"  # Có Zalo cũng tạm ổn
    else:
        quality["contact_cta"] = "low"

    # Chunk 5: Social
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
# VI. BUSINESS CRAWLER SERVICE — V5: TWO-PASS STRATEGY
# ═══════════════════════════════════════════════════════════════════════════════

# Anh Khánh + Chị Lan: Mandatory pages — luôn crawl nếu tồn tại
_MANDATORY_PATHS = [
    "/lien-he", "/contact", "/pages/lien-he", "/pages/contact",
    "/about", "/gioi-thieu", "/about-us", "/ve-chung-toi",
]

_FALLBACK_PATHS = [
    "/he-thong-cua-hang", "/stores", "/chi-nhanh", "/cua-hang",
    "/san-pham", "/products", "/dich-vu", "/services",
]

_RETRY_MAX = 3


class BusinessCrawler:
    def __init__(self, rag: RAG, loader: DocumentLoader, db: AsyncSession) -> None:
        self._rag = rag
        self._loader = loader
        self._db = db

    async def crawl_business(self, url: str, document_type: str, document_id: int) -> int:
        log.info("[BusinessCrawlerV5] Bắt đầu crawl: %s", url)

        # ═══ PASS 1: Homepage + Discovery ═══
        homepage = await self._load_with_retry(url, document_type)
        if not homepage:
            log.error("[BusinessCrawlerV5] Không thể load homepage: %s", url)
            return 0

        homepage_raw, homepage_html = self._normalize_loader_result(homepage)

        if len(homepage_raw.strip()) < 300:
            log.warning(
                "[BusinessCrawlerV5] Homepage quá ít text (%d chars). JS-rendered?",
                len(homepage_raw.strip()),
            )

        # Extract nav từ homepage
        nav_urls = _extract_nav_urls(homepage_raw, url)

        # Discover URLs
        discovered_internal, social_links = _discover_brand_urls(homepage_raw, url, top_n=8)

        # ═══ PASS 2: Mandatory Crawl (Anh Khánh) ═══
        # Luôn thử crawl /lien-he và /about để đảm bảo contact + story
        all_urls = [url]  # Homepage
        mandatory_urls = []
        base = url.rstrip("/")
        
        for path in _MANDATORY_PATHS:
            test_url = base + path
            # Chỉ thêm nếu chưa có trong discovered
            if test_url not in discovered_internal and test_url.rstrip("/") != url.rstrip("/"):
                mandatory_urls.append(test_url)
        
        # Thêm discovered URLs
        for b_url in discovered_internal:
            if b_url.rstrip("/") != url.rstrip("/"):
                all_urls.append(b_url)
        
        # Thêm mandatory URLs (ưu tiên sau cùng để không chen ngang discovered tốt)
        all_urls.extend(mandatory_urls)

        # Fallback nếu vẫn ít
        if len(all_urls) <= 2:
            for path in _FALLBACK_PATHS:
                all_urls.append(base + path)

        log.info("[BusinessCrawlerV5] Tổng hợp %d URLs (bao gồm %d mandatory)", 
                 len(all_urls), len(mandatory_urls))

        # Crawl tất cả
        pages_for_db: list[dict[str, Any]] = []
        crawled_urls = set([url])  # Homepage đã crawl
        
        for brand_url in all_urls[1:]:  # Bỏ homepage
            if urlparse(brand_url).netloc != urlparse(url).netloc:
                continue
            if brand_url in crawled_urls:
                continue

            loaded = await self._load_with_retry(brand_url, document_type)
            if loaded:
                raw, html = self._normalize_loader_result(loaded)
                if len(raw.strip()) > 50:
                    pages_for_db.append({"url": brand_url, "raw": raw, "html": html})
                    crawled_urls.add(brand_url)
                    log.info("[BusinessCrawlerV5] Crawl OK: %s (%d chars)", brand_url, len(raw))
                else:
                    log.warning("[BusinessCrawlerV5] Trang rỗng: %s", brand_url)
            else:
                log.warning("[BusinessCrawlerV5] Bỏ qua: %s", brand_url)

        # ═══ PASS 3: Extract & Merge ═══
        # Merge tất cả text
        all_raw_texts = [homepage_raw] + [p["raw"] for p in pages_for_db]
        aggregated_raw = "\n\n".join(all_raw_texts)
        
        # Merge HTML nếu có
        all_html = [homepage_html] + [p.get("html") for p in pages_for_db if p.get("html")]
        aggregated_html = "\n".join(filter(None, all_html))

        # Extract
        identity = _extract_brand_identity(pages_for_db, homepage_raw, homepage_html, nav_urls=nav_urls)
        visual = _extract_visual_identity(aggregated_html or homepage_html or homepage_raw)
        contact = _extract_contact(aggregated_raw, url, html=aggregated_html)
        
        # Merge social từ discovery
        for link in social_links:
            if "facebook.com" in link or "fb.com" in link:
                contact.social_links.setdefault("facebook", []).append(link)
            elif "zalo.me" in link:
                zid_match = re.search(r'zalo\.me/(\d+)', link)
                if zid_match and _validate_zalo_oa(zid_match.group(1)):
                    contact.social_links.setdefault("zalo", []).append(link)
            elif "tiktok.com" in link:
                contact.social_links.setdefault("tiktok", []).append(link)

        # Deduplicate
        for platform in contact.social_links:
            contact.social_links[platform] = list(dict.fromkeys(contact.social_links[platform]))[:3]

        # ═══ PASS 4: RAG & Save ═══
        rag_chunks, chunk_quality = _compose_rag_chunks(identity, contact, visual)
        full_rag_text = "\n\n".join([
            f"=== {k.upper().replace('_', ' ')} ===\n{v}"
            for k, v in rag_chunks.items() if v.strip()
        ])

        if not full_rag_text.strip():
            full_rag_text = f"Tên thương hiệu: {identity.brand_name or url}\nURL nguồn: {url}"

        # Save to Vector DB
        for chunk_name, chunk_text in rag_chunks.items():
            if chunk_text.strip():
                metadata = {
                    "chunk_type": chunk_name,
                    "brand_name": identity.brand_name,
                    "source_url": url,
                    "document_id": document_id,
                    "quality": chunk_quality.get(chunk_name, "unknown"),
                }
                await self._rag.add(chunk_text, **metadata)

        # Save to PostgreSQL
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
                "mandatory_crawled": len([p for p in pages_for_db if any(m in p["url"] for m in _MANDATORY_PATHS)]),
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
            "[BusinessCrawlerV5] HOÀN THÀNH — page_id=%s brand=%r quality=%s",
            page.id, identity.brand_name, chunk_quality,
        )
        return 1

    async def _load_with_retry(self, url: str, document_type: str) -> Any:
        for attempt in range(_RETRY_MAX):
            try:
                return self._loader.load_web(url, document_type=document_type)
            except Exception as e:
                log.warning("[BusinessCrawlerV5] Retry %d/%d: %s — %s", attempt + 1, _RETRY_MAX, url, e)
                if attempt == _RETRY_MAX - 1:
                    return None
        return None

    def _normalize_loader_result(self, result: Any) -> tuple[str, Optional[str]]:
        if isinstance(result, str):
            return result, None
        if isinstance(result, dict):
            return result.get("text", str(result)), result.get("html") or result.get("raw_html")
        raw = getattr(result, "text", str(result))
        html = getattr(result, "raw_html", getattr(result, "html", None))
        return raw, html