from atlas_api.embedding_providers.base import EmbeddingProvider
from atlas_api.repositories.retrieval import (
    RetrievalRepository,
    StoredChunkEmbedding,
    StoredKeywordChunk,
)
from atlas_api.schemas.rag import SearchRequest, SearchResult
from atlas_api.services.query_rewrite import QueryRewriteService
from atlas_api.services.reranking import RerankerService

RRF_K = 60


class RetrievalService:
    def __init__(
        self,
        repository: RetrievalRepository,
        embedding_provider: EmbeddingProvider,
        query_rewrite_service: QueryRewriteService,
        reranker_service: RerankerService | None = None,
    ) -> None:
        self._repository = repository
        self._embedding_provider = embedding_provider
        self._query_rewrite_service = query_rewrite_service
        self._reranker_service = reranker_service

    @property
    def reranker_enabled(self) -> bool:
        return self._reranker_service.enabled if self._reranker_service is not None else False

    def search(self, payload: SearchRequest) -> list[SearchResult]:
        if payload.search_mode == "vector":
            candidates = self._vector_search(payload)
        elif payload.search_mode == "keyword":
            candidates = self._keyword_search(payload)
        else:
            vector_results = self._vector_search(payload)
            keyword_results = self._keyword_search(payload)
            candidates = self._rank_fuse(vector_results, keyword_results, limit=payload.top_k)

        if self._reranker_service is None:
            return candidates

        return self._reranker_service.rerank(query=payload.query, chunks=candidates)

    def _vector_search(self, payload: SearchRequest) -> list[SearchResult]:
        merged_chunks: dict[int, SearchResult] = {}

        for query in self._query_rewrite_service.rewrite(payload.query):
            query_embedding = self._embedding_provider.embed_text(query)
            stored_chunks = self._repository.similarity_search(
                query_embedding=query_embedding.embedding,
                query_dimensions=query_embedding.dimensions,
                limit=payload.top_k,
                collection=payload.collection,
            )

            for stored_chunk in stored_chunks:
                existing_chunk = merged_chunks.get(stored_chunk.chunk_id)
                matched_queries = (
                    [*existing_chunk.matched_queries]
                    if existing_chunk is not None
                    else []
                )
                if query not in matched_queries:
                    matched_queries.append(query)

                if (
                    existing_chunk is None
                    or existing_chunk.similarity_score is None
                    or stored_chunk.similarity_score > existing_chunk.similarity_score
                ):
                    result = self._from_vector_chunk(stored_chunk)
                    result.matched_queries = matched_queries
                    merged_chunks[stored_chunk.chunk_id] = result
                else:
                    existing_chunk.matched_queries = matched_queries

        return sorted(
            merged_chunks.values(),
            key=lambda chunk: (-(chunk.similarity_score or 0.0), chunk.chunk_id),
        )[: payload.top_k]

    def _keyword_search(self, payload: SearchRequest) -> list[SearchResult]:
        return [
            self._from_keyword_chunk(chunk, query=payload.query)
            for chunk in self._repository.keyword_search(
                query=payload.query,
                limit=payload.top_k,
                collection=payload.collection,
            )
        ]

    def _rank_fuse(
        self,
        vector_results: list[SearchResult],
        keyword_results: list[SearchResult],
        *,
        limit: int,
    ) -> list[SearchResult]:
        fused_results: dict[int, SearchResult] = {}
        fusion_scores: dict[int, float] = {}

        for rank, result in enumerate(vector_results, start=1):
            fused_results[result.chunk_id] = result
            fusion_scores[result.chunk_id] = fusion_scores.get(result.chunk_id, 0.0) + (
                1 / (RRF_K + rank)
            )

        for rank, result in enumerate(keyword_results, start=1):
            existing_result = fused_results.get(result.chunk_id)
            if existing_result is None:
                fused_results[result.chunk_id] = result
            else:
                existing_result.keyword_rank = result.keyword_rank
                if "keyword" not in existing_result.matched_by:
                    existing_result.matched_by.append("keyword")
                for query in result.matched_queries:
                    if query not in existing_result.matched_queries:
                        existing_result.matched_queries.append(query)

            fusion_scores[result.chunk_id] = fusion_scores.get(result.chunk_id, 0.0) + (
                1 / (RRF_K + rank)
            )

        return sorted(
            fused_results.values(),
            key=lambda result: (
                -fusion_scores[result.chunk_id],
                -(result.similarity_score or 0.0),
                -(result.keyword_rank or 0.0),
                result.chunk_id,
            ),
        )[:limit]

    @staticmethod
    def _from_vector_chunk(chunk: StoredChunkEmbedding) -> SearchResult:
        return SearchResult(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            source_name=chunk.source_name,
            collection=chunk.collection,
            section=chunk.section,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            similarity_score=chunk.similarity_score,
            matched_by=["vector"],
        )

    @staticmethod
    def _from_keyword_chunk(chunk: StoredKeywordChunk, *, query: str) -> SearchResult:
        return SearchResult(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            source_name=chunk.source_name,
            collection=chunk.collection,
            section=chunk.section,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            keyword_rank=chunk.keyword_rank,
            matched_by=["keyword"],
            matched_queries=[query],
        )
