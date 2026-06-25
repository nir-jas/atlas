from types import SimpleNamespace

import pytest

from atlas_api.embedding_providers.openai import OpenAIEmbeddingProvider


class RecordingEmbeddingsClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(
            data=[
                SimpleNamespace(embedding=[0.1, 0.2, 0.3]),
                SimpleNamespace(embedding=[0.4, 0.5, 0.6]),
            ]
        )


def test_openai_provider_batches_texts_without_network_access() -> None:
    embeddings_client = RecordingEmbeddingsClient()
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        model="text-embedding-3-small",
        dimensions=3,
        client=SimpleNamespace(embeddings=embeddings_client),
    )

    results = provider.embed_texts(["first", "second"])

    assert [result.embedding for result in results] == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert embeddings_client.calls == [
        {
            "input": ["first", "second"],
            "model": "text-embedding-3-small",
            "dimensions": 3,
        }
    ]


def test_openai_provider_requires_an_api_key() -> None:
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAIEmbeddingProvider(api_key="", client=object())


def test_openai_provider_rejects_unexpected_vector_dimensions() -> None:
    embeddings_client = RecordingEmbeddingsClient()
    provider = OpenAIEmbeddingProvider(
        api_key="test-key",
        dimensions=4,
        client=SimpleNamespace(embeddings=embeddings_client),
    )

    with pytest.raises(RuntimeError, match="VECTOR_DIMENSIONS=4"):
        provider.embed_texts(["first", "second"])
