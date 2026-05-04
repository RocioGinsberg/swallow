from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote

from swallow.knowledge_retrieval.raw_material import (
    FilesystemRawMaterialStore,
    InvalidRawMaterialRef,
    UnsupportedRawMaterialScheme,
    artifact_source_ref_from_legacy_ref,
    parse_source_ref,
)
from swallow.orchestration.models import RetrievalItem

ARTIFACTS_SOURCE_TYPE = "artifacts"
KNOWLEDGE_SOURCE_TYPE = "knowledge"
SOURCE_POLICY_NOISE_LABELS = {"archive_note", "current_state", "observation_doc"}
SUPPORTING_EVIDENCE_LABELS = {"supporting_evidence"}
WORKSPACE_FILE_PREFIX = "file://workspace/"


@dataclass(frozen=True, slots=True)
class SourcePointer:
    reference: str
    path: str
    source_type: str
    source_ref: str = ""
    artifact_ref: str = ""
    content_hash: str = ""
    parser_version: str = ""
    span: str = ""
    source_anchor_key: str = ""
    source_anchor_version: str = ""
    resolved_ref: str = ""
    resolved_path: str = ""
    resolution_status: str = "unresolved"
    resolution_reason: str = ""
    line_start: int = 0
    line_end: int = 0
    heading_level: int = 0
    heading_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EvidencePack:
    primary_objects: list[dict[str, Any]] = field(default_factory=list)
    canonical_objects: list[dict[str, Any]] = field(default_factory=list)
    supporting_evidence: list[dict[str, Any]] = field(default_factory=list)
    fallback_hits: list[dict[str, Any]] = field(default_factory=list)
    source_pointers: list[SourcePointer] = field(default_factory=list)
    deduped_supporting_evidence_count: int = 0
    deduped_fallback_hit_count: int = 0
    deduped_source_pointer_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_pointers"] = [pointer.to_dict() for pointer in self.source_pointers]
        return payload

    def summary(self) -> dict[str, int]:
        return {
            "primary_object_count": len(self.primary_objects),
            "canonical_object_count": len(self.canonical_objects),
            "supporting_evidence_count": len(self.supporting_evidence),
            "fallback_hit_count": len(self.fallback_hits),
            "source_pointer_count": len(self.source_pointers),
            "deduped_supporting_evidence_count": self.deduped_supporting_evidence_count,
            "deduped_fallback_hit_count": self.deduped_fallback_hit_count,
            "deduped_source_pointer_count": self.deduped_source_pointer_count,
            "deduped_total_count": (
                self.deduped_supporting_evidence_count
                + self.deduped_fallback_hit_count
                + self.deduped_source_pointer_count
            ),
        }


def build_evidence_pack(
    retrieval_items: list[RetrievalItem],
    *,
    workspace_root: str | Path | None = None,
    base_dir: str | Path | None = None,
) -> EvidencePack:
    primary_objects: list[dict[str, Any]] = []
    canonical_objects: list[dict[str, Any]] = []
    supporting_evidence: list[dict[str, Any]] = []
    fallback_hits: list[dict[str, Any]] = []
    source_pointers: list[SourcePointer] = []
    support_index_by_anchor: dict[str, int] = {}
    fallback_index_by_anchor: dict[str, int] = {}
    pointer_index_by_anchor: dict[str, int] = {}
    deduped_supporting_evidence_count = 0
    deduped_fallback_hit_count = 0
    deduped_source_pointer_count = 0
    raw_store = _raw_store_for(workspace_root=workspace_root, base_dir=base_dir)

    for index, item in enumerate(retrieval_items, start=1):
        label = _source_policy_label(item)
        flags = _source_policy_flags(item, label)
        entry = _evidence_entry(index, item, label, flags)
        anchor_key = _source_anchor_key(item)
        if label in {"canonical_truth", "task_knowledge_truth"}:
            primary_objects.append(entry)
            if label == "canonical_truth":
                canonical_objects.append(entry)
        elif _is_supporting_evidence(item, label):
            if not _append_deduped_entry(
                supporting_evidence,
                support_index_by_anchor,
                anchor_key=anchor_key,
                entry=entry,
                prefer_new=_is_source_anchor_support(item),
            ):
                deduped_supporting_evidence_count += 1
        if "fallback_text_hit" in flags:
            if not _append_deduped_entry(
                fallback_hits,
                fallback_index_by_anchor,
                anchor_key=anchor_key,
                entry=entry,
                prefer_new=False,
            ):
                deduped_fallback_hit_count += 1
        pointer = _source_pointer(item, raw_store=raw_store)
        if not _append_deduped_pointer(source_pointers, pointer_index_by_anchor, pointer):
            deduped_source_pointer_count += 1

    return EvidencePack(
        primary_objects=primary_objects,
        canonical_objects=canonical_objects,
        supporting_evidence=supporting_evidence,
        fallback_hits=fallback_hits,
        source_pointers=source_pointers,
        deduped_supporting_evidence_count=deduped_supporting_evidence_count,
        deduped_fallback_hit_count=deduped_fallback_hit_count,
        deduped_source_pointer_count=deduped_source_pointer_count,
    )


