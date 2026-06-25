import pytest

from atlas_api.reranker_providers.base import RerankInput
from atlas_api.reranker_providers.fake import FakeRerankerProvider
from atlas_api.schemas.rag import SearchResult
from atlas_api.services.reranking import RerankerService


def make_chunk(chunk_id: int, text: str) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        document_id=chunk_id,
        source_name=f"source-{chunk_id}.md",
        collection="learning",
        section=None,
        chunk_index=0,
        text=text,
        similarity_score=1.0 - (chunk_id / 10),
        matched_by=["vector"],
    )


def make_service(
    *,
    enabled: bool = True,
    top_k: int = 5,
    score_threshold: float = 0.0,
) -> RerankerService:
    return RerankerService(
        provider=FakeRerankerProvider(),
        enabled=enabled,
        top_k=top_k,
        score_threshold=score_threshold,
    )


def test_reranker_can_reorder_chunks() -> None:
    chunks = [
        make_chunk(1, "Atlas pipeline overview."),
        make_chunk(2, "Atlas reranking pipeline."),
    ]

    results = make_service().rerank(query="Atlas reranking pipeline", chunks=chunks)

    assert [chunk.chunk_id for chunk in results] == [2, 1]
    assert results[0].reranker_score == pytest.approx(1.0)
    assert results[0].reranker_enabled is True
    assert results[0].similarity_score == pytest.approx(0.8)
    assert results[0].matched_by == ["vector"]


def test_reranker_threshold_filters_weak_chunks() -> None:
    chunks = [
        make_chunk(1, "Atlas pipeline overview."),
        make_chunk(2, "Atlas reranking pipeline."),
    ]

    results = make_service(score_threshold=0.8).rerank(
        query="Atlas reranking pipeline",
        chunks=chunks,
    )

    assert [chunk.chunk_id for chunk in results] == [2]
    assert results[0].reranker_score == pytest.approx(1.0)


def test_reranker_top_k_limits_output() -> None:
    chunks = [
        make_chunk(1, "Atlas reranking pipeline."),
        make_chunk(2, "Atlas reranking pipeline."),
        make_chunk(3, "Atlas reranking pipeline."),
    ]

    results = make_service(top_k=2).rerank(
        query="Atlas reranking pipeline",
        chunks=chunks,
    )

    assert [chunk.chunk_id for chunk in results] == [1, 2]


def test_disabling_reranker_preserves_existing_ranking() -> None:
    chunks = [
        make_chunk(1, "Atlas pipeline overview."),
        make_chunk(2, "Atlas reranking pipeline."),
    ]

    results = make_service(enabled=False, top_k=1, score_threshold=0.99).rerank(
        query="Atlas reranking pipeline",
        chunks=chunks,
    )

    assert results == chunks
    assert [chunk.chunk_id for chunk in results] == [1, 2]
    assert all(chunk.reranker_enabled is False for chunk in results)
    assert all(chunk.reranker_score is None for chunk in results)


def test_fake_reranker_is_deterministic() -> None:
    provider = FakeRerankerProvider()
    inputs = [
        RerankInput(chunk_id=1, text="Atlas reranking pipeline."),
        RerankInput(chunk_id=2, text="Unrelated notes."),
    ]

    first_scores = provider.score(
        query="Atlas reranking pipeline",
        chunks=inputs,
    )
    second_scores = provider.score(
        query="Atlas reranking pipeline",
        chunks=inputs,
    )

    assert first_scores == second_scores
