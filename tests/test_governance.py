import json

import pytest

from swallow.truth_governance.governance import (
    ApplyResult,
    DuplicateProposalError,
    OperatorToken,
    ProposalTarget,
    apply_proposal,
    register_canonical_proposal,
    register_mps_policy_proposal,
    register_policy_proposal,
    register_route_metadata_proposal,
    load_mps_policy,
)
from swallow.orchestration.models import AuditTriggerPolicy
from swallow.application.infrastructure.paths import (
    audit_policy_path,
    canonical_registry_index_path,
    canonical_registry_path,
    canonical_reuse_policy_path,
    knowledge_wiki_entry_path,
    mps_policy_path,
    route_capabilities_path,
    route_policy_path,
    route_registry_path,
    route_weights_path,
)
from swallow.knowledge_retrieval.knowledge_plane import (
    build_source_anchor_identity,
    list_knowledge_relations,
    load_task_knowledge_view,
)
from swallow.provider_router.router import apply_route_policy, apply_route_registry, current_route_policy, route_by_name
from swallow.provider_router.router import (
    load_route_capability_profiles,
    load_route_policy,
    load_route_registry,
    load_route_weights,
)
from swallow.application.services.consistency_audit import load_audit_trigger_policy


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


def test_apply_canonical_proposal_materializes_source_evidence_inside_apply_path(tmp_path) -> None:
    canonical_record = {
        "canonical_id": "canonical-staged-source",
        "canonical_key": "staged-candidate:staged-source",
        "source_task_id": "task-governance",
        "source_object_id": "",
        "promoted_at": "2026-04-28T00:00:00+00:00",
        "promoted_by": "swl_cli",
        "decision_note": "approved",
        "decision_ref": ".swl/staged_knowledge/registry.jsonl#staged-source",
        "artifact_ref": "",
        "source_ref": "file://workspace/source.md",
        "text": "Governance promotion carries source evidence.",
        "evidence_status": "source_only",
        "canonical_stage": "canonical",
        "canonical_status": "active",
        "superseded_by": "",
        "superseded_at": "",
        "source_pack": [
            {
                "reference": "source-1",
                "path": "source.md",
                "source_type": "raw_material",
                "source_ref": "file://workspace/source.md",
                "resolved_ref": "file://workspace/source.md",
                "resolved_path": "source.md",
                "resolution_status": "resolved",
                "line_start": 1,
                "line_end": 3,
                "content_hash": "sha256:source",
                "parser_version": "wiki-compiler-v1",
                "span": "L1-L3",
                "preview": "Source evidence preview.",
            }
        ],
        "relation_metadata": [{"relation_type": "derived_from", "target_ref": "file://workspace/source.md"}],
    }
    register_canonical_proposal(
        base_dir=tmp_path,
        proposal_id="staged-source",
        canonical_record=canonical_record,
        write_authority="operator-gated",
    )
    expected_evidence_id = build_source_anchor_identity(canonical_record["source_pack"][0])["evidence_id"]

    result = apply_proposal("staged-source", OperatorToken(source="cli"), ProposalTarget.CANONICAL_KNOWLEDGE)

    assert result.applied_writes == (
        "source_evidence_objects",
        "wiki_entry",
        "canonical_registry",
        "derived_from_relations",
    )
    assert result.payload == {
        "source_evidence_ids": [expected_evidence_id],
        "derived_relation_ids": ["relation-derived-from-staged-source-1"],
    }
    registry_records = [
        json.loads(line)
        for line in canonical_registry_path(tmp_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    view = load_task_knowledge_view(tmp_path, "task-governance")
    relations = list_knowledge_relations(tmp_path, "canonical-staged-source")

    assert registry_records[0]["source_evidence_ids"] == [expected_evidence_id]
    assert {item["object_id"] for item in view} == {expected_evidence_id, "canonical-staged-source"}
    assert relations[0]["relation_type"] == "derived_from"
    assert relations[0]["target_object_id"] == expected_evidence_id


def test_apply_canonical_proposal_supersedes_explicit_target_inside_apply_path(tmp_path) -> None:
    existing_record = {
        "canonical_id": "canonical-old",
        "canonical_key": "task-object:task-old:knowledge-old",
        "source_task_id": "task-old",
        "source_object_id": "knowledge-old",
        "promoted_at": "2026-04-27T00:00:00+00:00",
        "promoted_by": "swl_cli",
        "decision_note": "old approved",
        "decision_ref": ".swl/staged_knowledge/registry.jsonl#staged-old",
        "artifact_ref": "",
        "source_ref": "chat://old",
        "text": "Old target wiki entry.",
        "evidence_status": "source_only",
        "canonical_stage": "canonical",
        "canonical_status": "active",
        "superseded_by": "",
        "superseded_at": "",
    }
    canonical_registry_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    canonical_registry_path(tmp_path).write_text(json.dumps(existing_record) + "\n", encoding="utf-8")

    canonical_record = {
        "canonical_id": "canonical-new",
        "canonical_key": "task-object:task-new:knowledge-new",
        "source_task_id": "task-new",
        "source_object_id": "knowledge-new",
        "promoted_at": "2026-04-28T00:00:00+00:00",
        "promoted_by": "swl_cli",
        "decision_note": "new approved",
        "decision_ref": ".swl/staged_knowledge/registry.jsonl#staged-new",
        "artifact_ref": "",
        "source_ref": "chat://new",
        "text": "New superseding wiki entry.",
        "evidence_status": "source_only",
        "canonical_stage": "canonical",
        "canonical_status": "active",
        "superseded_by": "",
        "superseded_at": "",
    }
    register_canonical_proposal(
        base_dir=tmp_path,
        proposal_id="staged-new",
        canonical_record=canonical_record,
        supersede_target_ids=[" knowledge-old ", "knowledge-old"],
    )

    result = apply_proposal("staged-new", OperatorToken(source="cli"), ProposalTarget.CANONICAL_KNOWLEDGE)

    assert result.applied_writes == ("wiki_entry", "canonical_registry", "canonical_supersede_targets")
    assert result.payload == {
        "supersede_target_ids": ["knowledge-old"],
        "superseded_canonical_ids": ["canonical-old"],
    }
    assert result.detail == "canonical_applied canonical_id=canonical-new superseded_canonical_ids=canonical-old"
    registry_records = [
        json.loads(line)
        for line in canonical_registry_path(tmp_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert registry_records[0]["canonical_status"] == "superseded"
    assert registry_records[0]["superseded_by"] == "canonical-new"
    assert registry_records[0]["superseded_at"] == "2026-04-28T00:00:00+00:00"
    assert registry_records[1] == canonical_record


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
        persisted_weights = load_route_weights(tmp_path)
        persisted_profiles = load_route_capability_profiles(tmp_path)
        assert persisted_weights["local-codex"] == 0.42
        assert persisted_profiles["local-codex"]["task_family_scores"]["execution"] == 0.81
        assert not route_weights_path(tmp_path).exists()
        assert not route_capabilities_path(tmp_path).exists()
        assert route.quality_weight == 0.42
        assert route.task_family_scores["execution"] == 0.81
        assert route.unsupported_task_types == ["review"]
    finally:
        route.quality_weight = original_weight
        route.task_family_scores = original_scores
        route.unsupported_task_types = original_unsupported


def test_apply_route_metadata_proposal_saves_and_refreshes_route_registry(tmp_path) -> None:
    route = route_by_name("local-summary")
    assert route is not None
    original_model_hint = route.model_hint
    updated_registry = {
        "local-summary": {
            **route.to_dict(),
            "model_hint": "summary-governed",
        }
    }
    try:
        register_route_metadata_proposal(
            base_dir=tmp_path,
            proposal_id="route-registry",
            route_registry=updated_registry,
        )

        result = apply_proposal("route-registry", OperatorToken(source="cli"), ProposalTarget.ROUTE_METADATA)

        assert result.success is True
        assert result.applied_writes == ("route_registry",)
        persisted_registry = load_route_registry(tmp_path)
        assert persisted_registry["local-summary"]["model_hint"] == "summary-governed"
        assert not route_registry_path(tmp_path).exists()
        refreshed = route_by_name("local-summary")
        assert refreshed is not None
        assert refreshed.model_hint == "summary-governed"
    finally:
        route.model_hint = original_model_hint
        apply_route_registry(tmp_path.parent)


def test_apply_route_metadata_proposal_saves_and_refreshes_route_policy(tmp_path) -> None:
    route_policy = {
        "route_mode_routes": {"offline": "local-summary"},
        "complexity_bias_routes": {"high": "local-summary"},
        "strategy_complexity_hints": ["high"],
        "parallel_intent_hints": ["fanout"],
        "summary_fallback_route_name": "local-summary",
    }
    try:
        register_route_metadata_proposal(
            base_dir=tmp_path,
            proposal_id="route-policy",
            route_policy=route_policy,
        )

        result = apply_proposal("route-policy", OperatorToken(source="cli"), ProposalTarget.ROUTE_METADATA)

        assert result.success is True
        assert result.applied_writes == ("route_policy",)
        persisted_policy = load_route_policy(tmp_path)
        assert persisted_policy == {
            "complexity_bias_routes": {"high": "local-summary"},
            "parallel_intent_hints": ["fanout"],
            "route_mode_routes": {"offline": "local-summary"},
            "strategy_complexity_hints": ["high"],
            "summary_fallback_route_name": "local-summary",
        }
        assert not route_policy_path(tmp_path).exists()
        assert current_route_policy()["complexity_bias_routes"]["high"] == "local-summary"
        assert current_route_policy()["parallel_intent_hints"] == ["fanout"]
    finally:
        apply_route_policy(tmp_path.parent)


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
    persisted = load_audit_trigger_policy(tmp_path)
    assert persisted.to_dict() == {
        "enabled": True,
        "trigger_on_degraded": False,
        "trigger_on_cost_above": 0.75,
        "auditor_route": "http-qwen",
    }
    assert not audit_policy_path(tmp_path).exists()


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
    assert load_mps_policy(tmp_path, "mps_participant_limit") == 6
    assert not mps_policy_path(tmp_path).exists()