def _evidence_entry(index: int, item: RetrievalItem, label: str, flags: list[str]) -> dict[str, Any]:
    return {
        "rank": int(item.metadata.get("final_rank", index) or index),
        "reference": item.reference(),
        "title": item.display_title(),
        "source_type": item.source_type,
        "source_policy_label": label,
        "source_policy_flags": flags,
        "score": item.score,
        "canonical_id": str(item.metadata.get("canonical_id", "")),
        "knowledge_object_id": str(item.metadata.get("knowledge_object_id", "")),
        "evidence_status": str(item.metadata.get("evidence_status", "")),
        "source_ref": str(item.metadata.get("source_ref", "")),
        "artifact_ref": str(item.metadata.get("artifact_ref", "")),
        "content_hash": str(item.metadata.get("content_hash", "")),
        "parser_version": str(item.metadata.get("parser_version", "")),
        "span": str(item.metadata.get("span", "")),
        "heading_path": _heading_path(item),
        "source_anchor_key": str(item.metadata.get("source_anchor_key", "")),
        "source_anchor_version": str(item.metadata.get("source_anchor_version", "")),
        "source_preview_excerpt": _source_preview_excerpt(item),
        "duplicate_count": 0,
        "dedup_reason": str(item.metadata.get("dedup_reason", "")),
        "expansion_path_count": _positive_int_metadata(item, "expansion_path_count", default=1),
    }


def _source_pointer(item: RetrievalItem, *, raw_store: FilesystemRawMaterialStore | None = None) -> SourcePointer:
    resolved = _resolve_pointer(item, raw_store=raw_store)
    return SourcePointer(
        reference=item.reference(),
        path=item.path,
        source_type=item.source_type,
        source_ref=str(item.metadata.get("source_ref", "")),
        artifact_ref=str(item.metadata.get("artifact_ref", "")),
        content_hash=str(item.metadata.get("content_hash", "")),
        parser_version=str(item.metadata.get("parser_version", "")),
        span=str(item.metadata.get("span", "")),
        source_anchor_key=str(item.metadata.get("source_anchor_key", "")),
        source_anchor_version=str(item.metadata.get("source_anchor_version", "")),
        resolved_ref=resolved["resolved_ref"],
        resolved_path=resolved["resolved_path"],
        resolution_status=resolved["resolution_status"],
        resolution_reason=resolved["resolution_reason"],
        line_start=_int_metadata(item, "line_start"),
        line_end=_int_metadata(item, "line_end"),
        heading_level=_int_metadata(item, "heading_level"),
        heading_path=_heading_path(item),
    )


def _source_policy_label(item: RetrievalItem) -> str:
    explicit_label = str(item.metadata.get("source_policy_label", "")).strip()
    if explicit_label:
        return explicit_label

    path = item.path.replace("\\", "/").strip()
    storage_scope = str(item.metadata.get("storage_scope", "")).strip()
    if item.source_type == KNOWLEDGE_SOURCE_TYPE:
        if _is_source_anchor_support(item):
            return "supporting_evidence"
        if storage_scope == "canonical_registry" or str(item.metadata.get("canonical_id", "")).strip():
            return "canonical_truth"
        return "task_knowledge_truth"
    if item.source_type == ARTIFACTS_SOURCE_TYPE:
        return "artifact_source"
    if path in {"current_state.md", "docs/active_context.md"}:
        return "current_state"
    if path.startswith("docs/archive/") or path.startswith("docs/archive_phases/"):
        return "archive_note"
    if _is_observation_doc_path(path):
        return "observation_doc"
    if item.source_type == "repo":
        return "repo_source"
    if item.source_type == "notes":
        return "active_note"
    return f"{item.source_type or 'unknown'}_source"


