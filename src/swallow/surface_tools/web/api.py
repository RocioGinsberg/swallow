from __future__ import annotations

import hashlib
from pathlib import Path

from swallow.orchestration.models import EVENT_EXECUTOR_COMPLETED, EVENT_EXECUTOR_FAILED
from swallow.surface_tools.paths import artifacts_dir
from swallow.truth_governance.store import iter_task_states, load_events, load_knowledge_objects, load_state
from swallow.surface_tools.workspace import resolve_path


def _static_dir() -> Path:
    return resolve_path(Path(__file__), base=Path.cwd()).parent / "static"


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


def _relative_to_base(base_dir: Path, path: Path) -> str:
    try:
        return resolve_path(path, base=base_dir).relative_to(resolve_path(base_dir)).as_posix()
    except ValueError:
        return path.as_posix()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _coerce_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _coerce_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return default
    return default


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
    payload = load_events(base_dir, task_id)
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
    if ".." in artifact_name.split("/"):
        raise ValueError("Invalid artifact name")

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


def build_task_artifact_diff_payload(base_dir: Path, task_id: str, left_name: str, right_name: str) -> dict[str, object]:
    if not left_name or not right_name:
        raise ValueError("Both left and right artifact names are required")

    left = build_task_artifact_payload(base_dir, task_id, left_name)
    right = build_task_artifact_payload(base_dir, task_id, right_name)
    return {
        "task_id": task_id,
        "left": left,
        "right": right,
    }


def build_task_knowledge_payload(base_dir: Path, task_id: str) -> dict[str, object]:
    payload = load_knowledge_objects(base_dir, task_id)
    return {"task_id": task_id, "count": len(payload), "knowledge_objects": payload}


def build_task_subtask_tree_payload(base_dir: Path, task_id: str) -> dict[str, object]:
    state = load_state(base_dir, task_id)
    events = load_events(base_dir, task_id)
    planned_event = next((event for event in events if str(event.get("event_type", "")).strip() == "task.planned"), None)

    children_by_key: dict[str, dict[str, object]] = {}
    if planned_event is not None:
        payload = planned_event.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}
        card_ids = list(payload.get("card_ids", []))
        subtask_indices = list(payload.get("subtask_indices", []))
        if len(card_ids) > 1:
            for position, raw_card_id in enumerate(card_ids):
                card_id = str(raw_card_id).strip()
                if not card_id:
                    continue
                subtask_index = _coerce_int(
                    subtask_indices[position] if position < len(subtask_indices) else position + 1,
                    position + 1,
                )
                children_by_key[card_id] = {
                    "card_id": card_id,
                    "subtask_index": subtask_index,
                    "goal": "",
                    "status": "pending",
                    "attempts": 0,
                    "executor_name": "",
                    "latency_ms": 0,
                    "debate_rounds": 0,
                }

    for event in events:
        event_type = str(event.get("event_type", "")).strip()
        if not event_type.startswith("subtask."):
            continue

        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}
        event_parts = event_type.split(".")
        subtask_index = _coerce_int(payload.get("subtask_index"), _coerce_int(event_parts[1] if len(event_parts) > 1 else 0, 0))
        card_id = str(payload.get("card_id", "")).strip()
        child_key = card_id or f"subtask-{subtask_index}"
        child = children_by_key.setdefault(
            child_key,
            {
                "card_id": card_id,
                "subtask_index": subtask_index,
                "goal": "",
                "status": "pending",
                "attempts": 0,
                "executor_name": "",
                "latency_ms": 0,
                "debate_rounds": 0,
            },
        )

        if card_id:
            child["card_id"] = card_id
        if subtask_index:
            child["subtask_index"] = subtask_index
        goal = str(payload.get("goal", "")).strip()
        if goal:
            child["goal"] = goal
        executor_name = str(payload.get("executor_name", "")).strip()
        if executor_name:
            child["executor_name"] = executor_name
        child["latency_ms"] = max(_coerce_int(payload.get("latency_ms"), 0), _coerce_int(child.get("latency_ms"), 0))
        child["attempts"] = max(_coerce_int(payload.get("attempt_number"), 0), _coerce_int(child.get("attempts"), 0))

        if event_type.endswith(".execution"):
            child["status"] = str(payload.get("status") or payload.get("executor_status") or child.get("status") or "pending").strip() or "pending"
        elif event_type.endswith(".debate_round"):
            child["debate_rounds"] = max(
                _coerce_int(payload.get("round_number"), 1),
                _coerce_int(child.get("debate_rounds"), 0),
            )
        elif event_type.endswith(".debate_circuit_breaker"):
            child["status"] = "waiting_human"
        elif event_type.endswith(".review_gate"):
            review_status = str(payload.get("status", "")).strip()
            if review_status == "failed" and str(child.get("status", "")) == "pending":
                child["status"] = "failed"

    children = sorted(
        children_by_key.values(),
        key=lambda item: (_coerce_int(item.get("subtask_index"), 0), str(item.get("card_id", ""))),
    )
    return {
        "task_id": task_id,
        "status": state.status,
        "children": children,
    }


