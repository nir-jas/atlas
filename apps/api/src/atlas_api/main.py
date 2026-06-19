from fastapi import FastAPI

from atlas_api.core.config import settings
from atlas_api.http.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Personal knowledge platform for learning AI Engineering.",
    )
    app.include_router(api_router)
    return app


app = create_app()
