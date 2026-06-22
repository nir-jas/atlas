from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2_000)
    top_k: int = Field(default=5, ge=1, le=100)
    collection: str | None = Field(default=None, min_length=1, max_length=120)


class SearchResult(BaseModel):
    chunk_id: int
    document_id: int
    source_name: str
    collection: str
    section: str | None
    chunk_index: int
    text: str
    similarity_score: float
