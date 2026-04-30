from __future__ import annotations

from typing import Any

from swallow.orchestration.models import utc_now

CANONICAL_REUSE_POLICY_NAME = "active_canonical_only"
CANONICAL_REUSE_SUPERSEDED_RULE = "exclude"


def is_canonical_reuse_visible(record: dict[str, Any]) -> bool:
    return str(record.get("canonical_status", "active")).strip() != "superseded"


def build_canonical_reuse_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    visible_records = [record for record in records if is_canonical_reuse_visible(record)]
    hidden_records = [record for record in records if not is_canonical_reuse_visible(record)]
    latest_visible = visible_records[-1] if visible_records else {}
    return {
        "refreshed_at": utc_now(),
        "policy_name": CANONICAL_REUSE_POLICY_NAME,
        "superseded_rule": CANONICAL_REUSE_SUPERSEDED_RULE,
        "total_canonical_count": len(records),
        "reuse_visible_count": len(visible_records),
        "reuse_hidden_count": len(hidden_records),
        "latest_visible_canonical_id": latest_visible.get("canonical_id", "") if visible_records else "",
        "latest_visible_source_task_id": latest_visible.get("source_task_id", "") if visible_records else "",
        "latest_visible_source_object_id": latest_visible.get("source_object_id", "") if visible_records else "",
        "visible_records": visible_records,
    }


def build_canonical_reuse_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Canonical Reuse Policy",
        "",
        f"- refreshed_at: {summary.get('refreshed_at', 'unknown')}",
        f"- policy_name: {summary.get('policy_name', CANONICAL_REUSE_POLICY_NAME)}",
        f"- superseded_rule: {summary.get('superseded_rule', CANONICAL_REUSE_SUPERSEDED_RULE)}",
        f"- total_canonical_count: {summary.get('total_canonical_count', 0)}",
        f"- reuse_visible_count: {summary.get('reuse_visible_count', 0)}",
        f"- reuse_hidden_count: {summary.get('reuse_hidden_count', 0)}",
        f"- latest_visible_canonical_id: {summary.get('latest_visible_canonical_id', '') or '-'}",
        f"- latest_visible_source_task_id: {summary.get('latest_visible_source_task_id', '') or '-'}",
        f"- latest_visible_source_object_id: {summary.get('latest_visible_source_object_id', '') or '-'}",
        "",
        "## Visible Records",
    ]
    visible_records = summary.get("visible_records", [])
    if not isinstance(visible_records, list) or not visible_records:
        lines.append("- none")
        return "\n".join(lines)

    for record in visible_records:
        lines.extend(
            [
                f"- {record.get('canonical_id', 'unknown')}",
                f"  canonical_key: {record.get('canonical_key', 'unknown')}",
                f"  source_task_id: {record.get('source_task_id', 'unknown')}",
                f"  source_object_id: {record.get('source_object_id', 'unknown')}",
                f"  source_ref: {record.get('source_ref', '') or 'none'}",
                f"  artifact_ref: {record.get('artifact_ref', '') or 'none'}",
                f"  canonical_status: {record.get('canonical_status', 'active')}",
            ]
        )
    return "\n".join(lines)
