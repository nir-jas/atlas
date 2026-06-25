from hashlib import sha256

from atlas_api.schemas.embeddings import EmbeddingResult


class FakeEmbeddingProvider:
    provider = "fake"
    model = "fake-deterministic-v1"

    def __init__(self, dimensions: int = 8) -> None:
        self.dimensions = dimensions

    def embed_text(self, text: str) -> EmbeddingResult:
        seed = f"{self.provider}:{self.model}:{text}".encode()
        digest = sha256(seed).digest()
        values = []

        for index in range(self.dimensions):
            byte = digest[index % len(digest)]
            values.append(round(byte / 255, 6))

        return EmbeddingResult(
            provider=self.provider,
            model=self.model,
            dimensions=self.dimensions,
            embedding=values,
        )

    def embed_texts(self, texts: list[str]) -> list[EmbeddingResult]:
        return [self.embed_text(text) for text in texts]
