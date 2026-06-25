class FakeLLMProvider:
    """Deterministic answer provider used for local development and tests."""

    provider = "fake"
    model = "fake-grounded-v1"

    def generate_answer(self, *, query: str, context: str) -> str:
        if not context:
            raise ValueError("Context is required to generate an answer")
        return f"Fake grounded answer for: {query}"
