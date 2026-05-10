"""Application middleware including CORS, error handling, and request logging."""
from __future__ import annotations

import time
from contextvars import ContextVar
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.core.logging import get_logger

request_id_var: ContextVar[str] = ContextVar("request_id", default="")
logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign unique request ID to every request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", "")
        if not request_id:
            import uuid
            request_id = str(uuid.uuid4())[:12]
        request_id_var.set(request_id)
        request.headers.__dict__["_list"].append((b"x-request-id", request_id.encode()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all HTTP requests with timing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start_time
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration * 1000, 2),
            request_id=request_id_var.get(""),
        )
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling for consistent error responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            logger.error("unhandled_error", error=str(exc), path=request.url.path)
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "detail": str(exc) if get_settings().debug else None},
            )


def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware on the FastAPI application."""
    settings = get_settings()

    # Must be outermost for CORS headers on errors
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)


def setup_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""

    @app.exception_handler(404)
    async def not_found(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=404, content={"error": "Not found"})

    @app.exception_handler(500)
    async def server_error(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"error": "Internal server error"})