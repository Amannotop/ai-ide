"""Conversation and messaging service."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.config.settings import get_settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.db.session import get_session
from app.models.base import AgentTask, Conversation, EmbeddingIndex, FileSnapshot, Message, WorkspaceMemory
from app.schemas import (
    AgentTaskCreate,
    AgentTaskSchema,
    AgentTaskUpdate,
    ChatMessage,
    ChatCompletionRequest,
    ConversationCreate,
    ConversationSchema,
    EmbeddingCreate,
    WorkspaceMemoryCreate,
)

logger = get_logger(__name__)


class ConversationService:
    """Service for managing conversations and messages."""

    async def list_conversations(self, limit: int = 20, offset: int = 0) -> list[ConversationSchema]:
        """List recent conversations."""
        async for session in get_session():
            result = await session.execute(
                Conversation.__table__.select().order_by(Conversation.created_at.desc()).limit(limit).offset(offset)
            )
            rows = result.fetchall()
            return [ConversationSchema.model_validate(dict(r._mapping)) for r in rows]
        return []

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Get a conversation by ID."""
        async for session in get_session():
            result = await session.get(Conversation, conversation_id)
            return result

    async def create_conversation(self, data: ConversationCreate) -> ConversationSchema:
        """Create a new conversation."""
        async for session in get_session():
            conv = Conversation(
                id=str(uuid4()),
                title=data.title,
                model=data.model or get_settings().ollama_default_model,
                metadata_=data.metadata_,
            )
            session.add(conv)
            await session.flush()
            await session.refresh(conv)
            return ConversationSchema.model_validate(conv)

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        name: str | None = None,
        metadata_: dict[str, Any] | None = None,
    ) -> Message:
        """Add a message to a conversation."""
        async for session in get_session():
            conv = await session.get(Conversation, conversation_id)
            if not conv:
                raise NotFoundError(f"Conversation not found: {conversation_id}")
            msg = Message(
                id=str(uuid4()),
                conversation_id=conversation_id,
                role=role,
                content=content,
                name=name,
                metadata_=metadata_,
            )
            session.add(msg)
            await session.flush()
            await session.refresh(msg)
            conv.updated_at = datetime.now(timezone.utc)
            return msg

    async def get_messages(self, conversation_id: str, limit: int = 100, offset: int = 0) -> list[Message]:
        """Get messages for a conversation."""
        async for session in get_session():
            result = await session.execute(
                Message.__table__.select()
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
                .limit(limit)
                .offset(offset)
            )
            return [Message(**dict(r._mapping)) for r in result.fetchall()]

    async def update_conversation(self, conversation_id: str, data: ConversationUpdate) -> ConversationSchema:
        """Update conversation metadata."""
        async for session in get_session():
            conv = await session.get(Conversation, conversation_id)
            if not conv:
                raise NotFoundError(f"Conversation not found: {conversation_id}")
            if data.title is not None:
                conv.title = data.title
            if data.summary is not None:
                conv.summary = data.summary
            if data.metadata_ is not None:
                conv.metadata_ = data.metadata_
            await session.flush()
            return ConversationSchema.model_validate(conv)

    async def delete_conversation(self, conversation_id: str) -> dict[str, str]:
        """Delete a conversation and its messages."""
        async for session in get_session():
            conv = await session.get(Conversation, conversation_id)
            if not conv:
                raise NotFoundError(f"Conversation not found: {conversation_id}")
            await session.delete(conv)
            return {"status": "deleted", "id": conversation_id}


class MemoryService:
    """Service for workspace memory management."""

    async def store_memory(self, data: WorkspaceMemoryCreate) -> dict[str, str]:
        """Store a memory entry."""
        async for session in get_session():
            mem = WorkspaceMemory(
                workspace_id=data.workspace_id,
                memory_key=data.memory_key,
                content=data.content,
                tags=data.tags,
                metadata_=data.metadata_,
            )
            session.add(mem)
            await session.flush()
            logger.info("memory_stored", key=data.memory_key, workspace=data.workspace_id)
            return {"status": "stored", "id": mem.id}

    async def search_memory(self, workspace_id: str, query: str, limit: int = 10) -> list[WorkspaceMemory]:
        """Search memory by content similarity (simple text search)."""
        async for session in get_session():
            result = await session.execute(
                WorkspaceMemory.__table__.select()
                .where(WorkspaceMemory.workspace_id == workspace_id)
                .where(WorkspaceMemory.content.ilike(f"%{query}%"))
                .limit(limit)
            )
            return [WorkspaceMemory(**dict(r._mapping)) for r in result.fetchall()]

    async def get_memory(self, memory_id: str) -> WorkspaceMemory | None:
        """Get a memory entry by ID."""
        async for session in get_session():
            result = await session.get(WorkspaceMemory, memory_id)
            if result:
                result.access_count += 1
                result.last_accessed = datetime.now(timezone.utc)
                await session.flush()
            return result


