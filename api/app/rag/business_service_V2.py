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

# Khởi tạo logging hiển thị giống FastAPI console
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("business_crawler")


# ── I. REGEX THU GOM DỮ LIỆU THÔ ĐA ĐỊNH DẠNG (TỐI ĐA NGỮ CẢNH CHO LLM) ───────

# Bốc sạch chuỗi giống số điện thoại VN (9-11 số), chấp nhận khoảng trắng, dấu chấm, gạch ngang, hotline 1800/1900
_PHONE_LOOSE_RE = re.compile(
    r'(?:\+?84|0)[.\s]?\d{2,4}[.\s]?\d{3}[.\s]?\d{3,4}|\b1[89]00\d{4,6}\b|\b\d{4}[.\s]?\d{3}[.\s]?\d{3}\b'
)

# Bắt email thuần hoặc email nằm trong thẻ mailto:
_EMAIL_RE = re.compile(r'([\w.-]+@[\w.-]+\.\w+)', re.IGNORECASE)

# Giờ mở cửa: Bắt cụm thời gian thô
_HOURS_RE = re.compile(
    r'(?:giờ\s*mở\s*cửa|giờ\s*làm\s*việc|mở\s*cửa|⏰)[^\n:：]{0,15}[:\s：]+([^\n]{5,100})'
    r'|(\d{1,2}[h:]\d{0,2}\s*[-–]\s*\d{1,2}[h:]\d{0,2})',
    re.IGNORECASE
)

# Bắt cả src ảnh logo VÀ href của các thẻ link rel="icon" / rel="shortcut icon"
_LOGO_RE = re.compile(
    r'src=["\']([^"\'>\s]*logo[^"\'>\s]*)["\']'
    r'|href=["\']([^"\'>\s]*favicon[^"\'>\s]*|[^"\'>\s]*logo[^"\'>\s]*)["\']'
    r'|(?<=!\[)[^\]]*(?=\]\(([^)]*logo[^)]*)\))', 
    re.IGNORECASE
)

# Quét nhanh các thuộc tính màu sắc đặc trưng trong mã nguồn (mã màu Hex hoặc các class màu cơ bản)
_COLOR_RE = re.compile(
    r'(?:background-color|color|bg-|text-)[:\s]*([#][0-9a-fA-F]{3,6}|green|blue|orange|red|yellow|brown|purple|pink)', 
    re.IGNORECASE
)


# ── II. REGEX CẤU TRÚC MARKDOWN & LINK NAVIGATION ─────────────────────────────
_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_MD_LINK_RE = re.compile(
    r'\[([^\]]+)\]\(((?:/[^\s\)\"]*|https?://[^\s\)\"]*))(?:\s+"[^"]*")?\)',
    re.IGNORECASE,
)

# Tagline thô xuất hiện trên trang chủ
_TAGLINE_SAFE_RE = re.compile(
    r'^(?!.*\]\().*(chuyên|cung cấp|được thành lập|với hơn|hệ thống|chuỗi).{20,200}$',
    re.IGNORECASE | re.MULTILINE,
)

_SKIP_SCHEME_RE = re.compile(r'^(javascript|tel|mailto|zalo|sms|whatsapp):', re.IGNORECASE)
_MIN_SCORE = 1
_BLACKLIST_SCORE = -100


# ── III. SCORING TABLES (ĐẨY TRANG LIÊN HỆ LÊN ƯU TIÊN SỐ 1) ───────────────────

_PATH_SCORES: list[tuple[int, re.Pattern[str]]] = [
    # ƯU TIÊN TUYỆT ĐỐI: Đẩy trang Liên hệ lên ngôi vương để bốc trọn info chi tiết
    (+25, re.compile(r'(lien-he|contact|he-thong-cua-hang|stores|address|map)', re.IGNORECASE)),
    # Nhóm thông tin giới thiệu doanh nghiệp
    (+15, re.compile(r'(about|gioi-thieu|brand|company|story|ve-chung-toi)', re.IGNORECASE)),
    # Nhóm tin tức/blog giữ điểm thấp để không chen hàng trang liên hệ
    (+1, re.compile(r'/(blog|news|kinh-nghiem|articles?|tin-tuc)(/|$)', re.IGNORECASE)),
    # Hạ điểm sâu các trang giỏ hàng, thanh toán
    (-15, re.compile(r'/(checkout|account|cart|search|login|sign-?in|register|wishlist|gio-hang|don-hang)(/|$)', re.IGNORECASE)),
]

