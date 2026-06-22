from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from atlas_api.core.dependencies import get_upload_dir
from atlas_api.db.base import Base
from atlas_api.db.session import get_session
from atlas_api.main import create_app
from atlas_api.models import Chunk, ChunkEmbedding, Document

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

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_upload_dir] = override_get_upload_dir

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
