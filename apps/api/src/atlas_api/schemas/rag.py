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
    matched_queries: list[str] = Field(default_factory=list)


class ContextPreviewRequest(SearchRequest):
    max_chunks: int | None = Field(default=None, ge=1, le=100)
    similarity_score_threshold: float | None = Field(default=None, ge=-1, le=1)


class ContextPreviewResponse(BaseModel):
    query: str
    retrieved_chunks: list[SearchResult]
    assembled_context: str


class AnswerRequest(SearchRequest):
    similarity_score_threshold: float | None = Field(default=None, ge=-1, le=1)


class Citation(BaseModel):
    source: str
    section: str
    chunk_id: str


class AnswerResponse(BaseModel):
    answer: str
    citations: list[Citation]
    retrieved_chunks_count: int
