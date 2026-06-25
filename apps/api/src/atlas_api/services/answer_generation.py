from atlas_api.llm_providers.base import LLMProvider
from atlas_api.schemas.rag import AnswerRequest, AnswerResponse, Citation
from atlas_api.services.context_assembly import ContextAssemblyService
from atlas_api.services.retrieval import RetrievalService

INSUFFICIENT_CONTEXT_ANSWER = "Insufficient context to answer the question."


class AnswerGenerationService:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        context_assembly_service: ContextAssemblyService,
        llm_provider: LLMProvider,
        default_similarity_score_threshold: float,
        max_context_characters: int,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._context_assembly_service = context_assembly_service
        self._llm_provider = llm_provider
        self._default_similarity_score_threshold = default_similarity_score_threshold
        self._max_context_characters = max_context_characters

    def answer(self, payload: AnswerRequest) -> AnswerResponse:
        retrieved_chunks = self._retrieval_service.search(payload)
        threshold = (
            payload.similarity_score_threshold
            if payload.similarity_score_threshold is not None
            else self._default_similarity_score_threshold
        )
        assembled_context = self._context_assembly_service.assemble(
            query=payload.query,
            retrieved_chunks=retrieved_chunks,
            similarity_score_threshold=threshold,
            max_characters=self._max_context_characters,
        )
        if not assembled_context.retrieved_chunks:
            return AnswerResponse(
                answer=INSUFFICIENT_CONTEXT_ANSWER,
                citations=[],
                retrieved_chunks_count=0,
            )

        answer = self._llm_provider.generate_answer(
            query=payload.query,
            context=assembled_context.text,
        )
        citations = [
            Citation(
                source=chunk.source_name,
                section=chunk.section or "Unspecified",
                chunk_id=str(chunk.chunk_id),
            )
            for chunk in assembled_context.retrieved_chunks
        ]
        return AnswerResponse(
            answer=answer,
            citations=citations,
            retrieved_chunks_count=len(assembled_context.retrieved_chunks),
        )
