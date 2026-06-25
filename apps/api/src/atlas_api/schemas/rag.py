from typing import Literal

from pydantic import BaseModel, Field

SearchMode = Literal["vector", "keyword", "hybrid"]
SearchMatchType = Literal["vector", "keyword"]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2_000)
    top_k: int = Field(default=5, ge=1, le=100)
    collection: str | None = Field(default=None, min_length=1, max_length=120)
    search_mode: SearchMode = "hybrid"


class SearchResult(BaseModel):
    chunk_id: int
    document_id: int
    source_name: str
    collection: str
    section: str | None
    chunk_index: int
    text: str
    similarity_score: float | None = None
    keyword_rank: float | None = None
    matched_by: list[SearchMatchType] = Field(default_factory=list)
    matched_queries: list[str] = Field(default_factory=list)
    reranker_enabled: bool = False
    reranker_score: float | None = None


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
    reranker_enabled: bool
    retrieved_chunks: list[SearchResult] = Field(default_factory=list)
