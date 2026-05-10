"""Base service with common utilities."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from app.core.exceptions import ServiceError
from app.core.logging import get_logger


class BaseService:
    """Base class for all services."""

    def __init__(self, db_session: Any | None = None) -> None:
        self._db = db_session
        self._logger = get_logger(self.__class__.__name__)

    @property
    def logger(self):
        return self._logger

    @property
    def db(self):
        return self._db

    async def health(self) -> dict[str, Any]:
        """Health check for the service."""
        return {"status": "healthy", "service": self.__class__.__name__}

    async def validate(self, data: Any, rules: dict[str, Any] | None = None) -> dict[str, Any]:
        """Validate data against rules."""
        errors: dict[str, list[str]] = {}
        if rules:
            for field, rule in rules.items():
                value = getattr(data, field, None) if hasattr(data, field) else None
                if "required" in rule and (value is None or value == ""):
                    errors.setdefault(field, []).append("This field is required")
                if "max_length" in rule and value and len(str(value)) > rule["max_length"]:
                    errors.setdefault(field, []).append(f"Max length is {rule['max_length']}")
        return errors

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """Execute code within a transaction with rollback on error."""
        if self._db is None:
            raise ServiceError("Database session not available")
        try:
            yield
            await self._db.commit()
        except Exception:
            await self._db.rollback()
            raise