from fastapi import APIRouter

from app.api.v1.endpoints import health, optimise, profiles, runs

api_router = APIRouter()

api_router.include_router(
    health.router,
    tags=["Health"],
)

api_router.include_router(
    optimise.router,
    tags=["Optimisation"],
)

api_router.include_router(
    runs.router,
    tags=["Runs"],
)

api_router.include_router(
    profiles.router,
    tags=["Profiles"],
)
