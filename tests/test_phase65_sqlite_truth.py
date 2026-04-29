from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from swallow.cli import main
from swallow.consistency_audit import load_audit_trigger_policy
from swallow.governance import (
    OperatorToken,
    ProposalTarget,
    apply_proposal,
    register_policy_proposal,
    register_route_metadata_proposal,
)
from swallow.models import AuditTriggerPolicy, RouteCapabilities, RouteSpec, TaxonomyProfile
from swallow.paths import route_registry_path, swallow_db_path
from swallow.router import (
    apply_route_registry,
    load_default_route_registry,
    load_route_capability_profiles,
    load_route_registry,
    load_route_weights,
    route_by_name,
    save_route_registry,
)
from swallow.sqlite_store import get_connection


def _custom_route(*, model_hint: str = "roundtrip-model", weight: float = 0.73) -> RouteSpec:
    return RouteSpec(
        name="phase65-route",
        executor_name="phase65-executor",
        backend_kind="http_api",
        model_hint=model_hint,
        dialect_hint="plain_text",
        fallback_route_name="",
        quality_weight=weight,
        task_family_scores={"review": 0.91, "execution": 0.44},
        unsupported_task_types=["planning"],
        executor_family="api",
        execution_site="remote",
        remote_capable=True,
        transport_kind="http",
        capabilities=RouteCapabilities(
            execution_kind="artifact_generation",
            supports_tool_loop=False,
            filesystem_access="workspace_read",
            network_access="optional",
            deterministic=False,
            resumable=True,
        ),
        taxonomy=TaxonomyProfile(system_role="general-executor", memory_authority="task-state"),
    )


def _route_change_count(base_dir: Path) -> int:
    row = get_connection(base_dir).execute("SELECT COUNT(*) AS count FROM route_change_log").fetchone()
    return int(row["count"])


def _policy_change_count(base_dir: Path) -> int:
    row = get_connection(base_dir).execute("SELECT COUNT(*) AS count FROM policy_change_log").fetchone()
    return int(row["count"])


