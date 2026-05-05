from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath

from swallow.knowledge_retrieval.knowledge_plane import (
    FilesystemRawMaterialStore,
    InvalidRawMaterialRef,
    StagedCandidate,
    load_raw_material_bytes,
    parse_raw_material_source_ref,
    parse_raw_material_source_ref_scheme,
    submit_staged_knowledge,
)
from swallow.orchestration.models import ExecutorResult, TaskCard, TaskState
from swallow.provider_router.agent_llm import call_agent_llm, extract_json_object
from swallow.truth_governance.store import write_artifact


WIKI_COMPILER_EXECUTOR_NAME = "wiki-compiler"
WIKI_COMPILER_SYSTEM_ROLE = "specialist"
WIKI_COMPILER_MEMORY_AUTHORITY = "staged-knowledge"
WIKI_COMPILER_PARSER_VERSION = "wiki-compiler-v1"
# Staged compiler metadata is intentionally broader than the persisted relation enum.
# Only `refines` is promoted into a governed relation row in this phase; the other
# signals stay on staged candidates/source packs for Operator review.
WIKI_COMPILER_METADATA_RELATION_TYPES: tuple[str, ...] = (
    "supersedes",
    "refines",
    "contradicts",
    "refers_to",
    "derived_from",
)
PROMPT_PACK_ARTIFACT = "wiki_compiler_prompt_pack.json"
RESULT_ARTIFACT = "wiki_compiler_result.json"
PREVIEW_LIMIT = 320


@dataclass(frozen=True, slots=True)
class WikiCompilerSourceAnchor:
    reference: str
    path: str
    source_type: str
    source_ref: str
    artifact_ref: str = ""
    resolved_ref: str = ""
    resolved_path: str = ""
    resolution_status: str = "unresolved"
    resolution_reason: str = ""
    line_start: int = 0
    line_end: int = 0
    heading_level: int = 0
    heading_path: str = ""
    content_hash: str = ""
    parser_version: str = WIKI_COMPILER_PARSER_VERSION
    span: str = ""
    preview: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WikiCompilerDraft:
    title: str
    text: str
    rationale: str
    relation_metadata: list[dict[str, object]]
    conflict_flag: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "text": self.text,
            "rationale": self.rationale,
            "relation_metadata": [dict(item) for item in self.relation_metadata],
            "conflict_flag": self.conflict_flag,
        }


@dataclass(frozen=True, slots=True)
class WikiCompilerRunResult:
    candidate: StagedCandidate | None
    prompt_pack: dict[str, object]
    compiler_result: dict[str, object]
    source_pack: list[dict[str, object]]
    prompt_artifact: Path | None = None
    result_artifact: Path | None = None
    dry_run: bool = False


def build_wiki_compiler_source_pack(
    base_dir: Path,
    source_refs: list[str],
    *,
    workspace_root: Path | str | None = None,
    parser_version: str = WIKI_COMPILER_PARSER_VERSION,
) -> list[dict[str, object]]:
    normalized_refs = [str(item).strip() for item in source_refs if str(item).strip()]
    if not normalized_refs:
        raise ValueError("At least one --source-ref is required.")

    store = FilesystemRawMaterialStore(base_dir, workspace_root=Path(workspace_root) if workspace_root else base_dir)
    anchors = [
        _source_anchor_for_ref(
            store,
            source_ref,
            reference=f"source-{index}",
            parser_version=parser_version,
        ).to_dict()
        for index, source_ref in enumerate(normalized_refs, start=1)
    ]
    unresolved = [
        str(anchor.get("source_ref", ""))
        for anchor in anchors
        if str(anchor.get("resolution_status", "")) != "resolved"
    ]
    if unresolved:
        raise ValueError(f"Unable to resolve source_ref(s): {', '.join(unresolved)}")
    return anchors


