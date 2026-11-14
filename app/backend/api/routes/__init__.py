from fastapi import APIRouter

from .catalog import router as catalog_router
from .search import router as search_router
from .suggest import router as suggest_router
from .terrain import router as terrain_router


def build_api_router() -> APIRouter:
    api = APIRouter(prefix='/api')
    api.include_router(catalog_router)
    api.include_router(terrain_router)
    api.include_router(search_router)
    api.include_router(suggest_router)
    return api
