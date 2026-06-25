from dataclasses import dataclass

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from atlas_api.models.chunk import Chunk
from atlas_api.models.chunk_embedding import ChunkEmbedding
from atlas_api.models.document import Document


@dataclass(frozen=True)
class StoredChunkEmbedding:
    chunk_id: int
    document_id: int
    source_name: str
    collection: str
    section: str | None
    chunk_index: int
    text: str
    similarity_score: float


class RetrievalRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def similarity_search(
        self,
        query_embedding: list[float],
        query_dimensions: int,
        limit: int,
        collection: str | None = None,
    ) -> list[StoredChunkEmbedding]:
        """Return ranked chunks using the database's vector implementation.

        PostgreSQL evaluates cosine distance with pgvector. SQLite retains a
        deliberately minimal exact-match branch solely for unit tests; it is
        not part of the application retrieval path in deployed environments.
        """
        if self._session.bind is not None and self._session.bind.dialect.name == "postgresql":
            distance = ChunkEmbedding.embedding.cosine_distance(query_embedding)
            similarity_score = (1 - distance).label("similarity_score")
            ordering = (distance.asc(), Chunk.id.asc())
        else:
            similarity_score = case(
                (ChunkEmbedding.embedding == query_embedding, 1.0),
                else_=0.0,
            ).label("similarity_score")
            ordering = (similarity_score.desc(), Chunk.id.asc())

        statement = (
            select(Chunk, Document, similarity_score)
            .join(ChunkEmbedding, ChunkEmbedding.chunk_id == Chunk.id)
            .join(Document, Document.id == Chunk.document_id)
            .where(ChunkEmbedding.dimensions == query_dimensions)
            .order_by(*ordering)
            .limit(limit)
        )
        if collection is not None:
            statement = statement.where(Document.collection == collection)

        return [
            StoredChunkEmbedding(
                chunk_id=chunk.id,
                document_id=document.id,
                source_name=document.filename,
                collection=document.collection,
                section=chunk.section,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                similarity_score=float(score),
            )
            for chunk, document, score in self._session.execute(statement)
        ]
