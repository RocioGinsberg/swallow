from __future__ import annotations

from swallow.orchestration.models import ExecutionFitFinding, ExecutionFitResult, ExecutorResult, TaskState


def evaluate_execution_fit(state: TaskState, executor_result: ExecutorResult) -> ExecutionFitResult:
    findings: list[ExecutionFitFinding] = []

    if state.route_executor_family == state.topology_executor_family:
        findings.append(
            ExecutionFitFinding(
                code="executor_family.route_topology_aligned",
                level="pass",
                message="Route and topology declare the same executor family.",
                details={
                    "route_executor_family": state.route_executor_family,
                    "topology_executor_family": state.topology_executor_family,
                },
            )
        )
    else:
        findings.append(
            ExecutionFitFinding(
                code="executor_family.route_topology_mismatch",
                level="fail",
                message="Route and topology executor-family declarations do not match.",
                details={
                    "route_executor_family": state.route_executor_family,
                    "topology_executor_family": state.topology_executor_family,
                },
            )
        )

    if state.topology_executor_family == "cli":
        findings.append(
            ExecutionFitFinding(
                code="executor_family.cli_supported",
                level="pass",
                message="Current execution baseline supports the CLI executor family.",
                details={"executor_family": state.topology_executor_family},
            )
        )
    else:
        findings.append(
            ExecutionFitFinding(
                code="executor_family.unsupported",
                level="fail",
                message="Current execution baseline only supports the CLI executor family.",
                details={"executor_family": state.topology_executor_family},
            )
        )

    if state.topology_execution_site == "local":
        findings.append(
            ExecutionFitFinding(
                code="execution_site.local_declared",
                level="pass",
                message="Execution topology declares a local execution site.",
                details={"execution_site": state.topology_execution_site},
            )
        )
    elif state.topology_execution_site == "remote" and state.topology_transport_kind == "mock_remote_transport":
        findings.append(
            ExecutionFitFinding(
                code="execution_site.mock_remote_declared",
                level="pass",
                message="Execution topology declares the mock-remote execution site used for topology validation.",
                details={"execution_site": state.topology_execution_site},
            )
        )
    else:
        findings.append(
            ExecutionFitFinding(
                code="execution_site.unsupported",
                level="fail",
                message="Current baseline only supports local execution-site behavior.",
                details={"execution_site": state.topology_execution_site},
            )
        )

    if state.topology_transport_kind in {"local_process", "local_detached_process"}:
        findings.append(
            ExecutionFitFinding(
                code=(
                    "transport.local_process_declared"
                    if state.topology_transport_kind == "local_process"
                    else "transport.local_detached_process_declared"
                ),
                level="pass",
                message=(
                    "Execution topology declares the local-process transport baseline."
                    if state.topology_transport_kind == "local_process"
                    else "Execution topology declares the local-detached-process transport baseline."
                ),
                details={"transport_kind": state.topology_transport_kind},
            )
        )
    elif state.topology_transport_kind == "mock_remote_transport":
        findings.append(
            ExecutionFitFinding(
                code="transport.mock_remote_declared",
                level="pass",
                message="Execution topology declares the mock-remote transport used for topology validation.",
                details={"transport_kind": state.topology_transport_kind},
            )
        )
    else:
        findings.append(
            ExecutionFitFinding(
                code="transport.unsupported",
                level="fail",
                message="Current baseline only supports local or local-detached process transport.",
                details={"transport_kind": state.topology_transport_kind},
            )
        )

    if state.topology_dispatch_status in {"local_dispatched", "detached_dispatched", "mock_remote_dispatched"} and state.dispatch_started_at:
        findings.append(
            ExecutionFitFinding(
                code=(
                    "dispatch.local_started"
                    if state.topology_dispatch_status == "local_dispatched"
                    else "dispatch.detached_started"
                    if state.topology_dispatch_status == "detached_dispatched"
                    else "dispatch.mock_remote_started"
                ),
                level="pass",
                message=(
                    "Dispatch state is consistent with a started local execution."
                    if state.topology_dispatch_status == "local_dispatched"
                    else "Dispatch state is consistent with a started detached local execution."
                    if state.topology_dispatch_status == "detached_dispatched"
                    else "Dispatch state is consistent with a started mock-remote execution."
                ),
                details={
                    "dispatch_status": state.topology_dispatch_status,
                    "dispatch_started_at": state.dispatch_started_at,
                },
            )
        )
    else:
        findings.append(
            ExecutionFitFinding(
                code="dispatch.local_inconsistent",
                level="fail",
                message="Executor ran without a consistent local, detached, or mock-remote dispatch record.",
                details={
                    "dispatch_status": state.topology_dispatch_status,
                    "dispatch_started_at": state.dispatch_started_at,
                },
            )
        )

    if state.execution_lifecycle == "dispatched":
        findings.append(
            ExecutionFitFinding(
                code="execution_lifecycle.dispatched",
                level="pass",
                message="Execution-fit checks ran during the dispatched lifecycle state.",
                details={"execution_lifecycle": state.execution_lifecycle},
            )
        )
    else:
        findings.append(
            ExecutionFitFinding(
                code="execution_lifecycle.unexpected",
                level="warn",
                message="Execution-fit checks did not run during the dispatched lifecycle state.",
                details={"execution_lifecycle": state.execution_lifecycle, "expected": "dispatched"},
            )
        )

    if executor_result.executor_name == state.executor_name:
        findings.append(
            ExecutionFitFinding(
                code="executor.selected_route_aligned",
                level="pass",
                message="Executor output matches the selected executor for this attempt.",
                details={
                    "executor_name": executor_result.executor_name,
                    "selected_executor": state.executor_name,
                },
            )
        )
    else:
        findings.append(
            ExecutionFitFinding(
                code="executor.selected_route_mismatch",
                level="fail",
                message="Executor output does not match the selected executor for this attempt.",
                details={
                    "executor_name": executor_result.executor_name,
                    "selected_executor": state.executor_name,
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
        "failed": "Execution-fit checks found at least one blocking topology mismatch.",
        "warning": "Execution-fit checks passed with warnings.",
        "passed": "Execution-fit checks passed.",
    }
    return ExecutionFitResult(status=status, message=message_map[status], findings=findings)


def build_execution_fit_report(result: ExecutionFitResult) -> str:
    lines = [
        "# Execution Fit Report",
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
