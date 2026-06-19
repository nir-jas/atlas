from pydantic import BaseModel, Field


class ChunkCreate(BaseModel):
    chunk_index: int = Field(ge=0)
    text: str = Field(min_length=1)
    section: str | None = None
    character_count: int = Field(gt=0)
