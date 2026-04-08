from __future__ import annotations

from .models import KnowledgeObject


KNOWLEDGE_STAGES = {"raw", "candidate", "verified", "canonical"}


def build_knowledge_objects(
    *,
    items: list[str] | None = None,
    stage: str = "raw",
    source_ref: str | None = None,
    artifact_refs: list[str] | None = None,
    retrieval_eligible: bool = False,
) -> list[KnowledgeObject]:
    normalized_stage = stage.strip().lower() if stage else "raw"
    if normalized_stage not in KNOWLEDGE_STAGES:
        normalized_stage = "raw"

    objects: list[KnowledgeObject] = []
    normalized_artifact_refs = [(item or "").strip() for item in (artifact_refs or [])]
    for index, item in enumerate(items or [], start=1):
        text = item.strip()
        if not text:
            continue
        artifact_ref = normalized_artifact_refs[index - 1] if index - 1 < len(normalized_artifact_refs) else ""
        evidence_status = "artifact_backed" if artifact_ref else ("source_only" if source_ref else "unbacked")
        objects.append(
            KnowledgeObject(
                object_id=f"knowledge-{index:04d}",
                text=text,
                stage=normalized_stage,
                source_kind="external_knowledge_capture" if source_ref else "operator_capture",
                source_ref=(source_ref or "").strip(),
                task_linked=True,
                evidence_status=evidence_status,
                artifact_ref=artifact_ref,
                retrieval_eligible=retrieval_eligible,
                knowledge_reuse_scope="retrieval_candidate" if retrieval_eligible else "task_only",
            )
        )
    return objects


def summarize_knowledge_stages(objects: list[dict[str, object]] | list[KnowledgeObject]) -> dict[str, int]:
    counts = {"raw": 0, "candidate": 0, "verified": 0, "canonical": 0}
    for item in objects:
        stage = item.stage if isinstance(item, KnowledgeObject) else str(item.get("stage", "raw"))
        counts[stage] = counts.get(stage, 0) + 1
    return counts


def summarize_knowledge_evidence(objects: list[dict[str, object]] | list[KnowledgeObject]) -> dict[str, int]:
    counts = {"artifact_backed": 0, "source_only": 0, "unbacked": 0}
    for item in objects:
        status = item.evidence_status if isinstance(item, KnowledgeObject) else str(item.get("evidence_status", "unbacked"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def summarize_knowledge_reuse(objects: list[dict[str, object]] | list[KnowledgeObject]) -> dict[str, int]:
    counts = {"task_only": 0, "retrieval_candidate": 0}
    for item in objects:
        scope = (
            item.knowledge_reuse_scope
            if isinstance(item, KnowledgeObject)
            else str(item.get("knowledge_reuse_scope", "task_only"))
        )
        counts[scope] = counts.get(scope, 0) + 1
    return counts


def is_retrieval_reuse_ready(item: dict[str, object] | KnowledgeObject) -> bool:
    stage = item.stage if isinstance(item, KnowledgeObject) else str(item.get("stage", "raw"))
    evidence_status = item.evidence_status if isinstance(item, KnowledgeObject) else str(item.get("evidence_status", "unbacked"))
    reuse_scope = (
        item.knowledge_reuse_scope
        if isinstance(item, KnowledgeObject)
        else str(item.get("knowledge_reuse_scope", "task_only"))
    )
    return reuse_scope == "retrieval_candidate" and stage == "verified" and evidence_status == "artifact_backed"
