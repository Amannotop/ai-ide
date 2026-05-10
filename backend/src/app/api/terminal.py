"""Terminal management API endpoints."""
from __future__ import annotations

import asyncio
import os
import subprocess

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config.settings import get_settings
from app.core.exceptions import ToolError
from app.core.logging import get_logger
from app.schemas import TerminalCommand

logger = get_logger(__name__)
router = APIRouter(tags=["terminal"])

terminal_sessions: dict[str, dict] = {}


async def run_command(command: str, cwd: str | None = None, timeout: int = 30000) -> dict:
    """Execute a shell command and return results."""
    safe_cwd = cwd or str(get_settings().workspace_root)

    blocked = ["rm -rf /", "mkfs", "dd if=", ">:"]
    for pattern in blocked:
        if pattern in command.lower():
            raise ToolError(f"Blocked command: {pattern}")

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=safe_cwd,
            env={**os.environ, "TERM": "xterm-256color"},
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
            import json
            message = json.loads(data)
            msg_type = message.get("type", "")

            if msg_type == "exec":
                command = message.get("command", "")
                cwd = message.get("cwd", "")

                blocked = ["rm -rf /", "mkfs", "dd if="]
                if any(b in command.lower() for b in blocked):
                    await websocket.send_text(json.dumps({"type": "error", "data": {"exit_code": -1, "error": "Blocked command"}}))
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
                            await websocket.send_text(json.dumps({
                                "type": "output",
                                "data": {"channel": channel, "text": line.decode("utf-8", errors="replace")},
                            }))

                    await asyncio.gather(stream_output(proc.stdout, "stdout"), stream_output(proc.stderr, "stderr"))
                    exit_code = await proc.wait()
                    await websocket.send_text(json.dumps({"type": "exit", "data": {"exit_code": exit_code}}))
                except Exception as e:
                    await websocket.send_text(json.dumps({"type": "error", "data": {"error": str(e), "exit_code": -1}}))

            elif msg_type == "kill" and proc:
                proc.kill()
                await websocket.send_text(json.dumps({"type": "killed", "data": {}}))

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