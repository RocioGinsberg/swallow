from __future__ import annotations

from pathlib import Path

from swallow.application.commands.knowledge import (
    StagePromotePreflightError,
    promote_stage_candidate_command,
    reject_stage_candidate_command,
)
from swallow.application.commands.proposals import apply_reviewed_proposals_command, review_proposals_command
from swallow.application.commands.tasks import (
    acknowledge_task_command,
    create_task_command,
    rerun_task_command,
    resume_task_command,
    retry_task_command,
    run_task_command,
)
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
from swallow.surface_tools.web.http_models import (
    WebRequestError,
    proposal_apply_response,
    proposal_review_response,
    resolve_workspace_relative_file,
    stage_decision_response,
    stage_promote_response,
    task_acknowledge_response,
    task_recovery_response,
    task_response,
    task_run_response,
)


def _static_dir() -> Path:
    return resolve_path(Path(__file__), base=Path.cwd()).parent / "static"


def _status_for_value_error(exc: ValueError) -> int:
    message = str(exc)
    if message.startswith("Unknown staged candidate:"):
        return 404
    return 400


def create_fastapi_app(base_dir: Path):
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles
        from swallow.surface_tools.web.schemas import (
            CreateTaskRequest,
            ProposalApplyRequest,
            ProposalReviewRequest,
            StageDecisionRequest,
            TaskActionRequest,
        )
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "FastAPI is required for `swl serve`. Install `fastapi` and `uvicorn` to use the control center."
        ) from exc

    app = FastAPI(title="Swallow Control Center", version="0.1.0")
    globals().update(
        {
            "CreateTaskRequest": CreateTaskRequest,
            "TaskActionRequest": TaskActionRequest,
            "StageDecisionRequest": StageDecisionRequest,
            "ProposalReviewRequest": ProposalReviewRequest,
            "ProposalApplyRequest": ProposalApplyRequest,
        }
    )
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

    @app.post("/api/tasks")
    def create_task_route(request: CreateTaskRequest) -> dict[str, object]:
        try:
            state = create_task_command(
                base_dir=base_dir,
                title=request.title,
                goal=request.goal,
                workspace_root=base_dir,
                executor_name=request.executor_name,
                input_context=request.input_context,
                constraints=request.constraints,
                acceptance_criteria=request.acceptance_criteria,
                priority_hints=request.priority_hints,
                next_action_proposals=request.next_action_proposals,
                planning_source=request.planning_source,
                complexity_hint=request.complexity_hint,
                knowledge_items=request.knowledge_items,
                knowledge_stage=request.knowledge_stage,
                knowledge_source=request.knowledge_source,
                knowledge_artifact_refs=request.knowledge_artifact_refs,
                knowledge_retrieval_eligible=request.knowledge_retrieval_eligible,
                knowledge_canonicalization_intent=request.knowledge_canonicalization_intent,
                capability_refs=request.capability_refs,
                route_mode=request.route_mode,
            )
        except WebRequestError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=_status_for_value_error(exc), detail=str(exc)) from exc
        return {"task": task_response(state)}

    @app.get("/api/tasks/{task_id}")
    def task(task_id: str) -> dict[str, object]:
        try:
            return build_task_payload(base_dir, task_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/tasks/{task_id}/run")
    def task_run(task_id: str, request: TaskActionRequest = TaskActionRequest()) -> dict[str, object]:
        try:
            result = run_task_command(
                base_dir=base_dir,
                task_id=task_id,
                executor_name=request.executor_name,
                capability_refs=request.capability_refs,
                route_mode=request.route_mode,
            )
            return task_run_response(result)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except WebRequestError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=_status_for_value_error(exc), detail=str(exc)) from exc

    @app.post("/api/tasks/{task_id}/retry")
    def task_retry(task_id: str, request: TaskActionRequest = TaskActionRequest()) -> dict[str, object]:
        try:
            result = retry_task_command(
                base_dir=base_dir,
                task_id=task_id,
                executor_name=request.executor_name,
                capability_refs=request.capability_refs,
                route_mode=request.route_mode,
                from_phase=request.from_phase,
            )
            return task_recovery_response(result)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except WebRequestError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=_status_for_value_error(exc), detail=str(exc)) from exc

    @app.post("/api/tasks/{task_id}/resume")
    def task_resume(task_id: str, request: TaskActionRequest = TaskActionRequest()) -> dict[str, object]:
        try:
            result = resume_task_command(
                base_dir=base_dir,
                task_id=task_id,
                executor_name=request.executor_name,
                capability_refs=request.capability_refs,
                route_mode=request.route_mode,
            )
            return task_recovery_response(result)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except WebRequestError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=_status_for_value_error(exc), detail=str(exc)) from exc

    @app.post("/api/tasks/{task_id}/rerun")
    def task_rerun(task_id: str, request: TaskActionRequest = TaskActionRequest()) -> dict[str, object]:
        try:
            result = rerun_task_command(
                base_dir=base_dir,
                task_id=task_id,
                executor_name=request.executor_name,
                capability_refs=request.capability_refs,
                route_mode=request.route_mode,
                from_phase=request.from_phase,
            )
            return task_run_response(result)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except WebRequestError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/tasks/{task_id}/acknowledge")
    def task_acknowledge(task_id: str) -> dict[str, object]:
        try:
            result = acknowledge_task_command(base_dir, task_id)
            return task_acknowledge_response(result)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except WebRequestError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

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

    @app.post("/api/knowledge/staged/{candidate_id}/promote")
    def knowledge_promote(
        candidate_id: str,
        request: StageDecisionRequest = StageDecisionRequest(),
    ) -> dict[str, object]:
        try:
            result = promote_stage_candidate_command(
                base_dir,
                candidate_id,
                note=request.note,
                refined_text=request.refined_text,
                force=request.force,
            )
            return stage_promote_response(result)
        except StagePromotePreflightError as exc:
            raise HTTPException(status_code=409, detail={"message": str(exc), "notices": exc.notices}) from exc
        except WebRequestError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=_status_for_value_error(exc), detail=str(exc)) from exc

    @app.post("/api/knowledge/staged/{candidate_id}/reject")
    def knowledge_reject(
        candidate_id: str,
        request: StageDecisionRequest = StageDecisionRequest(),
    ) -> dict[str, object]:
        try:
            candidate = reject_stage_candidate_command(base_dir, candidate_id, note=request.note)
            return stage_decision_response(candidate)
        except WebRequestError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=_status_for_value_error(exc), detail=str(exc)) from exc

    @app.post("/api/proposals/review")
    def proposal_review(request: ProposalReviewRequest) -> dict[str, object]:
        try:
            bundle_path = resolve_workspace_relative_file(base_dir, request.bundle_path)
            result = review_proposals_command(
                base_dir,
                bundle_path,
                decision=request.decision,
                proposal_ids=request.proposal_ids,
                note=request.note,
                reviewer=request.reviewer,
            )
            return proposal_review_response(result, base_dir)
        except WebRequestError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/proposals/apply")
    def proposal_apply(request: ProposalApplyRequest) -> dict[str, object]:
        try:
            review_path = resolve_workspace_relative_file(base_dir, request.review_path)
            result = apply_reviewed_proposals_command(
                base_dir,
                review_path,
                proposal_id=request.proposal_id,
            )
            return proposal_apply_response(result, base_dir)
        except WebRequestError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app
