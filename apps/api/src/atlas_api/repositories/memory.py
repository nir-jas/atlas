from atlas_api.repositories.base import KnowledgeRepository
from atlas_api.schemas.knowledge import KnowledgeNote


class InMemoryKnowledgeRepository(KnowledgeRepository):
    def __init__(self) -> None:
        self._notes = [
            KnowledgeNote(
                id="ai-engineering-foundations",
                title="AI Engineering Foundations",
                summary="Core ideas for building production LLM applications.",
                tags=["ai-engineering", "foundations"],
            ),
            KnowledgeNote(
                id="rag-basics",
                title="RAG Basics",
                summary=(
                    "Retrieval augmented generation connects model responses "
                    "to source material."
                ),
                tags=["rag", "retrieval"],
            ),
        ]

    def list_notes(self) -> list[KnowledgeNote]:
        return list(self._notes)

    def search_notes(self, query: str, limit: int = 5) -> list[KnowledgeNote]:
        normalized_query = query.lower()
        matches = [
            note
            for note in self._notes
            if normalized_query in note.title.lower()
            or normalized_query in note.summary.lower()
            or any(normalized_query in tag for tag in note.tags)
        ]
        return matches[:limit] if matches else self._notes[:limit]
