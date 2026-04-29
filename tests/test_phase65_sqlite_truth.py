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
    load_mps_policy,
    register_mps_policy_proposal,
    register_policy_proposal,
    register_route_metadata_proposal,
)
from swallow.models import AuditTriggerPolicy, RouteCapabilities, RouteSpec, TaxonomyProfile
from swallow.paths import route_registry_path, swallow_db_path
from swallow.router import (
    apply_route_registry,
    load_default_route_policy,
    load_default_route_registry,
    load_route_capability_profiles,
    load_route_policy,
    load_route_registry,
    load_route_weights,
    route_by_name,
    save_route_registry,
)
from swallow.sqlite_store import get_connection
from swallow.mps_policy_store import MPS_ROUND_LIMIT_KIND


def _custom_route(
    *,
    name: str = "phase65-route",
    model_hint: str = "roundtrip-model",
    weight: float = 0.73,
    scores: dict[str, float] | None = None,
) -> RouteSpec:
    return RouteSpec(
        name=name,
        executor_name="phase65-executor",
        backend_kind="http_api",
        model_hint=model_hint,
        dialect_hint="plain_text",
        fallback_route_name="",
        quality_weight=weight,
        task_family_scores=scores or {"review": 0.91, "execution": 0.44},
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


def _modified_default_registry(*, model_hint: str = "phase65-mutated-model") -> dict[str, dict[str, object]]:
    payload = load_default_route_registry()
    payload["local-codex"] = dict(payload["local-codex"])
    payload["local-codex"]["model_hint"] = model_hint
    return payload


def _modified_default_route_policy() -> dict[str, object]:
    payload = load_default_route_policy()
    payload["summary_fallback_route_name"] = "local-codex"
    return payload


def _assert_default_route_state(base_dir: Path) -> None:
    default_registry = load_default_route_registry()
    assert load_route_registry(base_dir)["local-codex"]["model_hint"] == default_registry["local-codex"]["model_hint"]
    route = route_by_name("local-codex")
    assert route is not None
    assert route.model_hint == default_registry["local-codex"]["model_hint"]
    assert load_route_policy(base_dir) == load_default_route_policy()
    assert load_route_weights(base_dir)["local-codex"] == 1.0
    assert load_route_capability_profiles(base_dir).get("local-codex") is None


def _raise_once_after(original, message: str):
    state = {"raised": False}

    def wrapped(*args, **kwargs):
        result = original(*args, **kwargs)
        if not state["raised"]:
            state["raised"] = True
            raise RuntimeError(message)
        return result

    return wrapped


def _write_review_record(base_dir: Path, *, route_name: str = "local-codex", weight: float = 0.42) -> Path:
    review_path = base_dir / "review.json"
    review_path.write_text(
        json.dumps(
            {
                "kind": "optimization_proposal_review",
                "review_id": "phase65-review",
                "reviewed_at": "2026-04-30T00:00:00+00:00",
                "decision": "approved",
                "source_bundle_path": "",
                "source_bundle_id": "phase65-bundle",
                "reviewer": "swl_cli",
                "note": "Phase 65 artifact failure regression.",
                "entries": [
                    {
                        "proposal_id": "proposal-route-weight",
                        "proposal_type": "route_weight",
                        "route_name": route_name,
                        "task_family": None,
                        "decision": "approved",
                        "description": "Adjust route weight.",
                        "suggested_action": "set route weight",
                        "note": "",
                        "severity": "info",
                        "priority": "info",
                        "rationale": "regression fixture",
                        "suggested_weight": weight,
                        "suggested_task_family_score": None,
                        "mark_task_family_unsupported": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return review_path


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


def test_route_registry_round_trip_with_non_trivial_capability_profiles(tmp_path: Path) -> None:
    task_families = ("planning", "execution", "review", "synthesis", "retrieval")
    route_payload = {
        f"phase65-route-{index}": _custom_route(
            name=f"phase65-route-{index}",
            model_hint=f"roundtrip-model-{index}",
            weight=round(0.6 + index / 10, 2),
            scores={
                task_family: round(0.5 + index / 10 + score_index / 100, 3)
                for score_index, task_family in enumerate(task_families, start=1)
            },
        ).to_dict()
        for index in range(1, 4)
    }

    try:
        register_route_metadata_proposal(
            base_dir=tmp_path,
            proposal_id="route-non-trivial-roundtrip",
            route_registry=route_payload,
        )
        apply_proposal(
            "route-non-trivial-roundtrip",
            OperatorToken(source="cli"),
            ProposalTarget.ROUTE_METADATA,
        )

        loaded = load_route_registry(tmp_path)
        profiles = load_route_capability_profiles(tmp_path)
        rows = get_connection(tmp_path).execute(
            "SELECT target_kind, before_payload, after_payload FROM route_change_log"
        ).fetchall()
        after_payload = json.loads(str(rows[0]["after_payload"]))

        assert loaded == route_payload
        assert set(profiles) == set(route_payload)
        assert len(rows) == 1
        assert str(rows[0]["target_kind"]) == "route_registry"
        assert isinstance(json.loads(str(rows[0]["before_payload"])), dict)
        assert set(after_payload) == set(route_payload)
        for route_name, route in route_payload.items():
            assert len(profiles[route_name]["task_family_scores"]) == 5
            assert profiles[route_name]["task_family_scores"] == route["task_family_scores"]
            assert after_payload[route_name]["task_family_scores"] == route["task_family_scores"]
    finally:
        save_route_registry(tmp_path, load_default_route_registry())
        apply_route_registry(tmp_path)


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


def test_route_metadata_transaction_rolls_back_when_registry_save_fails_before_upsert(tmp_path: Path) -> None:
    apply_route_registry(tmp_path)
    register_route_metadata_proposal(
        base_dir=tmp_path,
        proposal_id="route-registry-before-upsert",
        route_registry=_modified_default_registry(),
    )

    with patch("swallow.truth.route.save_route_registry", side_effect=RuntimeError("registry failed")):
        with pytest.raises(RuntimeError, match="registry failed"):
            apply_proposal("route-registry-before-upsert", OperatorToken(source="cli"), ProposalTarget.ROUTE_METADATA)

    _assert_default_route_state(tmp_path)
    assert _route_change_count(tmp_path) == 0


def test_route_metadata_transaction_rolls_back_when_policy_save_fails_after_registry_upsert(tmp_path: Path) -> None:
    apply_route_registry(tmp_path)
    register_route_metadata_proposal(
        base_dir=tmp_path,
        proposal_id="route-policy-after-registry",
        route_registry=_modified_default_registry(),
        route_policy=_modified_default_route_policy(),
    )

    with patch("swallow.truth.route.save_route_policy", side_effect=RuntimeError("policy failed")):
        with pytest.raises(RuntimeError, match="policy failed"):
            apply_proposal("route-policy-after-registry", OperatorToken(source="cli"), ProposalTarget.ROUTE_METADATA)

    _assert_default_route_state(tmp_path)
    assert _route_change_count(tmp_path) == 0


def test_route_metadata_transaction_rolls_back_when_weights_save_fails_after_policy_upsert(tmp_path: Path) -> None:
    apply_route_registry(tmp_path)
    register_route_metadata_proposal(
        base_dir=tmp_path,
        proposal_id="route-weights-after-policy",
        route_policy=_modified_default_route_policy(),
        route_weights={"local-codex": 0.22},
    )

    with patch("swallow.truth.route.save_route_weights", side_effect=RuntimeError("weights failed")):
        with pytest.raises(RuntimeError, match="weights failed"):
            apply_proposal("route-weights-after-policy", OperatorToken(source="cli"), ProposalTarget.ROUTE_METADATA)

    _assert_default_route_state(tmp_path)
    assert _route_change_count(tmp_path) == 0


def test_route_metadata_transaction_rolls_back_when_capability_apply_fails_after_upsert(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import swallow.truth.route as route_truth

    apply_route_registry(tmp_path)
    monkeypatch.setattr(
        route_truth,
        "apply_route_capability_profiles",
        _raise_once_after(route_truth.apply_route_capability_profiles, "capability apply failed"),
    )
    register_route_metadata_proposal(
        base_dir=tmp_path,
        proposal_id="route-capability-after-upsert",
        route_capability_profiles={
            "local-codex": {
                "task_family_scores": {"execution": 0.81},
                "unsupported_task_types": ["review"],
            }
        },
    )

    with pytest.raises(RuntimeError, match="capability apply failed"):
        apply_proposal("route-capability-after-upsert", OperatorToken(source="cli"), ProposalTarget.ROUTE_METADATA)

    _assert_default_route_state(tmp_path)
    assert _route_change_count(tmp_path) == 0


def test_route_metadata_transaction_rolls_back_when_in_memory_weight_apply_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import swallow.truth.route as route_truth

    apply_route_registry(tmp_path)
    monkeypatch.setattr(
        route_truth,
        "apply_route_weights",
        _raise_once_after(route_truth.apply_route_weights, "weight apply failed"),
    )
    register_route_metadata_proposal(
        base_dir=tmp_path,
        proposal_id="route-weight-in-memory-failure",
        route_weights={"local-codex": 0.24},
    )

    with pytest.raises(RuntimeError, match="weight apply failed"):
        apply_proposal("route-weight-in-memory-failure", OperatorToken(source="cli"), ProposalTarget.ROUTE_METADATA)

    _assert_default_route_state(tmp_path)
    assert _route_change_count(tmp_path) == 0


def test_route_metadata_transaction_rolls_back_when_audit_insert_fails_after_insert(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import swallow.truth.route as route_truth

    apply_route_registry(tmp_path)
    monkeypatch.setattr(
        route_truth,
        "_write_route_change_logs",
        _raise_once_after(route_truth._write_route_change_logs, "route audit failed"),
    )
    register_route_metadata_proposal(
        base_dir=tmp_path,
        proposal_id="route-audit-after-insert",
        route_weights={"local-codex": 0.25},
    )

    with pytest.raises(RuntimeError, match="route audit failed"):
        apply_proposal("route-audit-after-insert", OperatorToken(source="cli"), ProposalTarget.ROUTE_METADATA)

    _assert_default_route_state(tmp_path)
    assert _route_change_count(tmp_path) == 0


def test_route_metadata_commit_survives_caller_exception_after_commit(tmp_path: Path) -> None:
    register_route_metadata_proposal(
        base_dir=tmp_path,
        proposal_id="route-caller-after-commit",
        route_weights={"local-codex": 0.31},
    )

    with patch("swallow.governance._emit_event", side_effect=RuntimeError("caller failed")):
        with pytest.raises(RuntimeError, match="caller failed"):
            apply_proposal("route-caller-after-commit", OperatorToken(source="cli"), ProposalTarget.ROUTE_METADATA)

    assert load_route_weights(tmp_path)["local-codex"] == 0.31
    assert route_by_name("local-codex").quality_weight == 0.31
    assert _route_change_count(tmp_path) == 1


def test_route_review_artifact_write_failure_logs_warning_after_sqlite_commit(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    review_path = _write_review_record(tmp_path, weight=0.43)
    register_route_metadata_proposal(
        base_dir=tmp_path,
        proposal_id="route-review-artifact-failure",
        review_path=review_path,
    )

    with patch("swallow.meta_optimizer._write_json", side_effect=OSError("disk full")):
        with caplog.at_level("WARNING", logger="swallow.governance"):
            result = apply_proposal(
                "route-review-artifact-failure",
                OperatorToken(source="cli"),
                ProposalTarget.ROUTE_METADATA,
            )

    assert result.success is True
    assert load_route_weights(tmp_path)["local-codex"] == 0.43
    assert route_by_name("local-codex").quality_weight == 0.43
    assert _route_change_count(tmp_path) == 2
    assert isinstance(result.payload, tuple)
    assert not result.payload[1].exists()
    assert "SQLite truth already committed" in caplog.text


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


def test_policy_transaction_rolls_back_when_audit_trigger_save_fails_after_upsert(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import swallow.truth.policy as policy_truth

    policy = AuditTriggerPolicy(enabled=True, trigger_on_degraded=False, auditor_route="http-qwen")
    monkeypatch.setattr(
        policy_truth,
        "save_audit_trigger_policy",
        _raise_once_after(policy_truth.save_audit_trigger_policy, "audit policy save failed"),
    )
    register_policy_proposal(
        base_dir=tmp_path,
        proposal_id="policy-audit-trigger-after-upsert",
        audit_trigger_policy=policy,
    )

    with pytest.raises(RuntimeError, match="audit policy save failed"):
        apply_proposal("policy-audit-trigger-after-upsert", OperatorToken(source="cli"), ProposalTarget.POLICY)

    assert load_audit_trigger_policy(tmp_path).to_dict() == AuditTriggerPolicy().to_dict()
    assert _policy_change_count(tmp_path) == 0


def test_policy_transaction_rolls_back_when_mps_save_fails_after_upsert(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import swallow.truth.policy as policy_truth

    monkeypatch.setattr(
        policy_truth,
        "save_mps_policy",
        _raise_once_after(policy_truth.save_mps_policy, "mps policy save failed"),
    )
    register_mps_policy_proposal(
        base_dir=tmp_path,
        proposal_id="policy-mps-after-upsert",
        kind=MPS_ROUND_LIMIT_KIND,
        value=2,
    )

    with pytest.raises(RuntimeError, match="mps policy save failed"):
        apply_proposal("policy-mps-after-upsert", OperatorToken(source="cli"), ProposalTarget.POLICY)

    assert load_mps_policy(tmp_path, MPS_ROUND_LIMIT_KIND) is None
    assert _policy_change_count(tmp_path) == 0


def test_policy_transaction_rolls_back_when_after_payload_capture_fails_after_upsert(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import swallow.truth.policy as policy_truth

    state = {"calls": 0}
    original_payload_reader = policy_truth._policy_record_payload

    def fail_after_upsert(connection, policy_id: str):
        result = original_payload_reader(connection, policy_id)
        state["calls"] += 1
        if state["calls"] == 2:
            raise RuntimeError("policy after payload failed")
        return result

    policy = AuditTriggerPolicy(enabled=True, trigger_on_degraded=False, auditor_route="http-qwen")
    monkeypatch.setattr(policy_truth, "_policy_record_payload", fail_after_upsert)
    register_policy_proposal(
        base_dir=tmp_path,
        proposal_id="policy-after-payload-failure",
        audit_trigger_policy=policy,
    )

    with pytest.raises(RuntimeError, match="policy after payload failed"):
        apply_proposal("policy-after-payload-failure", OperatorToken(source="cli"), ProposalTarget.POLICY)

    assert load_audit_trigger_policy(tmp_path).to_dict() == AuditTriggerPolicy().to_dict()
    assert _policy_change_count(tmp_path) == 0


def test_policy_transaction_rolls_back_when_audit_insert_fails_after_insert(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import swallow.truth.policy as policy_truth

    policy = AuditTriggerPolicy(enabled=True, trigger_on_degraded=False, auditor_route="http-qwen")
    monkeypatch.setattr(
        policy_truth,
        "_write_policy_change_log",
        _raise_once_after(policy_truth._write_policy_change_log, "policy audit failed"),
    )
    register_policy_proposal(
        base_dir=tmp_path,
        proposal_id="policy-audit-after-insert",
        audit_trigger_policy=policy,
    )

    with pytest.raises(RuntimeError, match="policy audit failed"):
        apply_proposal("policy-audit-after-insert", OperatorToken(source="cli"), ProposalTarget.POLICY)

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
