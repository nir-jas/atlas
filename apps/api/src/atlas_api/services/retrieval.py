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
        query_embedding = self._embedding_provider.embed_text(payload.query)
        stored_chunks = self._repository.similarity_search(
            query_embedding=query_embedding.embedding,
            query_dimensions=query_embedding.dimensions,
            limit=payload.top_k,
            collection=payload.collection,
        )
        return [
            SearchResult(
                chunk_id=stored_chunk.chunk_id,
                document_id=stored_chunk.document_id,
                source_name=stored_chunk.source_name,
                collection=stored_chunk.collection,
                section=stored_chunk.section,
                chunk_index=stored_chunk.chunk_index,
                text=stored_chunk.text,
                similarity_score=stored_chunk.similarity_score,
            )
            for stored_chunk in stored_chunks
        ]
