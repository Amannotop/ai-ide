"""File management API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, WebSocket

from app.core.logging import get_logger
from app.schemas import (
    CodeSearchResult,
    ContextRetrieveRequest,
    ContextRetrieveResponse,
    FileReadRequest,
    FileResponse,
    FileSearchRequest,
)
from app.services.ai import embedding_service
from app.services.workspace import WorkspaceService

router = APIRouter(tags=["files"])
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
async def read_file(request: FileReadRequest = FileReadRequest(path=".")) -> FileResponse:
    """Read a file from the workspace."""
    ws = WorkspaceService()
    return await ws.read_file(request)


@router.post("/write", response_model=FileResponse)
async def write_file(request: FileReadRequest) -> FileResponse:
    """Write a file to the workspace."""
    from app.schemas import FileWriteRequest

    ws = WorkspaceService()
    write_req = FileWriteRequest(path=request.path, content="", create_if_missing=True)
    return await ws.write_file(write_req)


@router.post("/search", response_model=list[CodeSearchResult])
async def code_search(query: str = "", workspace_id: str = "default", limit: int = 10) -> list[CodeSearchResult]:
    """Semantic code search within workspace."""
    try:
        results = await embedding_service.search_embeddings(
            query=query,
            workspace_id=workspace_id,
            limit=limit,
        )
        return [
            CodeSearchResult(
                file=r.get("source", ""),
                line=0,
                content=r.get("content", ""),
                score=r.get("score", 0.0),
                snippet=r.get("content", "")[:200] if r.get("content") else "",
            )
            for r in results
        ]
    except Exception:
        return []


@router.post("/context", response_model=ContextRetrieveResponse)
async def retrieve_context(request: ContextRetrieveRequest) -> ContextRetrieveResponse:
    """Retrieve relevant context for a query."""
    from app.services.conversation import memory_service

    embedding_results = await embedding_service.search_embeddings(
        query=request.query,
        workspace_id=request.workspace_id,
        limit=max(1, request.limit // 1000),
    )

    memory_results = await memory_service.search_memory(
        workspace_id=request.workspace_id,
        query=request.query,
        limit=20,
    )

    files = [{"path": r.get("source", ""), "content": r.get("content", ""), "score": r.get("score", 0.0)} for r in embedding_results]
    memories = [{"key": m.memory_key, "content": m.content, "access_count": m.access_count} for m in memory_results]

    return ContextRetrieveResponse(
        files=files,
        memory=memories,
        summary=f"Retrieved {len(files)} file contexts and {len(memories)} memory entries.",
    )