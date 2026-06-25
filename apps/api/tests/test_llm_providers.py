from types import SimpleNamespace

import pytest

from atlas_api.llm_providers.fake import FakeLLMProvider
from atlas_api.llm_providers.openai import OpenAILLMProvider


class RecordingResponsesClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(output_text="Grounded OpenAI answer.")


def test_fake_provider_is_deterministic_and_requires_context() -> None:
    provider = FakeLLMProvider()

    assert provider.generate_answer(
        query="What is Atlas?",
        context="Source: atlas.md\nSection: Overview\n\nAtlas is a knowledge platform.",
    ) == "Fake grounded answer for: What is Atlas?"
    with pytest.raises(ValueError, match="Context is required"):
        provider.generate_answer(query="What is Atlas?", context="")


def test_openai_provider_uses_the_responses_api_without_network_access() -> None:
    responses_client = RecordingResponsesClient()
    provider = OpenAILLMProvider(
        api_key="test-key",
        model="gpt-5.4",
        client=SimpleNamespace(responses=responses_client),
    )

    answer = provider.generate_answer(
        query="What is context assembly?",
        context="Source: rag.md\nSection: Context\n\nContext is assembled before generation.",
    )

    assert answer == "Grounded OpenAI answer."
    assert responses_client.calls == [
        {
            "model": "gpt-5.4",
            "instructions": (
                "Answer the user question using only the supplied context. "
                "If the context does not support an answer, say so. "
                "Do not include citations in the answer text."
            ),
            "input": (
                "Question:\nWhat is context assembly?\n\nContext:\n"
                "Source: rag.md\nSection: Context\n\n"
                "Context is assembled before generation."
            ),
            "store": False,
        }
    ]


def test_openai_provider_requires_an_api_key() -> None:
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        OpenAILLMProvider(api_key="", client=object())
