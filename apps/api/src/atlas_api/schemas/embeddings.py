from pydantic import BaseModel, Field


class EmbeddingResult(BaseModel):
    provider: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=120)
    dimensions: int = Field(gt=0)
    embedding: list[float] = Field(min_length=1)


class ChunkEmbeddingCreate(EmbeddingResult):
    pass
