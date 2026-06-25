"""store chunk embeddings as pgvector values

Revision ID: 20260622_0004
Revises: 20260619_0003
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "20260622_0004"
down_revision: str | None = "20260619_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.alter_column(
        "chunk_embeddings",
        "embedding",
        existing_type=sa.JSON(),
        type_=Vector(),
        postgresql_using="embedding::text::vector",
    )
    op.create_index(
        "ix_chunk_embeddings_dimensions",
        "chunk_embeddings",
        ["dimensions"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_chunk_embeddings_dimensions", table_name="chunk_embeddings")
    op.alter_column(
        "chunk_embeddings",
        "embedding",
        existing_type=Vector(),
        type_=sa.JSON(),
        postgresql_using="embedding::text::json",
    )