def _source_policy_flags(item: RetrievalItem, label: str) -> list[str]:
    flags = item.metadata.get("source_policy_flags", [])
    if isinstance(flags, list) and flags:
        return [str(flag) for flag in flags]
    if isinstance(flags, str) and flags.strip():
        return [flag]

    inferred_flags: list[str] = []
    if label in SOURCE_POLICY_NOISE_LABELS:
        inferred_flags.append("operator_context_noise")
    if label == "supporting_evidence":
        inferred_flags.append("source_anchor_support")
    if label not in {"canonical_truth", "task_knowledge_truth", *SUPPORTING_EVIDENCE_LABELS}:
        inferred_flags.append("fallback_text_hit")
    if str(item.metadata.get("knowledge_retrieval_mode", "")).strip() == "text_fallback":
        inferred_flags.append("text_fallback_retrieval")
    if label == "canonical_truth":
        inferred_flags.append("primary_truth_candidate")
    return inferred_flags


def _is_observation_doc_path(path: str) -> bool:
    if path.startswith("results/"):
        return True
    if not path.startswith("docs/plans/"):
        return False
    return path.endswith("/observations.md") or path.endswith("/closeout.md") or "/candidate-r/" in path


def _is_supporting_evidence(item: RetrievalItem, label: str) -> bool:
    return label in SUPPORTING_EVIDENCE_LABELS or item.source_type == ARTIFACTS_SOURCE_TYPE


def _is_source_anchor_support(item: RetrievalItem) -> bool:
    if str(item.metadata.get("source_anchor_key", "")).strip():
        return True
    if str(item.metadata.get("canonicalization_intent", "")).strip() == "support":
        return True
    if str(item.metadata.get("knowledge_source_kind", "")).strip() == "wiki_compiler_source_pack":
        return True
    object_id = str(item.metadata.get("knowledge_object_id", item.chunk_id)).strip()
    return object_id.startswith("evidence-src-")


def _append_deduped_entry(
    entries: list[dict[str, Any]],
    index_by_anchor: dict[str, int],
    *,
    anchor_key: str,
    entry: dict[str, Any],
    prefer_new: bool,
) -> bool:
    if not anchor_key:
        entries.append(entry)
        return True

    existing_index = index_by_anchor.get(anchor_key)
    if existing_index is None:
        index_by_anchor[anchor_key] = len(entries)
        entries.append(entry)
        return True

    existing = entries[existing_index]
    _mark_duplicate_entry(existing, entry)
    if prefer_new and str(existing.get("source_policy_label", "")) != "supporting_evidence":
        replacement = dict(entry)
        replacement["duplicate_count"] = int(existing.get("duplicate_count", 0) or 0)
        replacement["dedup_reason"] = existing.get("dedup_reason", "duplicate_source_anchor")
        replacement["expansion_path_count"] = max(
            int(existing.get("expansion_path_count", 1) or 1),
            int(replacement.get("expansion_path_count", 1) or 1),
        )
        entries[existing_index] = replacement
    return False


def _mark_duplicate_entry(existing: dict[str, Any], duplicate: dict[str, Any]) -> None:
    try:
        duplicate_count = int(existing.get("duplicate_count", 0) or 0)
    except (TypeError, ValueError):
        duplicate_count = 0
    existing["duplicate_count"] = duplicate_count + 1
    existing["dedup_reason"] = "duplicate_source_anchor"
    existing["expansion_path_count"] = max(
        int(existing.get("expansion_path_count", 1) or 1),
        int(duplicate.get("expansion_path_count", 1) or 1),
    )


def _append_deduped_pointer(
    pointers: list[SourcePointer],
    index_by_anchor: dict[str, int],
    pointer: SourcePointer,
) -> bool:
    if not pointer.source_anchor_key:
        pointers.append(pointer)
        return True

    existing_index = index_by_anchor.get(pointer.source_anchor_key)
    if existing_index is None:
        index_by_anchor[pointer.source_anchor_key] = len(pointers)
        pointers.append(pointer)
        return True

    if pointers[existing_index].resolution_status != "resolved" and pointer.resolution_status == "resolved":
        pointers[existing_index] = pointer
    return False


def _source_anchor_key(item: RetrievalItem) -> str:
    return str(item.metadata.get("source_anchor_key", "")).strip()


def _source_preview_excerpt(item: RetrievalItem) -> str:
    return str(item.metadata.get("source_preview", "")).strip()


def _raw_store_for(
    *,
    workspace_root: str | Path | None,
    base_dir: str | Path | None,
) -> FilesystemRawMaterialStore | None:
    if workspace_root is None and base_dir is None:
        return None
    resolved_base_dir = Path(base_dir) if base_dir is not None else Path(workspace_root or ".")
    resolved_workspace_root = Path(workspace_root) if workspace_root is not None else resolved_base_dir
    return FilesystemRawMaterialStore(resolved_base_dir, workspace_root=resolved_workspace_root)