_LABEL_SCORES: list[tuple[int, re.Pattern[str]]] = [
    (+10, re.compile(r'liên\s*hệ|contact|địa\s*chỉ|cửa\s*hàng|hotline', re.IGNORECASE)),
    (+5, re.compile(r'giới\s*thiệu|về\s*chúng\s*tôi|câu\s*chuyện|about\s*us', re.IGNORECASE)),
]


# ── IV. CORE HELPER FUNCTIONS ─────────────────────────────────────────────────

def _clean_md_text(text: str) -> str:
    return re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text).strip()


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


def _discover_brand_urls(raw: str, base_url: str, top_n: int = 6) -> list[str]:
    """Quét sạch link nội bộ điểm cao VÀ mở bung để lấy cả link MXH (Facebook, Zalo...) cho LLM đọc"""
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
        full = urljoin(base_url, href) if href.startswith("/") else href
        parsed = urlparse(full)
        
        # KIỂM TRA LINK NGOẠI SÀN: Nếu là MXH chính chủ của Brand -> Gom về cho LLM xử lý ngữ cảnh
        if parsed.netloc != domain:
            if any(soc in parsed.netloc for soc in ["facebook.com", "fb.com", "zalo.me", "tiktok.com", "youtube.com", "instagram.com"]):
                social_links.add(full)
            continue
            
        if full.rstrip("/") == base_url.rstrip("/"):
            continue

        s = _score_url(full, label)
        if s >= _MIN_SCORE:
            if full not in scored or scored[full] < s:
                scored[full] = s

    # Lấy các internal link cốt lõi tốt nhất (Chắc chắn bốc trúng trang Liên hệ/Giới thiệu trước)
    qualified = [url for url, s in sorted(scored.items(), key=lambda x: x[1], reverse=True)]
    
    return qualified[:top_n] + list(social_links)[:4]


