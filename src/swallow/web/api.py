from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..paths import artifacts_dir, events_path
from ..store import iter_task_states, load_knowledge_objects, load_state


def _filter_task_states(states: list[object], focus: str) -> list[object]:
    if focus == "all":
        return states
    if focus == "active":
        return [state for state in states if state.status in {"created", "running"}]
    if focus == "failed":
        return [state for state in states if state.status == "failed"]
    if focus == "needs-review":
        return [
            state
            for state in states
            if state.status == "failed" or state.phase == "summarize" or state.executor_status != "completed"
        ]
    if focus == "recent":
        return states
    return states


def _load_json_lines(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []

    payloads: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        data = json.loads(stripped)
        if isinstance(data, dict):
            payloads.append(data)
    return payloads


def _relative_to_base(base_dir: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _checksum_tree(path: Path) -> str:
    if not path.exists():
        return "missing"

    digest = hashlib.sha256()
    for file_path in sorted(item for item in path.rglob("*") if item.is_file()):
        digest.update(file_path.relative_to(path).as_posix().encode("utf-8"))
        digest.update(file_path.read_bytes())
    return digest.hexdigest()


def _collect_artifact_index(base_dir: Path, task_id: str, artifact_paths: dict[str, str]) -> list[dict[str, object]]:
    artifact_root = artifacts_dir(base_dir, task_id)
    indexed: dict[str, dict[str, object]] = {}

    for artifact_key, raw_path in sorted(artifact_paths.items()):
        resolved_path = Path(str(raw_path))
        if not resolved_path.is_absolute():
            resolved_path = base_dir / resolved_path
        relative_name = resolved_path.name
        indexed[relative_name] = {
            "name": relative_name,
            "artifact_key": artifact_key,
            "path": _relative_to_base(base_dir, resolved_path),
            "exists": resolved_path.exists(),
        }

    if artifact_root.exists():
        for file_path in sorted(item for item in artifact_root.rglob("*") if item.is_file()):
            relative_name = file_path.relative_to(artifact_root).as_posix()
            indexed.setdefault(
                relative_name,
                {
                    "name": relative_name,
                    "artifact_key": "",
                    "path": _relative_to_base(base_dir, file_path),
                    "exists": True,
                },
            )

    return list(indexed.values())


def build_tasks_payload(base_dir: Path, focus: str = "all") -> dict[str, object]:
    states = sorted(
        iter_task_states(base_dir),
        key=lambda state: (state.updated_at, state.task_id),
        reverse=True,
    )
    filtered = _filter_task_states(states, focus)
    return {
        "focus": focus,
        "count": len(filtered),
        "tasks": [
            {
                "task_id": state.task_id,
                "title": state.title,
                "goal": state.goal,
                "status": state.status,
                "phase": state.phase,
                "updated_at": state.updated_at,
                "executor_name": state.executor_name,
                "route_name": state.route_name,
                "attempt_id": state.current_attempt_id,
                "attempt_number": state.current_attempt_number,
            }
            for state in filtered
        ],
    }


def build_task_payload(base_dir: Path, task_id: str) -> dict[str, object]:
    return load_state(base_dir, task_id).to_dict()


def build_task_events_payload(base_dir: Path, task_id: str) -> dict[str, object]:
    payload = _load_json_lines(events_path(base_dir, task_id))
    return {"task_id": task_id, "count": len(payload), "events": payload}


def build_task_artifacts_payload(base_dir: Path, task_id: str) -> dict[str, object]:
    state = load_state(base_dir, task_id)
    artifacts = _collect_artifact_index(base_dir, task_id, state.artifact_paths)
    return {
        "task_id": task_id,
        "count": len(artifacts),
        "artifacts": artifacts,
        "artifacts_checksum": _checksum_tree(artifacts_dir(base_dir, task_id)),
    }


def build_task_artifact_payload(base_dir: Path, task_id: str, artifact_name: str) -> dict[str, object]:
    state = load_state(base_dir, task_id)
    for artifact in _collect_artifact_index(base_dir, task_id, state.artifact_paths):
        if artifact["name"] != artifact_name:
            continue
        path = base_dir / str(artifact["path"])
        return {
            "task_id": task_id,
            "name": artifact["name"],
            "artifact_key": artifact["artifact_key"],
            "path": artifact["path"],
            "exists": artifact["exists"],
            "content": _read_text(path) if artifact["exists"] else "",
        }
    raise FileNotFoundError(f"Unknown artifact: {artifact_name}")


def build_task_knowledge_payload(base_dir: Path, task_id: str) -> dict[str, object]:
    payload = load_knowledge_objects(base_dir, task_id)
    return {"task_id": task_id, "count": len(payload), "knowledge_objects": payload}


def create_fastapi_app(base_dir: Path):
    try:
        from fastapi import FastAPI, HTTPException
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "FastAPI is required for `swl serve`. Install `fastapi` and `uvicorn` to use the control center."
        ) from exc

    app = FastAPI(title="Swallow Control Center", version="0.1.0")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/tasks")
    def tasks(focus: str = "all") -> dict[str, object]:
        return build_tasks_payload(base_dir, focus=focus)

    @app.get("/api/tasks/{task_id}")
    def task(task_id: str) -> dict[str, object]:
        try:
            return build_task_payload(base_dir, task_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/tasks/{task_id}/events")
    def task_events(task_id: str) -> dict[str, object]:
        try:
            return build_task_events_payload(base_dir, task_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/tasks/{task_id}/artifacts")
    def task_artifacts(task_id: str) -> dict[str, object]:
        try:
            return build_task_artifacts_payload(base_dir, task_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/tasks/{task_id}/artifacts/{artifact_name:path}")
    def task_artifact(task_id: str, artifact_name: str) -> dict[str, object]:
        try:
            return build_task_artifact_payload(base_dir, task_id, artifact_name)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/tasks/{task_id}/knowledge")
    def task_knowledge(task_id: str) -> dict[str, object]:
        try:
            return build_task_knowledge_payload(base_dir, task_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app
