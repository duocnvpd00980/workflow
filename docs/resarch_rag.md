Việc cần làm
RAG context cho content generation:

Thêm rag_context field vào BlogState
Viết hàm get_rag_context(business_id, topic) — keyword search FbPost + lấy final_report snippet + people_also_ask
Nhét vào user prompt trong template, không phải system prompt

Brand data bổ sung:

_normalize_brand_voice thêm default cho pronouns và topicsToAvoid
research_mapper truyền industry + products từ Business ORM vào business_context

Workflow:

Thêm group vào BlogState TypedDict (hiện thiếu)
Xóa _executor + _sync_run_workflow (đã fix bug rồi nhưng code cũ còn đó)

Sau này nếu cần:

Vector DB khi số lượng FbPost > 200
RAG cho email_sale và social_media graph