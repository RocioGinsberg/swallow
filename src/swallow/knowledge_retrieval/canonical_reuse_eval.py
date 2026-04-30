from __future__ import annotations

from typing import Any

from swallow.orchestration.models import utc_now

CANONICAL_REUSE_EVAL_JUDGMENTS = ("useful", "noisy", "needs_review")


def resolve_canonical_reuse_citations(
    *,
    task_id: str,
    citations: list[str],
    visible_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    visible_by_citation: dict[str, dict[str, Any]] = {}
    for record in visible_records:
        canonical_id = str(record.get("canonical_id", "")).strip()
        if not canonical_id:
            continue
        visible_by_citation[f".swl/canonical_knowledge/reuse_policy.json#{canonical_id}"] = record

    resolved: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for citation in [citation.strip() for citation in citations if citation.strip()]:
        record = visible_by_citation.get(citation)
        if record is None:
            unresolved.append(citation)
            continue
        source_task_id = str(record.get("source_task_id", "")).strip()
        task_relation = "unknown_task"
        if task_id:
            task_relation = "current_task" if source_task_id == task_id else "cross_task"
        resolved.append(
            {
                "citation": citation,
                "canonical_id": record.get("canonical_id", ""),
                "canonical_key": record.get("canonical_key", ""),
                "canonical_status": record.get("canonical_status", "active"),
                "canonical_policy": "reuse_visible",
                "source_task_id": source_task_id,
                "source_object_id": record.get("source_object_id", ""),
                "source_ref": record.get("source_ref", ""),
                "artifact_ref": record.get("artifact_ref", ""),
                "evidence_status": record.get("evidence_status", ""),
                "task_relation": task_relation,
            }
        )
    return resolved, unresolved


def match_retrieval_items_for_citations(
    *,
    citations: list[str],
    retrieval_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    citation_set = {citation.strip() for citation in citations if citation.strip()}
    matches: list[dict[str, Any]] = []
    for item in retrieval_items:
        citation = str(item.get("citation", item.get("path", ""))).strip()
        if not citation or citation not in citation_set:
            continue
        metadata = item.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        matches.append(
            {
                "citation": citation,
                "path": item.get("path", ""),
                "title": item.get("title", ""),
                "source_type": item.get("source_type", ""),
                "storage_scope": metadata.get("storage_scope", ""),
                "canonical_id": metadata.get("canonical_id", ""),
                "canonical_policy": metadata.get("canonical_policy", ""),
                "source_ref": metadata.get("source_ref", ""),
                "artifact_ref": metadata.get("artifact_ref", ""),
                "knowledge_task_relation": metadata.get("knowledge_task_relation", ""),
            }
        )
    return matches


def build_canonical_reuse_evaluation_record(
    *,
    task_id: str,
    citations: list[str],
    judgment: str,
    note: str = "",
    evaluated_by: str = "swl_cli",
    resolved_citations: list[dict[str, Any]] | None = None,
    unresolved_citations: list[str] | None = None,
    retrieval_context_ref: str = "",
    retrieval_context_available: bool = False,
    retrieval_context_count: int = 0,
    retrieval_matches: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized_judgment = judgment.strip().lower()
    if normalized_judgment not in CANONICAL_REUSE_EVAL_JUDGMENTS:
        raise ValueError(f"Unsupported canonical reuse evaluation judgment: {judgment}")
    unique_citations = [citation.strip() for citation in citations if citation.strip()]
    resolved_payload = resolved_citations or []
    unresolved_payload = unresolved_citations or []
    retrieval_payload = retrieval_matches or []
    return {
        "task_id": task_id,
        "evaluated_at": utc_now(),
        "evaluated_by": evaluated_by,
        "judgment": normalized_judgment,
        "citations": unique_citations,
        "citation_count": len(unique_citations),
        "resolved_citations": resolved_payload,
        "resolved_citation_count": len(resolved_payload),
        "unresolved_citations": unresolved_payload,
        "unresolved_citation_count": len(unresolved_payload),
        "retrieval_context_ref": retrieval_context_ref.strip(),
        "retrieval_context_available": retrieval_context_available,
        "retrieval_context_count": retrieval_context_count,
        "retrieval_matches": retrieval_payload,
        "retrieval_match_count": len(retrieval_payload),
        "note": note.strip(),
    }


def build_canonical_reuse_evaluation_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    judgment_counts = {judgment: 0 for judgment in CANONICAL_REUSE_EVAL_JUDGMENTS}
    resolved_citation_count = 0
    unresolved_citation_count = 0
    retrieval_match_count = 0
    for record in records:
        judgment = str(record.get("judgment", "needs_review")).strip().lower()
        judgment_counts[judgment] = judgment_counts.get(judgment, 0) + 1
        resolved_citation_count += int(record.get("resolved_citation_count", 0) or 0)
        unresolved_citation_count += int(record.get("unresolved_citation_count", 0) or 0)
        retrieval_match_count += int(record.get("retrieval_match_count", 0) or 0)
    latest = records[-1] if records else {}
    return {
        "refreshed_at": utc_now(),
        "evaluation_count": len(records),
        "judgment_counts": judgment_counts,
        "resolved_citation_count": resolved_citation_count,
        "unresolved_citation_count": unresolved_citation_count,
        "retrieval_match_count": retrieval_match_count,
        "latest_judgment": latest.get("judgment", "") if records else "",
        "latest_task_id": latest.get("task_id", "") if records else "",
        "latest_citations": latest.get("citations", []) if records else [],
        "latest_retrieval_context_ref": latest.get("retrieval_context_ref", "") if records else "",
        "latest_resolved_citations": latest.get("resolved_citations", []) if records else [],
        "latest_unresolved_citations": latest.get("unresolved_citations", []) if records else [],
    }


def build_canonical_reuse_evaluation_report(
    records: list[dict[str, Any]],
    summary: dict[str, Any],
) -> str:
    lines = [
        "# Canonical Reuse Evaluation",
        "",
        f"- refreshed_at: {summary.get('refreshed_at', 'unknown')}",
        f"- evaluation_count: {summary.get('evaluation_count', 0)}",
        f"- useful_count: {summary.get('judgment_counts', {}).get('useful', 0)}",
        f"- noisy_count: {summary.get('judgment_counts', {}).get('noisy', 0)}",
        f"- needs_review_count: {summary.get('judgment_counts', {}).get('needs_review', 0)}",
        f"- resolved_citation_count: {summary.get('resolved_citation_count', 0)}",
        f"- unresolved_citation_count: {summary.get('unresolved_citation_count', 0)}",
        f"- retrieval_match_count: {summary.get('retrieval_match_count', 0)}",
        f"- latest_judgment: {summary.get('latest_judgment', '') or '-'}",
        f"- latest_task_id: {summary.get('latest_task_id', '') or '-'}",
        f"- latest_citations: {', '.join(summary.get('latest_citations', [])) or '-'}",
        f"- latest_retrieval_context_ref: {summary.get('latest_retrieval_context_ref', '') or '-'}",
        "",
        "## Records",
    ]
    if not records:
        lines.append("- none")
        return "\n".join(lines)

    for record in records:
        lines.extend(
            [
                f"- judgment={record.get('judgment', 'unknown')} task_id={record.get('task_id', 'unknown')}",
                f"  evaluated_at: {record.get('evaluated_at', 'unknown')}",
                f"  evaluated_by: {record.get('evaluated_by', 'unknown')}",
                f"  citations: {', '.join(record.get('citations', [])) or 'none'}",
                f"  resolved_citation_count: {record.get('resolved_citation_count', 0)}",
                f"  unresolved_citation_count: {record.get('unresolved_citation_count', 0)}",
                f"  retrieval_context_ref: {record.get('retrieval_context_ref', '') or 'none'}",
                f"  retrieval_match_count: {record.get('retrieval_match_count', 0)}",
                f"  note: {record.get('note', '') or 'none'}",
            ]
        )
        resolved_citations = record.get("resolved_citations", [])
        if resolved_citations:
            lines.append("  resolved:")
            for resolved in resolved_citations:
                lines.append(
                    "    - "
                    f"{resolved.get('citation', 'unknown')} "
                    f"(canonical_id={resolved.get('canonical_id', 'unknown')}, "
                    f"source_task_id={resolved.get('source_task_id', 'unknown')}, "
                    f"source_object_id={resolved.get('source_object_id', 'unknown')}, "
                    f"task_relation={resolved.get('task_relation', 'unknown')})"
                )
        unresolved_citations = record.get("unresolved_citations", [])
        if unresolved_citations:
            lines.append(f"  unresolved: {', '.join(unresolved_citations)}")
        retrieval_matches = record.get("retrieval_matches", [])
        if retrieval_matches:
            lines.append("  retrieval_matches:")
            for match in retrieval_matches:
                lines.append(
                    "    - "
                    f"{match.get('citation', 'unknown')} "
                    f"(storage_scope={match.get('storage_scope', 'unknown')}, "
                    f"canonical_id={match.get('canonical_id', 'unknown')}, "
                    f"knowledge_task_relation={match.get('knowledge_task_relation', 'unknown')})"
                )
    return "\n".join(lines)


def build_canonical_reuse_regression_baseline(
    *,
    task_id: str,
    summary: dict[str, Any],
) -> dict[str, Any]:
    judgment_counts = summary.get("judgment_counts", {})
    if not isinstance(judgment_counts, dict):
        judgment_counts = {}
    return {
        "baseline_generated_at": utc_now(),
        "task_id": task_id,
        "evaluation_count": int(summary.get("evaluation_count", 0) or 0),
        "judgment_counts": {
            "useful": int(judgment_counts.get("useful", 0) or 0),
            "noisy": int(judgment_counts.get("noisy", 0) or 0),
            "needs_review": int(judgment_counts.get("needs_review", 0) or 0),
        },
        "resolved_citation_count": int(summary.get("resolved_citation_count", 0) or 0),
        "unresolved_citation_count": int(summary.get("unresolved_citation_count", 0) or 0),
        "retrieval_match_count": int(summary.get("retrieval_match_count", 0) or 0),
        "latest_judgment": str(summary.get("latest_judgment", "") or ""),
        "latest_task_id": str(summary.get("latest_task_id", "") or ""),
        "latest_citations": list(summary.get("latest_citations", []) or []),
        "latest_retrieval_context_ref": str(summary.get("latest_retrieval_context_ref", "") or ""),
    }


def build_canonical_reuse_regression_current(
    *,
    task_id: str,
    summary: dict[str, Any],
) -> dict[str, Any]:
    current = build_canonical_reuse_regression_baseline(task_id=task_id, summary=summary)
    current["current_generated_at"] = current.pop("baseline_generated_at", "")
    return current


def compare_canonical_reuse_regression(
    *,
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    baseline_judgment_counts = baseline.get("judgment_counts", {})
    if not isinstance(baseline_judgment_counts, dict):
        baseline_judgment_counts = {}
    current_judgment_counts = current.get("judgment_counts", {})
    if not isinstance(current_judgment_counts, dict):
        current_judgment_counts = {}

    deltas = {
        "evaluation_count_delta": int(current.get("evaluation_count", 0) or 0) - int(baseline.get("evaluation_count", 0) or 0),
        "useful_delta": int(current_judgment_counts.get("useful", 0) or 0) - int(baseline_judgment_counts.get("useful", 0) or 0),
        "noisy_delta": int(current_judgment_counts.get("noisy", 0) or 0) - int(baseline_judgment_counts.get("noisy", 0) or 0),
        "needs_review_delta": int(current_judgment_counts.get("needs_review", 0) or 0)
        - int(baseline_judgment_counts.get("needs_review", 0) or 0),
        "resolved_citation_delta": int(current.get("resolved_citation_count", 0) or 0)
        - int(baseline.get("resolved_citation_count", 0) or 0),
        "unresolved_citation_delta": int(current.get("unresolved_citation_count", 0) or 0)
        - int(baseline.get("unresolved_citation_count", 0) or 0),
        "retrieval_match_delta": int(current.get("retrieval_match_count", 0) or 0)
        - int(baseline.get("retrieval_match_count", 0) or 0),
    }

    mismatches: list[str] = []
    if deltas["evaluation_count_delta"] != 0:
        mismatches.append("evaluation_count")
    if deltas["useful_delta"] != 0:
        mismatches.append("judgment_useful")
    if deltas["noisy_delta"] != 0:
        mismatches.append("judgment_noisy")
    if deltas["needs_review_delta"] != 0:
        mismatches.append("judgment_needs_review")
    if deltas["resolved_citation_delta"] != 0:
        mismatches.append("resolved_citation_count")
    if deltas["unresolved_citation_delta"] != 0:
        mismatches.append("unresolved_citation_count")
    if deltas["retrieval_match_delta"] != 0:
        mismatches.append("retrieval_match_count")
    if list(baseline.get("latest_citations", []) or []) != list(current.get("latest_citations", []) or []):
        mismatches.append("latest_citations")
    if str(baseline.get("latest_judgment", "") or "") != str(current.get("latest_judgment", "") or ""):
        mismatches.append("latest_judgment")
    if str(baseline.get("latest_retrieval_context_ref", "") or "") != str(current.get("latest_retrieval_context_ref", "") or ""):
        mismatches.append("latest_retrieval_context_ref")

    return {
        "comparison_generated_at": utc_now(),
        "baseline_task_id": str(baseline.get("task_id", "") or ""),
        "current_task_id": str(current.get("task_id", "") or ""),
        "status": "match" if not mismatches else "mismatch",
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "deltas": deltas,
    }


def build_canonical_reuse_regression_report(
    *,
    baseline: dict[str, Any],
    current: dict[str, Any],
    comparison: dict[str, Any],
) -> str:
    baseline_judgment_counts = baseline.get("judgment_counts", {})
    if not isinstance(baseline_judgment_counts, dict):
        baseline_judgment_counts = {}
    current_judgment_counts = current.get("judgment_counts", {})
    if not isinstance(current_judgment_counts, dict):
        current_judgment_counts = {}
    deltas = comparison.get("deltas", {})
    if not isinstance(deltas, dict):
        deltas = {}
    lines = [
        "# Canonical Reuse Regression",
        "",
        f"- comparison_generated_at: {comparison.get('comparison_generated_at', 'unknown')}",
        f"- status: {comparison.get('status', 'unknown')}",
        f"- mismatch_count: {comparison.get('mismatch_count', 0)}",
        f"- mismatches: {', '.join(comparison.get('mismatches', [])) or '-'}",
        "",
        "## Baseline",
        f"- generated_at: {baseline.get('baseline_generated_at', 'unknown')}",
        f"- task_id: {baseline.get('task_id', '') or '-'}",
        f"- evaluation_count: {baseline.get('evaluation_count', 0)}",
        f"- useful_count: {baseline_judgment_counts.get('useful', 0)}",
        f"- noisy_count: {baseline_judgment_counts.get('noisy', 0)}",
        f"- needs_review_count: {baseline_judgment_counts.get('needs_review', 0)}",
        f"- resolved_citation_count: {baseline.get('resolved_citation_count', 0)}",
        f"- unresolved_citation_count: {baseline.get('unresolved_citation_count', 0)}",
        f"- retrieval_match_count: {baseline.get('retrieval_match_count', 0)}",
        f"- latest_judgment: {baseline.get('latest_judgment', '') or '-'}",
        f"- latest_citations: {', '.join(baseline.get('latest_citations', [])) or '-'}",
        f"- latest_retrieval_context_ref: {baseline.get('latest_retrieval_context_ref', '') or '-'}",
        "",
        "## Current",
        f"- generated_at: {current.get('current_generated_at', 'unknown')}",
        f"- task_id: {current.get('task_id', '') or '-'}",
        f"- evaluation_count: {current.get('evaluation_count', 0)}",
        f"- useful_count: {current_judgment_counts.get('useful', 0)}",
        f"- noisy_count: {current_judgment_counts.get('noisy', 0)}",
        f"- needs_review_count: {current_judgment_counts.get('needs_review', 0)}",
        f"- resolved_citation_count: {current.get('resolved_citation_count', 0)}",
        f"- unresolved_citation_count: {current.get('unresolved_citation_count', 0)}",
        f"- retrieval_match_count: {current.get('retrieval_match_count', 0)}",
        f"- latest_judgment: {current.get('latest_judgment', '') or '-'}",
        f"- latest_citations: {', '.join(current.get('latest_citations', [])) or '-'}",
        f"- latest_retrieval_context_ref: {current.get('latest_retrieval_context_ref', '') or '-'}",
        "",
        "## Delta",
        f"- evaluation_count_delta: {deltas.get('evaluation_count_delta', 0)}",
        f"- useful_delta: {deltas.get('useful_delta', 0)}",
        f"- noisy_delta: {deltas.get('noisy_delta', 0)}",
        f"- needs_review_delta: {deltas.get('needs_review_delta', 0)}",
        f"- resolved_citation_delta: {deltas.get('resolved_citation_delta', 0)}",
        f"- unresolved_citation_delta: {deltas.get('unresolved_citation_delta', 0)}",
        f"- retrieval_match_delta: {deltas.get('retrieval_match_delta', 0)}",
    ]
    return "\n".join(lines)
