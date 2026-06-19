from typing import Annotated

from fastapi import APIRouter, Depends, status

from atlas_api.core.dependencies import get_knowledge_service
from atlas_api.schemas.knowledge import AnswerRequest, AnswerResponse, KnowledgeNote
from atlas_api.services.knowledge import KnowledgeService

router = APIRouter(tags=["knowledge"])
KnowledgeServiceDep = Annotated[KnowledgeService, Depends(get_knowledge_service)]


@router.get("/notes", response_model=list[KnowledgeNote])
def list_notes(
    service: KnowledgeServiceDep,
) -> list[KnowledgeNote]:
    return service.list_notes()


@router.post(
    "/answers",
    response_model=AnswerResponse,
    status_code=status.HTTP_200_OK,
)
def answer_question(
    payload: AnswerRequest,
    service: KnowledgeServiceDep,
) -> AnswerResponse:
    return service.answer_question(payload.question)

