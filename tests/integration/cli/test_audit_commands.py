from __future__ import annotations

from pathlib import Path

from swallow.surface_tools.consistency_audit import load_audit_trigger_policy
from tests.helpers.cli_runner import run_cli


def test_audit_policy_show_set_characterization_stdout_stderr_exit_code(tmp_path: Path) -> None:
    show_before = run_cli(tmp_path, "audit", "policy", "show")

    show_before.assert_success()
    assert show_before.stderr == ""
    assert "# Audit Trigger Policy" in show_before.stdout
    assert "- enabled: no" in show_before.stdout

    set_result = run_cli(
        tmp_path,
        "audit",
        "policy",
        "set",
        "--enabled",
        "--trigger-on-degraded",
        "--trigger-on-cost-above",
        "1.25",
        "--auditor-route",
        "local-http",
    )

    set_result.assert_success()
    assert set_result.stderr == ""
    assert "# Audit Trigger Policy" in set_result.stdout
    assert "- enabled: yes" in set_result.stdout
    assert "- trigger_on_degraded: yes" in set_result.stdout
    assert "- trigger_on_cost_above: 1.250000" in set_result.stdout
    assert "- auditor_route: local-http" in set_result.stdout

    policy = load_audit_trigger_policy(tmp_path)
    assert policy.enabled is True
    assert policy.trigger_on_degraded is True
    assert policy.trigger_on_cost_above == 1.25
    assert policy.auditor_route == "local-http"
