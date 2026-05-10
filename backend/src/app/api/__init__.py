"""Main API router - aggregates all feature routers."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.agent import router as agent_router
from app.api.files import router as files_router
from app.api.git import router as git_router
from app.api.health import router as health_router
from app.api.terminal import router as terminal_router

api_router = APIRouter(prefix="/api/v1")


def register_routes() -> None:
    """Register all API routes."""
    api_router.include_router(health_router)
    api_router.include_router(files_router, prefix="/files")
    api_router.include_router(terminal_router, prefix="/terminal")
    api_router.include_router(git_router, prefix="/git")
    api_router.include_router(agent_router, prefix="/agent")


register_routes()