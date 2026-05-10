"""Terminal management API endpoints."""
from __future__ import annotations

import asyncio
import os
import shlex
import sys
import termios
from collections.abc import AsyncGenerator

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config.settings import get_settings
from app.core.exceptions import ToolError
from app.core.logging import get_logger
from app.schemas import TerminalCommand, TerminalCreate

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/terminal", tags=["terminal"])

# Active terminal sessions
terminal_sessions: dict[str, dict] = {}


async def run_command(command: str, cwd: str | None = None, timeout: int = 30000) -> dict:
    """Execute a shell command and return results."""
    import subprocess

    safe_cwd = cwd or str(settings().workspace_root)

    # Verify cwd is within workspace
    if not safe_cwd.startswith(str(settings().workspace_root)):
        raise ToolError(f"Directory outside workspace: {safe_cwd}")

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=safe_cwd,
            env={
                **os.environ,
                "PATH": os.environ.get("PATH", ""),
                "HOME": os.environ.get("HOME", ""),
                "SHELL": os.environ.get("SHELL", "/bin/bash"),
            },
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout / 1000)
        except asyncio.TimeoutError:
            proc.kill()
            raise ToolError(f"Command timed out after {timeout}ms", exit_code=-1)

        return {
            "exit_code": proc.returncode,
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "command": command,
            "cwd": safe_cwd,
            "success": proc.returncode == 0,
        }
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Command execution failed: {e}", exit_code=-1)


@router.websocket("/ws")
async def terminal_websocket(websocket: WebSocket):
    """WebSocket endpoint for interactive terminal sessions."""
    await websocket.accept()
    session_id = str(id(websocket))
    proc = None

    terminal_sessions[session_id] = {"websocket": websocket, "process": None}

    try:
        while True:
            data = await websocket.receive_text()
            message = __import__("json").loads(data)
            msg_type = message.get("type", "")

            if msg_type == "exec":
                command = message.get("command", "")
                cwd = message.get("cwd", "")

                # Security: validate command
                blocked_patterns = ["rm -rf /", "mkfs", "dd if=", ">:\\"]
                for pattern in blocked_patterns:
                    if pattern in command.lower():
                        await websocket.send_text(__import__("json").dumps({
                            "type": "error",
                            "data": {"error": "Blocked command", "exit_code": -1},
                        }))
                        continue

                try:
                    proc = await asyncio.create_subprocess_shell(
                        command,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=cwd or str(get_settings().workspace_root),
                        env={**os.environ, "TERM": "xterm-256color"},
                    )
                    terminal_sessions[session_id]["process"] = proc

                    async def stream_output(stream, channel):
                        async for line in stream:
                            await websocket.send_text(__import__("json").dumps({
                                "type": "output",
                                "data": {"channel": channel, "text": line.decode("utf-8", errors="replace")},
                            }))

                    await asyncio.gather(
                        stream_output(proc.stdout, "stdout"),
                        stream_output(proc.stderr, "stderr"),
                    )

                    exit_code = await proc.wait()
                    await websocket.send_text(__import__("json").dumps({
                        "type": "exit",
                        "data": {"exit_code": exit_code},
                    }))
                except Exception as e:
                    await websocket.send_text(__import__("json").dumps({
                        "type": "error",
                        "data": {"error": str(e), "exit_code": -1},
                    }))

            elif msg_type == "input":
                if proc and proc.stdin:
                    try:
                        proc.stdin.write(message.get("data", "") + "\n")
                        await proc.stdin.drain()
                    except Exception:
                        pass

            elif msg_type == "kill":
                if proc:
                    proc.kill()
                    await websocket.send_text(__import__("json").dumps({
                        "type": "killed",
                        "data": {},
                    }))

    except WebSocketDisconnect:
        pass
    finally:
        if proc and not proc.returncode:
            proc.kill()
        terminal_sessions.pop(session_id, None)


@router.post("/exec", response_model=dict)
async def execute_command(cmd: TerminalCommand) -> dict:
    """Execute a single terminal command."""
    result = await run_command(cmd.command, cwd=cmd.cwd, timeout=cmd.timeout or 30000)
    return result


@router.get("/sessions")
async def list_sessions() -> dict:
    """List active terminal sessions."""
    return {"sessions": list(terminal_sessions.keys())}


def settings():
    return get_settings()