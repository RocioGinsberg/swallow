from __future__ import annotations

from pathlib import Path

from swallow.application.queries.control_center import (
    build_task_artifact_diff_payload,
    build_task_artifact_payload,
    build_task_artifacts_payload,
    build_task_events_payload,
    build_task_execution_timeline_payload,
    build_task_knowledge_payload,
    build_task_payload,
    build_task_subtask_tree_payload,
    build_tasks_payload,
)
from swallow.surface_tools.workspace import resolve_path


def _static_dir() -> Path:
    return resolve_path(Path(__file__), base=Path.cwd()).parent / "static"


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
