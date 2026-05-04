from pathlib import Path

from swallow.application.commands.knowledge import (
    StagePromotePreflightError,
    UnknownStagedCandidateError,
    promote_stage_candidate_command,
    reject_stage_candidate_command,
)
from swallow.application.commands.proposals import apply_reviewed_proposals_command, review_proposals_command
from swallow.application.commands.tasks import (
    TaskAcknowledgeCommandResult,
    TaskRecoveryCommandResult,
    acknowledge_task_command,
    create_task_command,
    rerun_task_command,
    resume_task_command,
    retry_task_command,
    run_task_command,
)
from swallow.application.commands.wiki import refresh_wiki_evidence_command
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
from swallow.application.queries.knowledge import (
    KnowledgeObjectNotFoundError,
    build_canonical_knowledge_payload,
    build_knowledge_detail_payload,
    build_knowledge_relations_payload,
    build_staged_knowledge_payload,
    build_wiki_knowledge_payload,
)
from swallow.application.services.wiki_jobs import (
    create_wiki_draft_job,
    create_wiki_refine_job,
    load_wiki_job_record,
    load_wiki_job_result,
    run_wiki_job,
)
from swallow.adapters.http.exceptions import TaskActionBlockedError


def _static_dir() -> Path:
    return Path(__file__).parent / "static"


def _task_recovery_or_raise(result: TaskRecoveryCommandResult) -> TaskRecoveryCommandResult:
    if result.blocked:
        detail: dict[str, object] = {
            "blocked": True,
            "blocked_kind": result.blocked_kind,
            "task_id": result.state.task_id,
        }
        if result.retry_policy is not None:
            detail["retry_policy"] = result.retry_policy
        if result.stop_policy is not None:
            detail["stop_policy"] = result.stop_policy
        if result.checkpoint_snapshot is not None:
            detail["checkpoint_snapshot"] = result.checkpoint_snapshot
        raise TaskActionBlockedError(
            blocked_kind=result.blocked_kind or "unknown",
            blocked_reason=f"Task action is blocked: {result.blocked_kind or 'unknown'}",
            detail=detail,
        )
    return result


def _task_acknowledge_or_raise(result: TaskAcknowledgeCommandResult) -> TaskAcknowledgeCommandResult:
    if result.blocked:
        raise TaskActionBlockedError(
            blocked_kind="acknowledge",
            blocked_reason=result.blocked_reason or "Task action is blocked: acknowledge",
            detail={
                "blocked": True,
                "blocked_kind": "acknowledge",
                "blocked_reason": result.blocked_reason,
                "task_id": result.state.task_id,
            },
        )
    return result


