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
from atlas_api.models import Document

_ = Document


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
    assert payload["status"] == "uploaded"
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
