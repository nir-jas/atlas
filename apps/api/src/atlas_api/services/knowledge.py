from atlas_api.ai_providers.base import AIProvider
from atlas_api.repositories.base import KnowledgeRepository
from atlas_api.schemas.knowledge import AnswerResponse, KnowledgeNote


class KnowledgeService:
    def __init__(self, repository: KnowledgeRepository, ai_provider: AIProvider) -> None:
        self._repository = repository
        self._ai_provider = ai_provider

    def list_notes(self) -> list[KnowledgeNote]:
        return self._repository.list_notes()

    def answer_question(self, question: str) -> AnswerResponse:
        notes = self._repository.search_notes(question)
        context = [note.summary for note in notes]
        answer = self._ai_provider.generate_answer(question=question, context=context)
        return AnswerResponse(answer=answer, sources=notes)

