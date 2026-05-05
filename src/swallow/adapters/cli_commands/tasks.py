from __future__ import annotations

import json
from collections.abc import Callable
from importlib import import_module
from pathlib import Path

from swallow._io_helpers import read_json_lines_or_empty, read_json_or_empty, read_json_strict
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
from swallow.application.infrastructure.paths import (
    artifacts_dir,
    canonical_registry_index_path,
    canonical_registry_path,
    canonical_reuse_eval_path,
    canonical_reuse_policy_path,
    canonical_reuse_regression_path,
    capability_assembly_path,
    capability_manifest_path,
    checkpoint_snapshot_path,
    compatibility_path,
    dispatch_path,
    execution_budget_policy_path,
    execution_fit_path,
    execution_site_path,
    handoff_path,
    knowledge_decisions_path,
    knowledge_index_path,
    knowledge_partition_path,
    knowledge_policy_path,
    memory_path,
    remote_handoff_contract_path,
    retry_policy_path,
    route_path,
    stop_policy_path,
    task_semantics_path,
    retrieval_path,
    topology_path,
)
from swallow.application.infrastructure.workspace import resolve_path
from swallow.truth_governance.store import iter_task_states, load_knowledge_objects, load_state


ArtifactPrinter = Callable[[Path, str | None], int]

TEXT_ARTIFACT_PRINTERS: dict[str, str] = {
    "summarize": "summary.md",
    "semantics": "task_semantics_report.md",
    "resume-note": "resume_note.md",
    "validation": "validation_report.md",
    "compatibility": "compatibility_report.md",
    "grounding": "grounding_evidence_report.md",
    "knowledge-objects": "knowledge_objects_report.md",
    "knowledge-partition": "knowledge_partition_report.md",
    "knowledge-index": "knowledge_index_report.md",
    "knowledge-policy": "knowledge_policy_report.md",
    "retrieval": "retrieval_report.md",
    "topology": "topology_report.md",
    "execution-site": "execution_site_report.md",
    "handoff": "handoff_report.md",
    "remote-handoff": "remote_handoff_contract_report.md",
    "execution-fit": "execution_fit_report.md",
    "retry-policy": "retry_policy_report.md",
    "execution-budget-policy": "execution_budget_policy_report.md",
    "stop-policy": "stop_policy_report.md",
    "route": "route_report.md",
}

JSON_ARTIFACT_PRINTERS: dict[str, Callable[[Path, str], Path]] = {
    "memory": memory_path,
    "compatibility-json": compatibility_path,
    "route-json": route_path,
    "topology-json": topology_path,
    "execution-site-json": execution_site_path,
    "dispatch-json": dispatch_path,
    "handoff-json": handoff_path,
    "remote-handoff-json": remote_handoff_contract_path,
    "execution-fit-json": execution_fit_path,
    "retry-policy-json": retry_policy_path,
    "execution-budget-policy-json": execution_budget_policy_path,
    "stop-policy-json": stop_policy_path,
    "checkpoint-json": checkpoint_snapshot_path,
    "capabilities-json": capability_assembly_path,
    "semantics-json": task_semantics_path,
    "knowledge-partition-json": knowledge_partition_path,
    "knowledge-index-json": knowledge_index_path,
    "knowledge-policy-json": knowledge_policy_path,
    "retrieval-json": retrieval_path,
}


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


def handle_task_read_command(base_dir: Path, args: object) -> int | None:
    if getattr(args, "command", None) != "task":
        return None

    task_command = getattr(args, "task_command", None)
    if task_command == "list":
        return _handle_task_list(base_dir, args)
    if task_command == "queue":
        return _handle_task_queue(base_dir, args)
    if task_command == "attempts":
        return _handle_task_attempts(base_dir, args)
    if task_command == "compare-attempts":
        return _handle_compare_attempts(base_dir, args)
    if task_command == "control":
        state = load_state(base_dir, getattr(args, "task_id"))
        print("\n".join(_cli().build_task_control_snapshot(base_dir, state)))
        return 0
    if task_command == "intake":
        print("\n".join(_cli().build_intake_snapshot(base_dir, getattr(args, "task_id"))))
        return 0
    if task_command == "staged":
        return _handle_task_staged(base_dir, args)
    if task_command == "knowledge-review-queue":
        return _handle_knowledge_review_queue(base_dir, args)
    if task_command == "capabilities":
        return _handle_capabilities(base_dir, args)
    if task_command == "checkpoint":
        print((artifacts_dir(base_dir, getattr(args, "task_id")) / "checkpoint_snapshot_report.md").read_text(encoding="utf-8"), end="")
        return 0
    if task_command == "policy":
        return _handle_policy(base_dir, args)
    if task_command == "artifacts":
        state = load_state(base_dir, getattr(args, "task_id"))
        print(_cli().build_grouped_artifact_index(state.artifact_paths), end="")
        return 0
    if task_command == "dispatch":
        state = load_state(base_dir, getattr(args, "task_id"))
        topology = read_json_or_empty(topology_path(base_dir, getattr(args, "task_id")))
        if _cli().is_mock_remote_task(state, topology):
            print("[MOCK-REMOTE]")
        return _print_text_artifact(artifacts_dir(base_dir, getattr(args, "task_id")) / "dispatch_report.md")
    if task_command in ARTIFACT_PRINTER_DISPATCH:
        return _dispatch_artifact_printer(args, base_dir)
    return None