class EmbeddingService:
    """Service for embedding generation and storage."""

    async def generate_embedding(self, text: str, model: str | None = None) -> list[float]:
        """Generate embedding for text using Ollama."""
        settings = get_settings()
        model = model or settings.embedding_model

        try:
            import httpx as HTTPXClient

            async with HTTPXClient.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{settings.ollama_base_url}/api/embeddings",
                    json={"model": model, "prompt": text},
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("embedding", [])
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            # Fallback: deterministic hash-based embedding
            import hashlib

            h = hashlib.sha256(text.encode()).hexdigest()
            return [int(h[i:i + 8], 16) / 2**32 for i in range(0, min(len(h), 768), 8)]

    async def store_embedding(self, data: EmbeddingCreate) -> dict[str, str]:
        """Store an embedding in the database."""
        async for session in get_session():
            emb = EmbeddingIndex(
                workspace_id=data.workspace_id,
                embed_type=data.embed_type,
                source=data.source,
                content=data.content,
                embedding=data.embedding if data.embedding else await self.generate_embedding(data.content),
                tokens=data.tokens,
                metadata_=data.metadata_,
            )
            session.add(emb)
            await session.flush()
            return {"status": "stored", "id": emb.id}

    async def search_embeddings(self, query: str, workspace_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search embeddings by cosine similarity."""
        query_embedding = await self.generate_embedding(query)

        async for session in get_session():
            result = await session.execute(
                EmbeddingIndex.__table__.select().where(EmbeddingIndex.workspace_id == workspace_id)
            )
            rows = result.fetchall()

        scored = []
        for row in rows:
            emb = row._mapping
            vec = emb.get("embedding") or []
            if vec:
                score = self._cosine_similarity(query_embedding, vec)
            else:
                score = 0.0
            scored.append({"score": score, **{k: v for k, v in emb.items() if k != "embedding"}})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = sum(x * x for x in a) ** 0.5
        mag_b = sum(x * x for x in b) ** 0.5
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)


class AgentTaskService:
    """Service for agent task management."""

    async def create_task(self, data: AgentTaskCreate) -> AgentTaskSchema:
        """Create a new agent task."""
        async for session in get_session():
            task = AgentTask(
                id=str(uuid4()),
                workspace_id=data.workspace_id,
                task_type=data.task_type,
                goal=data.goal,
                plan=data.plan,
                conversation_id=data.conversation_id,
                max_retries=data.max_retries,
            )
            session.add(task)
            await session.flush()
            await session.refresh(task)
            logger.info("agent_task_created", task_id=task.id, task_type=data.task_type)
            return AgentTaskSchema.model_validate(task)

    async def get_task(self, task_id: str) -> AgentTask | None:
        """Get task by ID."""
        async for session in get_session():
            return await session.get(AgentTask, task_id)

    async def update_task(self, task_id: str, data: AgentTaskUpdate) -> AgentTaskSchema:
        """Update task status and progress."""
        async for session in get_session():
            task = await session.get(AgentTask, task_id)
            if not task:
                raise NotFoundError(f"Task not found: {task_id}")
            for field, value in data.model_dump(exclude_unset=True).items():
                if hasattr(task, field):
                    setattr(task, field, value)
            await session.flush()
            return AgentTaskSchema.model_validate(task)

    async def list_tasks(self, workspace_id: str, status: str | None = None, limit: int = 50) -> list[AgentTaskSchema]:
        """List tasks for a workspace."""
        async for session in get_session():
            query = AgentTask.__table__.select().where(AgentTask.workspace_id == workspace_id).order_by(AgentTask.created_at.desc()).limit(limit)
            if status:
                query = query.where(AgentTask.status == status)
            result = await session.execute(query)
            return [AgentTaskSchema.model_validate(dict(r._mapping)) for r in result.fetchall()]


# Global service singletons
conversation_service = ConversationService()
memory_service = MemoryService()
embedding_service = EmbeddingService()
agent_task_service = AgentTaskService()