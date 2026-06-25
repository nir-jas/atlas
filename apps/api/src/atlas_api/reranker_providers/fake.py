import re

from atlas_api.reranker_providers.base import RerankInput, RerankScore

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_+#.-]*")


class FakeRerankerProvider:
    """Deterministic lexical reranker used for local development and tests."""

    provider = "fake"
    model = "fake-reranker-v1"

    def score(self, *, query: str, chunks: list[RerankInput]) -> list[RerankScore]:
        query_terms = self._unique_terms(query)
        if not query_terms:
            return [RerankScore(chunk_id=chunk.chunk_id, score=0.0) for chunk in chunks]

        normalized_query = " ".join(query.lower().split())
        scores: list[RerankScore] = []
        for chunk in chunks:
            chunk_text = chunk.text.lower()
            chunk_terms = set(self._unique_terms(chunk.text))
            overlap = len([term for term in query_terms if term in chunk_terms])
            score = overlap / len(query_terms)
            if normalized_query and normalized_query in " ".join(chunk_text.split()):
                score = min(score + 0.1, 1.0)
            scores.append(RerankScore(chunk_id=chunk.chunk_id, score=round(score, 4)))

        return scores

    @staticmethod
    def _unique_terms(text: str) -> list[str]:
        terms: list[str] = []
        for raw_term in TOKEN_PATTERN.findall(text.lower()):
            term = raw_term.strip(".,:;!?()[]{}\"'")
            if term and term not in terms:
                terms.append(term)

        return terms
