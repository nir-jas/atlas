from fastapi import APIRouter

from atlas_api.http.v1 import documents, knowledge, rag

router = APIRouter()
router.include_router(documents.router)
router.include_router(knowledge.router)
router.include_router(rag.router)
