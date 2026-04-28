from __future__ import annotations

from .knowledge_index import invalidation_reason_for
from .knowledge_objects import canonicalization_status_for, is_retrieval_reuse_ready
from .knowledge_store import OPERATOR_CANONICAL_WRITE_AUTHORITY
from .models import LIBRARIAN_MEMORY_AUTHORITY, utc_now


CANONICAL_PROMOTION_DECISION_AUTHORITIES = {
    LIBRARIAN_MEMORY_AUTHORITY,
    OPERATOR_CANONICAL_WRITE_AUTHORITY,
}


def summarize_object_state(item: dict[str, object]) -> dict[str, object]:
    return {
        "stage": item.get("stage", "raw"),
        "evidence_status": item.get("evidence_status", "unbacked"),
        "retrieval_eligible": bool(item.get("retrieval_eligible", False)),
        "knowledge_reuse_scope": item.get("knowledge_reuse_scope", "task_only"),
        "canonicalization_intent": item.get("canonicalization_intent", "none"),
    }


def latest_decisions_by_object(decisions: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    latest: dict[str, dict[str, object]] = {}
    for decision in decisions:
        object_id = str(decision.get("object_id", "")).strip()
        if object_id:
            latest[object_id] = decision
    return latest


def classify_review_entry(item: dict[str, object], latest_decision: dict[str, object] | None) -> dict[str, object]:
    object_id = str(item.get("object_id", "unknown"))
    queue_state = "pending-review"
    recommended_action = "review"
    blocked_reason = ""

    if latest_decision and str(latest_decision.get("decision_type", "")) == "reject":
        queue_state = "rejected"
        recommended_action = "none"
    elif str(item.get("stage", "raw")) == "canonical":
        queue_state = "promoted"
        recommended_action = "none"
    else:
        canonicalization_status = canonicalization_status_for(item)
        if canonicalization_status in {"review_ready", "promotion_ready"}:
            queue_state = "promote-ready"
            recommended_action = "promote-canonical"
        elif is_retrieval_reuse_ready(item):
            queue_state = "reuse-ready"
            recommended_action = "promote-reuse"
        elif str(item.get("knowledge_reuse_scope", "task_only")) == "retrieval_candidate":
            queue_state = "blocked"
            recommended_action = "review"
            blocked_reason = invalidation_reason_for(item)
        elif canonicalization_status == "blocked_stage":
            queue_state = "blocked"
            recommended_action = "review"
            blocked_reason = "canonicalization_stage_not_ready"
        elif canonicalization_status == "blocked_evidence":
            queue_state = "blocked"
            recommended_action = "review"
            blocked_reason = "canonicalization_evidence_not_ready"

    return {
        "object_id": object_id,
        "stage": item.get("stage", "raw"),
        "evidence_status": item.get("evidence_status", "unbacked"),
        "knowledge_reuse_scope": item.get("knowledge_reuse_scope", "task_only"),
        "canonicalization_status": canonicalization_status_for(item),
        "queue_state": queue_state,
        "recommended_action": recommended_action,
        "blocked_reason": blocked_reason,
        "latest_decision": latest_decision or {},
        "text": item.get("text", ""),
    }


def build_review_queue(
    knowledge_objects: list[dict[str, object]],
    decisions: list[dict[str, object]],
) -> dict[str, object]:
    latest_by_object = latest_decisions_by_object(decisions)
    entries = [
        classify_review_entry(item, latest_by_object.get(str(item.get("object_id", ""))))
        for item in knowledge_objects
    ]
    counts: dict[str, int] = {}
    for entry in entries:
        state = str(entry.get("queue_state", "pending-review"))
        counts[state] = counts.get(state, 0) + 1
    return {
        "generated_at": utc_now(),
        "count": len(entries),
        "state_counts": counts,
        "entries": entries,
    }


def build_review_queue_report(queue: dict[str, object]) -> str:
    entries = list(queue.get("entries", []))
    state_counts = dict(queue.get("state_counts", {}))
    lines = [
        "# Knowledge Review Queue",
        "",
        f"- generated_at: {queue.get('generated_at', 'unknown')}",
        f"- count: {queue.get('count', len(entries))}",
        f"- pending_review: {state_counts.get('pending-review', 0)}",
        f"- promote_ready: {state_counts.get('promote-ready', 0)}",
        f"- reuse_ready: {state_counts.get('reuse-ready', 0)}",
        f"- blocked: {state_counts.get('blocked', 0)}",
        f"- promoted: {state_counts.get('promoted', 0)}",
        f"- rejected: {state_counts.get('rejected', 0)}",
        "",
        "## Entries",
    ]
    if not entries:
        lines.append("- none")
        return "\n".join(lines)

    for entry in entries:
        latest_decision = dict(entry.get("latest_decision", {}))
        decision_summary = "none"
        if latest_decision:
            decision_summary = (
                f"{latest_decision.get('decision_type', 'unknown')}/"
                f"{latest_decision.get('decision_target', 'unknown')}@"
                f"{latest_decision.get('decided_at', 'unknown')}"
            )
        lines.extend(
            [
                f"- {entry.get('object_id', 'unknown')} [{entry.get('stage', 'raw')}/{entry.get('evidence_status', 'unbacked')}/{entry.get('knowledge_reuse_scope', 'task_only')}]",
                f"  queue_state: {entry.get('queue_state', 'pending-review')}",
                f"  recommended_action: {entry.get('recommended_action', 'review')}",
                f"  blocked_reason: {entry.get('blocked_reason', '') or 'none'}",
                f"  canonicalization_status: {entry.get('canonicalization_status', 'not_requested')}",
                f"  latest_decision: {decision_summary}",
                f"  text: {entry.get('text', '') or '(empty)'}",
            ]
        )
    return "\n".join(lines)


def apply_knowledge_decision(
    knowledge_objects: list[dict[str, object]],
    *,
    object_id: str,
    decision_type: str,
    decision_target: str,
    caller_authority: str,
    note: str = "",
    decided_by: str = "swl_cli",
) -> tuple[list[dict[str, object]], dict[str, object]]:
    updated_objects = [dict(item) for item in knowledge_objects]
    selected_index = -1
    selected_item: dict[str, object] | None = None
    for index, item in enumerate(updated_objects):
        if str(item.get("object_id", "")) == object_id:
            selected_index = index
            selected_item = dict(item)
            break
    if selected_index < 0 or selected_item is None:
        raise ValueError(f"Unknown knowledge object: {object_id}")

    previous_state = summarize_object_state(selected_item)
    updated_item = dict(selected_item)
    stage = str(updated_item.get("stage", "raw"))
    evidence_status = str(updated_item.get("evidence_status", "unbacked"))
    normalized_caller_authority = caller_authority.strip()

    if decision_type == "promote":
        if stage != "verified":
            raise ValueError("Knowledge promotion requires verified stage.")
        if evidence_status != "artifact_backed":
            raise ValueError("Knowledge promotion requires artifact-backed evidence.")
        if decision_target == "reuse":
            updated_item["retrieval_eligible"] = True
            updated_item["knowledge_reuse_scope"] = "retrieval_candidate"
        elif decision_target == "canonical":
            if normalized_caller_authority not in CANONICAL_PROMOTION_DECISION_AUTHORITIES:
                raise PermissionError(
                    "Canonical promotion requires caller_authority=canonical-promotion or operator-gated."
                )
            updated_item["stage"] = "canonical"
            if str(updated_item.get("canonicalization_intent", "none")) == "none":
                updated_item["canonicalization_intent"] = "promote"
        else:
            raise ValueError(f"Unsupported promotion target: {decision_target}")
    elif decision_type == "reject":
        if decision_target == "reuse":
            updated_item["retrieval_eligible"] = False
            updated_item["knowledge_reuse_scope"] = "task_only"
        elif decision_target == "canonical":
            if stage == "canonical":
                raise ValueError("Canonical knowledge cannot be rejected from the canonical target after promotion.")
            updated_item["canonicalization_intent"] = "none"
        else:
            raise ValueError(f"Unsupported rejection target: {decision_target}")
    else:
        raise ValueError(f"Unsupported decision type: {decision_type}")

    updated_objects[selected_index] = updated_item
    decision_record = {
        "object_id": object_id,
        "decision_type": decision_type,
        "decision_target": decision_target,
        "previous_state": previous_state,
        "new_state": summarize_object_state(updated_item),
        "decided_at": utc_now(),
        "decided_by": decided_by,
        "caller_authority": normalized_caller_authority,
        "note": note.strip(),
    }
    return updated_objects, decision_record


def build_knowledge_decisions_report(decisions: list[dict[str, object]]) -> str:
    lines = [
        "# Knowledge Decision Record",
        "",
        f"- count: {len(decisions)}",
        "",
        "## Decisions",
    ]
    if not decisions:
        lines.append("- none")
        return "\n".join(lines)

    for decision in reversed(decisions):
        lines.extend(
            [
                f"- {decision.get('object_id', 'unknown')} {decision.get('decision_type', 'unknown')} {decision.get('decision_target', 'unknown')}",
                f"  decided_at: {decision.get('decided_at', 'unknown')}",
                f"  decided_by: {decision.get('decided_by', 'unknown')}",
                f"  caller_authority: {decision.get('caller_authority', '') or 'unknown'}",
                f"  note: {decision.get('note', '') or 'none'}",
                f"  previous_state: {decision.get('previous_state', {})}",
                f"  new_state: {decision.get('new_state', {})}",
            ]
        )
    return "\n".join(lines)
