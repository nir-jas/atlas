from fastapi import APIRouter

from atlas_api.http.v1 import documents, knowledge

router = APIRouter()
router.include_router(documents.router)
router.include_router(knowledge.router)
