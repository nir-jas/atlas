from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from atlas_api.ai_providers.local import LocalAIProvider
from atlas_api.core.config import settings
from atlas_api.db.session import get_session
from atlas_api.embedding_providers.fake import FakeEmbeddingProvider
from atlas_api.repositories.documents import DocumentRepository
from atlas_api.repositories.memory import InMemoryKnowledgeRepository
from atlas_api.services.chunking import ChunkingService
from atlas_api.services.documents import DocumentService
from atlas_api.services.knowledge import KnowledgeService


@lru_cache
def get_knowledge_service() -> KnowledgeService:
    repository = InMemoryKnowledgeRepository()
    provider = LocalAIProvider()
    return KnowledgeService(repository=repository, ai_provider=provider)


def get_upload_dir() -> Path:
    return Path(settings.upload_dir)


SessionDep = Annotated[Session, Depends(get_session)]
UploadDirDep = Annotated[Path, Depends(get_upload_dir)]


def get_document_service(session: SessionDep, upload_dir: UploadDirDep) -> DocumentService:
    repository = DocumentRepository(session)
    return DocumentService(
        repository=repository,
        upload_dir=upload_dir,
        chunking_service=ChunkingService(),
        embedding_provider=FakeEmbeddingProvider(),
    )
