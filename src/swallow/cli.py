from __future__ import annotations

import argparse
from pathlib import Path

from .doctor import diagnose_codex, format_codex_doctor_result
from .orchestrator import create_task, run_task
from .paths import artifacts_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="swl", description="Phase 0 AI workflow bootstrap CLI.")
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

    run_parser = task_subparsers.add_parser("run", help="Run a task through the Phase 0 loop.")
    run_parser.add_argument("task_id", help="Task identifier.")

    summarize_parser = task_subparsers.add_parser("summarize", help="Print the task summary artifact.")
    summarize_parser.add_argument("task_id", help="Task identifier.")

    resume_note_parser = task_subparsers.add_parser(
        "resume-note",
        help="Print the task resume note artifact.",
    )
    resume_note_parser.add_argument("task_id", help="Task identifier.")

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
        )
        print(state.task_id)
        return 0

    if args.command == "task" and args.task_command == "run":
        state = run_task(base_dir=base_dir, task_id=args.task_id)
        print(f"{state.task_id} {state.status} retrieval={state.retrieval_count}")
        return 0

    if args.command == "task" and args.task_command in {"summarize", "resume-note"}:
        artifact_name = "summary.md" if args.task_command == "summarize" else "resume_note.md"
        print((artifacts_dir(base_dir, args.task_id) / artifact_name).read_text(encoding="utf-8"), end="")
        return 0

    if args.command == "doctor" and args.doctor_command == "codex":
        exit_code, result = diagnose_codex()
        print(format_codex_doctor_result(result))
        return exit_code

    parser.error("Unsupported command.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
