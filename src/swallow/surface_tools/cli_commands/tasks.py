from __future__ import annotations

from pathlib import Path

from swallow.application.commands.tasks import (
    acknowledge_task_command,
    append_task_knowledge_capture_command,
    create_task_command,
    decide_task_knowledge_command,
    evaluate_task_canonical_reuse_command,
    resume_task_command,
    retry_task_command,
    rerun_task_command,
    run_task_command,
    run_task_consistency_audit_command,
    update_planning_handoff_command,
)
from swallow.surface_tools.workspace import resolve_path


def handle_task_write_command(base_dir: Path, args: object) -> int | None:
    if getattr(args, "command", None) != "task":
        return None

    task_command = getattr(args, "task_command", None)
    if task_command == "create":
        return _handle_task_create(base_dir, args)
    if task_command == "planning-handoff":
        return _handle_planning_handoff(base_dir, args)
    if task_command == "knowledge-capture":
        return _handle_knowledge_capture(base_dir, args)
    if task_command == "knowledge-promote":
        return _handle_knowledge_decision(base_dir, args, decision_type="promote", output_verb="knowledge_promoted")
    if task_command == "knowledge-reject":
        return _handle_knowledge_decision(base_dir, args, decision_type="reject", output_verb="knowledge_rejected")
    if task_command == "run":
        return _print_run_result(
            run_task_command(
                base_dir=base_dir,
                task_id=getattr(args, "task_id"),
                executor_name=getattr(args, "executor"),
                capability_refs=getattr(args, "capability"),
                route_mode=getattr(args, "route_mode"),
            ).state
        )
    if task_command == "acknowledge":
        result = acknowledge_task_command(base_dir, getattr(args, "task_id"))
        state = result.state
        if result.blocked:
            print(
                f"{state.task_id} acknowledge_blocked "
                f"status={state.status} "
                f"phase={state.phase} "
                f"dispatch_status={state.topology_dispatch_status} "
                f"reason={result.blocked_reason}"
            )
            return 1
        print(
            f"{state.task_id} dispatch_acknowledged "
            f"status={state.status} "
            f"phase={state.phase} "
            f"dispatch_status={state.topology_dispatch_status} "
            f"route={state.route_name}"
        )
        return 0
    if task_command == "retry":
        return _handle_retry(base_dir, args)
    if task_command == "resume":
        return _handle_resume(base_dir, args)
    if task_command == "rerun":
        return _print_run_result(
            rerun_task_command(
                base_dir=base_dir,
                task_id=getattr(args, "task_id"),
                executor_name=getattr(args, "executor"),
                capability_refs=getattr(args, "capability"),
                route_mode=getattr(args, "route_mode"),
                from_phase=getattr(args, "from_phase"),
            ).state
        )
    if task_command == "canonical-reuse-evaluate":
        result = evaluate_task_canonical_reuse_command(
            base_dir,
            getattr(args, "task_id"),
            citations=getattr(args, "citation"),
            judgment=getattr(args, "judgment"),
            note=getattr(args, "note"),
        )
        print(
            f"{result['record']['task_id']} canonical_reuse_evaluated "
            f"judgment={result['record']['judgment']} citations={result['record']['citation_count']}"
        )
        return 0
    if task_command == "consistency-audit":
        result = run_task_consistency_audit_command(
            base_dir,
            getattr(args, "task_id"),
            auditor_route=getattr(args, "auditor_route"),
            sample_artifact_path=getattr(args, "artifact"),
        )
        artifact_ref = result.audit_artifact or "-"
        print(
            f"{result.task_id} consistency_audit status={result.status} "
            f"verdict={result.verdict} route={result.auditor_route} artifact={artifact_ref}"
        )
        return 0
    return None


def _handle_task_create(base_dir: Path, args: object) -> int:
    input_context: dict[str, object] = {}
    if getattr(args, "executor").strip() == "literature-specialist" and getattr(args, "document_paths"):
        document_paths: list[str] = []
        seen_paths: set[str] = set()
        for raw_path in getattr(args, "document_paths"):
            normalized = str(resolve_path(raw_path))
            if not normalized or normalized in seen_paths:
                continue
            document_paths.append(normalized)
            seen_paths.add(normalized)
        if document_paths:
            input_context["document_paths"] = document_paths
    state = create_task_command(
        base_dir=base_dir,
        title=getattr(args, "title").strip(),
        goal=getattr(args, "goal").strip(),
        workspace_root=resolve_path(getattr(args, "workspace_root")),
        executor_name=getattr(args, "executor").strip(),
        input_context=input_context,
        constraints=getattr(args, "constraint"),
        acceptance_criteria=getattr(args, "acceptance_criterion"),
        priority_hints=getattr(args, "priority_hint"),
        next_action_proposals=getattr(args, "next_action_proposal"),
        planning_source=getattr(args, "planning_source"),
        complexity_hint=getattr(args, "complexity_hint"),
        knowledge_items=getattr(args, "knowledge_item"),
        knowledge_stage=getattr(args, "knowledge_stage"),
        knowledge_source=getattr(args, "knowledge_source"),
        knowledge_artifact_refs=getattr(args, "knowledge_artifact_ref"),
        knowledge_retrieval_eligible=getattr(args, "knowledge_retrieval_eligible"),
        knowledge_canonicalization_intent=getattr(args, "knowledge_canonicalization_intent"),
        capability_refs=getattr(args, "capability"),
        route_mode=getattr(args, "route_mode"),
    )
    print(state.task_id)
    return 0


