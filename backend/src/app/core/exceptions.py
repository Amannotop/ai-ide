"""Service exceptions and custom errors."""
from __future__ import annotations

from typing import Any


class ServiceError(Exception):
    """Base service exception."""

    def __init__(self, message: str, code: str = "SERVICE_ERROR", details: dict[str, Any] | None = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(ServiceError):
    """Resource not found."""

    def __init__(self, message: str = "Not found", **kwargs):
        super().__init__(message, code="NOT_FOUND", **kwargs)


class PermissionError(ServiceError):
    """Permission denied."""

    def __init__(self, message: str = "Permission denied", **kwargs):
        super().__init__(message, code="PERMISSION_DENIED", **kwargs)


class ValidationError(ServiceError):
    """Validation failure."""

    def __init__(self, message: str = "Validation error", **kwargs):
        super().__init__(message, code="VALIDATION_ERROR", **kwargs)


class AgentError(ServiceError):
    """Agent execution error."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="AGENT_ERROR", **kwargs)


class ToolError(ServiceError):
    """Tool execution error."""

    def __init__(self, message: str, exit_code: int | None = None, **kwargs):
        super().__init__(message, code="TOOL_ERROR", **kwargs)
        self.exit_code = exit_code


class ModelError(ServiceError):
    """AI model error."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, code="MODEL_ERROR", **kwargs)