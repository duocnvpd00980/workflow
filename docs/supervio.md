# Supervisor AI — Đặc tả chức năng

> Tài liệu này mô tả vai trò, logic hoạt động, và nhiệm vụ cụ thể của Supervisor AI trong hệ thống marketing tự động. Dành cho dev đọc và implement.

---

## 1. Vai trò tổng quan

Supervisor là node trung tâm duy nhất giao tiếp trực tiếp với khách hàng. Nó đóng vai trò như một trợ lý tiếp nhận yêu cầu — tự quyết định xử lý ngay hay phân công cho các agent chuyên biệt ở giai đoạn 2.

Toàn bộ giai đoạn 1 (hiểu ý) xảy ra bên trong Supervisor. Không có node nào khác tham gia vào giai đoạn này.

---

## 2. Hai chế độ hoạt động

### Chế độ 1 — Tự xử (Direct Response)

Supervisor tự trả lời trong chat mà không khởi động bất kỳ agent nào.

Áp dụng khi:
- Khách hỏi thông tin (ngày lễ, xu hướng, đối thủ, dữ liệu)
- Khách đang brainstorm, chưa có yêu cầu rõ ràng
- Câu hỏi không liên quan đến sản xuất nội dung
- Khách muốn vờn, trao đổi, làm rõ ý tưởng

Supervisor dùng tool của chính nó để xử lý (xem mục 5), trả lời trực tiếp, rồi chờ phản hồi tiếp theo từ khách. Không hỏi "bạn có muốn tôi tạo nội dung không?" sau mỗi câu trả lời.

### Chế độ 2 — Phân công (Dispatch)

Supervisor thu thập đủ thông tin, xác nhận với khách, rồi khởi động giai đoạn 2.

Áp dụng khi:
- Khách ra lệnh sản xuất nội dung cụ thể (viết blog, chạy ads, làm social...)
- Có đủ 3 dấu hiệu: sản phẩm/chủ đề rõ + từ hành động rõ + (ngầm hiểu hoặc nói rõ) thời gian

Quy trình bắt buộc trước khi dispatch: hỏi thêm nếu thiếu thông tin → tóm tắt lại → chờ khách xác nhận → mới chạy.

---

## 3. Logic nhận diện mode

Supervisor phân tích tin nhắn của khách theo 3 dấu hiệu:

**Dấu hiệu "Hỏi / tìm hiểu":**
- Câu có dạng câu hỏi: "có không", "nên không", "là gì", "như thế nào"
- Hỏi về thông tin bên ngoài: ngày lễ, xu hướng, đối thủ, thị trường
- Không nhắc đến sản phẩm cụ thể nào của doanh nghiệp

**Dấu hiệu "Brainstorm / vờn":**
- Dùng từ mơ hồ: "nghĩ", "hay là", "kiểu như", "không biết có nên"
- Không có deadline hoặc kênh cụ thể
- Đang so sánh ý tưởng, chưa chốt hướng

**Dấu hiệu "Ra lệnh thật":**
- Có sản phẩm hoặc chủ đề cụ thể
- Có từ hành động rõ: "làm", "viết", "chạy", "đăng", "tạo"
- Có yếu tố thời gian: "hôm nay", "tuần này", "gấp", hoặc ngầm hiểu là ngay

Nếu chỉ có 1-2 dấu hiệu của "Ra lệnh" → vẫn coi là chưa đủ, tiếp tục hỏi làm rõ trước khi dispatch.

---

## 4. Quy trình hỏi — tóm tắt — xác nhận

Chỉ áp dụng khi đã xác định là chế độ 2.

**Bước 1 — Kiểm tra thông tin còn thiếu**

Supervisor đối chiếu yêu cầu của khách với hồ sơ doanh nghiệp đã lưu sẵn. Những gì đã có trong hồ sơ thì không hỏi lại.

Thông tin lưu trong hồ sơ (không bao giờ hỏi lại):
- Tên thương hiệu, ngành hàng
- Tone giọng mặc định
- Kênh đăng mặc định
- Style ảnh, màu sắc thương hiệu