def _extract_contact(raw: str, base_url: str) -> dict[str, Any]:
    """
    Hàm thu gom thông tin liên hệ thô cấp độ cao.
    Bảo toàn 100% chữ địa chỉ ở footer bằng cách bóc tách link Markdown ẩn, 
    đồng thời chuẩn hóa chính xác hệ thống liên kết MXH (Zalo, Facebook, Tiktok).
    """
    contact: dict[str, Any] = {}
    
    # Regex dùng để giải phóng text hiển thị khỏi link Markdown ẩn: [Text hiển thị](Link ẩn) -> Text hiển thị
    _REMOVE_MD_LINKS_RE = re.compile(r'\[([^\]]+)\]\([^)]+\)')
    
    # 1. Thu gom Số điện thoại độc lập
    raw_phones = _PHONE_LOOSE_RE.findall(raw)
    phones_found = []
    for p in raw_phones:
        if isinstance(p, tuple):
            p = p[0] or p[1]
        p_clean = p.strip()
        if len(re.sub(r'\D', '', p_clean)) >= 9:
            phones_found.append(p_clean)
    if phones_found:
        contact["all_detected_phones"] = list(set(phones_found))

    # 2. Thu gom toàn bộ DÒNG chứa địa chỉ (Chống bộ lọc loại bỏ nhầm link ẩn ở footer)
    addresses_found = []
    for line in raw.splitlines():
        line_clean = line.strip()
        if not line_clean:
            continue
            
        # 🛠️ BƯỚC ĐỘT PHÁ: Chuyển "[CH Tân Bình](https://...)" thành "CH Tân Bình" trước khi check từ khóa
        line_text_only = _REMOVE_MD_LINKS_RE.sub(r'\1', line_clean)
        
        # Kiểm tra nếu dòng chứa từ khóa hành chính hoặc từ khóa nhận diện địa điểm
        is_addr_line = (
            any(k in line_text_only.lower() for k in ["địa chỉ", "văn phòng", "chi nhánh", "cửa hàng", "showroom", "kho hàng", "khu vực"]) or
            any(k in line_text_only.lower() for k in ["đường", "phố", "quận", "huyện", "tp.", "thành phố", "hcm", "hà nội", "đà nẵng", "núi thành", "nguyễn minh hoàng"])
        )
        
        if is_addr_line and len(line_text_only) > 15:
            # Làm sạch các ký tự bullet point rác ở đầu dòng
            clean_text = line_text_only.lstrip(":-*•| ").strip()
            
            # Lúc này clean_text đã sạch bóng URL ẩn, lọc rác tệp tin hoặc trang thanh toán an toàn 100%
            if not any(x in clean_text.lower() for x in ["http://", "https://", ".png", ".jpg", ".jpeg", "thanh toán", "giỏ hàng"]):
                addresses_found.append(clean_text)
                
    if addresses_found:
        contact["all_detected_addresses"] = list(set(addresses_found))

    # 3. Thu gom Email
    emails = _EMAIL_RE.findall(raw)
    if emails:
        contact["emails"] = list(set([e.strip() for e in emails if not any(x in e for x in ["png", "gif", "jpg", "jpeg"])]))

    # 4. Thu gom Facebook & Tiktok (Chuẩn hóa prefix link đầy đủ)
    fbs = re.compile(r"facebook\.com/[^\s\)\"\'>]+").findall(raw)
    if fbs: 
        cleaned_fbs = []
        for f in fbs:
            f_clean = re.sub(r'[\]\)\(\/]+$', '', f).strip()
            f_clean = f_clean.replace("](", "").replace("(", "")
            if not f_clean.startswith("http"):
                f_clean = f"https://{f_clean}"
            cleaned_fbs.append(f_clean)
        contact["facebook_links"] = list(set(cleaned_fbs))
        
    tiktoks = re.compile(r"tiktok\.com/[^\s\)\"\'>]+").findall(raw)
    if tiktoks:
        cleaned_tiktoks = []
        for t in tiktoks:
            t_clean = re.sub(r'[\]\)\(\/]+$', '', t).strip()
            t_clean = t_clean.replace("](", "").replace("(", "")
            if not t_clean.startswith("http"):
                t_clean = f"https://{t_clean}"
            cleaned_tiktoks.append(t_clean)
        contact["tiktok_links"] = list(set(cleaned_tiktoks))

    # 5. Thu gom Zalo nâng cao - Trích xuất ID số để loại bỏ hoàn toàn lỗi nhân đôi chuỗi
    zalo_ids = re.compile(r"zalo\.me/(\d+)").findall(raw)
    if zalo_ids:
        contact["zalo_links"] = list(set([f"https://zalo.me/{zid}" for zid in zalo_ids]))
    else:
        zalos = re.compile(r"zalo\.me/[^\s\)\"\'>]+").findall(raw)
        if zalos:
            clean_zalos = []
            for z in zalos:
                z_clean = re.sub(r'[\]\)\(\/]+$', '', z).strip()
                z_clean = z_clean.replace("](", "").replace("(", "")
                if "http" not in z_clean:
                    z_clean = f"https://{z_clean}"
                clean_zalos.append(z_clean)
            if clean_zalos:
                contact["zalo_links"] = list(set(clean_zalos))

    return contact


def _extract_nav_urls(raw: str, base_url: str) -> list[dict[str, str]]:
    domain = urlparse(base_url).netloc
    seen: set[str] = set()
    nav_urls: list[dict[str, str]] = []

    for label, href in _MD_LINK_RE.findall(raw):
        full = urljoin(base_url, href) if href.startswith("/") else href
        if urlparse(full).netloc != domain or full in seen:
            continue
        seen.add(full)
        nav_urls.append({"url": full, "label": label.strip()})
    return nav_urls


