from fastapi import FastAPI

from app.api.v1.router import api_router as api_v1_router
from app.api.v2.router import api_router as api_v2_router
from app.core.config import settings


def create_application() -> FastAPI:
    docs_enabled = settings.environment != "production"

    application = FastAPI(
        title=settings.project_name,
        version=settings.version,
        openapi_url=(
            f"{settings.api_v1_prefix}/openapi.json" if docs_enabled else None
        ),
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
    )

    application.include_router(
        api_v1_router,
        prefix=settings.api_v1_prefix,
    )

    application.include_router(
        api_v2_router,
        prefix=settings.api_v2_prefix,
    )

    return application


app = create_application()
