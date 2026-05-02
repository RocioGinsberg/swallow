from __future__ import annotations

import re
from pathlib import Path

from swallow.surface_tools import meta_optimizer


SRC_ROOT = Path(__file__).resolve().parents[3] / "src" / "swallow"
READ_ONLY_META_OPTIMIZER_MODULES = (
    "surface_tools/meta_optimizer_snapshot.py",
    "surface_tools/meta_optimizer_proposals.py",
    "surface_tools/meta_optimizer_reports.py",
    "surface_tools/meta_optimizer_agent.py",
    "surface_tools/meta_optimizer_lifecycle.py",
)
PROHIBITED_TRUTH_MUTATION_TOKENS = (
    "apply_proposal",
    "save_state",
    "_apply_metadata_change",
    "save_route_registry",
    "save_route_policy",
    "save_route_weights",
    "save_route_capability_profiles",
)
DIRECT_SQL_MUTATION_RE = re.compile(r"\b(INSERT|UPDATE|DELETE)\b")


def _source(relative_path: str) -> str:
    return (SRC_ROOT / relative_path).read_text(encoding="utf-8")


def test_meta_optimizer_read_only_modules_do_not_reference_truth_mutation_apis() -> None:
    for relative_path in READ_ONLY_META_OPTIMIZER_MODULES:
        source = _source(relative_path)
        violations = [token for token in PROHIBITED_TRUTH_MUTATION_TOKENS if token in source]
        assert violations == [], f"{relative_path} references prohibited mutation APIs: {violations}"


def test_meta_optimizer_read_only_modules_do_not_embed_direct_sql_mutations() -> None:
    for relative_path in READ_ONLY_META_OPTIMIZER_MODULES:
        source = _source(relative_path)
        matches = sorted(set(DIRECT_SQL_MUTATION_RE.findall(source)))
        assert matches == [], f"{relative_path} embeds direct SQL mutation strings: {matches}"


def test_meta_optimizer_agent_module_has_no_apply_proposal_reference() -> None:
    assert "apply_proposal" not in _source("surface_tools/meta_optimizer_agent.py")


def test_meta_optimizer_facade_preserves_public_imports() -> None:
    assert callable(meta_optimizer.build_meta_optimizer_snapshot)
    assert callable(meta_optimizer.build_optimization_proposals)
    assert callable(meta_optimizer.build_meta_optimizer_report)
    assert callable(meta_optimizer.review_optimization_proposals)
    assert callable(meta_optimizer.apply_reviewed_optimization_proposals)
    assert callable(meta_optimizer.run_meta_optimizer)
    assert meta_optimizer.MetaOptimizerExecutor is not None
