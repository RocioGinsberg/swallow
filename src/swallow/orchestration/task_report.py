from __future__ import annotations

from pathlib import Path
from typing import Any

from swallow.knowledge_retrieval.knowledge_plane import (
    build_evidence_pack,
    source_policy_flags_for,
    source_policy_label_for,
    summarize_retrieval_trace,
    summarize_reused_knowledge,
    summarize_source_policy_warnings,
    summarize_truth_reuse_visibility,
)
from swallow.orchestration.models import RetrievalItem, TaskState


def build_source_grounding(
    retrieval_items: list[RetrievalItem],
    *,
    workspace_root: str | Path | None = None,
    base_dir: str | Path | None = None,
) -> str:
    lines = ["# Source Grounding", "", "## Top Retrieved Sources"]
    if not retrieval_items:
        lines.append("- No retrieval matches were available for this run.")
        return "\n".join(lines)

    evidence_pack = build_evidence_pack(retrieval_items, workspace_root=workspace_root, base_dir=base_dir)
    source_pointers_by_reference = {pointer.reference: pointer for pointer in evidence_pack.source_pointers}
    source_pointers_by_anchor = {
        pointer.source_anchor_key: pointer for pointer in evidence_pack.source_pointers if pointer.source_anchor_key
    }
    duplicate_count_by_anchor = _duplicate_count_by_anchor(evidence_pack)
    for item in retrieval_items:
        score_context = ", ".join(f"{key}={value}" for key, value in item.score_breakdown.items()) or "none"
        matched_terms = ", ".join(item.matched_terms) or "none"
        source_policy_label = str(item.metadata.get("source_policy_label", "") or source_policy_label_for(item))
        source_policy_flags = item.metadata.get("source_policy_flags", source_policy_flags_for(item, source_policy_label))
        source_policy_flag_text = ", ".join(str(flag) for flag in source_policy_flags) or "none"
        source_anchor_key = _metadata_text(item, "source_anchor_key")
        source_pointer = source_pointers_by_reference.get(item.reference()) or source_pointers_by_anchor.get(source_anchor_key)
        line_span = _format_line_span(source_pointer.line_start, source_pointer.line_end) if source_pointer else "none"
        duplicate_anchor_count = duplicate_count_by_anchor.get(source_anchor_key, 0) if source_anchor_key else 0
        lines.extend(
            [
                f"- [{item.source_type}] {item.reference()}",
                f"  title: {item.display_title()}",
                f"  source_policy_label: {source_policy_label}",
                f"  source_policy_flags: {source_policy_flag_text}",
                f"  source_anchor_key: {source_anchor_key or 'none'}",
                f"  source_anchor_version: {_metadata_text(item, 'source_anchor_version') or 'none'}",
                f"  duplicate_anchor_count: {duplicate_anchor_count}",
                f"  source_pointer_status: {source_pointer.resolution_status if source_pointer else 'unresolved'}",
                f"  source_pointer_ref: {source_pointer.resolved_ref if source_pointer and source_pointer.resolved_ref else 'none'}",
                f"  source_pointer_path: {source_pointer.resolved_path if source_pointer and source_pointer.resolved_path else 'none'}",
                f"  source_pointer_reason: {source_pointer.resolution_reason if source_pointer and source_pointer.resolution_reason else 'none'}",
                f"  line_span: {line_span}",
                f"  heading_path: {source_pointer.heading_path if source_pointer and source_pointer.heading_path else 'none'}",
                f"  storage_scope: {item.metadata.get('storage_scope', 'unknown')}",
                f"  knowledge_task_relation: {item.metadata.get('knowledge_task_relation', 'n/a')}",
                f"  canonical_id: {item.metadata.get('canonical_id', '') or 'none'}",
                f"  canonical_policy: {item.metadata.get('canonical_policy', '') or 'none'}",
                f"  source_ref: {item.metadata.get('source_ref', '') or 'none'}",
                f"  artifact_ref: {item.metadata.get('artifact_ref', '') or 'none'}",
                f"  source_preview_excerpt: {_source_preview_excerpt(item)}",
                f"  score: {item.score}",
                f"  matched_terms: {matched_terms}",
                f"  score_breakdown: {score_context}",
                f"  preview: {item.preview or '(empty)'}",
            ]
        )
    return "\n".join(lines)


