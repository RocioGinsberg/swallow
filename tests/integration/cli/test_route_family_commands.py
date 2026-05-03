from __future__ import annotations

import json
from pathlib import Path

from swallow.orchestration.orchestrator import create_task
from swallow.provider_router import route_policy as route_policy_module
from swallow.provider_router import route_registry as route_registry_module
from swallow.provider_router.router import load_route_policy, load_route_registry
from tests.helpers.cli_runner import run_cli


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def test_route_registry_show_apply_characterization_stdout_stderr_exit_code(tmp_path: Path) -> None:
    default_registry = route_registry_module.load_default_route_registry()
    registry_file = tmp_path / "route-registry.json"
    _write_json(registry_file, default_registry)

    show_before = run_cli(tmp_path, "route", "registry", "show")
    show_before.assert_success()
    assert show_before.stderr == ""
    assert "# Route Registry" in show_before.stdout
    assert "local-codex" in show_before.stdout

    apply_result = run_cli(tmp_path, "route", "registry", "apply", str(registry_file))
    apply_result.assert_success()
    assert apply_result.stderr == ""
    assert "# Route Registry" in apply_result.stdout
    assert load_route_registry(tmp_path) == default_registry


def test_route_policy_show_apply_characterization_stdout_stderr_exit_code(tmp_path: Path) -> None:
    default_policy = route_policy_module.load_default_route_policy()
    policy_file = tmp_path / "route-policy.json"
    _write_json(policy_file, default_policy)

    show_before = run_cli(tmp_path, "route", "policy", "show")
    show_before.assert_success()
    assert show_before.stderr == ""
    assert "# Route Policy" in show_before.stdout
    assert "- summary_fallback_route_name:" in show_before.stdout

    apply_result = run_cli(tmp_path, "route", "policy", "apply", str(policy_file))
    apply_result.assert_success()
    assert apply_result.stderr == ""
    assert "# Route Policy" in apply_result.stdout
    assert load_route_policy(tmp_path) == default_policy


def test_route_select_characterization_stdout_stderr_exit_code(tmp_path: Path) -> None:
    state = create_task(
        base_dir=tmp_path,
        title="Route select baseline",
        goal="Freeze route selection output before CLI migration.",
        workspace_root=tmp_path,
        complexity_hint="high",
    )

    result = run_cli(tmp_path, "route", "select", "--task-id", state.task_id)

    result.assert_success()
    assert result.stderr == ""
    assert "Route Selection" in result.stdout
    assert f"- task_id: {state.task_id}" in result.stdout
    assert "- selected_route: local-claude-code" in result.stdout
