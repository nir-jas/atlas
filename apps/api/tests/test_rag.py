from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from atlas_api.core.config import settings
from atlas_api.core.dependencies import (
    get_embedding_provider,
    get_llm_provider,
    get_query_rewrite_service,
    get_reranker_service,
    get_upload_dir,
)
from atlas_api.db.base import Base
from atlas_api.db.session import get_session
from atlas_api.embedding_providers.fake import FakeEmbeddingProvider
from atlas_api.llm_providers.fake import FakeLLMProvider
from atlas_api.main import create_app
from atlas_api.models import Chunk, ChunkEmbedding, Document
from atlas_api.query_rewrite_providers.fake import FakeQueryRewriteProvider
from atlas_api.reranker_providers.fake import FakeRerankerProvider
from atlas_api.services.query_rewrite import QueryRewriteService
from atlas_api.services.reranking import RerankerService

TestingSessionFactory = sessionmaker[Session]

_ = (Chunk, ChunkEmbedding, Document)


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_session() -> Iterator[Session]:
        with testing_session_local() as session:
            yield session

    def override_get_upload_dir() -> Path:
        return tmp_path / "uploads"

    def override_get_embedding_provider() -> FakeEmbeddingProvider:
        return FakeEmbeddingProvider(dimensions=settings.vector_dimensions)

    def override_get_llm_provider() -> FakeLLMProvider:
        return FakeLLMProvider()

    def override_get_query_rewrite_service() -> QueryRewriteService:
        return QueryRewriteService(FakeQueryRewriteProvider())

    def override_get_reranker_service() -> RerankerService:
        return RerankerService(
            provider=FakeRerankerProvider(),
            enabled=False,
            top_k=5,
            score_threshold=0.8,
        )

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_upload_dir] = override_get_upload_dir
    app.dependency_overrides[get_embedding_provider] = override_get_embedding_provider
    app.dependency_overrides[get_llm_provider] = override_get_llm_provider
    app.dependency_overrides[get_query_rewrite_service] = override_get_query_rewrite_service
    app.dependency_overrides[get_reranker_service] = override_get_reranker_service

    with TestClient(app) as test_client:
        yield test_client


def upload_text_document(client: TestClient, filename: str, collection: str, text: str) -> None:
    response = client.post(
        "/documents/upload",
        data={"collection": collection, "document_type": "note"},
        files={"file": (filename, text.encode(), "text/plain")},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "indexed"


def test_search_returns_most_similar_chunk(client: TestClient) -> None:
    matching_text = "Atlas retrieval ranks matching chunks first."
    upload_text_document(client, "matching.txt", "learning", matching_text)
    upload_text_document(client, "other.txt", "learning", "A separate unrelated document.")

    response = client.post("/rag/search", json={"query": matching_text})

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["source_name"] == "matching.txt"
    assert payload[0]["text"] == matching_text
    assert payload[0]["similarity_score"] == pytest.approx(1.0)


def test_search_respects_top_k(client: TestClient) -> None:
    upload_text_document(client, "one.txt", "learning", "First retrieval document.")
    upload_text_document(client, "two.txt", "learning", "Second retrieval document.")
    upload_text_document(client, "three.txt", "learning", "Third retrieval document.")

    response = client.post(
        "/rag/search",
        json={"query": "First retrieval document.", "top_k": 2},
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_search_filters_by_collection_before_ranking(client: TestClient) -> None:
    text = "Collection filtering keeps results scoped."
    upload_text_document(client, "learning.txt", "learning", text)
    upload_text_document(client, "research.txt", "research", text)

    response = client.post(
        "/rag/search",
        json={"query": text, "collection": "research"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["source_name"] == "research.txt"
    assert payload[0]["collection"] == "research"


def test_search_response_includes_chunk_metadata_and_score(client: TestClient) -> None:
    text = "# Overview\n\nAtlas retrieval exposes source metadata."
    upload_text_document(client, "overview.md", "learning", text)

    response = client.post("/rag/search", json={"query": text})

    assert response.status_code == 200
    result = response.json()[0]
    assert result["chunk_id"] == 1
    assert result["document_id"] == 1
    assert result["source_name"] == "overview.md"
    assert result["collection"] == "learning"
    assert result["section"] == "Overview"
    assert result["chunk_index"] == 0
    assert "Atlas retrieval exposes source metadata." in result["text"]
    assert isinstance(result["similarity_score"], float)
    assert isinstance(result["keyword_rank"], float)
    assert result["matched_by"] == ["vector", "keyword"]
    assert text in result["matched_queries"]
    assert result["reranker_enabled"] is False
    assert result["reranker_score"] is None


def test_keyword_search_finds_exact_technical_terms(client: TestClient) -> None:
    upload_text_document(
        client,
        "indexes.md",
        "learning",
        "PostgreSQL pgvector can use HNSW indexes for approximate nearest neighbor search.",
    )
    upload_text_document(
        client,
        "generation.md",
        "learning",
        "Answer generation uses retrieved context and citations.",
    )

    response = client.post(
        "/rag/search",
        json={"query": "HNSW", "search_mode": "keyword"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["source_name"] == "indexes.md"
    assert payload[0]["similarity_score"] is None
    assert payload[0]["keyword_rank"] > 0
    assert payload[0]["matched_by"] == ["keyword"]


def test_search_mode_selects_vector_keyword_and_hybrid(client: TestClient) -> None:
    text = "Hybrid retrieval combines pgvector similarity with keyword matches."
    upload_text_document(client, "hybrid.md", "learning", text)

    vector_response = client.post(
        "/rag/search",
        json={"query": text, "search_mode": "vector"},
    )
    keyword_response = client.post(
        "/rag/search",
        json={"query": "pgvector", "search_mode": "keyword"},
    )
    hybrid_response = client.post(
        "/rag/search",
        json={"query": text, "search_mode": "hybrid"},
    )

    assert vector_response.status_code == 200
    assert keyword_response.status_code == 200
    assert hybrid_response.status_code == 200
    assert vector_response.json()[0]["matched_by"] == ["vector"]
    assert keyword_response.json()[0]["matched_by"] == ["keyword"]
    assert hybrid_response.json()[0]["matched_by"] == ["vector", "keyword"]


def test_answer_generation_returns_citations_separately(client: TestClient) -> None:
    text = "Atlas answers questions from retrieved document chunks."
    upload_text_document(client, "answer.md", "learning", text)

    response = client.post("/rag/answer", json={"query": text})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == f"Fake grounded answer for: {text}"
    assert payload["answer"].find("answer.md") == -1
    assert payload["citations"] == [
        {"source": "answer.md", "section": "Unspecified", "chunk_id": "1"}
    ]
    assert payload["retrieved_chunks_count"] == 1
    assert payload["reranker_enabled"] is False
    assert payload["retrieved_chunks"][0]["source_name"] == "answer.md"
    assert payload["retrieved_chunks"][0]["matched_by"] == ["vector", "keyword"]


def test_answer_generation_returns_insufficient_context_without_matches(client: TestClient) -> None:
    response = client.post(
        "/rag/answer",
        json={"query": "What is absent?", "collection": "missing"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Insufficient context to answer the question.",
        "citations": [],
        "retrieved_chunks_count": 0,
        "reranker_enabled": False,
        "retrieved_chunks": [],
    }