def _handle_planning_handoff(base_dir: Path, args: object) -> int:
    state = update_planning_handoff_command(
        base_dir=base_dir,
        task_id=getattr(args, "task_id"),
        constraints=getattr(args, "constraint"),
        acceptance_criteria=getattr(args, "acceptance_criterion"),
        priority_hints=getattr(args, "priority_hint"),
        next_action_proposals=getattr(args, "next_action_proposal"),
        planning_source=getattr(args, "planning_source"),
        complexity_hint=getattr(args, "complexity_hint"),
    )
    print(
        f"{state.task_id} planning_handoff_updated "
        f"constraints={len(state.task_semantics.get('constraints', []))} "
        f"next_actions={len(state.task_semantics.get('next_action_proposals', []))}"
    )
    return 0


def _handle_knowledge_capture(base_dir: Path, args: object) -> int:
    state = append_task_knowledge_capture_command(
        base_dir=base_dir,
        task_id=getattr(args, "task_id"),
        knowledge_items=getattr(args, "knowledge_item"),
        knowledge_stage=getattr(args, "knowledge_stage"),
        knowledge_source=getattr(args, "knowledge_source"),
        knowledge_artifact_refs=getattr(args, "knowledge_artifact_ref"),
        knowledge_retrieval_eligible=getattr(args, "knowledge_retrieval_eligible"),
        knowledge_canonicalization_intent=getattr(args, "knowledge_canonicalization_intent"),
    )
    print(
        f"{state.task_id} knowledge_capture_added "
        f"added={len(getattr(args, 'knowledge_item'))} total={len(state.knowledge_objects)}"
    )
    return 0


def _handle_knowledge_decision(base_dir: Path, args: object, *, decision_type: str, output_verb: str) -> int:
    state = decide_task_knowledge_command(
        base_dir,
        getattr(args, "task_id"),
        object_id=getattr(args, "object_id"),
        decision_type=decision_type,
        decision_target=getattr(args, "target"),
        note=getattr(args, "note"),
    )
    print(f"{state.task_id} {output_verb} object={getattr(args, 'object_id')} target={getattr(args, 'target')}")
    return 0


def _handle_retry(base_dir: Path, args: object) -> int:
    result = retry_task_command(
        base_dir=base_dir,
        task_id=getattr(args, "task_id"),
        executor_name=getattr(args, "executor"),
        capability_refs=getattr(args, "capability"),
        route_mode=getattr(args, "route_mode"),
        from_phase=getattr(args, "from_phase"),
    )
    if result.blocked:
        retry_policy = result.retry_policy or {}
        stop_policy = result.stop_policy or {}
        checkpoint_snapshot = result.checkpoint_snapshot or {}
        print(
            f"{result.state.task_id} retry_blocked "
            f"retry_decision={retry_policy.get('retry_decision', 'pending')} "
            f"checkpoint_kind={stop_policy.get('checkpoint_kind', 'pending')} "
            f"suggested_path={checkpoint_snapshot.get('recommended_path', 'pending')}"
        )
        return 1
    if result.run_state is None:
        raise RuntimeError("Retry command completed without run state.")
    return _print_run_result(result.run_state)


def _handle_resume(base_dir: Path, args: object) -> int:
    result = resume_task_command(
        base_dir=base_dir,
        task_id=getattr(args, "task_id"),
        executor_name=getattr(args, "executor"),
        capability_refs=getattr(args, "capability"),
        route_mode=getattr(args, "route_mode"),
    )
    if result.blocked:
        checkpoint_snapshot = result.checkpoint_snapshot or {}
        print(
            f"{result.state.task_id} resume_blocked "
            f"checkpoint_state={checkpoint_snapshot.get('checkpoint_state', 'pending')} "
            f"recommended_path={checkpoint_snapshot.get('recommended_path', 'pending')} "
            f"suggested_reason={checkpoint_snapshot.get('recommended_reason', 'pending')}"
        )
        return 1
    if result.run_state is None:
        raise RuntimeError("Resume command completed without run state.")
    return _print_run_result(result.run_state)


def _print_run_result(state: object) -> int:
    print(
        f"{state.task_id} {state.status} retrieval={state.retrieval_count} "
        f"execution_phase={state.execution_phase}"
    )
    return 0
