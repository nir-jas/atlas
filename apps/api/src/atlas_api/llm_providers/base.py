from typing import Protocol


class LLMProvider(Protocol):
    provider: str
    model: str

    def generate_answer(self, *, query: str, context: str) -> str:
        """Generate a grounded answer from assembled prompt context."""
        ...


class LLMProviderError(RuntimeError):
    """Raised when an LLM provider cannot complete an answer request."""