def build_retrieval_report(
    state: TaskState,
    retrieval_items: list[RetrievalItem],
    *,
    base_dir: str | Path | None = None,
) -> str:
    reused_knowledge = summarize_reused_knowledge(retrieval_items)
    truth_reuse_visibility = summarize_truth_reuse_visibility(
        retrieval_items,
        task_knowledge_objects=state.knowledge_objects,
        base_dir=Path(base_dir) if base_dir is not None else None,
    )
    retrieval_trace = summarize_retrieval_trace(retrieval_items)
    source_policy_warnings = summarize_source_policy_warnings(retrieval_items)
    evidence_pack = build_evidence_pack(retrieval_items, workspace_root=state.workspace_root, base_dir=base_dir)
    evidence_pack_summary = evidence_pack.summary()
    lines = [
        "# Retrieval Report",
        "",
        f"- retrieval_count: {len(retrieval_items)}",
        f"- retrieval_mode: {retrieval_trace['retrieval_mode']}",
        f"- retrieval_adapter: {retrieval_trace['retrieval_adapter']}",
        f"- embedding_backend: {retrieval_trace['embedding_backend']}",
        f"- fallback_reason: {retrieval_trace['fallback_reason']}",
        f"- rerank_backend: {retrieval_trace['rerank_backend']}",
        f"- rerank_model: {retrieval_trace['rerank_model']}",
        f"- rerank_enabled: {retrieval_trace['rerank_enabled']}",
        f"- rerank_configured: {retrieval_trace['rerank_configured']}",
        f"- rerank_attempted: {retrieval_trace['rerank_attempted']}",
        f"- rerank_applied: {retrieval_trace['rerank_applied']}",
        f"- rerank_failure_reason: {retrieval_trace['rerank_failure_reason']}",
        f"- final_order_basis: {retrieval_trace['final_order_basis']}",
        f"- source_policy_warning_count: {len(source_policy_warnings)}",
        f"- evidence_pack_primary_object_count: {evidence_pack_summary['primary_object_count']}",
        f"- evidence_pack_canonical_object_count: {evidence_pack_summary['canonical_object_count']}",
        f"- evidence_pack_supporting_evidence_count: {evidence_pack_summary['supporting_evidence_count']}",
        f"- evidence_pack_fallback_hit_count: {evidence_pack_summary['fallback_hit_count']}",
        f"- evidence_pack_source_pointer_count: {evidence_pack_summary['source_pointer_count']}",
        f"- evidence_pack_deduped_supporting_evidence_count: {evidence_pack_summary['deduped_supporting_evidence_count']}",
        f"- evidence_pack_deduped_fallback_hit_count: {evidence_pack_summary['deduped_fallback_hit_count']}",
        f"- evidence_pack_deduped_source_pointer_count: {evidence_pack_summary['deduped_source_pointer_count']}",
        f"- evidence_pack_deduped_total_count: {evidence_pack_summary['deduped_total_count']}",
        f"- reused_knowledge_count: {reused_knowledge['count']}",
        f"- reused_task_knowledge_count: {reused_knowledge.get('task_knowledge_count', 0)}",
        f"- reused_canonical_registry_count: {reused_knowledge.get('canonical_registry_count', 0)}",
        f"- reused_knowledge_current_task_count: {reused_knowledge['current_task_count']}",
        f"- reused_knowledge_cross_task_count: {reused_knowledge['cross_task_count']}",
        f"- reused_knowledge_references: {', '.join(reused_knowledge['references']) or 'none'}",
        f"- retrieval_record_path: {state.artifact_paths.get('retrieval_json', '') or 'pending'}",
        f"- source_grounding_artifact: {state.artifact_paths.get('source_grounding', '') or 'pending'}",
        f"- task_memory_path: {state.artifact_paths.get('task_memory', '') or 'pending'}",
        "",
        "## Source Policy Warnings",
    ]
    if source_policy_warnings:
        lines.extend(f"- {warning}" for warning in source_policy_warnings)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## EvidencePack Summary",
            f"- primary_objects: {evidence_pack_summary['primary_object_count']}",
            f"- canonical_objects: {evidence_pack_summary['canonical_object_count']}",
            f"- supporting_evidence: {evidence_pack_summary['supporting_evidence_count']}",
            f"- fallback_hits: {evidence_pack_summary['fallback_hit_count']}",
            f"- source_pointers: {evidence_pack_summary['source_pointer_count']}",
            f"- deduped_supporting_evidence: {evidence_pack_summary['deduped_supporting_evidence_count']}",
            f"- deduped_fallback_hits: {evidence_pack_summary['deduped_fallback_hit_count']}",
            f"- deduped_source_pointers: {evidence_pack_summary['deduped_source_pointer_count']}",
            f"- deduped_total: {evidence_pack_summary['deduped_total_count']}",
            "",
            "## Truth Reuse Visibility",
        ]
    )
    for section_name, section in truth_reuse_visibility.items():
        lines.extend(
            [
                f"- {section_name}",
                f"  status: {section.get('status', 'unknown')}",
                f"  considered_count: {section.get('considered_count', 0)}",
                f"  matched_count: {section.get('matched_count', 0)}",
                f"  skipped_count: {section.get('skipped_count', 0)}",
                f"  absent_count: {section.get('absent_count', 0)}",
                f"  skipped_reasons: {_format_reason_counts(section.get('reason_counts', {}))}",
            ]
        )
    duplicate_count_by_anchor = _duplicate_count_by_anchor(evidence_pack)
    if evidence_pack.source_pointers:
        lines.extend(["", "## EvidencePack Source Pointers"])
        for pointer in evidence_pack.source_pointers[:8]:
            duplicate_anchor_count = (
                duplicate_count_by_anchor.get(pointer.source_anchor_key, 0) if pointer.source_anchor_key else 0
            )
            lines.extend(
                [
                    f"- {pointer.reference}",
                    f"  source_anchor_key: {pointer.source_anchor_key or 'none'}",
                    f"  source_anchor_version: {pointer.source_anchor_version or 'none'}",
                    f"  duplicate_anchor_count: {duplicate_anchor_count}",
                    f"  status: {pointer.resolution_status}",
                    f"  source_ref: {pointer.source_ref or 'none'}",
                    f"  resolved_ref: {pointer.resolved_ref or 'none'}",
                    f"  resolved_path: {pointer.resolved_path or 'none'}",
                    f"  reason: {pointer.resolution_reason or 'none'}",
                    f"  line_span: {_format_line_span(pointer.line_start, pointer.line_end)}",
                    f"  heading_path: {pointer.heading_path or 'none'}",
                ]
            )
    lines.extend(
        [
            "",
            "## Top References",
        ]
    )
    if not retrieval_items:
        lines.append("- No retrieval matches were available for this run.")
        return "\n".join(lines)

    for item in retrieval_items[:8]:
        score_context = ", ".join(f"{key}={value}" for key, value in item.score_breakdown.items()) or "none"
        source_policy_label = str(item.metadata.get("source_policy_label", "") or source_policy_label_for(item))
        source_policy_flags = item.metadata.get("source_policy_flags", source_policy_flags_for(item, source_policy_label))
        source_policy_flag_text = ", ".join(str(flag) for flag in source_policy_flags) or "none"
        source_anchor_key = _metadata_text(item, "source_anchor_key")
        duplicate_anchor_count = duplicate_count_by_anchor.get(source_anchor_key, 0) if source_anchor_key else 0
        lines.extend(
            [
                f"- [{item.source_type}] {item.reference()}",
                f"  title: {item.display_title()}",
                f"  source_policy_label: {source_policy_label}",
                f"  source_policy_flags: {source_policy_flag_text}",
                f"  source_anchor_key: {source_anchor_key or 'none'}",
                f"  source_anchor_version: {_metadata_text(item, 'source_anchor_version') or 'none'}",
                f"  duplicate_anchor_count: {duplicate_anchor_count}",
                f"  final_rank: {item.metadata.get('final_rank', 'unknown')}",
                f"  score: {item.score}",
                f"  raw_score: {item.metadata.get('raw_score', item.score)}",
                f"  score_breakdown: {score_context}",
                f"  vector_distance_milli: {item.score_breakdown.get('vector_distance_milli', 'n/a')}",
                f"  rerank_position: {item.metadata.get('rerank_position', 'n/a')}",
                f"  adapter: {item.metadata.get('adapter_name', 'unknown')}",
                f"  chunk_kind: {item.metadata.get('chunk_kind', 'unknown')}",
                f"  storage_scope: {item.metadata.get('storage_scope', 'unknown')}",
                f"  knowledge_task_relation: {item.metadata.get('knowledge_task_relation', 'n/a')}",
                f"  canonical_id: {item.metadata.get('canonical_id', '') or 'none'}",
                f"  canonical_policy: {item.metadata.get('canonical_policy', '') or 'none'}",
                f"  source_ref: {item.metadata.get('source_ref', '') or 'none'}",
                f"  artifact_ref: {item.metadata.get('artifact_ref', '') or 'none'}",
                f"  source_preview_excerpt: {_source_preview_excerpt(item)}",
            ]
        )
    return "\n".join(lines)


