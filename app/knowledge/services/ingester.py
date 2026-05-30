from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.core.node_parser import SentenceSplitter

class IngesterService:
    def __init__(self, vector_store):
        self.storage_context = StorageContext.from_defaults(vector_store=vector_store)

    def ingest(self, file_path):
        # 1. Đọc file
        documents = SimpleDirectoryReader(input_files=[file_path]).load_data()
        # 2. Chunking (Cắt nhỏ để AI dễ tìm)
        parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)
        # 3. Embedding & Save to Postgres
        index = VectorStoreIndex.from_documents(
            documents, 
            storage_context=self.storage_context,
            transformations=[parser]
        )
        return index