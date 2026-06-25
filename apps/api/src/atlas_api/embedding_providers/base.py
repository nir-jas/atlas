from typing import Protocol

from atlas_api.schemas.embeddings import EmbeddingResult


class EmbeddingProvider(Protocol):
    provider: str
    model: str
    dimensions: int

    def embed_text(self, text: str) -> EmbeddingResult:
        """Generate an embedding for one text chunk."""
        ...

    def embed_texts(self, texts: list[str]) -> list[EmbeddingResult]:
        """Generate embeddings for an ordered batch of text chunks."""
        ...
