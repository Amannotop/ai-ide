"""Pydantic schemas for API request/response validation."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Base ──────────────────────────────────────────────────────────

class TimestampSchema(BaseModel):
    created_at: datetime
    updated_at: datetime


# ── Health ────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "ai-ide-backend"
    version: str = "1.0.0"
    ready: bool = True


# ── Conversations ─────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    title: str = "New Conversation"
    model: str | None = None
    metadata_: dict[str, Any] = Field(default_factory=dict, alias="metadata")


class ConversationUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")


class ConversationSchema(TimestampSchema):
    id: str
    user_id: str | None
    title: str
    model: str | None
    summary: str | None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")
    message_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# ── Messages ──────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    role: str  # user, assistant, system, tool
    content: str
    name: str | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")


class MessageSchema(TimestampSchema):
    id: str
    conversation_id: str
    role: str
    content: str
    name: str | None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")

    model_config = ConfigDict(from_attributes=True)


# ── Workspace Memory ──────────────────────────────────────────────

class WorkspaceMemoryCreate(BaseModel):
    workspace_id: str
    memory_key: str
    content: str
    tags: list[str] | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")


class WorkspaceMemorySchema(TimestampSchema):
    id: str
    workspace_id: str
    memory_key: str
    content: str
    tags: list[str] | None
    embedding: Any | None
    access_count: int
    last_accessed: datetime | None

    model_config = ConfigDict(from_attributes=True)


# ── Embeddings ────────────────────────────────────────────────────

class EmbeddingCreate(BaseModel):
    workspace_id: str
    embed_type: str  # code, doc, chat
    source: str
    content: str
    embedding: list[float] | None = None
    tokens: int | None = None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")


class EmbeddingSchema(TimestampSchema):
    id: str
    workspace_id: str
    embed_type: str
    source: str
    content: str
    tokens: int | None
    metadata_: dict[str, Any] | None = Field(default=None, alias="metadata")

    model_config = ConfigDict(from_attributes=True)


# ── Agent Tasks ───────────────────────────────────────────────────

class AgentTaskCreate(BaseModel):
    workspace_id: str
    task_type: str
    goal: str
    plan: dict[str, Any] | None = None
    conversation_id: str | None = None
    max_retries: int = 3


class AgentTaskUpdate(BaseModel):
    status: str | None = None
    plan: dict[str, Any] | None = None
    execution_log: list[dict[str, Any]] | None = None
    result: str | None = None
    error: str | None = None
    retry_count: int | None = None


class AgentTaskSchema(TimestampSchema):
    id: str
    conversation_id: str | None
    workspace_id: str
    task_type: str
    goal: str
    status: str
    plan: dict[str, Any] | None
    execution_log: list[dict[str, Any]]
    result: str | None
    error: str | None
    retry_count: int
    max_retries: int

    model_config = ConfigDict(from_attributes=True)


# ── File Operations ───────────────────────────────────────────────

class FileReadRequest(BaseModel):
    path: str


class FileWriteRequest(BaseModel):
    path: str
    content: str
    create_if_missing: bool = True


class FileSearchRequest(BaseModel):
    pattern: str
    workspace_root: str | None = None


class FileReplaceRequest(BaseModel):
    path: str
    old_content: str
    new_content: str


class FileResponse(BaseModel):
    path: str
    content: str
    exists: bool
    size: int | None = None
    modified_at: datetime | None = None


# ── Terminal ──────────────────────────────────────────────────────

class TerminalCommand(BaseModel):
    command: str
    cwd: str | None = None
    timeout: int | None = 30000


class TerminalCreate(BaseModel):
    shell: str | None = None  # bash, zsh, fish, powershell


# ── AI / Model ────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # system, user, assistant, tool
    content: str | list[dict[str, Any]] | None = None
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage]
    temperature: float = 0.7
    max_tokens: int | None = 2048
    stream: bool = False
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | None = None
    context_files: list[str] | None = None


class ChatCompletionResponse(BaseModel):
    id: str
    model: str
    choices: list[dict[str, Any]]
    usage: dict[str, int] | None = None


class EmbeddingRequest(BaseModel):
    model: str | None = None
    input: str | list[str]


class EmbeddingResponse(BaseModel):
    model: str
    embeddings: list[list[float]]
    tokens: int


# ── Git ───────────────────────────────────────────────────────────

class GitCommitRequest(BaseModel):
    message: str
    files: list[str] | None = None
    all: bool = False


class GitBranch(BaseModel):
    name: str
    current: bool = False
    commits_ahead: int = 0
    commits_behind: int = 0


class GitStatus(BaseModel):
    branch: str | None
    ahead: int = 0
    behind: int = 0
    files: list[dict[str, str]] = Field(default_factory=list)


# ── Settings ──────────────────────────────────────────────────────

class AppSettings(BaseModel):
    app_name: str
    app_version: str
    debug: bool
    environment: str
    ollama_base_url: str
    ollama_default_model: str
    workspace_root: str


# ── Events (Server-Sent Events / WebSocket) ───────────────────────

class StreamEvent(BaseModel):
    type: str  # chunk, complete, error, tool_call
    data: dict[str, Any]


class AgentEvent(BaseModel):
    type: str  # plan, step, complete, error, log
    data: dict[str, Any]


class FileChangeEvent(BaseModel):
    type: str  # created, modified, deleted, renamed
    path: str
    workspace_id: str


# ── Plugin ────────────────────────────────────────────────────────

class PluginManifest(BaseModel):
    name: str
    version: str
    description: str
    author: str
    entry_point: str
    permissions: list[str] = Field(default_factory=list)
    config_schema: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)


class PluginConfig(BaseModel):
    enabled: bool = True
    settings: dict[str, Any] = Field(default_factory=dict)


# ── Search / Retrieval ────────────────────────────────────────────

class CodeSearchRequest(BaseModel):
    query: str
    workspace_id: str | None = None
    file_pattern: str | None = None
    limit: int = 10


class CodeSearchResult(BaseModel):
    file: str
    line: int
    content: str
    score: float
    snippet: str | None = None


class ContextRetrieveRequest(BaseModel):
    query: str
    workspace_id: str
    limit: int = 5000  # max tokens of context
    sources: list[str] | None = None  # ["files", "memory", "embeddings"]


class ContextRetrieveResponse(BaseModel):
    files: list[dict[str, Any]]
    memory: list[dict[str, Any]]
    embeddings: list[dict[str, Any]]
    summary: str | None = None