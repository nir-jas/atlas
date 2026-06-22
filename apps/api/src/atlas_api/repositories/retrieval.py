from dataclasses import dataclass

from sqlalchemy import select
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
    embedding: list[float]


class RetrievalRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_chunk_embeddings(self, collection: str | None = None) -> list[StoredChunkEmbedding]:
        statement = (
            select(Chunk, ChunkEmbedding, Document)
            .join(ChunkEmbedding, ChunkEmbedding.chunk_id == Chunk.id)
            .join(Document, Document.id == Chunk.document_id)
            .order_by(Chunk.id)
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
                embedding=embedding.embedding,
            )
            for chunk, embedding, document in self._session.execute(statement)
        ]
