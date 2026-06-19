import asyncio
import random
import traceback
import nodriver as uc


async def _scrape_facebook(fb_url: str, headless: bool, business_id: str):
    """
    HÀM CÀO DỮ LIỆU FACEBOOK - ĐÃ SỬA THEO LOGIC MỞ TAB MỚI VÀ QUÉT SITE BẤT TỬ
    """
    browser = None

    try:
        print("🚀 Mở trình duyệt...")
        browser = await uc.start(headless=headless, icon_mode=1)

        # 1. Chuẩn hóa URL mục tiêu (Luôn có dấu / ở cuối)
        target_url = fb_url.strip().lower()
        if not target_url.endswith("/"):
            target_url += "/"

        # Ép chuỗi cấu trúc sạch để lát nữa so khớp logic
        clean_search_url = f'"{target_url}"'  # '"https://www.facebook.com/mocseafood/"'

        # Đổi cách tìm kiếm sang toán tử site: như file OKOK chạy được của bạn
        # Trích xuất phần text sau https:// để làm câu lệnh tìm kiếm sạch cho Google
        search_query = f"site:{target_url.replace('https://', '').replace('http://', '')}"

        print(f"🔍 Vào Google tìm kiếm nâng cao: {search_query}...")
        page = await browser.get(f"https://www.google.com/search?q={search_query}")

        # Thêm thời gian đợi sau khi vào Google cho trang load thật ổn định
        print("⏳ Chờ 3 giây cho trang Google Search tải xong hoàn toàn...")
        await asyncio.sleep(3.0)

        matched_href = None
        click_target = None  # Biến lưu trữ Element dùng để click

        print("\n🔄 Bắt đầu quét các kết quả hiển thị...")
        links = await page.select_all("a:has(h3)")

        if not links:
            print("⚠️ Không tìm thấy kết quả nào hiển thị trên Google!")
            return None, None

        print(f"📊 --- XUẤT TOÀN BỘ LOG {len(links)} KẾT QUẢ TÌM THẤY ---")

        for i, link in enumerate(links):
            try:
                href_attr = link["href"] if "href" in link.attrs else None
                text_content = link.text.strip().replace('\n', ' ') if link.text else "KHÔNG CÓ TEXT"
                class_attr = link["class"] if "class" in link.attrs else "No Class"

                print(f"🔹 Kết quả [{i}]:")
                print(f"   + Text tiêu đề : {text_content}")
                print(f"   + Class thẻ <a>: {class_attr}")
                print(f"   + Link gốc URL : {href_attr}")

                if not href_attr:
                    print("   ❌ Trạng thái  : Bỏ qua (Không có href)")
                    print("-" * 60)
                    continue
                    
                href_lower = href_attr.strip().lower()
                # Bọc dấu ngoặc kép vào href quét được để so khớp chính xác tuyệt đối với clean_search_url
                href_with_quotes = f'"{href_lower}"'

                # SO SÁNH CHUẨN XÁC TẠI ĐÂY
                if clean_search_url in href_with_quotes:
                    print(f"   🎯 Trạng thái  : ✅ TRÙNG KHỚP HOÀN HẢO!")
                    if not matched_href:
                        matched_href = href_attr.strip()
                        click_target = link  # Lưu lại Element chuẩn để tí nữa click
                else:
                    print("   ❌ Trạng thái  : Không khớp từ khóa")

                print("-" * 60)

            except Exception as e:
                print(f"   ❌ Lỗi đọc phần tử ở vị trí [{i}]: {e}")
                print("-" * 60)

        print(f"📊 --- KẾT THÚC DANH SÁCH LOG --- \n")

        if not matched_href or not click_target:
            print(f"❌ Không tìm thấy homepage khớp với từ khóa: {fb_url}")
            return None, None

        # --- BỎ ĐOẠN JS BẺ HƯỚNG TẠI ĐÂY ĐỂ MỞ TAB MỚI TỰ NHIÊN ---

        # Chậm lại một chút trước khi bấm chuột
        await asyncio.sleep(1.0)

        try:
            await click_target.scroll_into_view()
        except Exception:
            pass

        print(f"🖱️ [HÀNH ĐỘNG] Click vào kết quả Facebook: {matched_href}")
        await click_target.click()

        # =====================================================
        # ĐỢI 3 GIÂY CỐ ĐỊNH SAU KHI CLICK THEO YÊU CẦU
        # =====================================================
        print("⏳ Đang đợi ĐÚNG 3 GIÂY CỐ ĐỊNH sau khi click để tab mới bật lên...")
        await asyncio.sleep(3.0)

        print("🔎 Bắt đầu quét kiểm tra danh sách các TABS hiển thị...")
        fb_tab = None

        # Vòng lặp duyệt qua toàn bộ các Tab đang có của browser giống file OKOK
        for tab in browser.tabs:
            try:
                url = str(tab.url).lower()
                print("🔹 Hệ thống ghi nhận TAB:", url)

                # Nếu tìm thấy tab mới sinh ra chứa facebook.com thì bốc lấy nó luôn
                if "facebook.com" in url:
                    fb_tab = tab
            except Exception:
                pass

        if not fb_tab:
            print("❌ Không tìm thấy tab Facebook nào được sinh ra!")
            return None, None

        print("🎉 Đã tóm được đúng Tab Facebook mới mở.")
        
        # Chờ thêm một khoảng nhỏ dự phòng cho Facebook tại tab mới nạp xong dữ liệu
        print("⏳ Đợi thêm 3.5 giây cho Facebook nạp toàn bộ bài viết trên tab mới...")
        await asyncio.sleep(3.5)

        current_url = str(fb_tab.url).lower()
        print(f"🔗 URL hiện tại của Tab Facebook: {current_url}")

        if "login" in current_url or "checkpoint" in current_url:
            print("❌ Thất bại: Facebook tại tab này chặn bắt Login rồi!")
            return None, None

        print("🎉 Đã vào được Facebook hợp lệ.")
        print("📜 Tiến hành cuộn trang (Scroll)...")

        for round_idx in range(2):
            print(f"🔄 Round {round_idx + 1}/2")
            try:
                await fb_tab.evaluate("window.scrollBy(0, 3000);")
            except Exception:
                pass
            await asyncio.sleep(2.0)

        print("📸 Lấy dữ liệu HTML...")
        html = await fb_tab.get_content()
        page_path = f"fb_page_{business_id}.html"

        with open(page_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"💾 Đã lưu {page_path} ({len(html):,} ký tự)")
        return page_path, None

    except Exception as e:
        print("❌ Lỗi toàn cục hàm Facebook:", e)
        traceback.print_exc()
        return None, None

    finally:
        print("⏳ Đóng trình duyệt...")
        try:
            if browser:
                await browser.stop()
                await asyncio.sleep(0.5)  # Tránh lỗi Event loop is closed
        except Exception:
            pass




async def main():
    fb_url = "https://www.facebook.com/mocseafood"
    print(f"🔥 Bắt đầu test hàm với URL: {fb_url}")
    
    page, popup = await _scrape_facebook(
        fb_url=fb_url, 
        headless=False,       
        business_id="test_id_001"
    )
    
    print("\n==============================")
    print(f"🎉 KẾT QUẢ TRẢ VỀ:\n- Page HTML Path: {page}")
    print("==============================")

if __name__ == "__main__":
    asyncio.run(main())