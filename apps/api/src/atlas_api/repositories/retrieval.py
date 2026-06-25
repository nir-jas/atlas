import re
from dataclasses import dataclass

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from atlas_api.models.chunk import Chunk
from atlas_api.models.chunk_embedding import ChunkEmbedding
from atlas_api.models.document import Document

KEYWORD_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_+#.-]*")


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


@dataclass(frozen=True)
class StoredKeywordChunk:
    chunk_id: int
    document_id: int
    source_name: str
    collection: str
    section: str | None
    chunk_index: int
    text: str
    keyword_rank: float


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

    def keyword_search(
        self,
        query: str,
        limit: int,
        collection: str | None = None,
    ) -> list[StoredKeywordChunk]:
        """Return chunks ranked by lexical match quality.

        PostgreSQL uses its built-in full-text search. SQLite keeps a compact
        fallback for local tests where PostgreSQL full-text primitives are not
        available.
        """
        if self._session.bind is not None and self._session.bind.dialect.name == "postgresql":
            ts_query = func.plainto_tsquery("english", query)
            search_vector = func.to_tsvector("english", Chunk.text)
            keyword_rank_expression = func.ts_rank_cd(search_vector, ts_query).label(
                "keyword_rank"
            )
            statement = (
                select(Chunk, Document, keyword_rank_expression)
                .join(Document, Document.id == Chunk.document_id)
                .where(search_vector.op("@@")(ts_query))
                .order_by(keyword_rank_expression.desc(), Chunk.id.asc())
                .limit(limit)
            )
            if collection is not None:
                statement = statement.where(Document.collection == collection)

            return [
                StoredKeywordChunk(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    source_name=document.filename,
                    collection=document.collection,
                    section=chunk.section,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    keyword_rank=float(rank),
                )
                for chunk, document, rank in self._session.execute(statement)
            ]

        terms = self._keyword_terms(query)
        if not terms:
            return []

        lowered_text = func.lower(Chunk.text)
        statement = (
            select(Chunk, Document)
            .join(Document, Document.id == Chunk.document_id)
            .where(or_(*(lowered_text.contains(term) for term in terms)))
        )
        if collection is not None:
            statement = statement.where(Document.collection == collection)

        matches: list[StoredKeywordChunk] = []
        for chunk, document in self._session.execute(statement):
            text = chunk.text.lower()
            keyword_score = float(sum(text.count(term) for term in terms))
            matches.append(
                StoredKeywordChunk(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    source_name=document.filename,
                    collection=document.collection,
                    section=chunk.section,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    keyword_rank=keyword_score,
                )
            )

        return sorted(matches, key=lambda match: (-match.keyword_rank, match.chunk_id))[:limit]

    @staticmethod
    def _keyword_terms(query: str) -> list[str]:
        terms: list[str] = []
        for term in KEYWORD_TOKEN_PATTERN.findall(query.lower()):
            if term not in terms:
                terms.append(term)

        return terms