def _extract_brand_identity(pages_for_db: list[dict[str, Any]], homepage_raw: str, homepage_html: str | None = None) -> dict[str, Any]:
    # 🛠️ SỬA LỖI 2: Đưa cả trang chủ vào full_text để tránh mất Sứ mệnh/Tầm nhìn nếu viết ở trang chủ
    pages_raw = [homepage_raw] + [p["raw"] for p in pages_for_db]
    full_text = "\n\n".join(pages_raw)

    _MISSION_RE = re.compile(r'(?:sứ\s*mệnh|mission)[^\n:：]{0,20}[:\s：]+([^\n]{30,400})', re.IGNORECASE)
    _VISION_RE = re.compile(r'(?:tầm\s*nhìn|vision)[^\n:：]{0,20}[:\s：]+([^\n]{30,400})', re.IGNORECASE)
    _STORY_RE = re.compile(r'(?:câu\s*chuyện|thành\s*lập|lịch\s*sử|story|founded?|established?)[^\n:：]{0,20}[:\s：]*((?:[^\n]+\n?){1,8})', re.IGNORECASE)

    identity: dict[str, Any] = {}

    # Tách lọc Title / Brand Name từ H1 trang chủ
    m = _H1_RE.search(homepage_raw)
    if m:
        h1_raw = _clean_md_text(m.group(1))
        parts = re.split(r'\s*[-–|:,]\s*', h1_raw, maxsplit=1)
        identity["brand_name"] = parts[0].strip()
        if len(parts) > 1: 
            identity["description"] = parts[1].strip()

    m = _MISSION_RE.search(full_text)
    if m: identity["mission"] = _clean_md_text(m.group(1)).strip()

    m = _VISION_RE.search(full_text)
    if m: identity["vision"] = _clean_md_text(m.group(1)).strip()

    m = _STORY_RE.search(full_text)
    if m: identity["story"] = _clean_md_text(m.group(1)).strip()

    taglines = _TAGLINE_SAFE_RE.findall(homepage_raw)
    if taglines:
        identity["taglines"] = list(set([_clean_md_text(t).strip() for t in taglines if 20 < len(_clean_md_text(t).strip()) < 300]))[:3]

    # 🛠️ SỬA LỖI 1 & 3: Ưu tiên quét trên HTML gốc nếu có để lấy Logo/Favicon chuẩn xác
    source_for_visual = homepage_html if homepage_html else homepage_raw
    
    detected_logos = []
    for match in _LOGO_RE.findall(source_for_visual):
        if isinstance(match, tuple):
            for group in match:
                if group and group.strip():
                    detected_logos.append(group.strip())
        elif isinstance(match, str) and match.strip():
            detected_logos.append(match.strip())
            
    if detected_logos:
        identity["raw_detected_logos"] = list(set(detected_logos))[:3]

    detected_colors = _COLOR_RE.findall(source_for_visual)
    if detected_colors:
        identity["raw_detected_colors"] = list(set([c.strip().lower() for c in detected_colors if c.strip()]))[:6]

    return identity


def _compose_brand_rag_text(identity: dict[str, Any], contact: dict[str, Any]) -> str:
    lines: list[str] = []

    if identity.get("brand_name"): lines.append(f"Tên thương hiệu: {identity['brand_name']}")
    if identity.get("description"): lines.append(f"Mô tả/Lĩnh vực: {identity['description']}")
    if identity.get("taglines"): lines.append("Slogan/Tagline nhận diện: " + " | ".join(identity["taglines"]))
    
    if identity.get("raw_detected_logos"):
        lines.append("Đường dẫn hoặc tài nguyên hình ảnh Logo phát hiện được:\n- " + "\n- ".join(identity["raw_detected_logos"]))
    if identity.get("raw_detected_colors"):
        lines.append("Các mã màu hoặc tông màu đặc trưng xuất hiện trong cấu trúc mã nguồn web:\n- " + ", ".join(identity["raw_detected_colors"]))

    if identity.get("mission"): lines.append(f"Sứ mệnh: {identity['mission']}")
    if identity.get("vision"): lines.append(f"Tầm nhìn: {identity['vision']}")
    if identity.get("story"): lines.append(f"Câu chuyện phát triển/Lịch sử: {identity['story']}")
    
    if contact.get("all_detected_phones"): 
        lines.append("Danh sách toàn bộ các Số điện thoại quét được trên hệ thống website:\n- " + "\n- ".join(contact["all_detected_phones"]))
    if contact.get("all_detected_addresses"): 
        lines.append("Danh sách toàn bộ Địa chỉ / Chi nhánh cửa hàng phát hiện được:\n- " + "\n- ".join(contact["all_detected_addresses"]))
    if contact.get("emails"): 
        lines.append("Email doanh nghiệp: " + ", ".join(contact["emails"]))
    if contact.get("facebook_links"): 
        lines.append("Danh sách liên kết Facebook phát hiện:\n- " + "\n- ".join(contact["facebook_links"]))
    if contact.get("zalo_links"): 
        lines.append("Danh sách liên kết Zalo phát hiện:\n- " + "\n- ".join(contact["zalo_links"]))
    if contact.get("tiktok_links"):
        lines.append("Danh sách liên kết Tiktok phát hiện:\n- " + "\n- ".join(contact["tiktok_links"]))

    return "\n\n".join(lines)


