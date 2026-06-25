from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RerankInput:
    chunk_id: int
    text: str


@dataclass(frozen=True)
class RerankScore:
    chunk_id: int
    score: float


class RerankerProvider(Protocol):
    provider: str
    model: str

    def score(self, *, query: str, chunks: list[RerankInput]) -> list[RerankScore]:
        """Score retrieved chunks against the original user query."""
        ...