def _cli():
    return import_module("swallow.adapters.cli")


def _handle_task_list(base_dir: Path, args: object) -> int:
    c = _cli()
    states = sorted(
        iter_task_states(base_dir),
        key=lambda state: (state.updated_at, state.task_id),
        reverse=True,
    )
    states = c.filter_task_states(states, getattr(args, "focus"))
    if getattr(args, "limit") is not None:
        states = states[: max(getattr(args, "limit"), 0)]
    print(f"task_id\tstatus\tphase\tattempt\tupdated_at\ttitle\tfocus={getattr(args, 'focus')}")
    for state in states:
        attempt_label = state.current_attempt_id or "-"
        print(
            "\t".join(
                [
                    state.task_id,
                    state.status,
                    state.phase,
                    attempt_label,
                    state.updated_at,
                    state.title,
                ]
            )
        )
    return 0


def _handle_task_queue(base_dir: Path, args: object) -> int:
    c = _cli()
    states = sorted(
        iter_task_states(base_dir),
        key=lambda state: (state.updated_at, state.task_id),
        reverse=True,
    )
    queue_entries = [entry for state in states if (entry := c.build_task_queue_entry(base_dir, state)) is not None]
    if getattr(args, "limit") is not None:
        queue_entries = queue_entries[: max(getattr(args, "limit"), 0)]
    print("task_id\taction\tstatus\tattempt\tupdated_at\treason\tregression\tknowledge\tnext\ttitle")
    for entry in queue_entries:
        print(
            "\t".join(
                [
                    entry["task_id"],
                    entry["action"],
                    entry["status"],
                    entry["attempt"],
                    entry["updated_at"],
                    entry["reason"],
                    entry["regression"],
                    entry["knowledge"],
                    entry["next"],
                    entry["title"],
                ]
            )
        )
    return 0


def _handle_task_attempts(base_dir: Path, args: object) -> int:
    c = _cli()
    task_id = getattr(args, "task_id")
    state = load_state(base_dir, task_id)
    attempts = c.build_attempt_summaries(base_dir, task_id)
    print("attempt_id\tattempt_number\tstatus\texecutor_status\texecution_lifecycle\tretrieval_count\thandoff_status\tstarted_at\tfinished_at")
    for attempt in attempts:
        print(
            "\t".join(
                [
                    attempt["attempt_id"],
                    attempt["attempt_number"],
                    attempt["status"],
                    attempt["executor_status"],
                    attempt["execution_lifecycle"],
                    attempt["retrieval_count"],
                    attempt["handoff_status"],
                    attempt["started_at"],
                    attempt["finished_at"],
                ]
            )
        )
    if not attempts and state.current_attempt_id:
        print(
            "\t".join(
                [
                    state.current_attempt_id,
                    str(state.current_attempt_number or 0),
                    state.status,
                    state.executor_status,
                    state.execution_lifecycle,
                    str(state.retrieval_count),
                    "pending",
                    state.updated_at,
                    "-",
                ]
            )
        )
    return 0


def _handle_compare_attempts(base_dir: Path, args: object) -> int:
    c = _cli()
    task_id = getattr(args, "task_id")
    attempts = c.build_attempt_summaries(base_dir, task_id)
    left, right = c.resolve_attempt_pair(attempts, getattr(args, "left"), getattr(args, "right"))
    lines = [
        f"Task Attempt Compare: {task_id}",
        f"left_attempt: {left['attempt_id']}",
        f"right_attempt: {right['attempt_id']}",
        "",
        "Comparison",
        f"status: {left['status']} -> {right['status']}",
        f"executor_status: {left['executor_status']} -> {right['executor_status']}",
        f"execution_lifecycle: {left['execution_lifecycle']} -> {right['execution_lifecycle']}",
        f"retrieval_count: {left['retrieval_count']} -> {right['retrieval_count']}",
        f"handoff_status: {left['handoff_status']} -> {right['handoff_status']}",
        f"compatibility_status: {left['compatibility_status']} -> {right['compatibility_status']}",
        f"execution_fit_status: {left['execution_fit_status']} -> {right['execution_fit_status']}",
        f"retry_policy_status: {left['retry_policy_status']} -> {right['retry_policy_status']}",
        f"stop_policy_status: {left['stop_policy_status']} -> {right['stop_policy_status']}",
    ]
    print("\n".join(lines))
    return 0


