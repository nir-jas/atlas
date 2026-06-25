from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from atlas_api.ai_providers.local import LocalAIProvider
from atlas_api.core.config import settings
from atlas_api.db.session import get_session
from atlas_api.embedding_providers.base import EmbeddingProvider
from atlas_api.embedding_providers.fake import FakeEmbeddingProvider
from atlas_api.embedding_providers.openai import OpenAIEmbeddingProvider
from atlas_api.llm_providers.base import LLMProvider
from atlas_api.llm_providers.fake import FakeLLMProvider
from atlas_api.llm_providers.openai import OpenAILLMProvider
from atlas_api.query_rewrite_providers.fake import FakeQueryRewriteProvider
from atlas_api.repositories.documents import DocumentRepository
from atlas_api.repositories.memory import InMemoryKnowledgeRepository
from atlas_api.repositories.retrieval import RetrievalRepository
from atlas_api.reranker_providers.base import RerankerProvider
from atlas_api.reranker_providers.fake import FakeRerankerProvider
from atlas_api.services.answer_generation import AnswerGenerationService
from atlas_api.services.chunking import ChunkingService
from atlas_api.services.context_assembly import ContextAssemblyService
from atlas_api.services.documents import DocumentService
from atlas_api.services.knowledge import KnowledgeService
from atlas_api.services.query_rewrite import QueryRewriteService
from atlas_api.services.reranking import RerankerService
from atlas_api.services.retrieval import RetrievalService


@lru_cache
def get_knowledge_service() -> KnowledgeService:
    repository = InMemoryKnowledgeRepository()
    provider = LocalAIProvider()
    return KnowledgeService(repository=repository, ai_provider=provider)


def get_upload_dir() -> Path:
    return Path(settings.upload_dir)


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    if settings.embedding_provider == "fake":
        return FakeEmbeddingProvider(dimensions=settings.vector_dimensions)

    return OpenAIEmbeddingProvider(
        api_key=settings.openai_api_key or "",
        model=settings.embedding_model,
        dimensions=settings.vector_dimensions,
    )


@lru_cache
def get_llm_provider() -> LLMProvider:
    if settings.llm_provider == "fake":
        return FakeLLMProvider()

    return OpenAILLMProvider(
        api_key=settings.openai_api_key or "",
        model=settings.llm_model,
    )


@lru_cache
def get_query_rewrite_service() -> QueryRewriteService:
    return QueryRewriteService(provider=FakeQueryRewriteProvider())


@lru_cache
def get_reranker_provider() -> RerankerProvider:
    provider_factories = {"fake": FakeRerankerProvider}
    return provider_factories[settings.reranker_provider]()


@lru_cache
def get_reranker_service() -> RerankerService:
    return RerankerService(
        provider=get_reranker_provider(),
        enabled=settings.reranker_enabled,
        top_k=settings.reranker_top_k,
        score_threshold=settings.reranker_score_threshold,
    )


SessionDep = Annotated[Session, Depends(get_session)]
UploadDirDep = Annotated[Path, Depends(get_upload_dir)]
EmbeddingProviderDep = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]
LLMProviderDep = Annotated[LLMProvider, Depends(get_llm_provider)]
QueryRewriteServiceDep = Annotated[
    QueryRewriteService,
    Depends(get_query_rewrite_service),
]
RerankerServiceDep = Annotated[RerankerService, Depends(get_reranker_service)]


def get_document_service(
    session: SessionDep,
    upload_dir: UploadDirDep,
    embedding_provider: EmbeddingProviderDep,
) -> DocumentService:
    repository = DocumentRepository(session)
    return DocumentService(
        repository=repository,
        upload_dir=upload_dir,
        chunking_service=ChunkingService(),
        embedding_provider=embedding_provider,
    )


def get_retrieval_service(
    session: SessionDep,
    embedding_provider: EmbeddingProviderDep,
    query_rewrite_service: QueryRewriteServiceDep,
    reranker_service: RerankerServiceDep,
) -> RetrievalService:
    return RetrievalService(
        repository=RetrievalRepository(session),
        embedding_provider=embedding_provider,
        query_rewrite_service=query_rewrite_service,
        reranker_service=reranker_service,
    )


@lru_cache
def get_context_assembly_service() -> ContextAssemblyService:
    return ContextAssemblyService()


ContextAssemblyServiceDep = Annotated[
    ContextAssemblyService,
    Depends(get_context_assembly_service),
]


def get_answer_generation_service(
    session: SessionDep,
    embedding_provider: EmbeddingProviderDep,
    context_assembly_service: ContextAssemblyServiceDep,
    llm_provider: LLMProviderDep,
    query_rewrite_service: QueryRewriteServiceDep,
    reranker_service: RerankerServiceDep,
) -> AnswerGenerationService:
    return AnswerGenerationService(
        retrieval_service=RetrievalService(
            repository=RetrievalRepository(session),
            embedding_provider=embedding_provider,
            query_rewrite_service=query_rewrite_service,
            reranker_service=reranker_service,
        ),
        context_assembly_service=context_assembly_service,
        llm_provider=llm_provider,
        default_similarity_score_threshold=settings.answer_similarity_score_threshold,
        max_context_characters=settings.answer_context_max_characters,
    )
