
prompt_docs = """
# 📋 PROMPT DOCS: TÁI CẤU TRÚC RAG SYSTEM - FASTEMBED + FAISS + BM25 HYBRID

## 🎯 MỤC TIÊU
Chuyển dự án RAG hiện tại (pgvector + Hierarchical RAG + Cross-encoder Rerank) sang kiến trúc nhẹ, nhanh, ổn định trên VPS CPU. Yêu cầu: nhẹ, nhanh, hiệu quả CPU, không GPU.

## 🖥️ MÔI TRƯỜNG
- VPS CPU (không GPU)
- 32GB RAM + 4GB VRAM
- Chạy LangGraph + Django + React cùng lúc
- Cloudflare Tunnel (remote access)
- Dữ liệu: quy định công ty, FAQ, chính sách nội bộ (< 1000 tài liệu, mỗi tài liệu ngắn < 500 từ)
- Ngôn ngữ: Tiếng Việt + tiếng Anh technical terms

## ❌ VẤN ĐỀ HIỆN TẠI (code cũ)

### Ingestion Service vấn đề:
1. Hierarchical chunking (Mẹ 1024 + Con 256) overkill cho dữ liệu ngắn
2. Mẹ lưu Postgres, Con lưu FAISS → 2 nơi, N+1 query khi retrieval
3. Không batch insert → insert từng dòng vào DB
4. Không deduplication trước parse → waste CPU re-ingest
5. Chunking chạy sync, block event loop
6. `_parent_text_cache` chỉ cache data mới, data cũ vẫn hit DB

### Retrieval Service vấn đề:
1. N+1 query: `_resolve_parent_text()` gọi DB từng node riêng lẻ
2. Rerank chạy sync (cross-encoder ONNX), block toàn bộ event loop
3. Không timeout, không semaphore giới hạn concurrent rerank
4. Threshold 0.55 quá thấp → lấy rác (từ giống nhưng nội dung khác)
5. Không lọc metadata → "public code" ra "public holiday"
6. Không query expansion → "tiền thưởng cuối năm" không ra "thưởng tháng 13"

### Tổng quan:
- Rerank đắt: 100-500ms, ngốn CPU, giảm throughput 10-20x
- Hierarchical RAG không phù hợp dữ liệu ngắn
- 2 hệ thống lưu trữ (Postgres + FAISS) phức tạp, không cần thiết

## ✅ KIẾN TRÚC MỚI (đề xuất)

### Tổng thể: Hybrid Search = BM25 + Vector + Metadata

```
Người dùng hỏi
    ↓
[1] Query Expansion (LLM mở rộng 3-5 cách diễn đạt)
    ↓
[2] Chạy song song:
    ├── BM25 keyword search → top 10
    ├── Vector search (FAISS) → top 10
    └── Metadata filter → chỉ giữ đúng category/tag
    ↓
[3] Reciprocal Rank Fusion (RRF): Gộp kết quả, loại trùng, xếp hạng lại
    ↓
[4] Semantic filter: Loại kết quả từ giống nhưng nội dung khác
    ↓
[5] Chỉ giữ top 3 có score > 0.7
    ↓
[6] Đưa context cho LLM sinh câu trả lời
```

### Thành phần chi tiết:

#### 1. Ingestion Pipeline (đơn giản hóa)
- **Bỏ Hierarchical chunking** → dùng Flat chunking 512 tokens (1 cấp)
- **Bỏ Mẹ-Con separation** → tất cả lưu FAISS + metadata
- **Batch insert**: Gom 50 nodes ghi 1 lần
- **Deduplication trước parse**: Hash content, skip nếu đã tồn tại
- **Async chunking**: Chạy trong ThreadPool, không block event loop
- **Metadata enrichment**: Mỗi đoạn gán tag domain, category, synonyms
- **Query hypothetical**: Tự đặt 3-5 câu hỏi giả định cho mỗi đoạn → lưu cả câu hỏi vào index

#### 2. Retrieval Pipeline (tối ưu)
- **Singleton FAISS index**: Load 1 lần khi startup, giữ trong RAM
- **Async I/O**: Non-blocking, handle nhiều concurrent request
- **ThreadPool cho CPU-intensive**: Chunking, embedding, rerank chạy riêng
- **Semaphore giới hạn**: Tối đa 3 concurrent rerank
- **Batch pre-fetch parents**: 1 query lấy hết, không N+1
- **Query expansion**: Dùng LLM hoặc từ điển đồng nghĩa domain
- **HyDE (Hypothetical Document Embedding)**: LLM viết đoạn giả định chứa câu trả lời → tìm theo đoạn giả định
- **Threshold nâng cao**: 0.55 → 0.7
- **Light Rerank**: Dùng keyword boost hoặc Tiny model (15MB), không cross-encoder nặng

#### 3. Storage
- **FAISS**: Index vector in-memory (chỉ lưu con, không mẹ)
- **BM25 index**: Whoosh hoặc rank-bm25 (index văn bản thuần)
- **Postgres (tùy chọn)**: Chỉ lưu metadata, không lưu full text parent
- **Persist FAISS**: Ghi xuống disk mỗi 5 phút / sau mỗi batch ingest
- **Backup**: Copy thư mục persist ra S3/backup server

#### 4. Routing & Guard
- **Intent Router**: Semantic routing dùng FastEmbed, cache kết quả
- **Input Guard**: Chặn từ khóa nguy hiểm, không block event loop
- **Semantic Cache L2**: Cache câu trả lời cho câu hỏi tương tự

## 📦 THƯ VIỆN & STACK

### Core:
- `fastembed` (embedding, ONNX Runtime, CPU-optimized)
- `faiss-cpu` (vector search in-memory)
- `rank-bm25` hoặc `whoosh` (BM25 keyword search)
- `llama-index-core` (framework RAG)
- `asyncio` + `ThreadPoolExecutor` (async I/O)

### Optional:
- `rapidfuzz` (fuzzy matching nhanh)
- `sentence-transformers` (nếu cần model custom)

### Không dùng:
- ❌ pgvector (loại bỏ)
- ❌ Cross-encoder reranker nặng (loại bỏ)
- ❌ HierarchicalNodeParser (loại bỏ)
- ❌ PostgreSQL docstore cho full text (giảm dùng)

## 📊 BENCHMARK MONG ĐỢI

| Metric | Code cũ | Code mới |
|---|---|---|
| Query latency | 2-5 giây | 50-200ms |
| Throughput | 50-100 QPS | 800-1200 QPS |
| RAM tiêu thụ | ~800MB+ | ~200MB |
| CPU usage | Cao (block) | Thấp (async) |
| Setup phức tạp | Cao (Postgres + extension) | Thấp (pip install) |
| Độ chính xác | 70% (rác, miss) | 85%+ (hybrid filter) |

## 🔧 IMPLEMENTATION CHECKLIST

### Phase 1: Core (bắt buộc)
- [ ] Singleton FAISS index manager (load 1 lần, giữ RAM)
- [ ] Flat chunking 512 tokens, bỏ Hierarchical
- [ ] Batch insert nodes (50/batch)
- [ ] Deduplication trước parse (SHA256 content hash)
- [ ] Async ingestion với ThreadPool
- [ ] BM25 index song song với FAISS
- [ ] Hybrid retrieval: BM25 + Vector + Metadata filter
- [ ] Reciprocal Rank Fusion (RRF) gộp kết quả
- [ ] Threshold 0.7, loại rác semantic

### Phase 2: Optimization (nên có)
- [ ] Query expansion (LLM hoặc synonym dictionary)
- [ ] HyDE (Hypothetical Document Embedding)
- [ ] Semantic cache L2
- [ ] Intent router cached
- [ ] Periodic persist FAISS (cron 5 phút)
- [ ] Backup index file ra S3

### Phase 3: Polish (nice to have)
- [ ] Light rerank Tiny model (nếu cần)
- [ ] Connection pool Postgres (nếu vẫn giữ metadata)
- [ ] Monitoring: latency, hit rate, cache miss
- [ ] A/B test: BM25-only vs Hybrid vs Vector-only

## ⚠️ LƯU Ý QUAN TRỌNG

1. **FAISS in-memory = volatile**: Crash = mất data nếu chưa persist. Bắt buộc persist định kỳ.
2. **FAISS không thread-safe khi write**: Nhiều worker Django cùng ghi → dùng queue (Redis/Celery) hoặc lock.
3. **BM25 không bắt được ý nghĩa sâu**: Câu hỏi so sánh, tóm tắt → vẫn cần vector.
4. **Hybrid = phức tạp hơn**: Nếu dữ liệu thực sự < 100 đoạn ngắn → BM25 đơn độc đã đủ.
5. **FastEmbed model**: Dùng `BAAI/bge-small-en-v1.5` (384-dim, 67MB). Nếu cần nhạy hơn → `BAAI/bge-base-en-v1.5` (768-dim, 110MB).

## 🎯 QUYẾT ĐỊNH CUỐI

| Dữ liệu | Kiến trúc |
|---|---|
| < 100 đoạn ngắn | BM25-only |
| 100-1000 đoạn | BM25 + Metadata filter |
| 1000-10000 đoạn | Hybrid: BM25 + Vector + Metadata |
| > 10000 đoạn | Hybrid + Index partitioning + CDC |

Với bài toán hiện tại (quy định công ty, FAQ): **Hybrid BM25 + Vector là lựa chọn tối ưu** — vừa bắt được từ khóa chính xác, vừa bắt được ý nghĩa đồng nghĩa, vừa lọc rác bằng metadata.

---
END PROMPT DOCS
"""

