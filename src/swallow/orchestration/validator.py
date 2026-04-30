from __future__ import annotations

from pathlib import Path

from swallow.orchestration.models import ExecutorResult, RetrievalItem, TaskState, ValidationFinding, ValidationResult


def validate_run_outputs(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    executor_result: ExecutorResult,
    artifact_paths: dict[str, str],
) -> ValidationResult:
    findings: list[ValidationFinding] = []
    artifact_names = [
        "executor_prompt",
        "executor_output",
        "executor_stdout",
        "executor_stderr",
        "summary",
        "resume_note",
        "compatibility_report",
        "source_grounding",
    ]

    missing_artifacts = [
        artifact_name
        for artifact_name in artifact_names
        if not artifact_paths.get(artifact_name) or not Path(artifact_paths[artifact_name]).exists()
    ]
    if missing_artifacts:
        findings.append(
            ValidationFinding(
                code="artifacts.missing",
                level="fail",
                message="Required task artifacts are missing.",
                details={"missing_artifacts": missing_artifacts},
            )
        )
    else:
        findings.append(
            ValidationFinding(
                code="artifacts.complete",
                level="pass",
                message="Required task artifacts are present.",
                details={"checked_artifacts": artifact_names},
            )
        )

    if retrieval_items:
        findings.append(
            ValidationFinding(
                code="retrieval.present",
                level="pass",
                message="Retrieval returned context for the run.",
                details={"retrieval_count": len(retrieval_items)},
            )
        )
    else:
        findings.append(
            ValidationFinding(
                code="retrieval.empty",
                level="warn",
                message="Retrieval returned no context for the run.",
                details={"retrieval_count": 0},
            )
        )

    if executor_result.status == "completed" and not (executor_result.output or "").strip():
        findings.append(
            ValidationFinding(
                code="executor.empty_output",
                level="fail",
                message="Executor reported success but produced no output.",
                details={"executor_name": executor_result.executor_name},
            )
        )
    else:
        findings.append(
            ValidationFinding(
                code="executor.consistent",
                level="pass",
                message="Executor status and output are consistent with the run result.",
                details={
                    "executor_name": executor_result.executor_name,
                    "executor_status": executor_result.status,
                    "failure_kind": executor_result.failure_kind,
                },
            )
        )

    if any(finding.level == "fail" for finding in findings):
        status = "failed"
    elif any(finding.level == "warn" for finding in findings):
        status = "warning"
    else:
        status = "passed"

    message_map = {
        "failed": "Validation found at least one blocking run issue.",
        "warning": "Validation passed with warnings.",
        "passed": "Validation passed.",
    }
    return ValidationResult(status=status, message=message_map[status], findings=findings)


def build_validation_report(result: ValidationResult) -> str:
    lines = [
        "# Validation Report",
        "",
        f"- status: {result.status}",
        f"- message: {result.message}",
        "",
        "## Findings",
    ]
    for finding in result.findings:
        lines.append(f"- [{finding.level}] {finding.code}: {finding.message}")
        if finding.details:
            details = ", ".join(f"{key}={value}" for key, value in finding.details.items())
            lines.append(f"  details: {details}")
    return "\n".join(lines)