def test_phase65_schema_tables_and_schema_version_exist(tmp_path: Path) -> None:
    connection = get_connection(tmp_path)

    tables = {
        str(row["name"])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    route_columns = {
        str(row["name"])
        for row in connection.execute("PRAGMA table_info(route_registry)").fetchall()
    }
    version_row = connection.execute("SELECT version, slug FROM schema_version").fetchone()

    assert swallow_db_path(tmp_path).exists()
    assert {"route_registry", "policy_records", "route_change_log", "policy_change_log"}.issubset(tables)
    assert {
        "capabilities_json",
        "taxonomy_json",
        "execution_site",
        "executor_family",
        "executor_name",
        "remote_capable",
    }.issubset(route_columns)
    assert int(version_row["version"]) == 1
    assert str(version_row["slug"]) == "phase65_initial"


def test_route_registry_round_trips_full_route_spec_through_sqlite(tmp_path: Path) -> None:
    route_payload = {"phase65-route": _custom_route().to_dict()}

    save_route_registry(tmp_path, route_payload)
    loaded = load_route_registry(tmp_path)
    profiles = load_route_capability_profiles(tmp_path)

    assert loaded == route_payload
    assert profiles["phase65-route"]["task_family_scores"]["review"] == 0.91
    assert profiles["phase65-route"]["unsupported_task_types"] == ["planning"]
    assert not route_registry_path(tmp_path).exists()


def test_route_registry_reader_priority_is_sqlite_then_legacy_json_then_default(tmp_path: Path) -> None:
    legacy_payload = {"phase65-route": _custom_route(model_hint="legacy-model").to_dict()}
    route_registry_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    route_registry_path(tmp_path).write_text(json.dumps(legacy_payload), encoding="utf-8")

    first_load = load_route_registry(tmp_path)
    route_registry_path(tmp_path).write_text(
        json.dumps({"phase65-route": _custom_route(model_hint="mutated-json").to_dict()}),
        encoding="utf-8",
    )
    second_load = load_route_registry(tmp_path)

    assert first_load["phase65-route"]["model_hint"] == "legacy-model"
    assert second_load["phase65-route"]["model_hint"] == "legacy-model"

    default_base = tmp_path / "default"
    default_load = load_route_registry(default_base)
    assert default_load == load_default_route_registry()


def test_route_metadata_transaction_rolls_back_sqlite_audit_and_in_memory(tmp_path: Path) -> None:
    apply_route_registry(tmp_path)
    route = route_by_name("local-codex")
    assert route is not None
    assert load_route_weights(tmp_path)["local-codex"] == 1.0

    register_route_metadata_proposal(
        base_dir=tmp_path,
        proposal_id="route-rollback",
        route_weights={"local-codex": 0.12},
        route_capability_profiles={
            "local-codex": {
                "task_family_scores": {"execution": 0.99},
                "unsupported_task_types": ["review"],
            }
        },
    )

    with patch("swallow.truth.route.save_route_capability_profiles", side_effect=RuntimeError("injected")):
        with pytest.raises(RuntimeError, match="injected"):
            apply_proposal("route-rollback", OperatorToken(source="cli"), ProposalTarget.ROUTE_METADATA)

    assert load_route_weights(tmp_path)["local-codex"] == 1.0
    assert load_route_capability_profiles(tmp_path).get("local-codex") is None
    assert route_by_name("local-codex").quality_weight == 1.0
    assert _route_change_count(tmp_path) == 0


def test_route_metadata_success_writes_route_change_log(tmp_path: Path) -> None:
    register_route_metadata_proposal(
        base_dir=tmp_path,
        proposal_id="route-audit",
        route_weights={"local-codex": 0.66},
    )

    apply_proposal("route-audit", OperatorToken(source="cli"), ProposalTarget.ROUTE_METADATA)

    rows = get_connection(tmp_path).execute(
        "SELECT proposal_id, target_kind, before_payload, after_payload FROM route_change_log"
    ).fetchall()
    assert len(rows) == 1
    assert str(rows[0]["proposal_id"]) == "route-audit"
    assert str(rows[0]["target_kind"]) == "route_weights"
    assert json.loads(str(rows[0]["before_payload"]))["local-codex"] == 1.0
    assert json.loads(str(rows[0]["after_payload"]))["local-codex"] == 0.66


def test_policy_transaction_rolls_back_policy_record_and_audit(tmp_path: Path) -> None:
    policy = AuditTriggerPolicy(enabled=True, trigger_on_degraded=False, auditor_route="http-qwen")
    register_policy_proposal(
        base_dir=tmp_path,
        proposal_id="policy-rollback",
        audit_trigger_policy=policy,
    )

    with patch("swallow.truth.policy._write_policy_change_log", side_effect=RuntimeError("audit failed")):
        with pytest.raises(RuntimeError, match="audit failed"):
            apply_proposal("policy-rollback", OperatorToken(source="cli"), ProposalTarget.POLICY)

    assert load_audit_trigger_policy(tmp_path).to_dict() == AuditTriggerPolicy().to_dict()
    assert _policy_change_count(tmp_path) == 0


def test_policy_success_writes_policy_change_log(tmp_path: Path) -> None:
    policy = AuditTriggerPolicy(enabled=True, trigger_on_degraded=False, auditor_route="http-qwen")
    register_policy_proposal(
        base_dir=tmp_path,
        proposal_id="policy-audit",
        audit_trigger_policy=policy,
    )

    apply_proposal("policy-audit", OperatorToken(source="cli"), ProposalTarget.POLICY)

    rows = get_connection(tmp_path).execute(
        "SELECT proposal_id, target_kind, before_payload, after_payload FROM policy_change_log"
    ).fetchall()
    assert len(rows) == 1
    assert str(rows[0]["proposal_id"]) == "policy-audit"
    assert str(rows[0]["target_kind"]) == "audit_trigger_policy"
    assert json.loads(str(rows[0]["before_payload"])) is None
    assert json.loads(str(rows[0]["after_payload"]))["auditor_route"] == "http-qwen"


def test_migrate_status_reports_phase65_initial_schema(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--base-dir", str(tmp_path), "migrate", "--status"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "schema_version: 1, pending: 0"
