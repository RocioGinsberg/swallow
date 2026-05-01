from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def workspace_root(base_dir: Path) -> Path:
    return base_dir.resolve()


def swl_root(base_dir: Path) -> Path:
    return workspace_root(base_dir) / ".swl"


def task_root(base_dir: Path, task_id: str) -> Path:
    return swl_root(base_dir) / "tasks" / task_id


def task_artifacts_root(base_dir: Path, task_id: str) -> Path:
    return task_root(base_dir, task_id) / "artifacts"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_lines(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    lines = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            lines.append(payload)
    return lines
