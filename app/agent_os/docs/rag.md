Người dùng hỏi
    ↓
[1] Query Expansion (LLM mở rộng 3-5 cách diễn đạt)
    ↓
[2] Chạy song song:
    ├── BM25 keyword search → top 10
    └── Vector search (FAISS) → top 10
    ↓
[3] Metadata filter: Loại kết quả sai category/tag
    ↓
[4] Fusion (RRF): Gộp BM25 + Vector, loại trùng, xếp hạng lại
    ↓
[5] Semantic filter: Loại "từ giống nghĩa khác" (score < 0.7)
    ↓
[6] Chỉ giữ top 3
    ↓
Đưa context cho LLM sinh câu trả lời




===============

Tài liệu mới đến
    ↓
[1] Kiểm tra duplicate (hash content)
    ├── Đã tồn tại → Bỏ qua (skip)
    └── Mới → Tiếp tục
    ↓
[2] Flat chunking (512 tokens, 1 cấp)
    ├── Không chia Mẹ-Con
    └── Mỗi chunk độc lập
    ↓
[3] Enrich metadata cho mỗi chunk
    ├── tag: ["thưởng", "lương", "Tết"]
    ├── category: "chính sách nhân sự"
    ├── source_id: "policy_2024_001"
    └── hypothetical_questions: ["Tiền thưởng cuối năm?", "Lương tháng 13 khi nào?"]
    ↓
[4] Tính embedding (FastEmbed, chạy trong ThreadPool)
    ↓
[5] Ghi song song:
    ├── FAISS index (vector, in-memory) → batch 50 chunks
    ├── BM25 index (text, inverted index) → batch 50 chunks
    └── Postgres (metadata only, không full text) → batch 50 rows
    ↓
[6] Persist FAISS xuống disk (async, không block)
    └── Mỗi 5 phút hoặc sau mỗi 100 chunks mới





======================


Khi UPDATE/XÓA tài liệu:
    ↓
[1] Đánh dấu trong Postgres metadata
    ├── status = "deleted" hoặc "outdated"
    └── deleted_at = timestamp
    ↓
[2] Không xóa ngay trong FAISS/BM25 (tốn kém)
    ↓
[3] Khi retrieval, LỌC BỎ kết quả có status = "deleted"
    ↓
[4] REBUILD index FAISS + BM25 khi:
    ├── Đạt ngưỡng: 10% tài liệu bị mark deleted
    ├── Hoặc: 1 giờ không có query nào (low traffic)
    └── Hoặc: 4h sáng hàng ngày (cron job)
    ↓
[5] Rebuild = tạo index mới từ Postgres (chỉ lấy status="active")
    ├── Export toàn bộ active documents
    ├── Flat chunking lại
    ├── Tạo FAISS index mới
    ├── Tạo BM25 index mới
    └── Swap atomically (không downtime)













==================


Người dùng hỏi
    ↓
[1] Exact Cache L1 (Redis/dict trong RAM)
    ├── Câu hỏi y hệt đã hỏi? → Trả lời ngay (0ms, 0 token, 0 CPU ngoài dict lookup)
    └── Không → Tiếp tục
    ↓
[2] Semantic Cache L2 (FAISS cache embedding câu hỏi + câu trả lời)
    ├── Embedding câu hỏi gần với cache? → Trả lời ngay (5ms, 0 token)
    └── Không → Tiếp tục
    ↓
[3] Fuzzy + Synonym Expansion (local, không LLM, không API)
    ├── rapidfuzz sửa typo
    ├── Synonym dict domain thay từ đồng nghĩa
    └── Sinh ra 2-3 biến thể câu hỏi
    ↓
[4] Chạy song song (tất cả local, CPU-only):
    ├── BM25 keyword search → top 10
    └── Vector search (FAISS) → top 10
    ↓
[5] Metadata filter (local, không DB call nếu metadata đã trong FAISS)
    ↓
[6] Fusion RRF (công thức toán học đơn giản, không ML)
    ↓
[7] Threshold filter: Score > 0.7, loại rác
    ↓
[8] Nếu top 1 score > 0.85 → Trả lời trực tiếp từ text (không qua LLM)
    └── Nếu score 0.7-0.85 → Trả lời template + context (không qua LLM)
    └── Nếu score < 0.7 → Fallback "Tôi không có thông tin này" (không qua LLM)
    ↓
[9] Cache kết quả vào L1 + L2




























