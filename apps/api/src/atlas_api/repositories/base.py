from typing import Protocol

from atlas_api.schemas.knowledge import KnowledgeNote


class KnowledgeRepository(Protocol):
    def list_notes(self) -> list[KnowledgeNote]:
        """Return available knowledge notes."""
        ...

    def search_notes(self, query: str, limit: int = 5) -> list[KnowledgeNote]:
        """Return notes relevant to a query."""
        ...

