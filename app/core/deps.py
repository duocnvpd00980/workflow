
from app.core.llm_engine import build_registry
from app.rag.service import RAG
from app.rag.loader import DocumentLoader

_registry = build_registry()
_rag      = RAG()
_loader   = DocumentLoader()

def get_llm(key="default"):  return _registry.get_llm(key)
def get_rag():               return _rag
def get_loader():            return _loader