def _duplicate_count_by_anchor(evidence_pack: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for collection_name in ("supporting_evidence", "fallback_hits"):
        for entry in getattr(evidence_pack, collection_name, []):
            if not isinstance(entry, dict):
                continue
            source_anchor_key = str(entry.get("source_anchor_key", "")).strip()
            if not source_anchor_key:
                continue
            duplicate_count = _safe_int(entry.get("duplicate_count", 0))
            if duplicate_count > counts.get(source_anchor_key, 0):
                counts[source_anchor_key] = duplicate_count
    return counts


def _format_reason_counts(reason_counts: object) -> str:
    if not isinstance(reason_counts, dict) or not reason_counts:
        return "none"
    parts = [
        f"{key}={value}"
        for key, value in sorted(reason_counts.items())
        if _safe_int(value) > 0
    ]
    return ", ".join(parts) if parts else "none"


def _source_preview_excerpt(item: RetrievalItem) -> str:
    preview = _metadata_text(item, "source_preview")
    return preview or "none"


def _metadata_text(item: RetrievalItem, key: str) -> str:
    return str(item.metadata.get(key, "")).strip()


def _safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _format_line_span(line_start: int, line_end: int) -> str:
    if line_start <= 0 and line_end <= 0:
        return "none"
    if line_end <= 0 or line_end == line_start:
        return f"L{line_start}"
    return f"L{line_start}-L{line_end}"
