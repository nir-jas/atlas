from pydantic import BaseModel, Field


class KnowledgeNote(BaseModel):
    id: str
    title: str
    summary: str
    tags: list[str] = Field(default_factory=list)


class AnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)


class AnswerResponse(BaseModel):
    answer: str
    sources: list[KnowledgeNote] = Field(default_factory=list)