# ── V. BUSINESS CRAWLER SERVICE CLASS ─────────────────────────────────────────

_FALLBACK_PATHS = ["/pages/lien-he", "/pages/about", "/about", "/gioi-thieu", "/about-us", "/ve-chung-toi"]

class BusinessCrawler:
    def __init__(self, rag: RAG, loader: DocumentLoader, db: AsyncSession) -> None:
        self._rag    = rag
        self._loader = loader
        self._db     = db

    async def crawl_business(self, url: str, document_type: str, document_id: int) -> int:
        homepage = self._loader.load_web(url, document_type=document_type)
        
        # Giả định nếu Loader của bạn có giữ lại mã nguồn HTML gốc (ví dụ: .raw_html hoặc .html)
        # Nếu không có, nó tự động fallback về dùng homepage.text
        homepage_html = getattr(homepage, "raw_html", getattr(homepage, "html", None))
        homepage_raw = homepage.text

        # Phát hiện các URL quan trọng
        discovered_urls = _discover_brand_urls(homepage_raw, url, top_n=6)
        
        # 🛠| SỬA LỖI 4: Ép buộc đưa trang chủ vào danh sách brand_pages để đồng bộ thông tin
        brand_urls = [url]
        for b_url in discovered_urls:
            if b_url.rstrip("/") != url.rstrip("/"):
                brand_urls.append(b_url)

        log.info("[BusinessCrawler] homepage=%s → tổng hợp %d brand URLs: %s", url, len(brand_urls), brand_urls)

        if len(brand_urls) <= 1: # Chỉ có mỗi trang chủ
            base = url.rstrip("/")
            for path in _FALLBACK_PATHS:
                brand_urls.append(base + path)

        pages_for_db: list[dict[str, Any]] = []
        for brand_url in brand_urls:
            # Bỏ qua không tái cào trang chủ trong vòng lặp vì đã cào ở trên
            if brand_url.rstrip("/") == url.rstrip("/"):
                continue
            if urlparse(brand_url).netloc != urlparse(url).netloc:
                continue
            try:
                loaded = self._loader.load_web(brand_url, document_type=document_type)
                pages_for_db.append({"url": brand_url, "raw": loaded.text})
                log.info("[BusinessCrawler] Cào thành công sub-page: %s (%d chars)", brand_url, len(loaded.text))
            except Exception as e:
                log.warning("[BusinessCrawler] Bỏ qua liên kết lỗi %s: %s", brand_url, e)

        # Trộn text thô trang chủ + các sub-pages phục vụ bóc liên hệ diện rộng
        aggregated_raw_text = homepage_raw + "\n\n" + "\n\n".join([p["raw"] for p in pages_for_db])

        # Trích xuất dữ liệu
        contact   = _extract_contact(aggregated_raw_text, url)
        identity  = _extract_brand_identity(pages_for_db, homepage_raw, homepage_html=homepage_html)
        nav_urls  = _extract_nav_urls(homepage_raw, url)
        
        brand_text = _compose_brand_rag_text(identity, contact)

        if not brand_text.strip():
            brand_text = f"Tên thương hiệu: {identity.get('brand_name') or url}\nURL nguồn: {url}"

        # Lưu trữ Vector DB cho RAG
        await self._rag.add(brand_text, **homepage.metadata)

        # Đồng bộ lưu xuống PostgreSQL DB chi tiết
        combined_content = homepage_raw + "\n\n---\n\n" + "\n\n---\n\n".join(
            f"[{p['url']}]\n{p['raw']}" for p in pages_for_db
        )

        page = DocumentPage(
            document_id=document_id,
            url=url,
            title=identity.get("brand_name") or url,
            content=combined_content,
            extracted={
                "source_url":  url,
                "brand_pages": brand_urls,
                "word_count":  len(brand_text.split()),
                "contact_raw": contact,
                "identity_raw": identity,
                "nav_urls":    nav_urls,
                "rag_text":    brand_text,
            },
        )
        self._db.add(page)
        await self._db.commit()
        await self._db.refresh(page)

        log.info(
            "[BusinessCrawler Successful] page_id=%s brand=%r brand_pages=%d rag_words=%d",
            page.id, identity.get("brand_name"), len(brand_urls), len(brand_text.split()),
        )
        return 1