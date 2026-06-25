"""Integration coverage for the PostgreSQL-only pgvector retrieval path.

Set ATLAS_TEST_DATABASE_URL to an isolated PostgreSQL database with pgvector
available to run this module. It never instantiates the OpenAI provider.
"""

import os
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from atlas_api.db.base import Base
from atlas_api.embedding_providers.fake import FakeEmbeddingProvider
from atlas_api.models import Chunk, ChunkEmbedding, Document
from atlas_api.repositories.documents import DocumentRepository
from atlas_api.repositories.retrieval import RetrievalRepository
from atlas_api.schemas.chunks import ChunkCreate
from atlas_api.schemas.documents import DocumentCreate
from atlas_api.schemas.embeddings import ChunkEmbeddingCreate

TEST_DATABASE_URL = os.environ.get("ATLAS_TEST_DATABASE_URL")
pytestmark = pytest.mark.integration
_ = (Chunk, ChunkEmbedding, Document)


@pytest.fixture()
def session() -> Generator[Session, None, None]:
    if not TEST_DATABASE_URL:
        pytest.skip("ATLAS_TEST_DATABASE_URL is not configured")

    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.drop_all(connection)
        Base.metadata.create_all(connection)

    session_factory = sessionmaker(bind=engine)
    with session_factory() as database_session:
        yield database_session

    Base.metadata.drop_all(engine)
    engine.dispose()


def test_pgvector_similarity_search_ranks_and_filters_metadata(session: Session) -> None:
    provider = FakeEmbeddingProvider(dimensions=8)
    repository = DocumentRepository(session)
    chunks = [
        ChunkCreate(chunk_index=0, text="pgvector ranks semantic chunks", character_count=30),
        ChunkCreate(chunk_index=1, text="unrelated content", character_count=17),
    ]
    document = repository.create_with_chunks(
        DocumentCreate(
            filename="vectors.md",
            collection="engineering",
            document_type="note",
            file_size=48,
        ),
        chunks=chunks,
        embeddings=[
            ChunkEmbeddingCreate(**provider.embed_text(chunk.text).model_dump()) for chunk in chunks
        ],
    )

    query = provider.embed_text(chunks[0].text)
    results = RetrievalRepository(session).similarity_search(
        query_embedding=query.embedding,
        query_dimensions=query.dimensions,
        limit=5,
        collection="engineering",
    )

    assert results[0].document_id == document.id
    assert results[0].text == chunks[0].text
    assert results[0].similarity_score == pytest.approx(1.0)
    assert RetrievalRepository(session).similarity_search(
        query_embedding=query.embedding,
        query_dimensions=query.dimensions,
        limit=5,
        collection="other",
    ) == []
    column_type = session.execute(
        text(
            "SELECT atttypid::regtype::text FROM pg_attribute "
            "WHERE attrelid = 'chunk_embeddings'::regclass AND attname = 'embedding'"
        )
    ).scalar_one()
    assert column_type == "vector"
