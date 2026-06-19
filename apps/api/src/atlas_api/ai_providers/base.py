from typing import Protocol


class AIProvider(Protocol):
    def generate_answer(self, question: str, context: list[str]) -> str:
        """Generate an answer using the supplied context."""

