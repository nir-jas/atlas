from typing import cast

from atlas_api.llm_providers.base import LLMProvider
from atlas_api.schemas.rag import AnswerRequest, SearchResult
from atlas_api.services.answer_generation import (
    INSUFFICIENT_CONTEXT_ANSWER,
    AnswerGenerationService,
)
from atlas_api.services.context_assembly import ContextAssemblyService
from atlas_api.services.retrieval import RetrievalService


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


class StubRetrievalService:
    def __init__(self, chunks: list[SearchResult]) -> None:
        self.chunks = chunks
        self.requests: list[AnswerRequest] = []

    def search(self, payload: AnswerRequest) -> list[SearchResult]:
        self.requests.append(payload)
        return self.chunks


class RecordingLLMProvider:
    provider = "recording"
    model = "recording-v1"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def generate_answer(self, *, query: str, context: str) -> str:
        self.calls.append((query, context))
        return "Grounded answer."


def make_service(
    chunks: list[SearchResult],
    llm_provider: RecordingLLMProvider,
    *,
    threshold: float = 0.5,
    max_context_characters: int = 4_000,
) -> AnswerGenerationService:
    retrieval_service = StubRetrievalService(chunks)
    return AnswerGenerationService(
        retrieval_service=cast(RetrievalService, retrieval_service),
        context_assembly_service=ContextAssemblyService(),
        llm_provider=cast(LLMProvider, llm_provider),
        default_similarity_score_threshold=threshold,
        max_context_characters=max_context_characters,
    )


def test_answer_generation_uses_selected_context_and_returns_citations() -> None:
    first = make_chunk(
        chunk_id=10,
        source_name="rag.md",
        section="Pipeline",
        text="Retrieval finds relevant chunks before generation.",
        similarity_score=0.96,
    )
    second = make_chunk(
        chunk_id=11,
        source_name="rag.md",
        section=None,
        text="Citations are returned separately from answer text.",
        similarity_score=0.82,
    )
    llm_provider = RecordingLLMProvider()

    result = make_service([first, second], llm_provider).answer(
        AnswerRequest(query="How does Atlas answer questions?")
    )

    assert result.answer == "Grounded answer."
    assert result.retrieved_chunks_count == 2
    assert result.reranker_enabled is False
    assert result.retrieved_chunks == [first, second]
    assert [citation.model_dump() for citation in result.citations] == [
        {"source": "rag.md", "section": "Pipeline", "chunk_id": "10"},
        {"source": "rag.md", "section": "Unspecified", "chunk_id": "11"},
    ]
    assert llm_provider.calls == [
        (
            "How does Atlas answer questions?",
            (
                "Source: rag.md\nSection: Pipeline\n\n"
                "Retrieval finds relevant chunks before generation.\n\n"
                "---\n\n"
                "Source: rag.md\nSection: Unspecified\n\n"
                "Citations are returned separately from answer text."
            ),
        )
    ]


def test_answer_generation_does_not_call_llm_without_qualifying_context() -> None:
    llm_provider = RecordingLLMProvider()
    result = make_service(
        [
            make_chunk(
                chunk_id=1,
                source_name="low-score.md",
                section="Notes",
                text="This chunk is below the threshold.",
                similarity_score=0.4,
            )
        ],
        llm_provider,
    ).answer(AnswerRequest(query="What is unavailable?"))

    assert result.answer == INSUFFICIENT_CONTEXT_ANSWER
    assert result.citations == []
    assert result.retrieved_chunks_count == 0
    assert result.reranker_enabled is False
    assert result.retrieved_chunks == []
    assert llm_provider.calls == []


def test_answer_generation_stops_at_the_context_budget() -> None:
    first = make_chunk(
        chunk_id=1,
        source_name="first.md",
        section="One",
        text="First ranked context.",
        similarity_score=0.9,
    )
    second = make_chunk(
        chunk_id=2,
        source_name="second.md",
        section="Two",
        text="Second ranked context.",
        similarity_score=0.8,
    )
    first_context = ContextAssemblyService().assemble("Question", [first]).text
    llm_provider = RecordingLLMProvider()

    result = make_service(
        [first, second],
        llm_provider,
        max_context_characters=len(first_context),
    ).answer(AnswerRequest(query="Question"))

    assert result.retrieved_chunks_count == 1
    assert result.retrieved_chunks == [first]
    assert [citation.chunk_id for citation in result.citations] == ["1"]
    assert llm_provider.calls == [("Question", first_context)]
