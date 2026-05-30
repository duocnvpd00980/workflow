from llama_index.core.postprocessor import LLMRerank

class RetrieverService:
    def __init__(self, index, llm):
        self.index = index
        self.llm = llm

    def search(self, query):
        retriever = self.index.as_retriever(similarity_top_k=5)
        nodes = retriever.retrieve(query)
        # Rerank để đảm bảo độ chính xác (Reliability)
        reranker = LLMRerank(llm=self.llm, top_n=3)
        final_nodes = reranker.postprocess_nodes(nodes, query_str=query)
        return "\n\n".join([n.get_content() for n in final_nodes])