# Save to file
with open('/mnt/agents/output/RAG_REFACTOR_PROMPT_DOCS.md', 'w', encoding='utf-8') as f:
    f.write(prompt_docs)

print("✅ Prompt docs saved successfully!")
print(f"Length: {len(prompt_docs)} characters")

prompt_docs = """
# 📋 PROMPT DOCS: TÁI CẤU TRÚC RAG SYSTEM - FASTEMBED + FAISS + BM25 HYBRID

## 🎯 MỤC TIÊU
Chuyển dự án RAG hiện tại (pgvector + Hierarchical RAG + Cross-encoder Rerank) sang kiến trúc nhẹ, nhanh, ổn định trên VPS CPU. Yêu cầu: nhẹ, nhanh, hiệu quả CPU, không GPU.

## 🖥️ MÔI TRƯỜNG
- VPS CPU (không GPU)
- 32GB RAM + 4GB VRAM
- Chạy LangGraph + Django + React cùng lúc
- Cloudflare Tunnel (remote access)
- Dữ liệu: quy định công ty, FAQ, chính sách nội bộ (< 1000 tài liệu, mỗi tài liệu ngắn < 500 từ)
- Ngôn ngữ: Tiếng Việt + tiếng Anh technical terms

## ❌ VẤN ĐỀ HIỆN TẠI (code cũ)

### Ingestion Service vấn đề:
1. Hierarchical chunking (Mẹ 1024 + Con 256) overkill cho dữ liệu ngắn
2. Mẹ lưu Postgres, Con lưu FAISS → 2 nơi, N+1 query khi retrieval
3. Không batch insert → insert từng dòng vào DB
4. Không deduplication trước parse → waste CPU re-ingest
5. Chunking chạy sync, block event loop
6. `_parent_text_cache` chỉ cache data mới, data cũ vẫn hit DB

### Retrieval Service vấn đề:
1. N+1 query: `_resolve_parent_text()` gọi DB từng node riêng lẻ
2. Rerank chạy sync (cross-encoder ONNX), block toàn bộ event loop
3. Không timeout, không semaphore giới hạn concurrent rerank
4. Threshold 0.55 quá thấp → lấy rác (từ giống nhưng nội dung khác)
5. Không lọc metadata → "public code" ra "public holiday"
6. Không query expansion → "tiền thưởng cuối năm" không ra "thưởng tháng 13"

### Tổng quan:
- Rerank đắt: 100-500ms, ngốn CPU, giảm throughput 10-20x
- Hierarchical RAG không phù hợp dữ liệu ngắn
- 2 hệ thống lưu trữ (Postgres + FAISS) phức tạp, không cần thiết

## ✅ KIẾN TRÚC MỚI (đề xuất)

### Tổng thể: Hybrid Search = BM25 + Vector + Metadata

```
Người dùng hỏi
    ↓
[1] Query Expansion (LLM mở rộng 3-5 cách diễn đạt)
    ↓
[2] Chạy song song:
    ├── BM25 keyword search → top 10
    ├── Vector search (FAISS) → top 10
    └── Metadata filter → chỉ giữ đúng category/tag
    ↓
[3] Reciprocal Rank Fusion (RRF): Gộp kết quả, loại trùng, xếp hạng lại
    ↓
[4] Semantic filter: Loại kết quả từ giống nhưng nội dung khác
    ↓
[5] Chỉ giữ top 3 có score > 0.7
    ↓
[6] Đưa context cho LLM sinh câu trả lời
```

### Thành phần chi tiết:

#### 1. Ingestion Pipeline (đơn giản hóa)
- **Bỏ Hierarchical chunking** → dùng Flat chunking 512 tokens (1 cấp)
- **Bỏ Mẹ-Con separation** → tất cả lưu FAISS + metadata
- **Batch insert**: Gom 50 nodes ghi 1 lần
- **Deduplication trước parse**: Hash content, skip nếu đã tồn tại
- **Async chunking**: Chạy trong ThreadPool, không block event loop
- **Metadata enrichment**: Mỗi đoạn gán tag domain, category, synonyms
- **Query hypothetical**: Tự đặt 3-5 câu hỏi giả định cho mỗi đoạn → lưu cả câu hỏi vào index

#### 2. Retrieval Pipeline (tối ưu)
- **Singleton FAISS index**: Load 1 lần khi startup, giữ trong RAM
- **Async I/O**: Non-blocking, handle nhiều concurrent request
- **ThreadPool cho CPU-intensive**: Chunking, embedding, rerank chạy riêng
- **Semaphore giới hạn**: Tối đa 3 concurrent rerank
- **Batch pre-fetch parents**: 1 query lấy hết, không N+1
- **Query expansion**: Dùng LLM hoặc từ điển đồng nghĩa domain
- **HyDE (Hypothetical Document Embedding)**: LLM viết đoạn giả định chứa câu trả lời → tìm theo đoạn giả định
- **Threshold nâng cao**: 0.55 → 0.7
- **Light Rerank**: Dùng keyword boost hoặc Tiny model (15MB), không cross-encoder nặng

#### 3. Storage
- **FAISS**: Index vector in-memory (chỉ lưu con, không mẹ)
- **BM25 index**: Whoosh hoặc rank-bm25 (index văn bản thuần)
- **Postgres (tùy chọn)**: Chỉ lưu metadata, không lưu full text parent
- **Persist FAISS**: Ghi xuống disk mỗi 5 phút / sau mỗi batch ingest
- **Backup**: Copy thư mục persist ra S3/backup server

#### 4. Routing & Guard
- **Intent Router**: Semantic routing dùng FastEmbed, cache kết quả
- **Input Guard**: Chặn từ khóa nguy hiểm, không block event loop
- **Semantic Cache L2**: Cache câu trả lời cho câu hỏi tương tự

## 📦 THƯ VIỆN & STACK

### Core:
- `fastembed` (embedding, ONNX Runtime, CPU-optimized)
- `faiss-cpu` (vector search in-memory)
- `rank-bm25` hoặc `whoosh` (BM25 keyword search)
- `llama-index-core` (framework RAG)
- `asyncio` + `ThreadPoolExecutor` (async I/O)

### Optional:
- `rapidfuzz` (fuzzy matching nhanh)
- `sentence-transformers` (nếu cần model custom)

### Không dùng:
- ❌ pgvector (loại bỏ)
- ❌ Cross-encoder reranker nặng (loại bỏ)
- ❌ HierarchicalNodeParser (loại bỏ)
- ❌ PostgreSQL docstore cho full text (giảm dùng)

## 📊 BENCHMARK MONG ĐỢI

| Metric | Code cũ | Code mới |
|---|---|---|
| Query latency | 2-5 giây | 50-200ms |
| Throughput | 50-100 QPS | 800-1200 QPS |
| RAM tiêu thụ | ~800MB+ | ~200MB |
| CPU usage | Cao (block) | Thấp (async) |
| Setup phức tạp | Cao (Postgres + extension) | Thấp (pip install) |
| Độ chính xác | 70% (rác, miss) | 85%+ (hybrid filter) |

## 🔧 IMPLEMENTATION CHECKLIST

### Phase 1: Core (bắt buộc)
- [ ] Singleton FAISS index manager (load 1 lần, giữ RAM)
- [ ] Flat chunking 512 tokens, bỏ Hierarchical
- [ ] Batch insert nodes (50/batch)
- [ ] Deduplication trước parse (SHA256 content hash)
- [ ] Async ingestion với ThreadPool
- [ ] BM25 index song song với FAISS
- [ ] Hybrid retrieval: BM25 + Vector + Metadata filter
- [ ] Reciprocal Rank Fusion (RRF) gộp kết quả
- [ ] Threshold 0.7, loại rác semantic

### Phase 2: Optimization (nên có)
- [ ] Query expansion (LLM hoặc synonym dictionary)
- [ ] HyDE (Hypothetical Document Embedding)
- [ ] Semantic cache L2
- [ ] Intent router cached
- [ ] Periodic persist FAISS (cron 5 phút)
- [ ] Backup index file ra S3

### Phase 3: Polish (nice to have)
- [ ] Light rerank Tiny model (nếu cần)
- [ ] Connection pool Postgres (nếu vẫn giữ metadata)
- [ ] Monitoring: latency, hit rate, cache miss
- [ ] A/B test: BM25-only vs Hybrid vs Vector-only

## ⚠️ LƯU Ý QUAN TRỌNG

1. **FAISS in-memory = volatile**: Crash = mất data nếu chưa persist. Bắt buộc persist định kỳ.
2. **FAISS không thread-safe khi write**: Nhiều worker Django cùng ghi → dùng queue (Redis/Celery) hoặc lock.
3. **BM25 không bắt được ý nghĩa sâu**: Câu hỏi so sánh, tóm tắt → vẫn cần vector.
4. **Hybrid = phức tạp hơn**: Nếu dữ liệu thực sự < 100 đoạn ngắn → BM25 đơn độc đã đủ.
5. **FastEmbed model**: Dùng `BAAI/bge-small-en-v1.5` (384-dim, 67MB). Nếu cần nhạy hơn → `BAAI/bge-base-en-v1.5` (768-dim, 110MB).

## 🎯 QUYẾT ĐỊNH CUỐI

| Dữ liệu | Kiến trúc |
|---|---|
| < 100 đoạn ngắn | BM25-only |
| 100-1000 đoạn | BM25 + Metadata filter |
| 1000-10000 đoạn | Hybrid: BM25 + Vector + Metadata |
| > 10000 đoạn | Hybrid + Index partitioning + CDC |

Với bài toán hiện tại (quy định công ty, FAQ): **Hybrid BM25 + Vector là lựa chọn tối ưu** — vừa bắt được từ khóa chính xác, vừa bắt được ý nghĩa đồng nghĩa, vừa lọc rác bằng metadata.

---
END PROMPT DOCS
"""

# Save to file
with open('/mnt/agents/output/RAG_REFACTOR_PROMPT_DOCS.md', 'w', encoding='utf-8') as f:
    f.write(prompt_docs)

print("✅ Prompt docs saved successfully!")
print(f"Length: {len(prompt_docs)} characters")
