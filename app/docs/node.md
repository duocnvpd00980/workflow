Node,Nhiệm vụ chính (Trách nhiệm duy nhất)
INPUT_GUARD,"Chặn các yêu cầu độc hại (PII, injection), chuẩn hóa định dạng đầu vào và thực hiện giới hạn tốc độ (rate limit)."
HEURISTIC_ROUTER,"Phân loại mục đích người dùng (Intent Classification) dựa trên từ khóa/quy tắc, quyết định luồng đi tiếp theo."
CACHE_LAYER,"Kiểm tra bộ nhớ đệm (Semantic Cache); nếu trùng khớp, trả về ngay lập tức để tiết kiệm chi phí/latency."
KNOWLEDGE_BASE,"Truy vấn dữ liệu từ Vector DB, thực hiện tìm kiếm ngữ nghĩa và lấy context phù hợp."
RELEVANCE_CHECK,"Đánh giá độ tin cậy và liên quan của kết quả từ KB; nếu không đạt, đẩy luồng sang fallback."
FALLBACK_SEARCH,Thực hiện tìm kiếm web (Tool execution) khi KB không có thông tin hoặc độ tin cậy thấp.
GENERATION,"LLM thực hiện tổng hợp thông tin, viết câu trả lời theo yêu cầu/tông giọng."
OUTPUT_GUARD,"Lọc nội dung cuối cùng, đảm bảo không chứa thông tin nhạy cảm, định dạng lại text sạch."
FINAL_RESPONSE,"Đóng gói kết quả cuối cùng, đính kèm telemetry/logs và trả về cho người dùng (End session)."