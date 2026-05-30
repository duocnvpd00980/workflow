from typing import Optional
from pydantic import BaseModel

class DocOut(BaseModel):
    id: int
    title: str
    status: str
    chunk_count: int
    file_size: Optional[str] = None
    created_at: str

class UploadOut(BaseModel):
    id: int
    title: str
    status: str
    message: str

class SearchOut(BaseModel):
    query: str
    results: list[dict]
    source: str
