from datetime import datetime
from typing import Annotated

from fastapi import Form
from pydantic import BaseModel, ConfigDict, Field


class DocumentUploadRequest(BaseModel):
    collection: str = Field(min_length=1, max_length=120)
    document_type: str = Field(min_length=1, max_length=120)

    @classmethod
    def as_form(
        cls,
        collection: Annotated[str, Form(min_length=1, max_length=120)],
        document_type: Annotated[str, Form(min_length=1, max_length=120)],
    ) -> "DocumentUploadRequest":
        return cls(collection=collection, document_type=document_type)


class DocumentCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    collection: str = Field(min_length=1, max_length=120)
    document_type: str = Field(min_length=1, max_length=120)
    file_size: int = Field(ge=0)
    status: str = "uploaded"


class DocumentResponse(BaseModel):
    id: int
    filename: str
    collection: str
    document_type: str
    file_size: int
    status: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)
