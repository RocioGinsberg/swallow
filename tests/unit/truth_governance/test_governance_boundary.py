from __future__ import annotations

from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[3] / "src" / "swallow"

PUBLIC_GOVERNANCE_NAMES = (
    "ApplyResult",
    "DuplicateProposalError",
    "OperatorToken",
    "ProposalTarget",
    "apply_proposal",
    "load_mps_policy",
    "register_canonical_proposal",
    "register_mps_policy_proposal",
    "register_policy_proposal",
    "register_route_metadata_proposal",
)

PROPOSAL_PAYLOAD_NAMES = (
    "_CanonicalProposal",
    "_RouteMetadataProposal",
    "_PolicyProposal",
    "_MpsPolicyProposal",
)


def _source(relative_path: str) -> str:
    return (SRC_ROOT / relative_path).read_text(encoding="utf-8")


def test_governance_facade_exports_stable_public_api() -> None:
    import swallow.truth_governance.governance as governance

    for name in PUBLIC_GOVERNANCE_NAMES:
        assert hasattr(governance, name), f"governance facade must export {name}"


def test_proposal_registry_owns_pending_payload_records() -> None:
    governance_source = _source("truth_governance/governance.py")
    registry_source = _source("truth_governance/proposal_registry.py")

    assert "_PENDING_PROPOSALS" not in governance_source
    assert "_PENDING_PROPOSALS" in registry_source
    for name in PROPOSAL_PAYLOAD_NAMES:
        assert name not in governance_source
        assert name in registry_source


def test_apply_handlers_own_repository_write_logic() -> None:
    governance_source = _source("truth_governance/governance.py")
    canonical_source = _source("truth_governance/apply_canonical.py")
    route_source = _source("truth_governance/apply_route_metadata.py")
    policy_source = _source("truth_governance/apply_policy.py")

    for token in (
        "KnowledgeRepo",
        "RouteRepo",
        "PolicyRepo",
        "_promote_canonical",
        "_apply_metadata_change",
        "_apply_policy_change",
    ):
        assert token not in governance_source

    assert "KnowledgeRepo" in canonical_source
    assert "_promote_canonical" in canonical_source
    assert "RouteRepo" in route_source
    assert "_apply_metadata_change" in route_source
    assert "PolicyRepo" in policy_source
    assert "_apply_policy_change" in policy_source


def test_route_metadata_handler_imports_meta_optimizer_owning_submodules() -> None:
    route_source = _source("truth_governance/apply_route_metadata.py")

    assert "swallow.surface_tools.meta_optimizer import" not in route_source
    assert "swallow.surface_tools.meta_optimizer_models" in route_source
    assert "swallow.surface_tools.meta_optimizer_proposals" in route_source
    assert "meta_optimizer_lifecycle" in route_source


def test_governance_models_is_record_only_cycle_breaker() -> None:
    models_path = SRC_ROOT / "truth_governance" / "governance_models.py"
    assert models_path.exists(), "governance_models.py should own cycle-breaking public records"
    source = models_path.read_text(encoding="utf-8")

    for token in (
        "KnowledgeRepo",
        "RouteRepo",
        "PolicyRepo",
        "PendingProposalRepo",
        "_apply_",
        "apply_proposal",
        "register_",
        "from swallow.truth_governance.apply_",
    ):
        assert token not in source

    import swallow.truth_governance.governance as governance
    import swallow.truth_governance.governance_models as models

    assert governance.ApplyResult is models.ApplyResult
    assert governance.OperatorToken is models.OperatorToken
    assert governance.ProposalTarget is models.ProposalTarget
