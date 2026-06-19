from fastapi import APIRouter

from atlas_api.core.config import settings
from atlas_api.http import system
from atlas_api.http.v1 import router as v1_router

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(v1_router, prefix=settings.api_v1_prefix)

