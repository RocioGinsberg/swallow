from __future__ import annotations

from swallow.application.services.meta_optimizer_agent import MetaOptimizerAgent, MetaOptimizerExecutor, run_meta_optimizer
from swallow.application.services.meta_optimizer_lifecycle import (
    _load_json,
    _write_json,
    apply_reviewed_optimization_proposals,
    load_optimization_proposal_bundle,
    load_optimization_proposal_review,
    review_optimization_proposals,
    save_optimization_proposal_bundle,
)
from swallow.application.services.meta_optimizer_models import (
    META_OPTIMIZER_AGENT_NAME,
    META_OPTIMIZER_EXECUTOR_NAME,
    META_OPTIMIZER_SNAPSHOT_KIND,
    PROPOSAL_APPLICATION_KIND,
    PROPOSAL_BUNDLE_KIND,
    PROPOSAL_REVIEW_KIND,
    VALID_PROPOSAL_REVIEW_DECISIONS,
    FailureFingerprint,
    MetaOptimizerSnapshot,
    OptimizationProposalApplicationRecord,
    OptimizationProposalBundle,
    OptimizationProposalReviewRecord,
    ProposalApplicationEntry,
    ProposalReviewEntry,
    RouteTaskFamilyTelemetryStats,
    RouteTelemetryStats,
    TaskFamilyTelemetryStats,
    _coerce_nonnegative_float,
    _coerce_nonnegative_int,
    _ensure_proposal_metadata,
    _slugify,
    _timestamp_token,
)
from swallow.application.services.meta_optimizer_proposals import (
    ROUTE_WEIGHT_PROPOSAL_PATTERN,
    _build_route_capability_proposals,
    _normalize_task_family_name,
    _suggest_task_family_score,
    build_optimization_proposals,
    extract_route_weight_proposals_from_report,
)
from swallow.application.services.meta_optimizer_reports import (
    build_meta_optimizer_report,
    build_optimization_proposal_application_report,
    build_optimization_proposal_review_report,
)
from swallow.application.services.meta_optimizer_snapshot import build_meta_optimizer_snapshot
