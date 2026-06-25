from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from atlas_api.core.dependencies import (
    ContextAssemblyServiceDep,
    get_answer_generation_service,
    get_retrieval_service,
)
from atlas_api.llm_providers.base import LLMProviderError
from atlas_api.schemas.rag import (
    AnswerRequest,
    AnswerResponse,
    ContextPreviewRequest,
    ContextPreviewResponse,
    SearchRequest,
    SearchResult,
)
from atlas_api.services.answer_generation import AnswerGenerationService
from atlas_api.services.retrieval import RetrievalService

router = APIRouter(tags=["rag"])
RetrievalServiceDep = Annotated[RetrievalService, Depends(get_retrieval_service)]
AnswerGenerationServiceDep = Annotated[
    AnswerGenerationService,
    Depends(get_answer_generation_service),
]


@router.post("/rag/search", response_model=list[SearchResult])
def search(
    payload: SearchRequest,
    service: RetrievalServiceDep,
) -> list[SearchResult]:
    return service.search(payload)


@router.post("/rag/context-preview", response_model=ContextPreviewResponse)
def context_preview(
    payload: ContextPreviewRequest,
    retrieval_service: RetrievalServiceDep,
    context_assembly_service: ContextAssemblyServiceDep,
) -> ContextPreviewResponse:
    retrieved_chunks = retrieval_service.search(payload)
    assembled_context = context_assembly_service.assemble(
        query=payload.query,
        retrieved_chunks=retrieved_chunks,
        max_chunks=payload.max_chunks,
        similarity_score_threshold=payload.similarity_score_threshold,
    )
    return ContextPreviewResponse(
        query=payload.query,
        retrieved_chunks=assembled_context.retrieved_chunks,
        assembled_context=assembled_context.text,
    )


@router.post("/rag/answer", response_model=AnswerResponse)
def answer(
    payload: AnswerRequest,
    service: AnswerGenerationServiceDep,
) -> AnswerResponse:
    try:
        return service.answer(payload)
    except LLMProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Answer generation provider failed",
        ) from error
