from datetime import datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from atlas_api.db.base import Base

if TYPE_CHECKING:
    from atlas_api.models.chunk import Chunk


class ChunkEmbedding(Base):
    __tablename__ = "chunk_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_id: Mapped[int] = mapped_column(
        ForeignKey("chunks.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    # SQLite is a lightweight unit-test database. PostgreSQL always receives
    # pgvector's native vector type, including in production migrations.
    embedding: Mapped[list[float]] = mapped_column(
        Vector().with_variant(JSON(), "sqlite"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    chunk: Mapped["Chunk"] = relationship(back_populates="embedding")
