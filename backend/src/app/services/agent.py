"""Agent execution engine - autonomous coding, debugging, and planning."""
from __future__ import annotations

import asyncio
import os
import re
from collections.abc import AsyncGenerator, Generator
from typing import Any

from app.config.settings import get_settings
from app.core.exceptions import AgentError, ToolError
from app.core.logging import get_logger
from app.services.ai import model_router
from app.schemas import (
    AgentEvent,
    ChatCompletionRequest,
    ChatMessage,
    EmbeddingRequest,
    FileReadRequest,
    FileWriteRequest,
    FileSearchRequest,
)
from app.services.workspace import WorkspaceService
from app.core.exceptions import ValidationError

logger = get_logger(__name__)

# Available tools for the agent
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file relative to workspace root."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to workspace root."},
                    "content": {"type": "string", "description": "Content to write to the file."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for files matching a glob pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern to search for."},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Execute a shell command and return the result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute."},
                    "timeout": {"type": "integer", "description": "Timeout in milliseconds.", "default": 30000},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_in_file",
            "description": "Replace text in a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file."},
                    "old_content": {"type": "string", "description": "Text to replace."},
                    "new_content": {"type": "string", "description": "New text to insert."},
                },
                "required": ["path", "old_content", "new_content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delayed_action",
            "description": "Wait for a specified number of milliseconds.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ms": {"type": "integer", "description": "Milliseconds to wait.", "default": 1000},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "Create a new directory in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to workspace root."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List directory contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to workspace root."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_code",
            "description": "Search for code patterns in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex or text pattern to search for."},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_resource",
            "description": "Read URI-like resource (file://, config://, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "uri": {"type": "string", "description": "Resource URI to read."},
                },
                "required": ["uri"],
            },
        },
    },
]