Thông tin cần hỏi nếu chưa có trong câu:
- Sản phẩm hoặc chủ đề cụ thể
- Mục tiêu (tăng đơn, tăng nhận diện, giới thiệu món mới...)
- Thời gian đăng (nếu chưa nói)
- Ưu đãi hoặc thông điệp đặc biệt (nếu có)

Tối đa 3 câu hỏi mỗi lần. Nếu cần hỏi hơn 3 câu → hồ sơ doanh nghiệp chưa đủ, không phải lỗi của khách. Cần bổ sung hồ sơ.

**Bước 2 — Tự suy những gì có thể suy**

Trước khi hỏi, Supervisor tự điền những thông tin có thể suy luận hợp lý:
- Khách nói "đăng hôm nay" nhưng không nói giờ → tự chọn giờ vàng phù hợp ngành
- Khách không đề cập tone → dùng tone mặc định trong hồ sơ
- Khách nói "quảng cáo" mà không nói kênh → dùng kênh mặc định trong hồ sơ

**Bước 3 — Tóm tắt lại toàn bộ**

Sau khi đủ thông tin, Supervisor tóm tắt lại bằng ngôn ngữ tự nhiên, rõ ràng:
- Làm gì
- Cho kênh nào
- Tone gì
- Đăng lúc nào
- Có ưu đãi gì không

**Bước 4 — Chờ xác nhận**

Supervisor không tự động chạy. Phải có hành động xác nhận rõ ràng từ khách (bấm nút hoặc gõ xác nhận). Nếu khách muốn sửa → quay lại bước 1, không dispatch.

---

## 5. Tools Supervisor được dùng

Đây là những tool Supervisor có thể gọi trực tiếp trong chế độ 1 mà không cần qua agent nào.

**Web search** — tìm kiếm thông tin bên ngoài: ngày lễ, xu hướng thị trường, thông tin đối thủ, tin tức liên quan ngành.

**Đọc hồ sơ doanh nghiệp** — tra cứu thông tin đã lưu sẵn: tone, kênh mặc định, lịch sử các lần chạy, sản phẩm thường đăng.

**Đọc lịch sử chat** — xem lại các yêu cầu và kết quả trước đó trong cùng session hoặc các session gần nhất.

**Tính toán / lên lịch** — tính giờ vàng, đề xuất lịch đăng, so sánh số liệu đơn giản nếu có dữ liệu sẵn.

**Truy vấn CSDL nội bộ** — đọc dữ liệu từ 3 bảng nội bộ để trả lời các câu hỏi liên quan đến lịch sử, nội dung cũ, và tài nguyên hệ thống. Supervisor chỉ được đọc, không ghi trực tiếp — việc ghi do các agent và hệ thống tự thực hiện sau mỗi lần chạy.

Supervisor không gọi tool của các agent chuyên biệt (Research, Blog, Ads...) trực tiếp. Nếu cần chạy các agent đó, phải đi qua quy trình xác nhận trước.

---

## 5a. Cấu trúc CSDL nội bộ Supervisor cần biết

Supervisor truy vấn 3 bảng sau. Dev cần đảm bảo các bảng này tồn tại và được ghi đầy đủ sau mỗi lần chạy giai đoạn 2.

### Bảng `runs` — lịch sử các lần chạy

Mỗi lần khách xác nhận và giai đoạn 2 được khởi động, hệ thống tạo 1 record vào bảng này.

| Trường | Kiểu | Mô tả |
|---|---|---|
| run_id | string / uuid | ID duy nhất của lần chạy |
| created_at | timestamp | Thời điểm bắt đầu chạy |
| request_summary | text | Tóm tắt yêu cầu ban đầu của khách |
| agents_used | array | Danh sách agent đã chạy, ví dụ: ["research","blog","qa","publisher"] |
| channels | array | Kênh đã đăng: ["facebook", "wordpress"...] |
| status | string | success / partial / failed |
| qa_score | number | Điểm chất lượng do QA agent chấm (0–10) |
| published_at | timestamp | Thời điểm đăng thực tế (null nếu chưa đăng) |

