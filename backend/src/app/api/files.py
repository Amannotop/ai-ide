"""File management API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db import get_session
from app.schemas import (
    CodeSearchRequest,
    CodeSearchResult,
    ContextRetrieveRequest,
    ContextRetrieveResponse,
    FileReadRequest,
    FileResponse,
    FileSearchRequest,
    FileWriteRequest,
    StreamEvent,
)
from app.services.workspace import WorkspaceService

router = APIRouter(prefix="/api/v1/files", tags=["files"])
logger = get_logger(__name__)


@router.get("/tree", response_model=dict)
async def get_workspace_tree() -> dict:
    """Get workspace directory tree."""
    ws = WorkspaceService()
    return await ws.get_tree()


@router.get("/list", response_model=list[dict])
async def list_files(path: str = ".") -> list[dict]:
    """List files in workspace path."""
    ws = WorkspaceService()
    return await ws.list_files(path)


@router.get("/read", response_model=FileResponse)
async def read_file(request: FileReadRequest = Depends()) -> FileResponse:
    """Read a file from the workspace."""
    ws = WorkspaceService()
    return await ws.read_file(request)


@router.post("/write", response_model=FileResponse)
async def write_file(request: FileWriteRequest) -> FileResponse:
    """Write a file to the workspace."""
    ws = WorkspaceService()
    return await ws.write_file(request)


@router.delete("/delete")
async def delete_file(path: str) -> dict:
    """Delete a file."""
    ws = WorkspaceService()
    return await ws.delete_file(path)


@router.post("/replace", response_model=FileResponse)
async def replace_in_file(request: FileWriteRequest) -> FileResponse:
    """Replace text in a file."""
    ws = WorkspaceService()
    # For simple replace, use write_file path with old/new from request metadata
    from app.schemas import FileReplaceRequest

    rr = FileReplaceRequest(
        path=request.path,
        old_content=request.content.split("---OLD---")[0] if "---OLD---" in request.content else "",
        new_content=request.content.split("---NEW---")[0] if "---NEW---" in request.content else request.content,
    )
    return await ws.replace_in_file(rr)


@router.post("/search", response_model=list[dict])
async def search_files(request: FileSearchRequest) -> list[dict]:
    """Search files by pattern."""
    ws = WorkspaceService()
    return await ws.search_files(request)


@router.post("/code-search", response_model=list[CodeSearchResult])
async def code_search(request: CodeSearchRequest) -> list[CodeSearchResult]:
    """Semantic code search within workspace."""
    ws = WorkspaceService()
    from app.services.ai import embedding_service

    results = await embedding_service.search_embeddings(
        query=request.query,
        workspace_id="default",
        limit=request.limit,
    )
    return [
        CodeSearchResult(
            file=r.get("source", ""),
            line=0,
            content=r.get("content", ""),
            score=r.get("score", 0.0),
            snippet=r.get("content", "")[:200],
        )
        for r in results
    ]


@router.post("/context", response_model=ContextRetrieveResponse)
async def retrieve_context(request: ContextRetrieveRequest) -> ContextRetrieveResponse:
    """Retrieve relevant context for a query."""
    from app.services.ai import embedding_service, memory_service
    from app.services.workspace import WorkspaceService

    ws = WorkspaceService()

    # Search embeddings
    embedding_results = await embedding_service.search_embeddings(
        query=request.query,
        workspace_id=request.workspace_id,
        limit=request.limit // 1000,
    )

    # Search memory
    memory_results = await memory_service.search_memory(
        workspace_id=request.workspace_id,
        query=request.query,
        limit=20,
    )

    # Build file context
    files: list[dict] = []
    for r in embedding_results:
        source = r.get("source", "")
        content = r.get("content", "")
        files.append({
            "path": source,
            "content": content,
            "score": r.get("score", 0.0),
        })

    # Build memory context
    memories: list[dict] = []
    for m in memory_results:
        memories.append({
            "key": m.memory_key,
            "content": m.content,
            "access_count": m.access_count,
        })

    return ContextRetrieveResponse(
        files=files,
        memory=memories,
        summary=f"Retrieved {len(files)} file contexts and {len(memories)} memory entries.",
    )