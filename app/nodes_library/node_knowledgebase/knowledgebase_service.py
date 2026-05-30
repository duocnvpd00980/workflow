import os
from .knowledgebase_protocol import KnowledgebaseOutput

try:
    from llama_index.core import StorageContext, load_index_from_storage
    from llama_index.embeddings.fastembed import FastEmbedEmbedding

    _LLAMA_AVAILABLE = True
except ImportError:
    _LLAMA_AVAILABLE = False

# Đường dẫn tuyệt đối để tránh lỗi không tìm thấy file
BASE_DIR = os.getcwd()
FAISS_PERSIST_DIR = os.path.join(BASE_DIR, "storage_test_faiss")
EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"
TOP_K = 4


class KnowledgeBaseService:
    def __init__(self):
        self._index = None
        self._embed_model = None

    def _get_embed_model(self):
        if self._embed_model is None:
            self._embed_model = FastEmbedEmbedding(model_name=EMBED_MODEL_NAME)
        return self._embed_model

    def _load_index(self):
        """Load index từ storage trực tiếp mà không cần khởi tạo lại FaissVectorStore thủ công."""
        if self._index is not None:
            return

        if not os.path.exists(FAISS_PERSIST_DIR):
            raise FileNotFoundError(
                f"[KNOWLEDGE] Thư mục chứa index không tồn tại: {FAISS_PERSIST_DIR}"
            )

        try:
            # Load trực tiếp từ persist_dir - LlamaIndex tự động đọc các file json/faiss bên trong
            storage_ctx = StorageContext.from_defaults(persist_dir=FAISS_PERSIST_DIR)
            self._index = load_index_from_storage(
                storage_context=storage_ctx,
                embed_model=self._get_embed_model(),
            )
        except Exception as e:
            print(f"❌ [KNOWLEDGE] Lỗi khi load index: {e}")
            raise

    async def run(self, query: str) -> KnowledgebaseOutput:
        if not _LLAMA_AVAILABLE:
            return KnowledgebaseOutput(
                retrieved_context="", source_nodes=[], top_score=None, node_count=0
            )

        self._load_index()

        # Retrieval
        retriever = self._index.as_retriever(similarity_top_k=TOP_K)
        nodes = retriever.retrieve(query)

        if not nodes:
            return KnowledgebaseOutput(
                retrieved_context="", source_nodes=[], top_score=None, node_count=0
            )

        context_parts = []
        source_nodes = []

        for n in nodes:
            context_parts.append(n.get_content())
            source_nodes.append(
                {
                    "text": n.get_content()[:200],
                    "score": float(n.score) if n.score is not None else 0.0,
                    "doc_id": n.node_id,
                }
            )

        return KnowledgebaseOutput(
            retrieved_context="\n\n---\n\n".join(context_parts),
            source_nodes=source_nodes,
            top_score=float(nodes[0].score) if nodes[0].score is not None else 0.0,
            node_count=len(nodes),
        )
