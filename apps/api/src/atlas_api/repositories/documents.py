from sqlalchemy import select
from sqlalchemy.orm import Session

from atlas_api.models.document import Document
from atlas_api.schemas.documents import DocumentCreate


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, payload: DocumentCreate) -> Document:
        document = Document(**payload.model_dump())
        self._session.add(document)
        self._session.commit()
        self._session.refresh(document)
        return document

    def list_all(self) -> list[Document]:
        statement = select(Document).order_by(Document.uploaded_at.desc(), Document.id.desc())
        return list(self._session.scalars(statement).all())
