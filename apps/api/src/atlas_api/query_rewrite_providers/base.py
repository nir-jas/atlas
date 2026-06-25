from typing import Protocol


class QueryRewriteProvider(Protocol):
    provider: str
    model: str

    def rewrite(self, query: str) -> list[str]:
        """Generate alternate retrieval queries for a user query."""
        ...
