from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from atlas_api.core.dependencies import get_upload_dir
from atlas_api.db.base import Base
from atlas_api.db.session import get_session
from atlas_api.main import create_app
from atlas_api.models import Chunk, Document
from atlas_api.services.chunking import ChunkingService

TestingSessionFactory = sessionmaker[Session]

_ = (Chunk, Document)


@pytest.fixture()
def session_factory() -> TestingSessionFactory:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return testing_session_local


@pytest.fixture()
def client(tmp_path: Path, session_factory: TestingSessionFactory) -> Iterator[TestClient]:
    def override_get_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    def override_get_upload_dir() -> Path:
        return tmp_path / "uploads"

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_upload_dir] = override_get_upload_dir

    with TestClient(app) as test_client:
        yield test_client


def test_successful_upload(client: TestClient, tmp_path: Path) -> None:
    response = client.post(
        "/documents/upload",
        data={"collection": "learning", "document_type": "note"},
        files={"file": ("sample.txt", b"hello atlas", "text/plain")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] == 1
    assert payload["filename"] == "sample.txt"
    assert payload["collection"] == "learning"
    assert payload["document_type"] == "note"
    assert payload["file_size"] == len(b"hello atlas")
    assert payload["status"] == "indexed"
    assert payload["uploaded_at"]

    uploaded_files = list((tmp_path / "uploads").iterdir())
    assert len(uploaded_files) == 1
    assert uploaded_files[0].read_bytes() == b"hello atlas"


def test_document_listing(client: TestClient) -> None:
    first_response = client.post(
        "/documents/upload",
        data={"collection": "learning", "document_type": "note"},
        files={"file": ("first.txt", b"first", "text/plain")},
    )
    second_response = client.post(
        "/documents/upload",
        data={"collection": "research", "document_type": "paper"},
        files={"file": ("second.txt", b"second", "text/plain")},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    response = client.get("/documents")

    assert response.status_code == 200
    payload = response.json()
    assert [document["filename"] for document in payload] == ["second.txt", "first.txt"]
    assert payload[0]["collection"] == "research"
    assert payload[1]["collection"] == "learning"


def test_markdown_chunking() -> None:
    service = ChunkingService(max_characters=80)
    content = b"# Intro\n\nAtlas stores files.\n\n## Details\n\nChunks preserve sections."

    chunks = service.chunk_document(filename="notes.md", content=content)

    assert [chunk.section for chunk in chunks] == ["Intro", "Details"]
    assert chunks[0].chunk_index == 0
    assert "Atlas stores files." in chunks[0].text
    assert chunks[1].chunk_index == 1
    assert "Chunks preserve sections." in chunks[1].text


def test_plain_text_chunking() -> None:
    service = ChunkingService(max_characters=25)
    content = b"First paragraph.\n\nSecond paragraph is longer than the limit."

    chunks = service.chunk_document(filename="note.txt", content=content)

    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2]
    assert all(chunk.section is None for chunk in chunks)
    assert chunks[0].text == "First paragraph."
    assert all(chunk.character_count <= 25 for chunk in chunks)


def test_chunks_created_after_upload(
    client: TestClient,
    session_factory: TestingSessionFactory,
) -> None:
    response = client.post(
        "/documents/upload",
        data={"collection": "learning", "document_type": "markdown"},
        files={
            "file": (
                "milestone.md",
                b"# Milestone\n\nUpload documents.\n\n## Next\n\nChunk content.",
                "text/markdown",
            )
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "indexed"

    with session_factory() as session:
        document = session.get_one(Document, response.json()["id"])
        statement = (
            select(Chunk)
            .where(Chunk.document_id == document.id)
            .order_by(Chunk.chunk_index)
        )
        chunks = list(session.scalars(statement))

    assert document.status == "indexed"
    assert [chunk.chunk_index for chunk in chunks] == [0, 1]
    assert [chunk.section for chunk in chunks] == ["Milestone", "Next"]
    assert chunks[0].character_count == len(chunks[0].text)