def _handle_task_staged(base_dir: Path, args: object) -> int:
    c = _cli()
    candidates = c.load_staged_candidates(base_dir)
    task_filter = getattr(args, "task").strip()
    if getattr(args, "status") != "all":
        candidates = [candidate for candidate in candidates if candidate.status == getattr(args, "status")]
    if task_filter:
        candidates = [candidate for candidate in candidates if candidate.source_task_id == task_filter]
    task_knowledge_count = len(load_knowledge_objects(base_dir, task_filter)) if task_filter and not candidates else 0
    print(
        c.build_task_staged_report(
            candidates,
            status_filter=getattr(args, "status"),
            task_filter=task_filter,
            task_knowledge_count=task_knowledge_count,
        )
    )
    return 0


def _handle_knowledge_review_queue(base_dir: Path, args: object) -> int:
    c = _cli()
    knowledge_objects = load_knowledge_objects(base_dir, getattr(args, "task_id"))
    decisions = read_json_lines_or_empty(knowledge_decisions_path(base_dir, getattr(args, "task_id")))
    print(c.render_review_queue_report(c.build_review_queue(knowledge_objects, decisions)))
    return 0


def _handle_capabilities(base_dir: Path, args: object) -> int:
    state = load_state(base_dir, getattr(args, "task_id"))
    manifest = json.loads(capability_manifest_path(base_dir, getattr(args, "task_id")).read_text(encoding="utf-8"))
    assembly = json.loads(capability_assembly_path(base_dir, getattr(args, "task_id")).read_text(encoding="utf-8"))
    lines = [
        f"Task Capabilities: {state.task_id}",
        "",
        "Requested Manifest",
        f"profile_refs: {', '.join(manifest.get('profile_refs', [])) or '-'}",
        f"workflow_refs: {', '.join(manifest.get('workflow_refs', [])) or '-'}",
        f"validator_refs: {', '.join(manifest.get('validator_refs', [])) or '-'}",
        f"skill_refs: {', '.join(manifest.get('skill_refs', [])) or '-'}",
        f"tool_refs: {', '.join(manifest.get('tool_refs', [])) or '-'}",
        "",
        "Effective Assembly",
        f"assembly_status: {assembly.get('assembly_status', 'pending')}",
        f"resolver: {assembly.get('resolver', 'unknown')}",
        f"effective_profiles: {', '.join(assembly.get('effective', {}).get('profile_refs', [])) or '-'}",
        f"effective_workflows: {', '.join(assembly.get('effective', {}).get('workflow_refs', [])) or '-'}",
        f"effective_validators: {', '.join(assembly.get('effective', {}).get('validator_refs', [])) or '-'}",
        f"notes: {'; '.join(assembly.get('notes', [])) or '-'}",
    ]
    print("\n".join(lines))
    return 0


def _handle_policy(base_dir: Path, args: object) -> int:
    c = _cli()
    task_id = getattr(args, "task_id")
    state = load_state(base_dir, task_id)
    retry_policy = read_json_or_empty(retry_policy_path(base_dir, task_id))
    execution_budget_policy = read_json_or_empty(execution_budget_policy_path(base_dir, task_id))
    stop_policy = read_json_or_empty(stop_policy_path(base_dir, task_id))
    lines = [f"Task Policy: {state.task_id}", f"title: {state.title}", ""]
    lines.extend(c.build_policy_snapshot(retry_policy, execution_budget_policy, stop_policy))
    lines.extend(
        [
            "",
            "Policy Artifacts",
            f"retry_policy_report: {state.artifact_paths.get('retry_policy_report', '-')}",
            f"execution_budget_policy_report: {state.artifact_paths.get('execution_budget_policy_report', '-')}",
            f"stop_policy_report: {state.artifact_paths.get('stop_policy_report', '-')}",
        ]
    )
    print("\n".join(lines))
    return 0


def _require_artifact_task_id(task_id: str | None) -> str:
    if not task_id:
        raise ValueError("task_id is required for task artifact printer.")
    return task_id


def _print_text_artifact(path: Path) -> int:
    print(path.read_text(encoding="utf-8"), end="")
    return 0


def _print_report(text: str) -> int:
    print(text)
    return 0


def _print_json_payload(payload: object) -> int:
    print(json.dumps(payload, indent=2))
    return 0


def _print_json_artifact(path: Path) -> int:
    return _print_json_payload(read_json_strict(path))


def _text_artifact_printer(artifact_name: str) -> ArtifactPrinter:
    return lambda base_dir, task_id: _print_text_artifact(
        artifacts_dir(base_dir, _require_artifact_task_id(task_id)) / artifact_name
    )


