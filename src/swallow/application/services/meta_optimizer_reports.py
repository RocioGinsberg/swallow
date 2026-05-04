from __future__ import annotations

from swallow.application.services.meta_optimizer_models import (
    MetaOptimizerSnapshot,
    OptimizationProposalApplicationRecord,
    OptimizationProposalReviewRecord,
)

def build_meta_optimizer_report(snapshot: MetaOptimizerSnapshot) -> str:
    lines = [
        "# Meta-Optimizer Proposals",
        "",
        f"- generated_at: {snapshot.generated_at}",
        f"- scanned_task_count: {len(snapshot.scanned_task_ids)}",
        f"- scanned_event_count: {snapshot.scanned_event_count}",
        f"- task_limit: {snapshot.task_limit}",
    ]

    if not snapshot.scanned_task_ids or not snapshot.route_stats:
        lines.extend(
            [
                "",
                "## Status",
                "- no data",
            ]
        )
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            "",
            "## Route Health",
        ]
    )
    for stats in snapshot.route_stats:
        lines.append(
            f"- {stats.route_name}: success_rate={stats.success_rate():.0%} "
            f"failure_rate={stats.failure_rate():.0%} "
            f"fallback_rate={stats.fallback_rate():.0%} "
            f"debate_retry={stats.debate_retry_count} "
            f"avg_latency_ms={stats.average_latency_ms()} "
            f"avg_cost=${stats.average_cost():.6f} "
            f"degraded={stats.degraded_count}/{stats.event_count}"
        )

    lines.extend(
        [
            "",
            "## Failure Fingerprints",
        ]
    )
    if snapshot.failure_fingerprints:
        for fingerprint in snapshot.failure_fingerprints:
            lines.append(
                f"- failure_kind={fingerprint.failure_kind} "
                f"error_code={fingerprint.error_code} "
                f"count={fingerprint.count} "
                f"routes={', '.join(sorted(fingerprint.routes))}"
            )
    else:
        lines.append("- no failure fingerprints detected.")

    total_executor_events = sum(stats.event_count for stats in snapshot.route_stats)
    degraded_routes = [stats for stats in snapshot.route_stats if stats.degraded_count > 0]
    lines.extend(
        [
            "",
            "## Degradation Trends",
            f"- degraded_executor_events: {snapshot.degraded_event_count}/{total_executor_events}",
        ]
    )
    if degraded_routes:
        for stats in degraded_routes:
            lines.append(
                f"- {stats.route_name}: degraded_events={stats.degraded_count}/{stats.event_count}"
            )
    else:
        lines.append("- degraded_routes: none")

    lines.extend(
        [
            "",
            "## Cost Summary",
        ]
    )
    for stats in snapshot.route_stats:
        lines.append(
            f"- {stats.route_name}: total_cost=${stats.total_cost:.6f} "
            f"avg_cost=${stats.average_cost():.6f} "
            f"task_families={', '.join(sorted(stats.task_families)) or 'unknown'}"
        )

    lines.extend(
        [
            "",
            "## Route Task Family Signals",
        ]
    )
    if snapshot.route_task_family_stats:
        for stats in snapshot.route_task_family_stats:
            lines.append(
                f"- {stats.route_name}/{stats.task_family}: success_rate={stats.success_rate():.0%} "
                f"degraded_rate={stats.degraded_rate():.0%} "
                f"events={stats.event_count}"
            )
    else:
        lines.append("- no route task family signals detected.")

    lines.extend(
        [
            "",
            "## Proposals",
        ]
    )
    for proposal in snapshot.proposals:
        proposal_label = proposal.proposal_id or proposal.proposal_type
        lines.append(f"- [{proposal_label}] {proposal.description}")
    if not snapshot.proposals:
        lines.append("- No immediate optimization proposals were generated.")

    return "\n".join(lines) + "\n"




def build_optimization_proposal_review_report(review_record: OptimizationProposalReviewRecord) -> str:
    lines = [
        "# Proposal Review Record",
        "",
        f"- review_id: {review_record.review_id}",
        f"- reviewed_at: {review_record.reviewed_at}",
        f"- reviewer: {review_record.reviewer}",
        f"- decision: {review_record.decision}",
        f"- source_bundle: {review_record.source_bundle_path}",
        f"- note: {review_record.note or 'none'}",
        "",
        "## Entries",
    ]
    if not review_record.entries:
        lines.append("- none")
        return "\n".join(lines) + "\n"

    for entry in review_record.entries:
        task_family_suffix = f" task_family={entry.task_family}" if entry.task_family else ""
        lines.append(
            f"- {entry.proposal_id}: decision={entry.decision} type={entry.proposal_type} "
            f"route={entry.route_name or 'global'}{task_family_suffix} "
            f"priority={entry.priority or entry.severity or 'info'}"
        )
    return "\n".join(lines) + "\n"




def build_optimization_proposal_application_report(
    application_record: OptimizationProposalApplicationRecord,
) -> str:
    lines = [
        "# Proposal Application Record",
        "",
        f"- application_id: {application_record.application_id}",
        f"- applied_at: {application_record.applied_at}",
        f"- source_review: {application_record.source_review_path}",
        f"- applied_count: {application_record.applied_count}",
        f"- noop_count: {application_record.noop_count}",
        f"- skipped_count: {application_record.skipped_count}",
        f"- route_weights_path: {application_record.route_weights_path}",
        f"- route_capabilities_path: {application_record.route_capabilities_path}",
        "",
        "## Entries",
    ]
    if not application_record.entries:
        lines.append("- none")
        return "\n".join(lines) + "\n"

    for entry in application_record.entries:
        detail = entry.detail
        if entry.before_weight is not None and entry.after_weight is not None:
            detail = f"{detail} ({entry.before_weight:.6f} -> {entry.after_weight:.6f})"
        if entry.before_task_family_score is not None or entry.after_task_family_score is not None:
            before_score = "-" if entry.before_task_family_score is None else f"{entry.before_task_family_score:.6f}"
            after_score = "-" if entry.after_task_family_score is None else f"{entry.after_task_family_score:.6f}"
            detail = f"{detail} ({before_score} -> {after_score})"
        lines.append(
            f"- {entry.proposal_id}: status={entry.status} type={entry.proposal_type} "
            f"route={entry.route_name or 'global'}"
            f"{f' task_family={entry.task_family}' if entry.task_family else ''} detail={detail}"
        )
    return "\n".join(lines) + "\n"
