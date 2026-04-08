from __future__ import annotations

import argparse
import json
from pathlib import Path

from .doctor import diagnose_codex, format_codex_doctor_result
from .orchestrator import create_task, run_task
from .paths import (
    artifacts_dir,
    compatibility_path,
    dispatch_path,
    execution_fit_path,
    handoff_path,
    memory_path,
    retrieval_path,
    route_path,
    topology_path,
)


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

    task_parser = subparsers.add_parser("task", help="Task lifecycle commands.")
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
        "--route-mode",
        default=None,
        choices=["auto", "live", "deterministic", "offline", "summary"],
        help="Override the task routing policy mode for this run.",
    )

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
            route_mode=args.route_mode,
        )
        print(state.task_id)
        return 0

    if args.command == "task" and args.task_command == "run":
        state = run_task(base_dir=base_dir, task_id=args.task_id, executor_name=args.executor, route_mode=args.route_mode)
        print(f"{state.task_id} {state.status} retrieval={state.retrieval_count}")
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
