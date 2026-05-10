"""Agent orchestration and execution API."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.exceptions import AgentError, ToolError
from app.core.logging import get_logger
from app.db import get_session
from app.schemas import (
    AgentEvent,
    AgentTaskCreate,
    AgentTaskSchema,
    AgentTaskUpdate,
    ChatCompletionRequest,
    ChatMessage,
    CodeSearchResult,
    StreamEvent,
    WorkspaceMemoryCreate,
)
from app.services.agent import AgentExecutor
from app.services.conversation import (
    AgentTaskService,
    agent_task_service,
    conversation_service,
    embedding_service,
    memory_service,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


# Active agent sessions
active_agents: dict[str, dict] = {}


@router.post("/tasks", response_model=AgentTaskSchema)
async def create_agent_task(task: AgentTaskCreate) -> AgentTaskSchema:
    """Create a new agent task."""
    return await agent_task_service.create_task(task)


@router.get("/tasks", response_model=list[AgentTaskSchema])
async def list_agent_tasks(
    workspace_id: str,
    status: str | None = None,
    limit: int = 50,
) -> list[AgentTaskSchema]:
    """List agent tasks for a workspace."""
    return await agent_task_service.list_tasks(workspace_id, status, limit)


@router.post("/execute", response_model=dict)
async def execute_agent_task(request: dict[str, Any]) -> dict:
    """Execute an agent task synchronously."""
    task_type = request.get("task_type", "code")
    goal = request.get("goal", "")
    workspace_id = request.get("workspace_id", "default")
    workspace_root = request.get("workspace_root", str(get_settings().workspace_root))

    executor = AgentExecutor(workspace_root=workspace_root)

    try:
        result = await executor.execute_task(task_type, goal)
        return {"status": "completed", "result": result}
    except Exception as e:
        logger.error("agent_execution_failed", error=str(e), task_type=task_type)
        raise AgentError(f"Agent task failed: {e}")


@router.websocket("/stream")
async def agent_stream(websocket: WebSocket):
    """WebSocket endpoint for streaming agent execution."""
    await websocket.accept()
    agent_id = str(id(websocket))

    active_agents[agent_id] = {"websocket": websocket, "running": False}

    try:
        while True:
            data = await websocket.receive_text()
            message = __import__("json").loads(data)
            action = message.get("action", "")

            if action == "execute":
                active_agents[agent_id]["running"] = True
                task_type = message.get("task_type", "code")
                goal = message.get("goal", "")
                workspace_root = message.get("workspace_root", str(get_settings().workspace_root))

                executor = AgentExecutor(workspace_root=workspace_root)

                # Stream execution events
                async for event in executor.stream_execute(task_type, goal):
                    await websocket.send_text(__import__("json").dumps({
                        "type": event["type"],
                        "data": event.get("data", {}),
                    }))

                active_agents[agent_id]["running"] = False

            elif action == "cancel":
                active_agents[agent_id]["running"] = False
                executor = AgentExecutor(workspace_root=str(get_settings().workspace_root))
                await executor.cancel()
                await websocket.send_text(__import__("json").dumps({
                    "type": "cancelled",
                    "data": {},
                }))

    except WebSocketDisconnect:
        active_agents[agent_id]["running"] = False
    finally:
        active_agents.pop(agent_id, None)


@router.get("/models")
async def list_available_models() -> dict:
    """List available AI models."""
    from app.services.ai import model_router
    models = await model_router.list_models()
    return {"models": models}


@router.get("/memory")
async def get_workspace_memory(workspace_id: str, query: str | None = None, limit: int = 20) -> dict:
    """Retrieve workspace memory."""
    if query:
        results = await memory_service.search_memory(workspace_id, query, limit)
        return {"type": "search", "results": [
            {"key": m.memory_key, "content": m.content, "access_count": m.access_count}
            for m in results
        ]}

    return {"type": "all", "workspace_id": workspace_id}


@router.post("/memory")
async def store_memory(data: WorkspaceMemoryCreate) -> dict:
    """Store workspace memory."""
    result = await memory_service.store_memory(data)
    return result


@router.post("/chat", response_model=dict)
async def agent_chat(request: ChatCompletionRequest) -> dict:
    """Chat endpoint with context retrieval."""
    from app.services.ai import model_router

    messages = [m.model_dump() for m in request.messages]
    model = request.model or get_settings().ollama_default_model

    # Add context files to system prompt
    if request.context_files:
        context_prompt = "Relevant files: " + ", ".join(request.context_files)
        messages.insert(0, {"role": "system", "content": context_prompt})

    if request.stream:
        # Return streaming response info
        return {"streaming": True, "model": model, "url": "/api/v1/agent/stream"}

    result = await model_router.chat_completion(
        req=request,
    )
    return result


@router.websocket("/chat-stream")
async def chat_stream(websocket: WebSocket):
    """WebSocket for streaming chat responses."""
    await websocket.accept()

    try:
        data = await websocket.receive_text()
        message = __import__("json").loads(data)

        from app.services.ai import model_router

        request = ChatCompletionRequest(**message)
        messages = [m.model_dump() for m in request.messages]

        # Create streaming response
        response_id = __import__("uuid").uuid4().hex[:12]
        full_response = []

        async for chunk in model_router.stream_completion(request):
            full_response.append(chunk)
            try:
                parsed = __import__("json").loads(chunk)
                content = parsed.get("message", {}).get("content", "")
                await websocket.send_text(__import__("json").dumps({
                    "type": "chunk",
                    "id": response_id,
                    "content": content,
                    "raw": chunk[:500],
                }))
            except Exception:
                await websocket.send_text(__import__("json").dumps({
                    "type": "chunk",
                    "id": response_id,
                    "content": chunk[:500],
                }))

        await websocket.send_text(__import__("json").dumps({
            "type": "complete",
            "id": response_id,
            "full_response": "".join(full_response),
        }))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_text(__import__("json").dumps({
            "type": "error",
            "error": str(e),
        }))