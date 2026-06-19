from pathlib import Path, PurePath
from uuid import uuid4

from atlas_api.models.document import Document
from atlas_api.repositories.documents import DocumentRepository
from atlas_api.schemas.documents import DocumentCreate, DocumentUploadRequest


class DocumentService:
    def __init__(self, repository: DocumentRepository, upload_dir: Path) -> None:
        self._repository = repository
        self._upload_dir = upload_dir

    def upload_document(
        self,
        payload: DocumentUploadRequest,
        original_filename: str | None,
        content: bytes,
    ) -> Document:
        filename = self._clean_filename(original_filename)
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        storage_path = self._upload_dir / f"{uuid4().hex}_{filename}"
        storage_path.write_bytes(content)

        try:
            return self._repository.create(
                DocumentCreate(
                    filename=filename,
                    collection=payload.collection,
                    document_type=payload.document_type,
                    file_size=len(content),
                )
            )
        except Exception:
            storage_path.unlink(missing_ok=True)
            raise

    def list_documents(self) -> list[Document]:
        return self._repository.list_all()

    def _clean_filename(self, filename: str | None) -> str:
        if not filename:
            return "uploaded-file"

        clean_name = PurePath(filename).name.strip()
        return clean_name or "uploaded-file"