def create_fastapi_app(base_dir: Path):
    try:
        from fastapi import BackgroundTasks, Depends, FastAPI, Request
        from fastapi.responses import FileResponse, JSONResponse
        from fastapi.staticfiles import StaticFiles
        from swallow.adapters.http.dependencies import get_base_dir, resolve_workspace_relative_file
        from swallow.adapters.http.schemas import (
            CandidateEnvelope,
            CreateTaskRequest,
            KnowledgeDetailEnvelope,
            KnowledgeListEnvelope,
            KnowledgeRelationsEnvelope,
            ProposalApplyEnvelope,
            ProposalApplyRequest,
            ProposalReviewEnvelope,
            ProposalReviewRequest,
            StageDecisionRequest,
            StagePromoteEnvelope,
            TaskActionRequest,
            TaskEnvelope,
            TaskRecoveryEnvelope,
            WikiDraftRequest,
            WikiEvidenceRefreshEnvelope,
            WikiJobEnvelope,
            WikiJobResultEnvelope,
            WikiRefineRequest,
            WikiRefreshEvidenceRequest,
        )
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "FastAPI is required for `swl serve`. Install `fastapi` and `uvicorn` to use the control center."
        ) from exc

    app = FastAPI(title="Swallow Control Center", version="0.1.0")
    app.state.base_dir = base_dir
    static_dir = _static_dir()
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.exception_handler(FileNotFoundError)
    def file_not_found_handler(_request: Request, exc: FileNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(UnknownStagedCandidateError)
    def unknown_staged_candidate_handler(_request: Request, exc: UnknownStagedCandidateError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(StagePromotePreflightError)
    def stage_promote_preflight_handler(_request: Request, exc: StagePromotePreflightError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": {"message": str(exc), "notices": exc.notices}})

    @app.exception_handler(TaskActionBlockedError)
    def task_action_blocked_handler(_request: Request, exc: TaskActionBlockedError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.detail})

    @app.exception_handler(KnowledgeObjectNotFoundError)
    def knowledge_object_not_found_handler(_request: Request, exc: KnowledgeObjectNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValueError)
    def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/tasks")
    def tasks(focus: str = "all", request_base_dir: Path = Depends(get_base_dir)) -> dict[str, object]:
        return build_tasks_payload(request_base_dir, focus=focus)

    @app.post("/api/tasks", response_model=TaskEnvelope)
    def create_task_route(request: CreateTaskRequest, request_base_dir: Path = Depends(get_base_dir)) -> TaskEnvelope:
        state = create_task_command(
            base_dir=request_base_dir,
            title=request.title,
            goal=request.goal,
            workspace_root=request_base_dir,
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
        return TaskEnvelope.from_state(state)

    @app.get("/api/tasks/{task_id}")
    def task(task_id: str, request_base_dir: Path = Depends(get_base_dir)) -> dict[str, object]:
        return build_task_payload(request_base_dir, task_id)

    @app.post("/api/tasks/{task_id}/run", response_model=TaskEnvelope)
    def task_run(
        task_id: str,
        request: TaskActionRequest | None = None,
        request_base_dir: Path = Depends(get_base_dir),
    ) -> TaskEnvelope:
        action_request = request or TaskActionRequest()
        result = run_task_command(
            base_dir=request_base_dir,
            task_id=task_id,
            executor_name=action_request.executor_name,
            capability_refs=action_request.capability_refs,
            route_mode=action_request.route_mode,
        )
        return TaskEnvelope.from_run_result(result)

    @app.post("/api/tasks/{task_id}/retry", response_model=TaskRecoveryEnvelope)
    def task_retry(
        task_id: str,
        request: TaskActionRequest | None = None,
        request_base_dir: Path = Depends(get_base_dir),
    ) -> TaskRecoveryEnvelope:
        action_request = request or TaskActionRequest()
        result = retry_task_command(
            base_dir=request_base_dir,
            task_id=task_id,
            executor_name=action_request.executor_name,
            capability_refs=action_request.capability_refs,
            route_mode=action_request.route_mode,
            from_phase=action_request.from_phase,
        )
        return TaskRecoveryEnvelope.from_result(_task_recovery_or_raise(result))

    @app.post("/api/tasks/{task_id}/resume", response_model=TaskRecoveryEnvelope)
    def task_resume(
        task_id: str,
        request: TaskActionRequest | None = None,
        request_base_dir: Path = Depends(get_base_dir),
    ) -> TaskRecoveryEnvelope:
        action_request = request or TaskActionRequest()
        result = resume_task_command(
            base_dir=request_base_dir,
            task_id=task_id,
            executor_name=action_request.executor_name,
            capability_refs=action_request.capability_refs,
            route_mode=action_request.route_mode,
        )
        return TaskRecoveryEnvelope.from_result(_task_recovery_or_raise(result))

    @app.post("/api/tasks/{task_id}/rerun", response_model=TaskEnvelope)
    def task_rerun(
        task_id: str,
        request: TaskActionRequest | None = None,
        request_base_dir: Path = Depends(get_base_dir),
    ) -> TaskEnvelope:
        action_request = request or TaskActionRequest()
        result = rerun_task_command(
            base_dir=request_base_dir,
            task_id=task_id,
            executor_name=action_request.executor_name,
            capability_refs=action_request.capability_refs,
            route_mode=action_request.route_mode,
            from_phase=action_request.from_phase,
        )
        return TaskEnvelope.from_run_result(result)

    @app.post("/api/tasks/{task_id}/acknowledge", response_model=TaskEnvelope)
    def task_acknowledge(task_id: str, request_base_dir: Path = Depends(get_base_dir)) -> TaskEnvelope:
        result = acknowledge_task_command(request_base_dir, task_id)
        return TaskEnvelope.from_acknowledge_result(_task_acknowledge_or_raise(result))

    @app.get("/api/tasks/{task_id}/events")
    def task_events(task_id: str, request_base_dir: Path = Depends(get_base_dir)) -> dict[str, object]:
        return build_task_events_payload(request_base_dir, task_id)

    @app.get("/api/tasks/{task_id}/artifacts")
    def task_artifacts(task_id: str, request_base_dir: Path = Depends(get_base_dir)) -> dict[str, object]:
        return build_task_artifacts_payload(request_base_dir, task_id)

    @app.get("/api/tasks/{task_id}/artifacts/{artifact_name:path}")
    def task_artifact(
        task_id: str,
        artifact_name: str,
        request_base_dir: Path = Depends(get_base_dir),
    ) -> dict[str, object]:
        return build_task_artifact_payload(request_base_dir, task_id, artifact_name)

    @app.get("/api/tasks/{task_id}/artifact-diff")
    def task_artifact_diff(
        task_id: str,
        left: str = "",
        right: str = "",
        request_base_dir: Path = Depends(get_base_dir),
    ) -> dict[str, object]:
        return build_task_artifact_diff_payload(request_base_dir, task_id, left, right)

    @app.get("/api/tasks/{task_id}/knowledge")
    def task_knowledge(task_id: str, request_base_dir: Path = Depends(get_base_dir)) -> dict[str, object]:
        return build_task_knowledge_payload(request_base_dir, task_id)

    @app.get("/api/knowledge/wiki", response_model=KnowledgeListEnvelope)
    def knowledge_wiki(
        status: str = "active",
        limit: int = 50,
        request_base_dir: Path = Depends(get_base_dir),
    ) -> KnowledgeListEnvelope:
        return KnowledgeListEnvelope.from_payload(
            build_wiki_knowledge_payload(request_base_dir, status=status, limit=limit)
        )

    @app.get("/api/knowledge/canonical", response_model=KnowledgeListEnvelope)
    def knowledge_canonical(
        status: str = "active",
        limit: int = 50,
        request_base_dir: Path = Depends(get_base_dir),
    ) -> KnowledgeListEnvelope:
        return KnowledgeListEnvelope.from_payload(
            build_canonical_knowledge_payload(request_base_dir, status=status, limit=limit)
        )

    @app.get("/api/knowledge/staged", response_model=KnowledgeListEnvelope)
    def knowledge_staged(
        status: str = "pending",
        limit: int = 50,
        request_base_dir: Path = Depends(get_base_dir),
    ) -> KnowledgeListEnvelope:
        return KnowledgeListEnvelope.from_payload(
            build_staged_knowledge_payload(request_base_dir, status=status, limit=limit)
        )

    @app.get("/api/knowledge/{object_id}", response_model=KnowledgeDetailEnvelope)
    def knowledge_detail(
        object_id: str,
        request_base_dir: Path = Depends(get_base_dir),
    ) -> KnowledgeDetailEnvelope:
        return KnowledgeDetailEnvelope.from_payload(build_knowledge_detail_payload(request_base_dir, object_id))

    @app.get("/api/knowledge/{object_id}/relations", response_model=KnowledgeRelationsEnvelope)
    def knowledge_relations(
        object_id: str,
        request_base_dir: Path = Depends(get_base_dir),
    ) -> KnowledgeRelationsEnvelope:
        return KnowledgeRelationsEnvelope.from_payload(build_knowledge_relations_payload(request_base_dir, object_id))

    @app.post("/api/wiki/draft", response_model=WikiJobEnvelope)
    def wiki_draft(
        request: WikiDraftRequest,
        background_tasks: BackgroundTasks,
        request_base_dir: Path = Depends(get_base_dir),
    ) -> WikiJobEnvelope:
        job = create_wiki_draft_job(
            request_base_dir,
            task_id=request.task_id,
            topic=request.topic,
            source_refs=request.source_refs,
            model=request.model,
        )
        background_tasks.add_task(run_wiki_job, request_base_dir, job.job_id)
        return WikiJobEnvelope.from_record(job)

    @app.post("/api/wiki/refine", response_model=WikiJobEnvelope)
    def wiki_refine(
        request: WikiRefineRequest,
        background_tasks: BackgroundTasks,
        request_base_dir: Path = Depends(get_base_dir),
    ) -> WikiJobEnvelope:
        job = create_wiki_refine_job(
            request_base_dir,
            task_id=request.task_id,
            mode=request.mode,
            target_object_id=request.target_object_id,
            source_refs=request.source_refs,
            model=request.model,
        )
        background_tasks.add_task(run_wiki_job, request_base_dir, job.job_id)
        return WikiJobEnvelope.from_record(job)

    @app.post("/api/wiki/refresh-evidence", response_model=WikiEvidenceRefreshEnvelope)
    def wiki_refresh_evidence(
        request: WikiRefreshEvidenceRequest,
        request_base_dir: Path = Depends(get_base_dir),
    ) -> WikiEvidenceRefreshEnvelope:
        result = refresh_wiki_evidence_command(
            request_base_dir,
            task_id=request.task_id,
            target_object_id=request.target_object_id,
            source_ref=request.source_ref,
            parser_version=request.parser_version,
            span=request.span,
            heading_path=request.heading_path,
        )
        return WikiEvidenceRefreshEnvelope.from_result(result)

    @app.get("/api/wiki/jobs/{job_id}", response_model=WikiJobEnvelope)
    def wiki_job_status(
        job_id: str,
        request_base_dir: Path = Depends(get_base_dir),
    ) -> WikiJobEnvelope:
        return WikiJobEnvelope.from_record(load_wiki_job_record(request_base_dir, job_id))

    @app.get("/api/wiki/jobs/{job_id}/result", response_model=WikiJobResultEnvelope)
    def wiki_job_result(
        job_id: str,
        request_base_dir: Path = Depends(get_base_dir),
    ) -> WikiJobResultEnvelope:
        return WikiJobResultEnvelope.from_payload(load_wiki_job_result(request_base_dir, job_id))

    @app.get("/api/tasks/{task_id}/subtask-tree")
    def task_subtask_tree(task_id: str, request_base_dir: Path = Depends(get_base_dir)) -> dict[str, object]:
        return build_task_subtask_tree_payload(request_base_dir, task_id)

    @app.get("/api/tasks/{task_id}/execution-timeline")
    def task_execution_timeline(task_id: str, request_base_dir: Path = Depends(get_base_dir)) -> dict[str, object]:
        return build_task_execution_timeline_payload(request_base_dir, task_id)

    @app.post("/api/knowledge/staged/{candidate_id}/promote", response_model=StagePromoteEnvelope)
    def knowledge_promote(
        candidate_id: str,
        request: StageDecisionRequest | None = None,
        request_base_dir: Path = Depends(get_base_dir),
    ) -> StagePromoteEnvelope:
        stage_request = request or StageDecisionRequest()
        result = promote_stage_candidate_command(
            request_base_dir,
            candidate_id,
            note=stage_request.note,
            refined_text=stage_request.refined_text,
            force=False,
            confirmed_notice_types=stage_request.confirmed_notice_types,
            confirmed_supersede_target_ids=stage_request.confirmed_supersede_target_ids,
            confirmed_conflict_flags=stage_request.confirmed_conflict_flags,
        )
        return StagePromoteEnvelope.from_result(result)

    @app.post("/api/knowledge/staged/{candidate_id}/reject", response_model=CandidateEnvelope)
    def knowledge_reject(
        candidate_id: str,
        request: StageDecisionRequest | None = None,
        request_base_dir: Path = Depends(get_base_dir),
    ) -> CandidateEnvelope:
        stage_request = request or StageDecisionRequest()
        candidate = reject_stage_candidate_command(request_base_dir, candidate_id, note=stage_request.note)
        return CandidateEnvelope.from_candidate(candidate)

    @app.post("/api/proposals/review", response_model=ProposalReviewEnvelope)
    def proposal_review(
        request: ProposalReviewRequest,
        request_base_dir: Path = Depends(get_base_dir),
    ) -> ProposalReviewEnvelope:
        bundle_path = resolve_workspace_relative_file(request_base_dir, request.bundle_path)
        result = review_proposals_command(
            request_base_dir,
            bundle_path,
            decision=request.decision,
            proposal_ids=request.proposal_ids,
            note=request.note,
            reviewer=request.reviewer,
        )
        return ProposalReviewEnvelope.from_result(result, request_base_dir)

    @app.post("/api/proposals/apply", response_model=ProposalApplyEnvelope)
    def proposal_apply(
        request: ProposalApplyRequest,
        request_base_dir: Path = Depends(get_base_dir),
    ) -> ProposalApplyEnvelope:
        review_path = resolve_workspace_relative_file(request_base_dir, request.review_path)
        result = apply_reviewed_proposals_command(
            request_base_dir,
            review_path,
            proposal_id=request.proposal_id,
        )
        return ProposalApplyEnvelope.from_result(result, request_base_dir)

    return app
