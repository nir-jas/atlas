from fastapi import APIRouter

from atlas_api.http.v1 import knowledge

router = APIRouter()
router.include_router(knowledge.router)

