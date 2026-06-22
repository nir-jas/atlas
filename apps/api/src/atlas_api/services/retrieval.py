from math import sqrt

from atlas_api.embedding_providers.base import EmbeddingProvider
from atlas_api.repositories.retrieval import RetrievalRepository
from atlas_api.schemas.rag import SearchRequest, SearchResult


class RetrievalService:
    def __init__(
        self,
        repository: RetrievalRepository,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._repository = repository
        self._embedding_provider = embedding_provider

    def search(self, payload: SearchRequest) -> list[SearchResult]:
        query_embedding = self._embedding_provider.embed_text(payload.query).embedding
        results = []

        for stored_chunk in self._repository.list_chunk_embeddings(payload.collection):
            similarity_score = self._cosine_similarity(query_embedding, stored_chunk.embedding)
            if similarity_score is None:
                continue

            results.append(
                SearchResult(
                    chunk_id=stored_chunk.chunk_id,
                    document_id=stored_chunk.document_id,
                    source_name=stored_chunk.source_name,
                    collection=stored_chunk.collection,
                    section=stored_chunk.section,
                    chunk_index=stored_chunk.chunk_index,
                    text=stored_chunk.text,
                    similarity_score=similarity_score,
                )
            )

        results.sort(key=lambda result: (-result.similarity_score, result.chunk_id))
        return results[: payload.top_k]

    def _cosine_similarity(
        self,
        left: list[float],
        right: list[float],
    ) -> float | None:
        if len(left) != len(right) or not left:
            return None

        dot_product = sum(
            left_value * right_value
            for left_value, right_value in zip(left, right, strict=True)
        )
        left_magnitude = sqrt(sum(value * value for value in left))
        right_magnitude = sqrt(sum(value * value for value in right))
        if left_magnitude == 0 or right_magnitude == 0:
            return None

        return dot_product / (left_magnitude * right_magnitude)