Dùng để trả lời: "Đã làm bao nhiêu bài?", "Tuần này chạy mấy lần?", "Bài nào QA chấm cao nhất?"

### Bảng `outputs` — nội dung đầu ra

Mỗi agent tạo ra nội dung thì ghi 1 record vào bảng này, liên kết với run_id tương ứng.

| Trường | Kiểu | Mô tả |
|---|---|---|
| output_id | string / uuid | ID duy nhất |
| run_id | string | Liên kết với bảng runs |
| agent | string | Agent tạo ra nội dung: blog / ads / social / image |
| content_type | string | Loại nội dung: blog_post / fb_ad / caption / image_url |
| content | text | Nội dung thực tế (hoặc URL nếu là ảnh) |
| created_at | timestamp | Thời điểm tạo |
| channel | string | Kênh đăng tương ứng |

Dùng để trả lời: "Cho tôi xem lại bài blog tuần trước", "Copy quảng cáo tháng 6 đâu rồi?", "Ảnh đã tạo hôm qua là gì?"

Khi trả về nội dung cũ cho khách: nếu có nhiều hơn 1 kết quả thì Supervisor liệt kê tóm tắt (tiêu đề + ngày tạo) để khách chọn xem cái nào, không dump hết một lúc.

### Bảng `usage` — tracking tài nguyên

Ghi lại lượng token tiêu thụ sau mỗi lần gọi API trong toàn hệ thống.

| Trường | Kiểu | Mô tả |
|---|---|---|
| usage_id | string / uuid | ID duy nhất |
| run_id | string | Liên kết với lần chạy (null nếu là Supervisor trả lời trực tiếp) |
| agent | string | Agent nào gọi API: supervisor / research / blog / ads... |
| tokens_input | number | Token đầu vào |
| tokens_output | number | Token đầu ra |
| tokens_total | number | Tổng token lần gọi đó |
| called_at | timestamp | Thời điểm gọi |
| model | string | Model đã dùng |

Dùng để trả lời: "Còn bao nhiêu token?", "Tháng này dùng hết chưa?", "Lần chạy vừa rồi tốn bao nhiêu?"

Quota giới hạn theo tháng được cấu hình riêng trong hồ sơ doanh nghiệp. Supervisor đọc tổng usage trong tháng hiện tại rồi so với quota để trả lời.

---

## 6. Quyết định agent nào được chạy

Sau khi khách xác nhận, Supervisor tạo ra một danh sách agent cần chạy dựa trên yêu cầu. Hệ thống chỉ khởi động đúng những agent có trong danh sách, bỏ qua phần còn lại.

Mapping tham khảo:

| Yêu cầu | Agent được chạy |
|---|---|
| Viết blog SEO | Research → Blog → QA → Publisher |
| Chạy ads Facebook | Research → Ads → QA → Publisher |
| Làm social media | Research → Social → Image → QA → Publisher |
| Full campaign | Research → Blog + Ads + Social + Image (song song) → QA → Publisher |
| Research báo cáo thôi | Research → Report |
| Chỉ tạo ảnh | Image → QA → Publisher |

Research agent chạy trước nếu yêu cầu cần dữ liệu thực tế (xu hướng, từ khoá, insight). Với yêu cầu không cần research (ví dụ: tạo ảnh theo brief đã có sẵn) thì bỏ qua.

QA agent chỉ chạy khi có nội dung cần kiểm tra. Publisher agent chỉ chạy khi có nội dung cần đăng. Report agent chỉ chạy khi yêu cầu là tóm tắt / phân tích, không có nội dung đăng bài.

---

## 7. Những điều Supervisor không được làm

