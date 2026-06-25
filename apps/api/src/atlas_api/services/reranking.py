from atlas_api.reranker_providers.base import RerankerProvider, RerankInput
from atlas_api.schemas.rag import SearchResult


class RerankerService:
    def __init__(
        self,
        provider: RerankerProvider,
        *,
        enabled: bool,
        top_k: int,
        score_threshold: float,
    ) -> None:
        self._provider = provider
        self._enabled = enabled
        self._top_k = top_k
        self._score_threshold = score_threshold

    @property
    def enabled(self) -> bool:
        return self._enabled

    def rerank(self, *, query: str, chunks: list[SearchResult]) -> list[SearchResult]:
        if not self._enabled:
            return chunks

        scores = self._provider.score(
            query=query,
            chunks=[
                RerankInput(chunk_id=chunk.chunk_id, text=chunk.text)
                for chunk in chunks
            ],
        )
        score_by_chunk_id = {score.chunk_id: score.score for score in scores}
        scored_chunks: list[tuple[int, SearchResult]] = []
        for retrieval_rank, chunk in enumerate(chunks):
            chunk.reranker_enabled = True
            chunk.reranker_score = score_by_chunk_id.get(chunk.chunk_id, 0.0)
            if chunk.reranker_score >= self._score_threshold:
                scored_chunks.append((retrieval_rank, chunk))

        return [
            chunk
            for _, chunk in sorted(
                scored_chunks,
                key=lambda ranked_chunk: (
                    -(ranked_chunk[1].reranker_score or 0.0),
                    ranked_chunk[0],
                ),
            )[: self._top_k]
        ]
