from fastapi import APIRouter

from app.api.v2.endpoints import optimise

api_router = APIRouter()
api_router.include_router(optimise.router, tags=["optimisation"])
