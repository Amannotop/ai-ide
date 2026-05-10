"""Health check and root API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Response

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "ai-ide-backend"}


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    """Readiness probe."""
    return {"ready": "true"}


@router.get("/")
async def root() -> dict[str, str]:
    """Root info endpoint."""
    return {"name": "ai-ide", "version": "1.0.0", "docs": "/api/v1/docs"}