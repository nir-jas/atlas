from pathlib import Path, PurePath
from uuid import uuid4

from atlas_api.embedding_providers.base import EmbeddingProvider
from atlas_api.models.document import Document
from atlas_api.repositories.documents import DocumentRepository
from atlas_api.schemas.documents import DocumentCreate, DocumentUploadRequest
from atlas_api.schemas.embeddings import ChunkEmbeddingCreate
from atlas_api.services.chunking import ChunkingService


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
        upload_dir: Path,
        chunking_service: ChunkingService,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._repository = repository
        self._upload_dir = upload_dir
        self._chunking_service = chunking_service
        self._embedding_provider = embedding_provider

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
        document_create = DocumentCreate(
            filename=filename,
            collection=payload.collection,
            document_type=payload.document_type,
            file_size=len(content),
        )

        try:
            chunks = self._chunking_service.chunk_document(filename=filename, content=content)
            if not chunks:
                return self._repository.create(document_create)

            embeddings = [
                ChunkEmbeddingCreate(**embedding.model_dump())
                for embedding in self._embedding_provider.embed_texts(
                    [chunk.text for chunk in chunks]
                )
            ]
            return self._repository.create_with_chunks(
                document_create,
                chunks=chunks,
                embeddings=embeddings,
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
