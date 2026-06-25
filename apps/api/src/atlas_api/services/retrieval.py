from atlas_api.embedding_providers.base import EmbeddingProvider
from atlas_api.repositories.retrieval import RetrievalRepository
from atlas_api.schemas.rag import SearchRequest, SearchResult
from atlas_api.services.query_rewrite import QueryRewriteService


class RetrievalService:
    def __init__(
        self,
        repository: RetrievalRepository,
        embedding_provider: EmbeddingProvider,
        query_rewrite_service: QueryRewriteService,
    ) -> None:
        self._repository = repository
        self._embedding_provider = embedding_provider
        self._query_rewrite_service = query_rewrite_service

    def search(self, payload: SearchRequest) -> list[SearchResult]:
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
                    or stored_chunk.similarity_score > existing_chunk.similarity_score
                ):
                    merged_chunks[stored_chunk.chunk_id] = SearchResult(
                        chunk_id=stored_chunk.chunk_id,
                        document_id=stored_chunk.document_id,
                        source_name=stored_chunk.source_name,
                        collection=stored_chunk.collection,
                        section=stored_chunk.section,
                        chunk_index=stored_chunk.chunk_index,
                        text=stored_chunk.text,
                        similarity_score=stored_chunk.similarity_score,
                        matched_queries=matched_queries,
                    )
                else:
                    existing_chunk.matched_queries = matched_queries

        return sorted(
            merged_chunks.values(),
            key=lambda chunk: (-chunk.similarity_score, chunk.chunk_id),
        )[: payload.top_k]