def _source_anchor_for_ref(
    store: FilesystemRawMaterialStore,
    source_ref: str,
    *,
    reference: str,
    parser_version: str,
) -> WikiCompilerSourceAnchor:
    normalized_ref = source_ref.strip()
    try:
        parsed = parse_raw_material_source_ref(normalized_ref)
    except InvalidRawMaterialRef as exc:
        return WikiCompilerSourceAnchor(
            reference=reference,
            path="",
            source_type="raw_material",
            source_ref=normalized_ref,
            resolution_status="unresolved",
            resolution_reason=str(exc),
            parser_version=parser_version,
        )

    display_path = _display_path_for_ref(parsed.scheme, parsed.key)
    source_type = "artifact" if parsed.scheme == "artifact" else "raw_material"
    try:
        exists = store.exists(normalized_ref)
    except Exception as exc:
        return WikiCompilerSourceAnchor(
            reference=reference,
            path=display_path,
            source_type=source_type,
            source_ref=normalized_ref,
            artifact_ref=display_path if parsed.scheme == "artifact" else "",
            resolved_ref=normalized_ref,
            resolved_path=display_path,
            resolution_status="unresolved",
            resolution_reason=str(exc),
            parser_version=parser_version,
        )
    if not exists:
        return WikiCompilerSourceAnchor(
            reference=reference,
            path=display_path,
            source_type=source_type,
            source_ref=normalized_ref,
            artifact_ref=display_path if parsed.scheme == "artifact" else "",
            resolved_ref=normalized_ref,
            resolved_path=display_path,
            resolution_status="missing",
            resolution_reason="raw_material_missing",
            parser_version=parser_version,
        )

    content = load_raw_material_bytes(store, normalized_ref).decode("utf-8", errors="replace")
    content_hash = store.content_hash(normalized_ref)
    line_count = max(len(content.splitlines()), 1)
    span = parsed.fragment or f"L1-L{line_count}"
    preview = _bounded_preview(content)
    return WikiCompilerSourceAnchor(
        reference=reference,
        path=display_path,
        source_type=source_type,
        source_ref=normalized_ref,
        artifact_ref=display_path if parsed.scheme == "artifact" else "",
        resolved_ref=normalized_ref,
        resolved_path=display_path,
        resolution_status="resolved",
        resolution_reason="exists",
        line_start=1,
        line_end=line_count,
        content_hash=content_hash,
        parser_version=parser_version,
        span=span,
        preview=preview,
    )


def _display_path_for_ref(scheme: str, key: str) -> str:
    key_path = PurePosixPath(key)
    if scheme == "file":
        if key == "workspace":
            return "."
        if key.startswith("workspace/"):
            return key.removeprefix("workspace/")
        return key
    if scheme == "artifact" and len(key_path.parts) >= 2:
        return PurePosixPath(".swl", "tasks", key_path.parts[0], "artifacts", *key_path.parts[1:]).as_posix()
    return key


def _bounded_preview(content: str) -> str:
    normalized = " ".join(line.strip() for line in content.splitlines() if line.strip())
    if len(normalized) <= PREVIEW_LIMIT:
        return normalized
    return normalized[: PREVIEW_LIMIT - 3].rstrip() + "..."


