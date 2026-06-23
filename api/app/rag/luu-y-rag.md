from rank_bm25 import BM25Okapi  # pip install rank_bm25

def hybrid_search(query, captions, bm25_index, dense_search_fn, k=5, alpha=0.5):
    # 1. BM25 score (lexical)
    bm25_scores = bm25_index.get_scores(query.split())
    
    # 2. Dense score (BGE-M3, đã có sẵn search_by_text)
    dense_results = dense_search_fn(query, k=len(captions))
    dense_scores = {r["image_id"]: r["score"] for r in dense_results}
    
    # 3. Reciprocal Rank Fusion — gộp 2 ranking
    bm25_ranked = sorted(range(len(captions)), key=lambda i: -bm25_scores[i])
    dense_ranked = sorted(dense_scores, key=lambda iid: -dense_scores[iid])
    
    rrf_scores = {}
    for rank, idx in enumerate(bm25_ranked):
        rrf_scores[idx] = rrf_scores.get(idx, 0) + 1 / (rank + 60)
    for rank, iid in enumerate(dense_ranked):
        rrf_scores[iid] = rrf_scores.get(iid, 0) + 1 / (rank + 60)
    
    return sorted(rrf_scores.items(), key=lambda x: -x[1])[:k]


Lưu ý quan trọng — BGE-M3 đã tự có sparse embedding sẵn, không cần thêm BM25 library:
BGE-M3 (model bạn đang dùng) thực ra vốn được thiết kế để trả về cả 3 loại: dense + sparse (lexical, kiểu BM25) + multi-vector (ColBERT-style), nếu bạn dùng đúng cách (thường qua thư viện FlagEmbedding với return_sparse=True). Nếu Embedder của bạn hiện chỉ gọi dense embedding (encode() trả về 1 vector), bạn có thể không cần thêm rank_bm25 riêng — chỉ cần bật thêm sparse output từ chính BGE-M3, rồi gộp dense + sparse score theo công thức trên (chính là cách hybrid search chuẩn mà BGE-M3 khuyến nghị).
Bạn cho mình xem Embedder.encode() hiện đang gọi model BGE-M3 bằng cách nào (qua FlagEmbedding, hay qua HuggingFace transformers thông thường)? Nếu đang dùng FlagEmbedding, mình có thể chỉ chỗ bật sparse ngay trong code hiện tại mà không cần thêm thư viện BM25 mới.



-----------------


from FlagEmbedding import BGEM3FlagModel

model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)

output = model.encode(
    ["A man holding a large fish", "Cálua restaurant at night"],
    return_dense=True,
    return_sparse=True,       # <-- bật thêm sparse, không tốn model riêng
    return_colbert_vecs=False # multi-vector, bỏ qua như đã nói
)

dense_vecs = output['dense_vecs']                # (2, 1024) — giống cái bạn đang dùng
sparse_vecs = output['lexical_weights']          # list of dict {token_id: weight}



# Tính điểm dense (cosine/dot — giống FAISS bạn đang làm)
dense_score = dense_vecs[0] @ dense_vecs[1].T

# Tính điểm sparse (lexical match — thư viện tự tính sẵn)
sparse_score = model.compute_lexical_matching_score(
    sparse_vecs[0], sparse_vecs[1]
)

# Gộp điểm — trọng số tùy bạn chỉnh
final_score = 0.6 * dense_score + 0.4 * sparse_score


1. Embedder của bạn dùng SentenceTransformer, không phải FlagEmbedding
pythonfrom sentence_transformers import SentenceTransformer
...
self._model = SentenceTransformer(EMBED_MODEL)   # EMBED_MODEL = "BAAI/bge-m3"
SentenceTransformer.encode() chỉ trả dense vector — không có tham số return_sparse=True như FlagEmbedding.BGEM3FlagModel. Để lấy sparse của BGE-M3, bạn phải đổi sang load model qua FlagEmbedding, nghĩa là động vào cả pipeline text RAG đang chạy production (class Store, RAG...) — rủi ro không cần thiết chỉ để thêm tính năng cho ảnh.
→ Vậy gợi ý "dùng sparse sẵn có của BGE-M3" ở trên không khả thi trực tiếp với code hiện tại của bạn mà không đổi thư viện.
2. Bạn đã có sẵn pipeline BM25 + dense + RRF hoàn chỉnh — chỉ là đang dùng cho text chunks, chưa dùng cho ảnh
Nhìn class Store (cho text), nó đã làm đúng pattern hybrid search:
pythonbm25_hits = self._store.bm25(variants, RETRIEVE_K)      # BM25Okapi
vec_hits  = await self._store.vector(variants[0], RETRIEVE_K)  # dense BGE-M3
fused     = _rrf([bm25_hits, vec_hits], weights=weights)  # gộp bằng RRF
→ Cách hợp lý nhất, nhất quán với code đang có, ít rủi ro nhất: copy đúng pattern này sang cho ImageStore (trong image_rag.py) — tức thêm BM25 riêng cho caption, dùng lại _tokenize() và _rrf() đã có sẵn trong service.py, không cần đổi thư viện embedding.
Lưu ý quan trọng khác bạn nên biết: file service.py này đang có 2 bộ class ImageRAG/ImageStore/ImageCaptioner/ImageEmbedder dùng SigLIP — khác hoàn toàn với image_rag.py bạn gửi trước đó (dùng BGE-M3 caption-based, không dùng SigLIP). Đây là code trùng tên, có thể là bản cũ chưa xóa — nếu cả 2 file cùng tồn tại và đều được import ở đâu đó trong app, dễ gây nhầm lẫn class nào đang thực sự chạy.
Bạn xác nhận giúp mình: hiện app/rag/service.py ở trên có đúng là file bạn đang dùng thật trong production không, hay đây là bản cũ và bạn đã chuyển hẳn sang dùng image_rag.py (BGE-M3 caption) rồi? Nếu đã chuyển hẳn, nên xóa hẳn phần ImageEmbedder/ImageStore/ImageCaptioner/ImageRAG dư trong service.py để tránh nhầm — mình có thể giúp dọn phần đó trước, rồi mới thêm BM25 cho ảnh sau.
=================