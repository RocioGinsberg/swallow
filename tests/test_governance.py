import json

import pytest

from swallow.governance import (
    ApplyResult,
    DuplicateProposalError,
    OperatorToken,
    ProposalTarget,
    apply_proposal,
    register_canonical_proposal,
    register_mps_policy_proposal,
    register_policy_proposal,
    register_route_metadata_proposal,
)
from swallow.models import AuditTriggerPolicy
from swallow.paths import (
    audit_policy_path,
    canonical_registry_index_path,
    canonical_registry_path,
    canonical_reuse_policy_path,
    knowledge_wiki_entry_path,
    mps_policy_path,
    route_capabilities_path,
    route_weights_path,
)
from swallow.router import route_by_name


def test_operator_token_rejects_invalid_source() -> None:
    with pytest.raises(ValueError, match="Invalid operator token source"):
        OperatorToken(source="agent_side_effect")  # type: ignore[arg-type]


def test_apply_canonical_proposal_writes_registry_wiki_and_derivatives(tmp_path) -> None:
    canonical_record = {
        "canonical_id": "canonical-staged-1234",
        "canonical_key": "task-object:task-governance:knowledge-0001",
        "source_task_id": "task-governance",
        "source_object_id": "knowledge-0001",
        "promoted_at": "2026-04-28T00:00:00+00:00",
        "promoted_by": "swl_cli",
        "decision_note": "approved",
        "decision_ref": ".swl/staged_knowledge/registry.jsonl#staged-1234",
        "artifact_ref": "",
        "source_ref": "chat://governance",
        "text": "Governance promotion goes through apply_proposal.",
        "evidence_status": "source_only",
        "canonical_stage": "canonical",
        "canonical_status": "active",
        "superseded_by": "",
        "superseded_at": "",
    }
    register_canonical_proposal(
        base_dir=tmp_path,
        proposal_id="staged-1234",
        canonical_record=canonical_record,
        write_authority="operator-gated",
        refresh_derived=True,
    )

    result = apply_proposal("staged-1234", OperatorToken(source="cli"), ProposalTarget.CANONICAL_KNOWLEDGE)

    assert isinstance(result, ApplyResult)
    assert result.success is True
    assert result.applied_writes == (
        "wiki_entry",
        "canonical_registry",
        "canonical_registry_index",
        "canonical_reuse_policy",
    )
    registry_records = [
        json.loads(line)
        for line in canonical_registry_path(tmp_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    wiki_entry = json.loads(knowledge_wiki_entry_path(tmp_path, "task-governance", "knowledge-0001").read_text(encoding="utf-8"))
    registry_index = json.loads(canonical_registry_index_path(tmp_path).read_text(encoding="utf-8"))
    reuse_policy = json.loads(canonical_reuse_policy_path(tmp_path).read_text(encoding="utf-8"))

    assert registry_records == [canonical_record]
    assert wiki_entry["stage"] == "canonical"
    assert registry_index["count"] == 1
    assert reuse_policy["reuse_visible_count"] == 1


def test_apply_canonical_proposal_requires_registered_payload() -> None:
    with pytest.raises(ValueError, match="Unknown proposal artifact"):
        apply_proposal("missing", OperatorToken(source="cli"), ProposalTarget.CANONICAL_KNOWLEDGE)


def test_duplicate_proposal_id_raises(tmp_path) -> None:
    canonical_record = {
        "canonical_id": "canonical-duplicate",
        "canonical_key": "task-object:task-duplicate:knowledge-0001",
        "source_task_id": "task-duplicate",
        "source_object_id": "knowledge-0001",
        "promoted_at": "2026-04-29T00:00:00+00:00",
        "promoted_by": "swl_cli",
        "decision_note": "approved",
        "decision_ref": ".swl/staged_knowledge/registry.jsonl#staged-duplicate",
        "artifact_ref": "",
        "source_ref": "chat://governance",
        "text": "Duplicate proposals should fail fast.",
        "evidence_status": "source_only",
        "canonical_stage": "canonical",
        "canonical_status": "active",
        "superseded_by": "",
        "superseded_at": "",
    }
    register_canonical_proposal(
        base_dir=tmp_path,
        proposal_id="duplicate-proposal",
        canonical_record=canonical_record,
    )

    with pytest.raises(DuplicateProposalError, match="duplicate-proposal"):
        register_canonical_proposal(
            base_dir=tmp_path,
            proposal_id="duplicate-proposal",
            canonical_record=canonical_record,
        )


def test_apply_route_metadata_proposal_saves_and_refreshes_registry(tmp_path) -> None:
    route = route_by_name("local-codex")
    assert route is not None
    original_weight = route.quality_weight
    original_scores = dict(route.task_family_scores)
    original_unsupported = list(route.unsupported_task_types)
    try:
        register_route_metadata_proposal(
            base_dir=tmp_path,
            proposal_id="route-direct",
            route_weights={"local-codex": 0.42},
            route_capability_profiles={
                "local-codex": {
                    "task_family_scores": {"execution": 0.81},
                    "unsupported_task_types": ["review"],
                }
            },
        )

        result = apply_proposal("route-direct", OperatorToken(source="cli"), ProposalTarget.ROUTE_METADATA)

        assert result.success is True
        assert result.applied_writes == ("route_weights", "route_capability_profiles")
        persisted_weights = json.loads(route_weights_path(tmp_path).read_text(encoding="utf-8"))
        persisted_profiles = json.loads(route_capabilities_path(tmp_path).read_text(encoding="utf-8"))
        assert persisted_weights["local-codex"] == 0.42
        assert persisted_profiles["local-codex"]["task_family_scores"]["execution"] == 0.81
        assert route.quality_weight == 0.42
        assert route.task_family_scores["execution"] == 0.81
        assert route.unsupported_task_types == ["review"]
    finally:
        route.quality_weight = original_weight
        route.task_family_scores = original_scores
        route.unsupported_task_types = original_unsupported


def test_apply_policy_proposal_saves_audit_trigger_policy(tmp_path) -> None:
    policy = AuditTriggerPolicy(
        enabled=True,
        trigger_on_degraded=False,
        trigger_on_cost_above=0.75,
        auditor_route="http-qwen",
    )
    register_policy_proposal(
        base_dir=tmp_path,
        proposal_id="audit-policy",
        audit_trigger_policy=policy,
    )

    result = apply_proposal("audit-policy", OperatorToken(source="cli"), ProposalTarget.POLICY)

    assert result.success is True
    assert result.applied_writes == ("audit_trigger_policy",)
    persisted = json.loads(audit_policy_path(tmp_path).read_text(encoding="utf-8"))
    assert persisted == {
        "enabled": True,
        "trigger_on_degraded": False,
        "trigger_on_cost_above": 0.75,
        "auditor_route": "http-qwen",
    }


def test_mps_rounds_within_hard_cap(tmp_path) -> None:
    with pytest.raises(ValueError, match="mps_round_limit value must be <= 3"):
        register_mps_policy_proposal(
            base_dir=tmp_path,
            proposal_id="mps-rounds",
            kind="mps_round_limit",
            value=4,
        )


def test_apply_proposal_accepts_mps_policy_kind(tmp_path) -> None:
    register_mps_policy_proposal(
        base_dir=tmp_path,
        proposal_id="mps-participants",
        kind="mps_participant_limit",
        value=6,
    )

    result = apply_proposal("mps-participants", OperatorToken(source="cli"), ProposalTarget.POLICY)

    assert result.success is True
    assert result.applied_writes == ("mps_policy",)
    persisted = json.loads(mps_policy_path(tmp_path).read_text(encoding="utf-8"))
    assert persisted == {"mps_participant_limit": 6}
