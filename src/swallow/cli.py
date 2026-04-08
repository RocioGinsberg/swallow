from __future__ import annotations

import argparse
import json
from pathlib import Path

from .doctor import diagnose_codex, format_codex_doctor_result
from .orchestrator import create_task, run_task
from .paths import (
    artifacts_dir,
    capability_assembly_path,
    capability_manifest_path,
    compatibility_path,
    dispatch_path,
    execution_fit_path,
    handoff_path,
    memory_path,
    retrieval_path,
    route_path,
    topology_path,
)
from .store import iter_task_states, load_state


ARTIFACT_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Core Run Record", ("summary", "resume_note", "executor_output", "executor_prompt")),
    ("Routing And Topology", ("route_report", "topology_report", "dispatch_report", "handoff_report")),
    ("Retrieval And Grounding", ("retrieval_report", "retrieval_json", "source_grounding")),
    ("Validation And Policy", ("validation_report", "validation_json", "compatibility_report", "compatibility_json", "execution_fit_report", "execution_fit_json")),
    ("Memory And Reuse", ("task_memory", "route_json", "topology_json", "dispatch_json", "handoff_json")),
)


def build_grouped_artifact_index(artifact_paths: dict[str, str]) -> str:
    lines = ["Task Artifact Index", ""]
    for heading, keys in ARTIFACT_GROUPS:
        lines.append(heading)
        for key in keys:
            path = artifact_paths.get(key)
            if path:
                lines.append(f"{key}: {path}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def filter_task_states(states: list[object], focus: str) -> list[object]:
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swl",
        description="CLI for the swallow stateful AI workflow system.",
    )
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Directory that stores the .swl task state and artifacts. Defaults to the current directory.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    task_parser = subparsers.add_parser("task", help="Task workbench and lifecycle commands.")
    task_subparsers = task_parser.add_subparsers(dest="task_command", required=True)
    doctor_parser = subparsers.add_parser("doctor", help="Diagnostic commands.")
    doctor_subparsers = doctor_parser.add_subparsers(dest="doctor_command", required=True)

    create_parser = task_subparsers.add_parser("create", help="Create a task.")
    create_parser.add_argument("--title", required=True, help="Short task title.")
    create_parser.add_argument("--goal", required=True, help="Concrete task goal.")
    create_parser.add_argument(
        "--workspace-root",
        default=".",
        help="Workspace to retrieve context from. Defaults to the current directory.",
    )
    create_parser.add_argument(
        "--executor",
        default="codex",
        help="Executor to persist for the task. Defaults to codex.",
    )
    create_parser.add_argument(
        "--capability",
        action="append",
        default=[],
        help="Capability reference to persist with the task, for example profile:baseline_local or validator:run_output_validation. Repeatable.",
    )
    create_parser.add_argument(
        "--route-mode",
        default="auto",
        choices=["auto", "live", "deterministic", "offline", "summary"],
        help="Routing policy mode to persist for the task. Defaults to auto.",
    )

    run_parser = task_subparsers.add_parser("run", help="Run a task through the current workflow loop.")
    run_parser.add_argument("task_id", help="Task identifier.")
    run_parser.add_argument(
        "--executor",
        default=None,
        help="Override the task executor for this run.",
    )
    run_parser.add_argument(
        "--capability",
        action="append",
        default=[],
        help="Override the task capability manifest for this run with repeatable kind:ref entries.",
    )
    run_parser.add_argument(
        "--route-mode",
        default=None,
        choices=["auto", "live", "deterministic", "offline", "summary"],
        help="Override the task routing policy mode for this run.",
    )

    list_parser = task_subparsers.add_parser("list", help="List tasks with compact status summaries.")
    list_parser.add_argument(
        "--focus",
        default="all",
        choices=["all", "active", "failed", "needs-review", "recent"],
        help="Restrict the list to a simple operator attention view. Defaults to all.",
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of tasks to print after filtering.",
    )
    inspect_parser = task_subparsers.add_parser("inspect", help="Print a compact per-task overview.")
    inspect_parser.add_argument("task_id", help="Task identifier.")
    capabilities_parser = task_subparsers.add_parser("capabilities", help="Print the task capability assembly summary.")
    capabilities_parser.add_argument("task_id", help="Task identifier.")
    review_parser = task_subparsers.add_parser("review", help="Print a review-focused task handoff summary.")
    review_parser.add_argument("task_id", help="Task identifier.")
    artifacts_parser = task_subparsers.add_parser("artifacts", help="Print grouped task artifact paths.")
    artifacts_parser.add_argument("task_id", help="Task identifier.")

    summarize_parser = task_subparsers.add_parser("summarize", help="Print the task summary artifact.")
    summarize_parser.add_argument("task_id", help="Task identifier.")

    resume_note_parser = task_subparsers.add_parser(
        "resume-note",
        help="Print the task resume note artifact.",
    )
    resume_note_parser.add_argument("task_id", help="Task identifier.")
    validation_parser = task_subparsers.add_parser("validation", help="Print the task validation report artifact.")
    validation_parser.add_argument("task_id", help="Task identifier.")
    compatibility_parser = task_subparsers.add_parser(
        "compatibility",
        help="Print the task compatibility report artifact.",
    )
    compatibility_parser.add_argument("task_id", help="Task identifier.")
    grounding_parser = task_subparsers.add_parser("grounding", help="Print the task source grounding artifact.")
    grounding_parser.add_argument("task_id", help="Task identifier.")
    retrieval_parser = task_subparsers.add_parser("retrieval", help="Print the task retrieval report artifact.")
    retrieval_parser.add_argument("task_id", help="Task identifier.")
    topology_parser = task_subparsers.add_parser("topology", help="Print the task topology report artifact.")
    topology_parser.add_argument("task_id", help="Task identifier.")
    dispatch_parser = task_subparsers.add_parser("dispatch", help="Print the task dispatch report artifact.")
    dispatch_parser.add_argument("task_id", help="Task identifier.")
    handoff_parser = task_subparsers.add_parser("handoff", help="Print the task handoff report artifact.")
    handoff_parser.add_argument("task_id", help="Task identifier.")
    execution_fit_parser = task_subparsers.add_parser(
        "execution-fit",
        help="Print the task execution-fit report artifact.",
    )
    execution_fit_parser.add_argument("task_id", help="Task identifier.")
    memory_parser = task_subparsers.add_parser("memory", help="Print the task memory record.")
    memory_parser.add_argument("task_id", help="Task identifier.")
    route_parser = task_subparsers.add_parser("route", help="Print the task route report artifact.")
    route_parser.add_argument("task_id", help="Task identifier.")
    compatibility_json_parser = task_subparsers.add_parser(
        "compatibility-json",
        help="Print the task compatibility record.",
    )
    compatibility_json_parser.add_argument("task_id", help="Task identifier.")
    route_json_parser = task_subparsers.add_parser("route-json", help="Print the task route record.")
    route_json_parser.add_argument("task_id", help="Task identifier.")
    topology_json_parser = task_subparsers.add_parser("topology-json", help="Print the task topology record.")
    topology_json_parser.add_argument("task_id", help="Task identifier.")
    dispatch_json_parser = task_subparsers.add_parser("dispatch-json", help="Print the task dispatch record.")
    dispatch_json_parser.add_argument("task_id", help="Task identifier.")
    handoff_json_parser = task_subparsers.add_parser("handoff-json", help="Print the task handoff record.")
    handoff_json_parser.add_argument("task_id", help="Task identifier.")
    execution_fit_json_parser = task_subparsers.add_parser(
        "execution-fit-json",
        help="Print the task execution-fit record.",
    )
    execution_fit_json_parser.add_argument("task_id", help="Task identifier.")
    capabilities_json_parser = task_subparsers.add_parser(
        "capabilities-json",
        help="Print the task capability assembly record.",
    )
    capabilities_json_parser.add_argument("task_id", help="Task identifier.")
    retrieval_json_parser = task_subparsers.add_parser("retrieval-json", help="Print the task retrieval record.")
    retrieval_json_parser.add_argument("task_id", help="Task identifier.")

    doctor_subparsers.add_parser("codex", help="Run a minimal Codex executor preflight.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    base_dir = Path(args.base_dir).resolve()

    if args.command == "task" and args.task_command == "create":
        state = create_task(
            base_dir=base_dir,
            title=args.title.strip(),
            goal=args.goal.strip(),
            workspace_root=Path(args.workspace_root).resolve(),
            executor_name=args.executor.strip(),
            capability_refs=args.capability,
            route_mode=args.route_mode,
        )
        print(state.task_id)
        return 0

    if args.command == "task" and args.task_command == "run":
        state = run_task(
            base_dir=base_dir,
            task_id=args.task_id,
            executor_name=args.executor,
            capability_refs=args.capability,
            route_mode=args.route_mode,
        )
        print(f"{state.task_id} {state.status} retrieval={state.retrieval_count}")
        return 0

    if args.command == "task" and args.task_command == "list":
        states = sorted(
            iter_task_states(base_dir),
            key=lambda state: (state.updated_at, state.task_id),
            reverse=True,
        )
        states = filter_task_states(states, args.focus)
        if args.limit is not None:
            states = states[: max(args.limit, 0)]
        print(f"task_id\tstatus\tphase\tattempt\tupdated_at\ttitle\tfocus={args.focus}")
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

    if args.command == "task" and args.task_command == "inspect":
        state = load_state(base_dir, args.task_id)

        def load_json_if_exists(path: Path) -> dict[str, object]:
            if not path.exists():
                return {}
            return json.loads(path.read_text(encoding="utf-8"))

        compatibility = load_json_if_exists(compatibility_path(base_dir, args.task_id))
        topology = load_json_if_exists(topology_path(base_dir, args.task_id))
        dispatch = load_json_if_exists(dispatch_path(base_dir, args.task_id))
        handoff = load_json_if_exists(handoff_path(base_dir, args.task_id))
        execution_fit = load_json_if_exists(execution_fit_path(base_dir, args.task_id))
        retrieval = load_json_if_exists(retrieval_path(base_dir, args.task_id))

        lines = [
            f"Task Overview: {state.task_id}",
            f"title: {state.title}",
            f"goal: {state.goal}",
            "",
            "State",
            f"status: {state.status}",
            f"phase: {state.phase}",
            f"updated_at: {state.updated_at}",
            f"attempt_id: {state.current_attempt_id or '-'}",
            f"attempt_number: {state.current_attempt_number or 0}",
            f"execution_lifecycle: {state.execution_lifecycle}",
            "",
            "Route And Topology",
            f"route_mode: {state.route_mode}",
            f"route_name: {state.route_name}",
            f"route_backend: {state.route_backend}",
            f"route_execution_site: {state.route_execution_site}",
            f"topology_execution_site: {topology.get('execution_site', state.topology_execution_site)}",
            f"topology_transport_kind: {topology.get('transport_kind', state.topology_transport_kind)}",
            f"topology_dispatch_status: {topology.get('dispatch_status', state.topology_dispatch_status)}",
            "",
            "Checks",
            f"compatibility_status: {compatibility.get('status', 'pending')}",
            f"execution_fit_status: {execution_fit.get('status', 'pending')}",
            f"validation_status: {load_json_if_exists(Path(state.artifact_paths.get('validation_json', ''))).get('status', 'pending') if state.artifact_paths.get('validation_json') else 'pending'}",
            "",
            "Retrieval And Memory",
            f"retrieval_count: {state.retrieval_count}",
            f"retrieval_record_available: {'yes' if isinstance(retrieval, list) and bool(retrieval) else 'no'}",
            f"grounding_available: {'yes' if state.artifact_paths.get('source_grounding') else 'no'}",
            f"memory_available: {'yes' if memory_path(base_dir, args.task_id).exists() else 'no'}",
            "",
            "Operator Guidance",
            f"handoff_status: {handoff.get('status', 'pending')}",
            f"blocking_reason: {handoff.get('blocking_reason', '') or '-'}",
            f"next_operator_action: {handoff.get('next_operator_action', 'Inspect task artifacts.')}",
            "",
            "Artifacts",
            f"summary: {state.artifact_paths.get('summary', '-')}",
            f"resume_note: {state.artifact_paths.get('resume_note', '-')}",
            f"route_report: {state.artifact_paths.get('route_report', '-')}",
            f"topology_report: {state.artifact_paths.get('topology_report', '-')}",
            f"dispatch_report: {state.artifact_paths.get('dispatch_report', '-')}",
            f"handoff_report: {state.artifact_paths.get('handoff_report', '-')}",
            f"retrieval_report: {state.artifact_paths.get('retrieval_report', '-')}",
            f"validation_report: {state.artifact_paths.get('validation_report', '-')}",
        ]
        print("\n".join(lines))
        return 0

    if args.command == "task" and args.task_command == "capabilities":
        state = load_state(base_dir, args.task_id)
        manifest = json.loads(capability_manifest_path(base_dir, args.task_id).read_text(encoding="utf-8"))
        assembly = json.loads(capability_assembly_path(base_dir, args.task_id).read_text(encoding="utf-8"))
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

    if args.command == "task" and args.task_command == "review":
        state = load_state(base_dir, args.task_id)

        def load_json_if_exists(path: Path) -> dict[str, object]:
            if not path.exists():
                return {}
            return json.loads(path.read_text(encoding="utf-8"))

        handoff = load_json_if_exists(handoff_path(base_dir, args.task_id))
        compatibility = load_json_if_exists(compatibility_path(base_dir, args.task_id))
        execution_fit = load_json_if_exists(execution_fit_path(base_dir, args.task_id))
        validation = load_json_if_exists(Path(state.artifact_paths.get("validation_json", ""))) if state.artifact_paths.get("validation_json") else {}
        lines = [
            f"Task Review: {state.task_id}",
            f"title: {state.title}",
            "",
            "Latest Attempt",
            f"attempt_id: {state.current_attempt_id or '-'}",
            f"attempt_number: {state.current_attempt_number or 0}",
            f"status: {state.status}",
            f"executor_status: {state.executor_status}",
            f"execution_lifecycle: {state.execution_lifecycle}",
            "",
            "Handoff",
            f"handoff_status: {handoff.get('status', 'pending')}",
            f"blocking_reason: {handoff.get('blocking_reason', '') or '-'}",
            f"next_operator_action: {handoff.get('next_operator_action', 'Review resume_note.md and summary.md.')}",
            "",
            "Checks",
            f"compatibility_status: {compatibility.get('status', 'pending')}",
            f"execution_fit_status: {execution_fit.get('status', 'pending')}",
            f"validation_status: {validation.get('status', 'pending')}",
            "",
            "Review Artifacts",
            f"resume_note: {state.artifact_paths.get('resume_note', '-')}",
            f"summary: {state.artifact_paths.get('summary', '-')}",
            f"handoff_report: {state.artifact_paths.get('handoff_report', '-')}",
            f"validation_report: {state.artifact_paths.get('validation_report', '-')}",
            f"compatibility_report: {state.artifact_paths.get('compatibility_report', '-')}",
            f"execution_fit_report: {state.artifact_paths.get('execution_fit_report', '-')}",
        ]
        print("\n".join(lines))
        return 0

    if args.command == "task" and args.task_command == "artifacts":
        state = load_state(base_dir, args.task_id)
        print(build_grouped_artifact_index(state.artifact_paths), end="")
        return 0

    if args.command == "task" and args.task_command in {
        "summarize",
        "resume-note",
        "validation",
        "compatibility",
        "grounding",
        "retrieval",
        "topology",
        "dispatch",
        "handoff",
        "execution-fit",
        "route",
    }:
        artifact_name = {
            "summarize": "summary.md",
            "resume-note": "resume_note.md",
            "validation": "validation_report.md",
            "compatibility": "compatibility_report.md",
            "grounding": "source_grounding.md",
            "retrieval": "retrieval_report.md",
            "topology": "topology_report.md",
            "dispatch": "dispatch_report.md",
            "handoff": "handoff_report.md",
            "execution-fit": "execution_fit_report.md",
            "route": "route_report.md",
        }[args.task_command]
        print((artifacts_dir(base_dir, args.task_id) / artifact_name).read_text(encoding="utf-8"), end="")
        return 0

    if args.command == "task" and args.task_command == "memory":
        print(json.dumps(json.loads(memory_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "compatibility-json":
        print(json.dumps(json.loads(compatibility_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "route-json":
        print(json.dumps(json.loads(route_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "topology-json":
        print(json.dumps(json.loads(topology_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "dispatch-json":
        print(json.dumps(json.loads(dispatch_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "handoff-json":
        print(json.dumps(json.loads(handoff_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "execution-fit-json":
        print(json.dumps(json.loads(execution_fit_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "capabilities-json":
        print(json.dumps(json.loads(capability_assembly_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "task" and args.task_command == "retrieval-json":
        print(json.dumps(json.loads(retrieval_path(base_dir, args.task_id).read_text(encoding="utf-8")), indent=2))
        return 0

    if args.command == "doctor" and args.doctor_command == "codex":
        exit_code, result = diagnose_codex()
        print(format_codex_doctor_result(result))
        return exit_code

    parser.error("Unsupported command.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