def _resolve_pointer(item: RetrievalItem, *, raw_store: FilesystemRawMaterialStore | None) -> dict[str, str]:
    candidates = _candidate_source_refs(item)
    if not candidates:
        return {
            "resolved_ref": "",
            "resolved_path": "",
            "resolution_status": "unresolved",
            "resolution_reason": "no_source_pointer",
        }

    unsupported_reasons: list[str] = []
    for candidate in candidates:
        try:
            parse_source_ref(candidate)
        except InvalidRawMaterialRef as exc:
            unsupported_reasons.append(f"{candidate}: {exc}")
            continue

        resolved_path = _display_path_for_ref(candidate)
        if raw_store is None:
            return {
                "resolved_ref": candidate,
                "resolved_path": resolved_path,
                "resolution_status": "unresolved",
                "resolution_reason": "raw_store_unavailable",
            }
        try:
            exists = raw_store.exists(candidate)
        except UnsupportedRawMaterialScheme as exc:
            unsupported_reasons.append(f"{candidate}: {exc}")
            continue
        except (InvalidRawMaterialRef, OSError) as exc:
            return {
                "resolved_ref": candidate,
                "resolved_path": resolved_path,
                "resolution_status": "unresolved",
                "resolution_reason": str(exc),
            }
        if exists:
            return {
                "resolved_ref": candidate,
                "resolved_path": resolved_path,
                "resolution_status": "resolved",
                "resolution_reason": "exists",
            }
        return {
            "resolved_ref": candidate,
            "resolved_path": resolved_path,
            "resolution_status": "missing",
            "resolution_reason": "raw_material_missing",
        }

    return {
        "resolved_ref": "",
        "resolved_path": "",
        "resolution_status": "unresolved",
        "resolution_reason": "; ".join(unsupported_reasons) or "unsupported_source_pointer",
    }


def _candidate_source_refs(item: RetrievalItem) -> list[str]:
    refs: list[str] = []
    source_ref = str(item.metadata.get("source_ref", "")).strip()
    if source_ref:
        refs.append(source_ref)

    artifact_ref = str(item.metadata.get("artifact_ref", "")).strip()
    converted_artifact_ref = _artifact_source_ref_or_empty(artifact_ref)
    if converted_artifact_ref:
        refs.append(converted_artifact_ref)

    path_ref = _path_source_ref_or_empty(item)
    if path_ref:
        refs.append(path_ref)

    deduped: list[str] = []
    for ref in refs:
        if ref and ref not in deduped:
            deduped.append(ref)
    return deduped


def _artifact_source_ref_or_empty(artifact_ref: str) -> str:
    if not artifact_ref:
        return ""
    try:
        return artifact_source_ref_from_legacy_ref(artifact_ref)
    except InvalidRawMaterialRef:
        return artifact_ref if artifact_ref.startswith("artifact://") else ""


def _path_source_ref_or_empty(item: RetrievalItem) -> str:
    normalized_path = item.path.replace("\\", "/").strip()
    if not normalized_path or PurePosixPath(normalized_path).is_absolute():
        return ""
    if any(part == ".." for part in PurePosixPath(normalized_path).parts):
        return ""
    if item.source_type == ARTIFACTS_SOURCE_TYPE or normalized_path.startswith(".swl/tasks/"):
        return _artifact_source_ref_or_empty(normalized_path)
    if normalized_path.startswith(".swl/"):
        return ""
    return WORKSPACE_FILE_PREFIX + quote(normalized_path, safe="/._-")


def _display_path_for_ref(source_ref: str) -> str:
    try:
        ref = parse_source_ref(source_ref)
    except InvalidRawMaterialRef:
        return ""

    if ref.scheme == "file":
        if ref.key == "workspace":
            return "."
        if ref.key.startswith("workspace/"):
            return ref.key.removeprefix("workspace/")
        return ref.key
    if ref.scheme == "artifact":
        key_path = PurePosixPath(ref.key)
        if len(key_path.parts) >= 2:
            return PurePosixPath(".swl", "tasks", key_path.parts[0], "artifacts", *key_path.parts[1:]).as_posix()
    return ref.key


def _heading_path(item: RetrievalItem) -> str:
    explicit_heading_path = str(item.metadata.get("heading_path", "")).strip()
    if explicit_heading_path:
        return explicit_heading_path
    if str(item.metadata.get("title_source", "")).strip() == "heading" and item.display_title():
        return item.display_title()
    if _int_metadata(item, "heading_level") > 0 and item.display_title():
        return item.display_title()
    return ""


def _int_metadata(item: RetrievalItem, key: str) -> int:
    try:
        return int(item.metadata.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def _positive_int_metadata(item: RetrievalItem, key: str, *, default: int) -> int:
    try:
        value = int(item.metadata.get(key, default) or default)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default