- Không tự động dispatch sau khi trả lời câu hỏi, dù câu trả lời có liên quan đến nội dung marketing
- Không hỏi quá 3 câu trong một lượt
- Không hỏi lại thông tin đã có trong hồ sơ doanh nghiệp
- Không chào hàng dịch vụ sau mỗi câu trả lời ("muốn tôi tạo nội dung không?")
- Không bắt đầu chạy agent khi chưa có xác nhận rõ ràng từ khách
- Không tự ý thay đổi yêu cầu đã được xác nhận khi đang chạy

---

## 8. Ví dụ minh hoạ theo từng tình huống

**Tình huống 1 — Khách hỏi thông tin**

> Khách: "Tháng 7 có ngày lễ gì đáng đăng không?"

Supervisor gọi web search, trả lời trực tiếp, gợi ý nhẹ một hướng nếu phù hợp, rồi để mở. Không hỏi "muốn làm bài không?".

**Tình huống 2 — Khách brainstorm**

> Khách: "Hay là mình làm gì đó cho mùa hè nhỉ..."

Supervisor gợi ý 2-3 hướng ngắn gọn, hỏi khách muốn đi theo hướng nào. Không chốt, không dispatch.

**Tình huống 3 — Khách ra lệnh đủ thông tin**

> Khách: "Làm bài đăng Facebook cho bánh mì thịt nướng hôm nay, tone vui"

Supervisor kiểm tra: đã có sản phẩm, kênh, tone, thời gian. Còn thiếu: có ưu đãi không? Hỏi 1 câu → khách trả lời → tóm tắt → xác nhận → dispatch.

**Tình huống 4 — Khách chỉ muốn research**

> Khách: "Mày research xem đối thủ đang chạy gì rồi báo tao"

Supervisor xác nhận ngắn ("Tôi sẽ research và báo cáo lại, không đăng bài nhé?") → khách OK → dispatch Research + Report, không chạy các agent nội dung.

**Tình huống 5 — Khách hỏi lịch sử sản xuất**

> Khách: "Tháng này mình đã đăng bao nhiêu bài rồi?"

Supervisor truy vấn bảng `runs`, lọc theo tháng hiện tại và status = success, đếm số record rồi trả lời trực tiếp. Không dispatch agent nào.

**Tình huống 6 — Khách muốn xem lại nội dung cũ**

> Khách: "Cho tôi xem lại bài quảng cáo tuần trước"

Supervisor truy vấn bảng `outputs`, lọc agent = ads và created_at trong 7 ngày gần nhất. Nếu có nhiều hơn 1 kết quả thì liệt kê tóm tắt (kênh + ngày tạo) để khách chọn, sau đó trả về nội dung cụ thể. Không dispatch agent nào.

**Tình huống 7 — Khách hỏi token còn lại**

> Khách: "Tháng này còn bao nhiêu token?"

Supervisor truy vấn bảng `usage`, cộng dồn tokens_total trong tháng hiện tại, so với quota trong hồ sơ doanh nghiệp, trả lời số đã dùng và số còn lại. Không dispatch agent nào.

---

## 9. Điểm cần làm rõ khi implement

Những vấn đề chưa được chốt, dev cần confirm với team trước khi build:

- Hồ sơ doanh nghiệp lưu ở đâu và cập nhật như thế nào
- Cơ chế xác nhận: nút bấm hay gõ text đều tính?
- Nếu khách xác nhận rồi muốn huỷ giữa chừng thì Supervisor xử lý thế nào
- Session và lịch sử chat lưu bao lâu, Supervisor đọc được bao nhiêu context
- Khi Supervisor không chắc chắn về mode (hỏi hay ra lệnh) thì mặc định về chế độ nào
- Quota token giới hạn theo tháng là bao nhiêu, lưu ở đâu trong hồ sơ doanh nghiệp
- Bảng `outputs` lưu full content hay chỉ lưu reference/URL — cần xác định trước khi thiết kế storage
- Khi khách hỏi "bài nào hay nhất" thì xếp theo qa_score hay theo tương tác thực tế — nếu theo tương tác thì cần thêm trường performance vào bảng `runs`
- Dữ liệu trong 3 bảng giữ bao lâu trước khi archive hoặc xoá