def build_task_execution_timeline_payload(base_dir: Path, task_id: str) -> dict[str, object]:
    load_state(base_dir, task_id)
    events = load_events(base_dir, task_id)
    entries: list[dict[str, object]] = []
    current_round = 0
    max_round = 0

    for event in events:
        event_type = str(event.get("event_type", "")).strip()
        payload = event.get("payload", {})
        if not isinstance(payload, dict):
            payload = {}

        if event_type == "task.debate_round" or event_type.endswith(".debate_round"):
            current_round = max(current_round, _coerce_int(payload.get("round_number"), current_round + 1))
            max_round = max(max_round, current_round)
            continue

        if event_type not in {EVENT_EXECUTOR_COMPLETED, EVENT_EXECUTOR_FAILED}:
            continue

        is_debate_retry = bool(str(payload.get("review_feedback", "")).strip())
        round_number = max(current_round, 1) if is_debate_retry else current_round
        entries.append(
            {
                "event_type": event_type,
                "round": round_number,
                "latency_ms": max(_coerce_int(payload.get("latency_ms"), 0), 0),
                "token_cost": max(_coerce_float(payload.get("token_cost"), 0.0), 0.0),
                "is_debate_retry": is_debate_retry,
                "timestamp": str(event.get("created_at", "")).strip(),
            }
        )
        max_round = max(max_round, round_number)

    return {
        "task_id": task_id,
        "entries": entries,
        "total_cost": round(sum(float(entry["token_cost"]) for entry in entries), 6),
        "total_latency_ms": sum(int(entry["latency_ms"]) for entry in entries),
        "debate_rounds": max_round,
    }


def create_fastapi_app(base_dir: Path):
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "FastAPI is required for `swl serve`. Install `fastapi` and `uvicorn` to use the control center."
        ) from exc

    app = FastAPI(title="Swallow Control Center", version="0.1.0")
    static_dir = _static_dir()
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

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
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/tasks/{task_id}/artifact-diff")
    def task_artifact_diff(task_id: str, left: str = "", right: str = "") -> dict[str, object]:
        try:
            return build_task_artifact_diff_payload(base_dir, task_id, left, right)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/tasks/{task_id}/knowledge")
    def task_knowledge(task_id: str) -> dict[str, object]:
        try:
            return build_task_knowledge_payload(base_dir, task_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/tasks/{task_id}/subtask-tree")
    def task_subtask_tree(task_id: str) -> dict[str, object]:
        try:
            return build_task_subtask_tree_payload(base_dir, task_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/tasks/{task_id}/execution-timeline")
    def task_execution_timeline(task_id: str) -> dict[str, object]:
        try:
            return build_task_execution_timeline_payload(base_dir, task_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app
