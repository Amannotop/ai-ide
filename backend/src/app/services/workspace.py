"""Workspace service - manages workspaces and file system interactions."""
from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any

from app.config.settings import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.schemas import FileResponse, FileReadRequest, FileWriteRequest, FileSearchRequest, FileReplaceRequest

logger = get_logger(__name__)


class WorkspaceService:
    """Service for workspace and file management."""

    def __init__(self, workspace_root: str | None = None) -> None:
        settings = get_settings()
        self.root = Path(workspace_root or settings.workspace_root).resolve()
        self._ensure_workspace()

    def _ensure_workspace(self) -> None:
        """Create workspace directory if it doesn't exist."""
        self.root.mkdir(parents=True, exist_ok=True)

    def _validate_path(self, path: Path) -> Path:
        """Ensure path is within workspace (prevent path traversal)."""
        try:
            resolved = path.resolve()
            resolved.relative_to(self.root)
            return resolved
        except ValueError:
            raise ValidationError(f"Path {path} is outside workspace")

    async def list_files(self, path: str = ".") -> list[dict[str, Any]]:
        """List files and directories in a workspace path."""
        target = self._validate_path(self.root / path)
        if not target.exists():
            raise NotFoundError(f"Path not found: {path}")

        entries: list[dict[str, Any]] = []
        for item in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name)):
            stat = item.stat()
            entries.append({
                "name": item.name,
                "path": str(item.relative_to(self.root)),
                "is_dir": item.is_dir(),
                "size": stat.st_size if item.is_file() else None,
                "modified": stat.st_mtime,
            })
        return entries

    async def read_file(self, request: FileReadRequest) -> FileResponse:
        """Read file contents from workspace."""
        path = self._validate_path(self.root / request.path)
        if not path.exists():
            return FileResponse(path=request.path, content="", exists=False)
        if not path.is_file():
            raise ValidationError(f"Path is not a file: {request.path}")
        stat = path.stat()
        return FileResponse(
            path=request.path,
            content=path.read_text(encoding="utf-8"),
            exists=True,
            size=stat.st_size,
            modified_at=stat.st_mtime,
        )

    async def write_file(self, request: FileWriteRequest) -> FileResponse:
        """Write content to file in workspace."""
        path = self._validate_path(self.root / request.path)
        if not request.create_if_missing and not path.exists():
            raise NotFoundError(f"File not found: {request.path}")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(request.content, encoding="utf-8")
        stat = path.stat()
        logger.info("file_written", path=request.path, size=len(request.content))
        return FileResponse(
            path=request.path,
            content=request.content,
            exists=True,
            size=stat.st_size,
        )

    async def delete_file(self, path: str) -> dict[str, str]:
        """Delete a file or empty directory."""
        target = self._validate_path(self.root / path)
        if not target.exists():
            raise NotFoundError(f"Path not found: {path}")
        if target.is_dir() and any(target.iterdir()):
            raise ValidationError(f"Cannot delete non-empty directory: {path}")

        if target.is_file():
            target.unlink()
        else:
            target.rmdir()
        logger.info("file_deleted", path=path)
        return {"status": "deleted", "path": path}

    async def search_files(self, request: FileSearchRequest) -> list[dict[str, Any]]:
        """Search for files matching a glob pattern."""
        import fnmatch

        root = self.root / (request.workspace_root or ".")
        results: list[dict[str, Any]] = []

        for item in root.rglob("*"):
            if fnmatch.fnmatch(item.name, request.pattern):
                try:
                    rel = item.relative_to(self.root)
                    results.append({
                        "name": item.name,
                        "path": str(rel),
                        "is_dir": item.is_dir(),
                        "size": item.stat().st_size if item.is_file() else None,
                    })
                except ValueError:
                    continue
        return results

    async def replace_in_file(self, request: FileReplaceRequest) -> FileResponse:
        """Replace text in a file."""
        path = self._validate_path(self.root / request.path)
        if not path.exists():
            raise NotFoundError(f"File not found: {request.path}")

        content = path.read_text(encoding="utf-8")
        if request.old_content not in content:
            raise ValidationError("Old content not found in file")

        new_content = content.replace(request.old_content, request.new_content)
        path.write_text(new_content, encoding="utf-8")
        logger.info("file_replaced", path=request.path)

        return FileResponse(
            path=request.path,
            content=new_content,
            exists=True,
            size=len(new_content),
        )

    async def create_directory(self, path: str) -> dict[str, Any]:
        """Create a new directory in the workspace."""
        target = self._validate_path(self.root / path)
        target.mkdir(parents=True, exist_ok=True)
        return {"status": "created", "path": path}

    async def get_tree(self, max_depth: int = 5) -> dict[str, Any]:
        """Get workspace directory tree structure."""
        return {
            "name": self.root.name,
            "path": "",
            "is_dir": True,
            "children": await self._build_tree(self.root, 0, max_depth),
        }

    async def _build_tree(self, directory: Path, depth: int, max_depth: int) -> list[dict[str, Any]]:
        """Recursively build directory tree."""
        if depth >= max_depth:
            return []
        items = []
        for item in sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name)):
            if item.name.startswith(".") and item.name not in (".env", ".gitignore"):
                continue
            node = {
                "name": item.name,
                "path": str(item.relative_to(self.root)),
                "is_dir": item.is_dir(),
            }
            if item.is_dir():
                node["children"] = await self._build_tree(item, depth + 1, max_depth)
            items.append(node)
        return items