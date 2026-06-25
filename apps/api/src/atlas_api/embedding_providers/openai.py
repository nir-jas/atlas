from typing import Any

from atlas_api.schemas.embeddings import EmbeddingResult


class OpenAIEmbeddingProvider:
    provider = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536,
        client: Any | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")

        self.model = model
        self.dimensions = dimensions
        self._client = client or self._build_client(api_key)

    @staticmethod
    def _build_client(api_key: str) -> Any:
        try:
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError(
                "The OpenAI SDK is not installed. Run `uv sync --extra dev`."
            ) from error
        return OpenAI(api_key=api_key)

    def embed_text(self, text: str) -> EmbeddingResult:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[EmbeddingResult]:
        if not texts:
            return []

        response = self._client.embeddings.create(
            input=texts,
            model=self.model,
            dimensions=self.dimensions,
        )
        embeddings = [item.embedding for item in response.data]
        if len(embeddings) != len(texts):
            raise RuntimeError("OpenAI returned an unexpected number of embeddings")

        results = [
            EmbeddingResult(
                provider=self.provider,
                model=self.model,
                dimensions=len(embedding),
                embedding=embedding,
            )
            for embedding in embeddings
        ]
        if any(result.dimensions != self.dimensions for result in results):
            raise RuntimeError(
                f"OpenAI returned embeddings that do not match VECTOR_DIMENSIONS={self.dimensions}"
            )
        return results
