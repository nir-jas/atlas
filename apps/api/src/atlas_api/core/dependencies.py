from functools import lru_cache

from atlas_api.ai_providers.local import LocalAIProvider
from atlas_api.repositories.memory import InMemoryKnowledgeRepository
from atlas_api.services.knowledge import KnowledgeService


@lru_cache
def get_knowledge_service() -> KnowledgeService:
    repository = InMemoryKnowledgeRepository()
    provider = LocalAIProvider()
    return KnowledgeService(repository=repository, ai_provider=provider)

