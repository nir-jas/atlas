from typing import Annotated

from fastapi import APIRouter, Depends

from atlas_api.core.dependencies import get_retrieval_service
from atlas_api.schemas.rag import SearchRequest, SearchResult
from atlas_api.services.retrieval import RetrievalService

router = APIRouter(tags=["rag"])
RetrievalServiceDep = Annotated[RetrievalService, Depends(get_retrieval_service)]


@router.post("/rag/search", response_model=list[SearchResult])
def search(
    payload: SearchRequest,
    service: RetrievalServiceDep,
) -> list[SearchResult]:
    return service.search(payload)