class ToolExecutor:
    """Executes tools in a sandboxed environment."""

    BLOCKED_PATTERNS = [
        "rm -rf /", "mkfs", "dd if=", ">:\\", "chmod 777",
        "chown root", "sudo", "su -", "passwd", "visudo",
        "iptables", "ufw", "nc -e", "wget.*\\.sh", "curl.*\\.sh",
        "eval", "`", "$(cat", "$(ls", "|| curl", "&& curl",
    ]

    def __init__(self, workspace_root: str) -> None:
        self.workspace_root = workspace_root
        self.workspace = WorkspaceService(workspace_root)
        self._cancelled = False

    def _validate_path(self, path: str) -> str:
        """Ensure path stays within workspace."""
        import os.path
        full = os.path.normpath(os.path.join(self.workspace_root, path))
        if not full.startswith(os.path.normpath(self.workspace_root)):
            raise ToolError(f"Path traversal blocked: {path}")
        return full

    def _validate_command(self, command: str) -> str:
        """Validate shell command against blocklist."""
        cmd_lower = command.lower()
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in cmd_lower:
                raise ToolError(f"Blocked command: {pattern}")
        return command

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a single tool by name."""
        method = getattr(self, f"_tool_{tool_name}", None)
        if method is None:
            raise ToolError(f"Unknown tool: {tool_name}")
        return await method(arguments)

    async def _tool_read_file(self, args: dict) -> dict:
        path = self._validate_path(args.get("path", ""))
        req = FileReadRequest(path=path)
        result = await self.workspace.read_file(req)
        return {"path": result.path, "content": result.content, "exists": result.exists}

    async def _tool_write_file(self, args: dict) -> dict:
        path = self._validate_path(args.get("path", ""))
        content = args.get("content", "")
        req = FileWriteRequest(path=path, content=content, create_if_missing=True)
        result = await self.workspace.write_file(req)
        return {"path": result.path, "written": True}

    async def _tool_replace_in_file(self, args: dict) -> dict:
        path = self._validate_path(args.get("path", ""))
        old = args.get("old_content", "")
        new = args.get("new_content", "")
        req = FileWriteRequest(path=path, content=new, create_if_missing=False)
        # Reuse workspace service
        from app.schemas import FileReplaceRequest

        rr = FileReplaceRequest(path=path, old_content=old, new_content=new)
        result = await self.workspace.replace_in_file(rr)
        return {"path": result.path, "replaced": True}

    async def _tool_search_files(self, args: dict) -> dict:
        pattern = args.get("pattern", "*")
        req = FileSearchRequest(pattern=pattern)
        results = await self.workspace.search_files(req)
        return {"results": [{"name": r["name"], "path": r["path"]} for r in results]}

    async def _tool_execute_command(self, args: dict) -> dict:
        command = self._validate_command(args.get("command", ""))
        timeout = args.get("timeout", 30000)
        cwd = args.get("cwd", self.workspace_root)
        cwd = self._validate_path(cwd)

        import subprocess
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env={**os.environ, "TERM": "xterm-256color"},
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout / 1000)
            except asyncio.TimeoutError:
                proc.kill()
                raise ToolError(f"Command timed out: {command}")

            return {
                "exit_code": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "success": proc.returncode == 0,
            }
        except subprocess.SubprocessError as e:
            raise ToolError(f"Command failed: {e}")

    async def _tool_create_directory(self, args: dict) -> dict:
        path = self._validate_path(args.get("path", ""))
        os.makedirs(path, exist_ok=True)
        return {"path": path, "created": True}

    async def _tool_list_directory(self, args: dict) -> dict:
        path = self._validate_path(args.get("path", ""))
        items = []
        for item in sorted(
            (self.workspace.root.parent / path).iterdir(),
            key=lambda p: (p.is_file(), p.name),
        ):
            items.append({"name": item.name, "is_dir": item.is_dir()})
        return {"items": items}

    async def _tool_find_code(self, args: dict) -> dict:
        pattern = args.get("pattern", "")
        results = []
        for root, dirs, files in os.walk(self.workspace.root):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                if f.endswith((".py", ".ts", ".js", ".tsx", ".jsx", ".go", ".rs")):
                    fp = os.path.join(root, f)
                    try:
                        with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                            for i, line in enumerate(fh, 1):
                                if pattern in line or re.search(pattern, line):
                                    results.append({"file": fp, "line": i, "content": line.strip()})
                    except Exception:
                        continue
        return {"results": results[:100]}

    async def _tool_read_resource(self, args: dict) -> dict:
        uri = args.get("uri", "")
        if uri.startswith("file://"):
            path = uri[7:]
            return await self._tool_read_file({"path": path})
        elif uri.startswith("config://"):
            key = uri[9:]
            settings = get_settings()
            val = getattr(settings, key, None)
            return {"key": key, "value": val}
        else:
            raise ToolError(f"Unknown URI scheme: {uri}")

    async def cancel(self) -> None:
        """Cancel current operation."""
        self._cancelled = True


class AgentExecutor:
    """Orchestrates agent task execution with planning and tool use."""

    def __init__(self, workspace_root: str = ".") -> None:
        self.workspace_root = workspace_root
        self.tool_executor = ToolExecutor(workspace_root)
        self._cancelled = False

    async def execute_task(self, task_type: str, goal: str) -> dict[str, Any]:
        """Execute a complete task end-to-end."""
        try:
            plan = await self._plan(task_type, goal)
            return await self._execute_plan(plan, goal)
        except Exception as e:
            logger.error("task_execution_failed", task_type=task_type, error=str(e))
            raise AgentError(f"Task failed: {e}")

    async def stream_execute(self, task_type: str, goal: str) -> AsyncGenerator[dict[str, Any], None]:
        """Execute task with streaming progress updates."""
        yield AgentEvent(type="planning", data={"goal": goal}).model_dump()

        try:
            plan = await self._plan(task_type, goal)
            yield AgentEvent(type="plan", data={"steps": len(plan["steps"])}).model_dump()

            for i, step in enumerate(plan["steps"]):
                if self._cancelled:
                    yield AgentEvent(type="cancelled", data={}).model_dump()
                    return

                yield AgentEvent(type="step_start", data={"step": i + 1, "description": step["description"]}).model_dump()

                result = await self._execute_step(step, goal)
                yield AgentEvent(type="step_result", data={"step": i + 1, "result": result}).model_dump()

            yield AgentEvent(type="complete", data={"status": "success"}).model_dump()
        except Exception as e:
            yield AgentEvent(type="error", data={"error": str(e)}).model_dump()
            logger.error("stream_execution_failed", error=str(e))

    async def cancel(self) -> None:
        """Cancel running task."""
        self._cancelled = True
        await self.tool_executor.cancel()

    async def _plan(self, task_type: str, goal: str) -> dict[str, Any]:
        """Use AI to create an execution plan."""
        messages = [
            {"role": "system", "content": "You are an expert planner. Break down this task into concrete, executable steps. Return JSON with a 'steps' array where each step has a 'description', 'action' (tool name), and 'parameters'."},
            {"role": "user", "content": f"Task type: {task_type}\nGoal: {goal}\n\nCreate a step-by-step plan to accomplish this goal. Each step should reference one of these tools: read_file, write_file, replace_in_file, search_files, execute_command, list_directory, create_directory, find_code."},
        ]

        try:
            result = await model_router.chat_completion(
                req=ChatCompletionRequest(
                    messages=[ChatMessage(**m) for m in messages],
                    temperature=0.3,
                    max_tokens=1024,
                )
            )
            content = result.get("message", {}).get("content", result.get("choices", [{}])[0].get("message", {}).get("content", "{}"))
            parsed = __import__("json").loads(content)
            return parsed if isinstance(parsed, dict) and "steps" in parsed else {"steps": [{"description": content, "action": "execute_command", "parameters": {"command": content}}]}
        except Exception as e:
            logger.error("planning_failed", error=str(e))
            # Fallback: direct execution
            return {"steps": [{"description": goal, "action": "execute_command", "parameters": {"command": goal}}]}

    async def _execute_step(self, step: dict, goal: str) -> dict:
        """Execute a single step in the plan."""
        action = step.get("action", "")
        params = step.get("parameters", {})

        try:
            if action in ("read_file", "write_file", "replace_in_file", "search_files",
                          "execute_command", "list_directory", "create_directory", "find_code", "read_resource"):
                method = getattr(self.tool_executor, f"_tool_{action}", None)
                if method:
                    return await method(params)
            return {"note": f"No handler for action: {action}"}
        except ToolError as e:
            return {"error": str(e), "retry": False}
        except Exception as e:
            return {"error": str(e), "retry": True}