from __future__ import annotations

from swallow.orchestration.models import CompatibilityFinding, CompatibilityResult, ExecutorResult, TaskState


def evaluate_route_compatibility(state: TaskState, executor_result: ExecutorResult) -> CompatibilityResult:
    findings: list[CompatibilityFinding] = []
    capabilities = state.route_capabilities or {}
    route_mode = state.route_mode or "auto"

    findings.append(
        CompatibilityFinding(
            code="route.declared",
            level="pass",
            message="Route selection is declared for this run.",
            details={
                "route_name": state.route_name,
                "route_backend": state.route_backend,
                "executor_name": state.executor_name,
            },
        )
    )

    if executor_result.executor_name == state.executor_name:
        findings.append(
            CompatibilityFinding(
                code="executor.route_aligned",
                level="pass",
                message="Executor output aligns with the selected route executor.",
                details={
                    "executor_name": executor_result.executor_name,
                    "route_name": state.route_name,
                },
            )
        )
    else:
        findings.append(
            CompatibilityFinding(
                code="executor.route_mismatch",
                level="fail",
                message="Executor output did not match the selected route executor.",
                details={
                    "executor_name": executor_result.executor_name,
                    "expected_executor_name": state.executor_name,
                    "route_name": state.route_name,
                },
            )
        )

    findings.extend(_mode_fit_findings(route_mode, capabilities, state))

    if any(finding.level == "fail" for finding in findings):
        status = "failed"
    elif any(finding.level == "warn" for finding in findings):
        status = "warning"
    else:
        status = "passed"

    message_map = {
        "failed": "Compatibility checks found at least one blocking route-policy mismatch.",
        "warning": "Compatibility checks passed with warnings.",
        "passed": "Compatibility checks passed.",
    }
    return CompatibilityResult(status=status, message=message_map[status], findings=findings)


def _mode_fit_findings(
    route_mode: str,
    capabilities: dict[str, object],
    state: TaskState,
) -> list[CompatibilityFinding]:
    execution_kind = str(capabilities.get("execution_kind", "unknown"))
    supports_tool_loop = bool(capabilities.get("supports_tool_loop", False))
    network_access = str(capabilities.get("network_access", "none"))
    deterministic = bool(capabilities.get("deterministic", False))
    findings: list[CompatibilityFinding] = []

    if route_mode == "live":
        if execution_kind != "code_execution":
            findings.append(
                CompatibilityFinding(
                    code="route_mode.live.execution_kind_mismatch",
                    level="fail",
                    message="Live mode requires a code-execution route.",
                    details={"route_name": state.route_name, "execution_kind": execution_kind},
                )
            )
        else:
            findings.append(
                CompatibilityFinding(
                    code="route_mode.live.execution_kind_ok",
                    level="pass",
                    message="Live mode selected a code-execution route.",
                    details={"route_name": state.route_name},
                )
            )
        if supports_tool_loop:
            findings.append(
                CompatibilityFinding(
                    code="route_mode.live.tool_loop_ok",
                    level="pass",
                    message="Live mode route supports a tool loop.",
                    details={"route_name": state.route_name},
                )
            )
        else:
            findings.append(
                CompatibilityFinding(
                    code="route_mode.live.tool_loop_missing",
                    level="fail",
                    message="Live mode requires tool-loop support.",
                    details={"route_name": state.route_name},
                )
            )
        if network_access == "none":
            findings.append(
                CompatibilityFinding(
                    code="route_mode.live.network_limited",
                    level="warn",
                    message="Live mode route does not declare any network access, so live backends may be limited.",
                    details={"route_name": state.route_name, "network_access": network_access},
                )
            )
        else:
            findings.append(
                CompatibilityFinding(
                    code="route_mode.live.network_declared",
                    level="pass",
                    message="Live mode route declares network expectations.",
                    details={"route_name": state.route_name, "network_access": network_access},
                )
            )
    elif route_mode == "deterministic":
        level = "pass" if deterministic else "fail"
        code = "route_mode.deterministic.ok" if deterministic else "route_mode.deterministic.missing"
        message = (
            "Deterministic mode selected a deterministic route."
            if deterministic
            else "Deterministic mode requires a deterministic route."
        )
        findings.append(
            CompatibilityFinding(
                code=code,
                level=level,
                message=message,
                details={"route_name": state.route_name, "deterministic": deterministic},
            )
        )
    elif route_mode == "offline":
        offline_safe = network_access == "none"
        findings.append(
            CompatibilityFinding(
                code="route_mode.offline.network_ok" if offline_safe else "route_mode.offline.network_mismatch",
                level="pass" if offline_safe else "fail",
                message=(
                    "Offline mode selected a route with no network dependency."
                    if offline_safe
                    else "Offline mode requires a route with no network dependency."
                ),
                details={"route_name": state.route_name, "network_access": network_access},
            )
        )
    elif route_mode == "summary":
        summary_safe = execution_kind == "artifact_generation"
        findings.append(
            CompatibilityFinding(
                code="route_mode.summary.execution_ok" if summary_safe else "route_mode.summary.execution_mismatch",
                level="pass" if summary_safe else "fail",
                message=(
                    "Summary mode selected an artifact-generation route."
                    if summary_safe
                    else "Summary mode requires an artifact-generation route."
                ),
                details={"route_name": state.route_name, "execution_kind": execution_kind},
            )
        )
    else:
        findings.append(
            CompatibilityFinding(
                code="route_mode.auto.deferred",
                level="pass",
                message="Automatic route mode deferred to the selected route baseline.",
                details={"route_name": state.route_name, "route_mode": route_mode},
            )
        )
    return findings


def build_compatibility_report(result: CompatibilityResult) -> str:
    lines = [
        "# Compatibility Report",
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
