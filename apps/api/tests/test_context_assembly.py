from fastapi.testclient import TestClient

from atlas_api.core.dependencies import (
    get_context_assembly_service,
    get_retrieval_service,
)
from atlas_api.main import create_app
from atlas_api.schemas.rag import SearchResult
from atlas_api.services.context_assembly import ContextAssemblyService


def make_chunk(
    *,
    chunk_id: int,
    source_name: str,
    section: str | None,
    text: str,
    similarity_score: float,
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        document_id=chunk_id,
        source_name=source_name,
        collection="learning",
        section=section,
        chunk_index=0,
        text=text,
        similarity_score=similarity_score,
    )


def test_assembly_includes_sources_separators_and_retrieval_order() -> None:
    chunks = [
        make_chunk(
            chunk_id=2,
            source_name="second.md",
            section="Details",
            text="Second ranked chunk.",
            similarity_score=0.92,
        ),
        make_chunk(
            chunk_id=1,
            source_name="first.md",
            section=None,
            text="First ranked chunk.",
            similarity_score=0.87,
        ),
    ]

    result = ContextAssemblyService().assemble("What is Atlas?", chunks)

    assert result.retrieved_chunks == chunks
    assert result.text == (
        "Source: second.md\n"
        "Section: Details\n\n"
        "Second ranked chunk.\n\n"
        "---\n\n"
        "Source: first.md\n"
        "Section: Unspecified\n\n"
        "First ranked chunk."
    )


def test_assembly_applies_score_threshold_before_chunk_limit() -> None:
    chunks = [
        make_chunk(
            chunk_id=1,
            source_name="highest.md",
            section="One",
            text="Highest score.",
            similarity_score=0.98,
        ),
        make_chunk(
            chunk_id=2,
            source_name="kept.md",
            section="Two",
            text="Second score.",
            similarity_score=0.8,
        ),
        make_chunk(
            chunk_id=3,
            source_name="filtered.md",
            section="Three",
            text="Low score.",
            similarity_score=0.42,
        ),
    ]

    result = ContextAssemblyService().assemble(
        "What should be included?",
        chunks,
        similarity_score_threshold=0.8,
        max_chunks=1,
    )

    assert result.retrieved_chunks == [chunks[0]]
    assert "highest.md" in result.text
    assert "kept.md" not in result.text
    assert "filtered.md" not in result.text


def test_assembly_returns_empty_context_when_no_chunks_meet_threshold() -> None:
    chunk = make_chunk(
        chunk_id=1,
        source_name="low-score.md",
        section="Notes",
        text="Not included.",
        similarity_score=0.25,
    )

    result = ContextAssemblyService().assemble(
        "Question",
        [chunk],
        similarity_score_threshold=0.5,
    )

    assert result.retrieved_chunks == []
    assert result.text == ""


class StubRetrievalService:
    def search(self, _payload: object) -> list[SearchResult]:
        return [
            make_chunk(
                chunk_id=1,
                source_name="overview.md",
                section="Overview",
                text="Atlas assembles retrieved context.",
                similarity_score=0.95,
            ),
            make_chunk(
                chunk_id=2,
                source_name="discarded.md",
                section="Other",
                text="This should be filtered.",
                similarity_score=0.3,
            ),
        ]


def test_context_preview_returns_the_exact_assembled_chunk_set() -> None:
    app = create_app()
    app.dependency_overrides[get_retrieval_service] = StubRetrievalService
    app.dependency_overrides[get_context_assembly_service] = ContextAssemblyService

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rag/context-preview",
            json={
                "query": "How does retrieval work?",
                "top_k": 5,
                "max_chunks": 1,
                "similarity_score_threshold": 0.8,
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "query": "How does retrieval work?",
        "retrieved_chunks": [
            {
                "chunk_id": 1,
                "document_id": 1,
                "source_name": "overview.md",
                "collection": "learning",
                "section": "Overview",
                "chunk_index": 0,
                "text": "Atlas assembles retrieved context.",
                "similarity_score": 0.95,
            }
        ],
        "assembled_context": (
            "Source: overview.md\n"
            "Section: Overview\n\n"
            "Atlas assembles retrieved context."
        ),
    }
