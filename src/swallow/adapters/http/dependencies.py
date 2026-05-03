from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, Request


def get_base_dir(request: Request) -> Path:
    base_dir = getattr(request.app.state, "base_dir", None)
    if not isinstance(base_dir, Path):
        raise RuntimeError("Control Center base_dir is not configured.")
    return base_dir


def resolve_workspace_relative_file(base_dir: Path, raw_path: str) -> Path:
    path_text = raw_path.strip()
    if not path_text:
        raise HTTPException(status_code=400, detail="Path must be a non-empty workspace-relative path.")
    relative_path = Path(path_text)
    if relative_path.is_absolute():
        raise HTTPException(status_code=400, detail="Path must be relative to the workspace.")
    if any(part == ".." for part in relative_path.parts):
        raise HTTPException(status_code=400, detail="Path must not contain parent traversal segments.")

    candidate = base_dir / relative_path
    if not candidate.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {path_text}")
    if not candidate.is_file():
        raise HTTPException(status_code=400, detail=f"Path is not a file: {path_text}")
    return candidate
