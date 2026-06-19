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
from atlas_api.embedding_providers.fake import FakeEmbeddingProvider
from atlas_api.main import create_app
from atlas_api.models import Chunk, ChunkEmbedding, Document
from atlas_api.services.chunking import ChunkingService

TestingSessionFactory = sessionmaker[Session]

_ = (Chunk, ChunkEmbedding, Document)


def make_pdf_with_text(text: str) -> bytes:
    escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = f"BT\n/F1 12 Tf\n72 720 Td\n({escaped_text}) Tj\nET\n".encode()
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        (
            b"3 0 obj\n"
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\n"
            b"endobj\n"
        ),
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        b"5 0 obj\n<< /Length " + str(len(content)).encode() + b" >>\nstream\n"
        + content
        + b"endstream\nendobj\n",
    ]

    pdf = b"%PDF-1.4\n"
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj

    xref_offset = len(pdf)
    xref_rows = [b"0000000000 65535 f \n"]
    xref_rows.extend(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    xref = b"xref\n0 6\n" + b"".join(xref_rows)
    trailer = (
        b"trailer\n<< /Root 1 0 R /Size 6 >>\nstartxref\n"
        + str(xref_offset).encode()
        + b"\n%%EOF\n"
    )
    return pdf + xref + trailer


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


def test_unsupported_binary_file_is_not_chunked() -> None:
    service = ChunkingService(max_characters=25)
    content = b"PK\x03\x04\x00binary payload"

    chunks = service.chunk_document(filename="sample.docx", content=content)

    assert chunks == []


def test_nul_bytes_are_removed_from_supported_text_chunks() -> None:
    service = ChunkingService(max_characters=25)
    content = b"First\x00 paragraph."

    chunks = service.chunk_document(filename="note.txt", content=content)

    assert chunks[0].text == "First paragraph."
    assert chunks[0].character_count == len("First paragraph.")


def test_pdf_chunking() -> None:
    service = ChunkingService(max_characters=80)
    content = make_pdf_with_text("Atlas PDF content for chunking.")

    chunks = service.chunk_document(filename="sample.pdf", content=content)

    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].section is None
    assert "Atlas PDF content for chunking." in chunks[0].text
    assert chunks[0].character_count == len(chunks[0].text)


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


def test_pdf_upload_creates_chunks_and_embeddings(
    client: TestClient,
    session_factory: TestingSessionFactory,
) -> None:
    pdf_content = make_pdf_with_text("Uploaded PDF content is indexed.")

    response = client.post(
        "/documents/upload",
        data={"collection": "learning", "document_type": "pdf"},
        files={"file": ("sample.pdf", pdf_content, "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "indexed"

    with session_factory() as session:
        document = session.get_one(Document, response.json()["id"])
        chunks = list(
            session.scalars(select(Chunk).where(Chunk.document_id == document.id))
        )
        embeddings = list(
            session.scalars(
                select(ChunkEmbedding).where(
                    ChunkEmbedding.chunk_id.in_([chunk.id for chunk in chunks])
                )
            )
        )

    assert document.status == "indexed"
    assert len(chunks) == 1
    assert "Uploaded PDF content is indexed." in chunks[0].text
    assert len(embeddings) == 1


def test_invalid_pdf_upload_is_stored_without_chunks_or_embeddings(
    client: TestClient,
    session_factory: TestingSessionFactory,
) -> None:
    response = client.post(
        "/documents/upload",
        data={"collection": "learning", "document_type": "pdf"},
        files={"file": ("broken.pdf", b"%PDF-1.4\x00binary payload", "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "uploaded"

    with session_factory() as session:
        document = session.get_one(Document, response.json()["id"])
        chunks = list(session.scalars(select(Chunk).where(Chunk.document_id == document.id)))
        embeddings = list(session.scalars(select(ChunkEmbedding)))

    assert document.status == "uploaded"
    assert chunks == []
    assert embeddings == []


def test_empty_text_upload_is_stored_without_chunks(
    client: TestClient,
    session_factory: TestingSessionFactory,
) -> None:
    response = client.post(
        "/documents/upload",
        data={"collection": "learning", "document_type": "note"},
        files={"file": ("empty.txt", b"", "text/plain")},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "uploaded"

    with session_factory() as session:
        chunks = list(
            session.scalars(select(Chunk).where(Chunk.document_id == response.json()["id"]))
        )

    assert chunks == []


def test_fake_embedding_is_deterministic() -> None:
    provider = FakeEmbeddingProvider(dimensions=8)

    first = provider.embed_text("Atlas chunk")
    second = provider.embed_text("Atlas chunk")
    different = provider.embed_text("Different chunk")

    assert first == second
    assert first.embedding != different.embedding
    assert first.provider == "fake"
    assert first.model == "fake-deterministic-v1"
    assert first.dimensions == 8
    assert len(first.embedding) == 8


def test_embeddings_created_for_chunks_after_upload(
    client: TestClient,
    session_factory: TestingSessionFactory,
) -> None:
    response = client.post(
        "/documents/upload",
        data={"collection": "learning", "document_type": "markdown"},
        files={
            "file": (
                "embeddings.md",
                b"# One\n\nFirst chunk.\n\n## Two\n\nSecond chunk.",
                "text/markdown",
            )
        },
    )

    assert response.status_code == 201

    with session_factory() as session:
        document = session.get_one(Document, response.json()["id"])
        chunks = list(
            session.scalars(
                select(Chunk)
                .where(Chunk.document_id == document.id)
                .order_by(Chunk.chunk_index)
            )
        )
        embeddings = list(
            session.scalars(
                select(ChunkEmbedding)
                .where(ChunkEmbedding.chunk_id.in_([chunk.id for chunk in chunks]))
                .order_by(ChunkEmbedding.chunk_id)
            )
        )

    assert len(chunks) == 2
    assert len(embeddings) == len(chunks)
    assert {embedding.chunk_id for embedding in embeddings} == {chunk.id for chunk in chunks}


def test_embedding_metadata_is_stored_correctly(
    client: TestClient,
    session_factory: TestingSessionFactory,
) -> None:
    response = client.post(
        "/documents/upload",
        data={"collection": "learning", "document_type": "note"},
        files={"file": ("metadata.txt", b"Embedding metadata check.", "text/plain")},
    )

    assert response.status_code == 201

    with session_factory() as session:
        chunk = session.scalar(
            select(Chunk).where(Chunk.document_id == response.json()["id"])
        )
        assert chunk is not None
        embedding = session.scalar(
            select(ChunkEmbedding).where(ChunkEmbedding.chunk_id == chunk.id)
        )

    assert embedding is not None
    assert embedding.provider == "fake"
    assert embedding.model == "fake-deterministic-v1"
    assert embedding.dimensions == 8
    assert len(embedding.embedding) == 8
    assert embedding.created_at is not None
