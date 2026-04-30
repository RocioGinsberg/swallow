from __future__ import annotations

import json
from pathlib import Path

from ._io_helpers import read_json_or_empty
from .canonical_registry import resolve_knowledge_object_id
from .knowledge_relations import create_knowledge_relation, list_knowledge_relations
from .paths import artifacts_dir


EXECUTOR_SIDE_EFFECTS_ARTIFACT = "executor_side_effects.json"


def persist_executor_side_effects(base_dir: Path, task_id: str, side_effects: dict[str, object]) -> Path:
    payload = dict(side_effects) if isinstance(side_effects, dict) else {}
    path = artifacts_dir(base_dir, task_id) / EXECUTOR_SIDE_EFFECTS_ARTIFACT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def load_executor_side_effects(base_dir: Path, task_id: str) -> dict[str, object]:
    path = artifacts_dir(base_dir, task_id) / EXECUTOR_SIDE_EFFECTS_ARTIFACT
    try:
        return read_json_or_empty(path)
    except (OSError, json.JSONDecodeError):
        return {}


def _normalize_relation_suggestions(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, list):
        return []
    suggestions: list[dict[str, object]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        source_object_id = str(item.get("source_object_id", "")).strip()
        target_object_id = str(item.get("target_object_id", "")).strip()
        relation_type = str(item.get("relation_type", "")).strip()
        context = str(item.get("context", "")).strip()
        if not source_object_id or not target_object_id or not relation_type:
            continue
        try:
            confidence = float(item.get("confidence", 0.0) or 0.0)
        except (TypeError, ValueError):
            confidence = 0.0
        suggestions.append(
            {
                "source_object_id": source_object_id,
                "target_object_id": target_object_id,
                "relation_type": relation_type,
                "confidence": max(confidence, 0.0),
                "context": context,
            }
        )
    return suggestions


def apply_relation_suggestions(base_dir: Path, task_id: str, *, dry_run: bool = False) -> dict[str, object]:
    side_effects = load_executor_side_effects(base_dir, task_id)
    suggestions = _normalize_relation_suggestions(side_effects.get("relation_suggestions", []))
    report: dict[str, object] = {
        "task_id": task_id,
        "dry_run": bool(dry_run),
        "suggestion_count": len(suggestions),
        "applied_count": 0,
        "duplicate_count": 0,
        "invalid_count": 0,
        "applied_relations": [],
        "duplicate_relations": [],
        "invalid_relations": [],
    }
    if not suggestions:
        return report

    seen_pairs: set[tuple[str, str, str]] = set()
    for suggestion in suggestions:
        source_input = str(suggestion.get("source_object_id", "")).strip()
        target_input = str(suggestion.get("target_object_id", "")).strip()
        relation_type = str(suggestion.get("relation_type", "")).strip()
        try:
            resolved_source = resolve_knowledge_object_id(base_dir, source_input)
            resolved_target = resolve_knowledge_object_id(base_dir, target_input)
        except ValueError as exc:
            report["invalid_count"] = int(report["invalid_count"]) + 1
            report["invalid_relations"].append({**suggestion, "error": str(exc)})  # type: ignore[attr-defined]
            continue

        relation_key = (resolved_source, resolved_target, relation_type)
        if relation_key in seen_pairs:
            report["duplicate_count"] = int(report["duplicate_count"]) + 1
            report["duplicate_relations"].append(suggestion)  # type: ignore[attr-defined]
            continue

        existing_relations = list_knowledge_relations(base_dir, resolved_source)
        if any(
            item.get("direction") == "outgoing"
            and str(item.get("counterparty_object_id", "")).strip() == resolved_target
            and str(item.get("relation_type", "")).strip() == relation_type
            for item in existing_relations
        ):
            seen_pairs.add(relation_key)
            report["duplicate_count"] = int(report["duplicate_count"]) + 1
            report["duplicate_relations"].append(suggestion)  # type: ignore[attr-defined]
            continue

        seen_pairs.add(relation_key)
        if dry_run:
            report["applied_count"] = int(report["applied_count"]) + 1
            report["applied_relations"].append(  # type: ignore[attr-defined]
                {
                    **suggestion,
                    "source_object_id": resolved_source,
                    "target_object_id": resolved_target,
                    "dry_run": True,
                }
            )
            continue

        relation = create_knowledge_relation(
            base_dir,
            source_object_id=resolved_source,
            target_object_id=resolved_target,
            relation_type=relation_type,
            confidence=float(suggestion.get("confidence", 0.0) or 0.0),
            context=str(suggestion.get("context", "")).strip(),
            created_by="swl_apply_suggestions",
        )
        report["applied_count"] = int(report["applied_count"]) + 1
        report["applied_relations"].append(relation)  # type: ignore[attr-defined]
    return report


def build_relation_suggestion_application_report(report: dict[str, object]) -> str:
    lines = [
        "# Knowledge Suggestion Application",
        "",
        f"- task_id: {report.get('task_id', '')}",
        f"- dry_run: {bool(report.get('dry_run', False))}",
        f"- suggestion_count: {int(report.get('suggestion_count', 0) or 0)}",
        f"- applied_count: {int(report.get('applied_count', 0) or 0)}",
        f"- duplicate_count: {int(report.get('duplicate_count', 0) or 0)}",
        f"- invalid_count: {int(report.get('invalid_count', 0) or 0)}",
        "",
        "## Applied",
    ]
    applied_relations = report.get("applied_relations", [])
    if not isinstance(applied_relations, list) or not applied_relations:
        lines.append("- none")
    else:
        for item in applied_relations:
            if not isinstance(item, dict):
                continue
            lines.append(
                "- "
                f"{item.get('source_object_id', '')} -> {item.get('target_object_id', '')} "
                f"[{item.get('relation_type', '')}]"
            )

    lines.extend(["", "## Duplicates"])
    duplicate_relations = report.get("duplicate_relations", [])
    if not isinstance(duplicate_relations, list) or not duplicate_relations:
        lines.append("- none")
    else:
        for item in duplicate_relations:
            if not isinstance(item, dict):
                continue
            lines.append(
                "- "
                f"{item.get('source_object_id', '')} -> {item.get('target_object_id', '')} "
                f"[{item.get('relation_type', '')}]"
            )

    lines.extend(["", "## Invalid"])
    invalid_relations = report.get("invalid_relations", [])
    if not isinstance(invalid_relations, list) or not invalid_relations:
        lines.append("- none")
    else:
        for item in invalid_relations:
            if not isinstance(item, dict):
                continue
            lines.append(
                "- "
                f"{item.get('source_object_id', '')} -> {item.get('target_object_id', '')} "
                f"[{item.get('relation_type', '')}] "
                f"error={item.get('error', '')}"
            )
    return "\n".join(lines) + "\n"
