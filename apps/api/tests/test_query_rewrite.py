from typing import cast

import pytest

from atlas_api.embedding_providers.base import EmbeddingProvider
from atlas_api.repositories.retrieval import RetrievalRepository, StoredChunkEmbedding
from atlas_api.schemas.embeddings import EmbeddingResult
from atlas_api.schemas.rag import SearchRequest
from atlas_api.services.query_rewrite import QueryRewriteService
from atlas_api.services.retrieval import RetrievalService


class StubQueryRewriteProvider:
    provider = "stub"
    model = "stub-v1"

    def rewrite(self, query: str) -> list[str]:
        return [f"{query} rewritten", f"{query} alternate"]


class MappingEmbeddingProvider:
    provider = "mapping"
    model = "mapping-v1"
    dimensions = 1

    def __init__(self) -> None:
        self.texts: list[str] = []

    def embed_text(self, text: str) -> EmbeddingResult:
        self.texts.append(text)
        return EmbeddingResult(
            provider=self.provider,
            model=self.model,
            dimensions=self.dimensions,
            embedding=[float(len(self.texts))],
        )

    def embed_texts(self, texts: list[str]) -> list[EmbeddingResult]:
        return [self.embed_text(text) for text in texts]


class StubRetrievalRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[list[float], int, int, str | None]] = []

    def similarity_search(
        self,
        query_embedding: list[float],
        query_dimensions: int,
        limit: int,
        collection: str | None = None,
    ) -> list[StoredChunkEmbedding]:
        self.calls.append((query_embedding, query_dimensions, limit, collection))
        query_number = int(query_embedding[0])
        if query_number == 1:
            return [
                make_stored_chunk(
                    chunk_id=10,
                    text="Original query match.",
                    similarity_score=0.42,
                )
            ]
        if query_number == 2:
            return [
                make_stored_chunk(
                    chunk_id=10,
                    text="Rewritten query match.",
                    similarity_score=0.91,
                )
            ]
        return [
            make_stored_chunk(
                chunk_id=20,
                text="Alternate query match.",
                similarity_score=0.73,
            ),
            make_stored_chunk(
                chunk_id=10,
                text="Lower duplicate match.",
                similarity_score=0.35,
            ),
        ]


def make_stored_chunk(
    *,
    chunk_id: int,
    text: str,
    similarity_score: float,
) -> StoredChunkEmbedding:
    return StoredChunkEmbedding(
        chunk_id=chunk_id,
        document_id=chunk_id + 100,
        source_name=f"source-{chunk_id}.md",
        collection="learning",
        section="Section",
        chunk_index=0,
        text=text,
        similarity_score=similarity_score,
    )


def make_service(
    repository: StubRetrievalRepository,
    embedding_provider: MappingEmbeddingProvider,
) -> RetrievalService:
    return RetrievalService(
        repository=cast(RetrievalRepository, repository),
        embedding_provider=cast(EmbeddingProvider, embedding_provider),
        query_rewrite_service=QueryRewriteService(StubQueryRewriteProvider()),
    )


def test_query_rewrite_includes_original_query_first() -> None:
    assert QueryRewriteService(StubQueryRewriteProvider()).rewrite("What is RAG?") == [
        "What is RAG?",
        "What is RAG? rewritten",
        "What is RAG? alternate",
    ]


def test_multi_query_retrieval_deduplicates_preserves_highest_score_and_matched_queries() -> None:
    repository = StubRetrievalRepository()
    embedding_provider = MappingEmbeddingProvider()
    service = make_service(repository, embedding_provider)

    results = service.search(SearchRequest(query="What is RAG?", top_k=5, collection="learning"))

    assert embedding_provider.texts == [
        "What is RAG?",
        "What is RAG? rewritten",
        "What is RAG? alternate",
    ]
    assert len(repository.calls) == 3
    assert [result.chunk_id for result in results] == [10, 20]
    assert results[0].similarity_score == pytest.approx(0.91)
    assert results[0].text == "Rewritten query match."
    assert results[0].matched_queries == [
        "What is RAG?",
        "What is RAG? rewritten",
        "What is RAG? alternate",
    ]
    assert results[1].matched_queries == ["What is RAG? alternate"]