def _json_artifact_printer(path_builder: Callable[[Path, str], Path]) -> ArtifactPrinter:
    return lambda base_dir, task_id: _print_json_artifact(
        path_builder(base_dir, _require_artifact_task_id(task_id))
    )


def _print_canonical_reuse_regression(base_dir: Path, task_id: str | None) -> int:
    c = _cli()
    required_task_id = _require_artifact_task_id(task_id)
    baseline = read_json_or_empty(canonical_reuse_regression_path(base_dir, required_task_id))
    records = read_json_lines_or_empty(canonical_reuse_eval_path(base_dir, required_task_id))
    current = c.build_canonical_reuse_regression_current(
        task_id=required_task_id,
        summary=c.build_canonical_reuse_evaluation_summary(records),
    )
    comparison = c.compare_canonical_reuse_regression(baseline=baseline, current=current)
    return _print_report(
        c.build_canonical_reuse_regression_report(baseline=baseline, current=current, comparison=comparison)
    )


def _print_canonical_reuse_eval(base_dir: Path, task_id: str | None) -> int:
    c = _cli()
    records = read_json_lines_or_empty(canonical_reuse_eval_path(base_dir, _require_artifact_task_id(task_id)))
    return _print_report(
        c.build_canonical_reuse_evaluation_report(records, c.build_canonical_reuse_evaluation_summary(records))
    )


ARTIFACT_PRINTER_DISPATCH: dict[str, ArtifactPrinter] = {
    **{command: _text_artifact_printer(artifact_name) for command, artifact_name in TEXT_ARTIFACT_PRINTERS.items()},
    **{command: _json_artifact_printer(path_builder) for command, path_builder in JSON_ARTIFACT_PRINTERS.items()},
    "knowledge-objects-json": lambda base_dir, task_id: _print_json_payload(
        load_knowledge_objects(base_dir, _require_artifact_task_id(task_id))
    ),
    "knowledge-decisions": lambda base_dir, task_id: _print_report(
        _cli().render_knowledge_decisions_report(
            read_json_lines_or_empty(knowledge_decisions_path(base_dir, _require_artifact_task_id(task_id)))
        )
    ),
    "canonical-registry": lambda base_dir, _task_id: _print_report(
        _cli().render_canonical_registry_report(read_json_lines_or_empty(canonical_registry_path(base_dir)))
    ),
    "canonical-registry-index": lambda base_dir, _task_id: _print_report(
        _cli().render_canonical_registry_index_report(read_json_or_empty(canonical_registry_index_path(base_dir)))
    ),
    "canonical-reuse": lambda base_dir, _task_id: _print_report(
        _cli().render_canonical_reuse_report(read_json_or_empty(canonical_reuse_policy_path(base_dir)))
    ),
    "canonical-reuse-regression": _print_canonical_reuse_regression,
    "canonical-reuse-eval": _print_canonical_reuse_eval,
    "knowledge-decisions-json": lambda base_dir, task_id: _print_json_payload(
        read_json_lines_or_empty(knowledge_decisions_path(base_dir, _require_artifact_task_id(task_id)))
    ),
    "canonical-registry-json": lambda base_dir, _task_id: _print_json_payload(
        read_json_lines_or_empty(canonical_registry_path(base_dir))
    ),
    "canonical-registry-index-json": lambda base_dir, _task_id: _print_json_payload(
        read_json_or_empty(canonical_registry_index_path(base_dir))
    ),
    "canonical-reuse-json": lambda base_dir, _task_id: _print_json_payload(
        read_json_or_empty(canonical_reuse_policy_path(base_dir))
    ),
    "canonical-reuse-eval-json": lambda base_dir, task_id: _print_json_payload(
        read_json_lines_or_empty(canonical_reuse_eval_path(base_dir, _require_artifact_task_id(task_id)))
    ),
    "canonical-reuse-regression-json": lambda base_dir, task_id: _print_json_payload(
        read_json_or_empty(canonical_reuse_regression_path(base_dir, _require_artifact_task_id(task_id)))
    ),
}


def _dispatch_artifact_printer(args: object, base_dir: Path) -> int:
    handler = ARTIFACT_PRINTER_DISPATCH.get(getattr(args, "task_command"))
    if handler is None:
        raise NotImplementedError(
            f"Read-only printer dispatch table missing handler for {getattr(args, 'task_command')!r}; "
            "either add an entry or remove it from the Phase 67 M3 in-scope command set."
        )
    return handler(base_dir, getattr(args, "task_id", None))


def _handle_task_create(base_dir: Path, args: object) -> int:
    input_context: dict[str, object] = {}
    if getattr(args, "document_paths"):
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