class WikiCompilerAgent:
    agent_name = WIKI_COMPILER_EXECUTOR_NAME
    system_role = WIKI_COMPILER_SYSTEM_ROLE
    memory_authority = WIKI_COMPILER_MEMORY_AUTHORITY

    def compile(
        self,
        base_dir: Path,
        state: TaskState,
        *,
        action: str,
        source_refs: list[str],
        topic: str = "",
        mode: str = "",
        target_object_id: str = "",
        model: str = "",
        dry_run: bool = False,
    ) -> WikiCompilerRunResult:
        normalized_action = action.strip()
        if normalized_action not in {"draft", "refine"}:
            raise ValueError("WikiCompilerAgent action must be draft or refine.")
        normalized_mode = mode.strip() or ("draft" if normalized_action == "draft" else "")
        if normalized_action == "refine" and normalized_mode not in {"supersede", "refines"}:
            raise ValueError("Wiki refine mode must be supersede or refines.")
        normalized_target = target_object_id.strip()
        if normalized_action == "refine" and not normalized_target:
            raise ValueError("Wiki refine requires a target object id.")

        source_pack = build_wiki_compiler_source_pack(
            base_dir,
            source_refs,
            workspace_root=state.workspace_root or base_dir,
        )
        prompt_pack = self._build_prompt_pack(
            state,
            action=normalized_action,
            mode=normalized_mode,
            topic=topic,
            target_object_id=normalized_target,
            source_pack=source_pack,
        )
        prompt_artifact = write_artifact(base_dir, state.task_id, PROMPT_PACK_ARTIFACT, json.dumps(prompt_pack, indent=2))
        if dry_run:
            return WikiCompilerRunResult(
                candidate=None,
                prompt_pack=prompt_pack,
                compiler_result={"status": "dry_run", "draft": {}},
                source_pack=source_pack,
                prompt_artifact=prompt_artifact,
                dry_run=True,
            )

        prompt = self._build_llm_prompt(prompt_pack)
        llm_response = call_agent_llm(
            prompt,
            system=self._system_prompt(),
            model=model.strip() or None,
        )
        draft = self._draft_from_payload(
            extract_json_object(llm_response.content),
            action=normalized_action,
            mode=normalized_mode,
            target_object_id=normalized_target,
        )
        compiler_result = {
            "status": "completed",
            "action": normalized_action,
            "mode": normalized_mode,
            "task_id": state.task_id,
            "model": llm_response.model,
            "input_tokens": llm_response.input_tokens,
            "output_tokens": llm_response.output_tokens,
            "draft": draft.to_dict(),
            "source_pack": source_pack,
        }
        result_artifact = write_artifact(base_dir, state.task_id, RESULT_ARTIFACT, json.dumps(compiler_result, indent=2))
        candidate = submit_staged_knowledge(
            base_dir,
            StagedCandidate(
                candidate_id="",
                text=draft.text,
                source_task_id=state.task_id,
                topic=topic.strip() or draft.title,
                source_kind="wiki_compiler",
                source_ref=str(source_pack[0].get("source_ref", "")) if source_pack else "",
                source_object_id="",
                submitted_by=self.agent_name,
                taxonomy_role=self.system_role,
                taxonomy_memory_authority=self.memory_authority,
                wiki_mode=normalized_mode,
                target_object_id=normalized_target,
                source_pack=source_pack,
                rationale=draft.rationale,
                relation_metadata=draft.relation_metadata,
                conflict_flag=draft.conflict_flag,
            ),
        )
        return WikiCompilerRunResult(
            candidate=candidate,
            prompt_pack=prompt_pack,
            compiler_result=compiler_result,
            source_pack=source_pack,
            prompt_artifact=prompt_artifact,
            result_artifact=result_artifact,
            dry_run=False,
        )

    def execute(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[object],
    ) -> ExecutorResult:
        del retrieval_items
        result = self.compile(
            base_dir,
            state,
            action=str(card.input_context.get("action", "draft")),
            source_refs=[str(item) for item in card.input_context.get("source_refs", [])],
            topic=str(card.input_context.get("topic", "")),
            mode=str(card.input_context.get("mode", "")),
            target_object_id=str(card.input_context.get("target_object_id", "")),
            model=str(card.input_context.get("model", "")),
            dry_run=bool(card.input_context.get("dry_run", False)),
        )
        candidate_id = result.candidate.candidate_id if result.candidate is not None else ""
        return ExecutorResult(
            executor_name=self.agent_name,
            status="completed",
            message=(
                "WikiCompilerAgent prepared a dry-run prompt pack."
                if result.dry_run
                else f"WikiCompilerAgent staged {candidate_id}."
            ),
            output=json.dumps(
                {
                    "candidate_id": candidate_id,
                    "dry_run": result.dry_run,
                    "source_count": len(result.source_pack),
                },
                indent=2,
            ),
            prompt=json.dumps(result.prompt_pack, indent=2),
            dialect="plain_text",
            estimated_input_tokens=int(result.compiler_result.get("input_tokens", 0) or 0),
            estimated_output_tokens=int(result.compiler_result.get("output_tokens", 0) or 0),
            side_effects={
                "kind": "wiki_compiler",
                "candidate_id": candidate_id,
                "prompt_artifact": str(result.prompt_artifact or ""),
                "result_artifact": str(result.result_artifact or ""),
                "source_count": len(result.source_pack),
                "dry_run": result.dry_run,
            },
        )

    async def execute_async(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[object],
    ) -> ExecutorResult:
        return await asyncio.to_thread(self.execute, base_dir, state, card, retrieval_items)

    def _build_prompt_pack(
        self,
        state: TaskState,
        *,
        action: str,
        mode: str,
        topic: str,
        target_object_id: str,
        source_pack: list[dict[str, object]],
    ) -> dict[str, object]:
        return {
            "kind": "wiki_compiler_prompt_pack_v1",
            "task_id": state.task_id,
            "action": action,
            "mode": mode,
            "topic": topic.strip(),
            "target_object_id": target_object_id,
            "source_pack": source_pack,
            "output_contract": {
                "required_keys": ["title", "text", "rationale"],
                "optional_keys": ["relation_metadata", "conflict_flag"],
                "relation_types": list(WIKI_COMPILER_METADATA_RELATION_TYPES),
            },
        }

    def _build_llm_prompt(self, prompt_pack: dict[str, object]) -> str:
        lines = [
            "# Wiki Compiler Task",
            "",
            "Return strict JSON only with keys: title, text, rationale, relation_metadata, conflict_flag.",
            "Do not promote or supersede knowledge. Produce a staged draft for operator review.",
            "relation_metadata may include derived_from refs. Only include supersedes/refines when requested by mode.",
            "",
            "Prompt Pack:",
            json.dumps(prompt_pack, indent=2),
        ]
        return "\n".join(lines)

    def _system_prompt(self) -> str:
        return (
            "You are the Swallow Wiki Compiler. Compile source material into a concise staged wiki draft. "
            "Return strict JSON only. Do not claim canonical promotion or apply any policy."
        )

    def _draft_from_payload(
        self,
        payload: dict[str, object],
        *,
        action: str,
        mode: str,
        target_object_id: str,
    ) -> WikiCompilerDraft:
        title = str(payload.get("title", "")).strip()
        text = str(payload.get("text", "")).strip()
        rationale = str(payload.get("rationale", "")).strip()
        if not text:
            raise ValueError("Wiki Compiler output must include non-empty text.")
        relation_metadata = self._normalize_relation_metadata(
            payload.get("relation_metadata", []),
            action=action,
            mode=mode,
            target_object_id=target_object_id,
        )
        return WikiCompilerDraft(
            title=title,
            text=text,
            rationale=rationale,
            relation_metadata=relation_metadata,
            conflict_flag=str(payload.get("conflict_flag", "")).strip(),
        )

    def _normalize_relation_metadata(
        self,
        raw_metadata: object,
        *,
        action: str,
        mode: str,
        target_object_id: str,
    ) -> list[dict[str, object]]:
        normalized: list[dict[str, object]] = []
        if isinstance(raw_metadata, list):
            for item in raw_metadata:
                if not isinstance(item, dict):
                    continue
                relation_type = str(item.get("relation_type", "")).strip()
                if relation_type not in WIKI_COMPILER_METADATA_RELATION_TYPES:
                    continue
                if action == "draft" and relation_type in {"supersedes", "refines"}:
                    continue
                normalized.append(dict(item))

        if action == "refine":
            requested_type = "supersedes" if mode == "supersede" else "refines"
            requested = {
                "relation_type": requested_type,
                "target_object_id": target_object_id,
            }
            normalized = [
                item
                for item in normalized
                if not (
                    str(item.get("relation_type", "")).strip() == requested_type
                    and str(item.get("target_object_id", "")).strip() == target_object_id
                )
            ]
            normalized.insert(0, requested)
        return normalized
def source_ref_scheme(source_ref: str) -> str:
    return parse_raw_material_source_ref_scheme(source_ref)
