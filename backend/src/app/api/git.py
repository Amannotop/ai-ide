"""Git integration API endpoints."""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.config.settings import get_settings
from app.core.exceptions import ToolError
from app.core.logging import get_logger

router = APIRouter(tags=["git"])
logger = get_logger(__name__)


def _validate_repo_path(path: str) -> Path:
    """Validate and resolve a repository path within workspace."""
    ws_root = Path(get_settings().workspace_root).resolve()
    repo_path = (ws_root / path).resolve()
    if not str(repo_path).startswith(str(ws_root)):
        raise ToolError(f"Path outside workspace: {path}")
    return repo_path


async def git_run(repo_path: Path, *args: str, timeout: int = 30000) -> dict[str, Any]:
    """Run a git command and return parsed results."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", *args, cwd=str(repo_path),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={**__import__("os").environ, "PATH": __import__("os").environ.get("PATH", "")},
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout / 1000)
        return {"returncode": proc.returncode, "stdout": stdout.decode("utf-8", errors="replace"), "stderr": stderr.decode("utf-8", errors="replace")}
    except asyncio.TimeoutError:
        proc.kill()
        raise ToolError(f"Git command timed out: {' '.join(args)}")
    except Exception as e:
        raise ToolError(f"Git command failed: {e}")


@router.get("/status")
async def git_status(repo_path: str = ".") -> dict:
    """Get git status for a repository."""
    path = _validate_repo_path(repo_path)
    if not (path / ".git").exists():
        return {"is_repo": False, "path": str(path)}

    result = await git_run(path, "status", "--porcelain", "--branch")
    if result["returncode"] != 0:
        raise HTTPException(status_code=400, detail=result["stderr"])

    lines = result["stdout"].strip().split("\n")
    branch_info = ""
    changes: list[dict] = []

    for line in lines:
        if line.startswith("## "):
            branch_info = line[3:]
        elif line:
            status = line[:2]
            filepath = line[3:]
            change_type = "modified" if status[0] in "M " else "new" if status[0] == "?" else "deleted" if status[0] == "D" else "renamed"
            changes.append({"file": filepath, "status": change_type, "staged": status[1] != " "})

    branch_name = branch_info.split("...")[0] if "..." in branch_info else branch_info
    ahead_behind = {"ahead": 0, "behind": 0}
    if "..." in branch_info and "[" in branch_info:
        info = branch_info.split("[")[1].rstrip("]")
        for part in info.split(", "):
            if "ahead" in part:
                ahead_behind["ahead"] = int(part.split()[-1])
            elif "behind" in part:
                ahead_behind["behind"] = int(part.split()[-1])

    return {"is_repo": True, "branch": branch_name or "unknown", "ahead": ahead_behind["ahead"], "behind": ahead_behind["behind"], "changes": changes}


@router.post("/init")
async def git_init(repo_path: str = ".") -> dict:
    """Initialize a new git repository."""
    path = _validate_repo_path(repo_path)
    result = await git_run(path, "init")
    if result["returncode"] != 0:
        raise HTTPException(status_code=400, detail=result["stderr"])
    logger.info("git_init", path=str(path))
    return {"status": "initialized", "path": str(path)}


@router.post("/commit")
async def git_commit(message: str = "", repo_path: str = ".") -> dict:
    """Commit changes in the repository."""
    path = _validate_repo_path(repo_path)
    await git_run(path, "add", "-A")
    result = await git_run(path, "commit", "-m", message)
    if result["returncode"] != 0:
        if "nothing to commit" in result["stdout"].lower():
            return {"status": "nothing_to_commit"}
        raise HTTPException(status_code=400, detail=result["stderr"])
    logger.info("git_commit", path=str(path), message=message)
    return {"status": "committed", "message": message}


@router.post("/push")
async def git_push(remote: str = "origin", branch: str | None = None, repo_path: str = ".") -> dict:
    """Push to remote repository."""
    path = _validate_repo_path(repo_path)
    args = ["push", remote]
    if branch:
        args.append(branch)
    result = await git_run(path, *args)
    if result["returncode"] != 0:
        raise HTTPException(status_code=400, detail=result["stderr"])
    return {"status": "pushed", "remote": remote}


@router.post("/pull")
async def git_pull(remote: str = "origin", branch: str | None = None, repo_path: str = ".") -> dict:
    """Pull from remote repository."""
    path = _validate_repo_path(repo_path)
    args = ["pull", remote]
    if branch:
        args.append(branch)
    result = await git_run(path, *args)
    if result["returncode"] != 0:
        raise HTTPException(status_code=400, detail=result["stderr"])
    return {"status": "pulled", "remote": remote}


@router.get("/branches")
async def git_branches(repo_path: str = ".") -> dict:
    """List git branches."""
    path = _validate_repo_path(repo_path)
    branches: list[dict] = []
    current = None
    try:
        result = await git_run(path, "branch", "-a")
        if result["returncode"] == 0:
            for line in result["stdout"].strip().split("\n"):
                if line:
                    name = line.strip().lstrip("* ").strip()
                    is_current = line.startswith("*")
                    if is_current:
                        current = name
                    branches.append({"name": name, "current": is_current})
    except Exception:
        pass
    return {"branches": branches, "current": current}


@router.get("/log")
async def git_log(repo_path: str = ".", limit: int = 20) -> list[dict]:
    """Get recent git commits."""
    path = _validate_repo_path(repo_path)
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "log", f"--{limit}", "--oneline", "--format=%H|%s|%an|%ai",
            cwd=str(path), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        commits = []
        for line in stdout.decode().strip().split("\n"):
            if "|" in line:
                parts = line.split("|", 3)
                commits.append({"hash": parts[0][:12], "message": parts[1], "author": parts[2], "date": parts[3] if len(parts) > 3 else ""})
        return commits
    except Exception:
        return []


@router.get("/diff")
async def git_diff(repo_path: str = ".") -> dict:
    """Get current diff."""
    path = _validate_repo_path(repo_path)
    result = await git_run(path, "diff")
    return {"diff": result["stdout"] if result["returncode"] == 0 else result["stderr"]}