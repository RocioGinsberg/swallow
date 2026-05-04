from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from uuid import uuid4

from swallow.application.commands.wiki import draft_wiki_command, refine_wiki_command
from swallow.application.infrastructure.paths import artifacts_dir, tasks_root
from swallow.orchestration.models import utc_now
from swallow.truth_governance.store import load_state, write_artifact


WIKI_JOB_STATUSES: tuple[str, ...] = ("queued", "running", "completed", "failed")
WIKI_JOB_ACTIONS: tuple[str, ...] = ("draft", "refine")


@dataclass(frozen=True, slots=True)
class WikiJobRecord:
    job_id: str
    task_id: str
    action: str
    status: str
    created_at: str
    updated_at: str
    topic: str = ""
    mode: str = ""
    target_object_id: str = ""
    source_refs: list[str] = field(default_factory=list)
    model: str = ""
    candidate_id: str = ""
    prompt_artifact: str = ""
    result_artifact: str = ""
    error: str = ""
    candidate: dict[str, object] = field(default_factory=dict)
    prompt_pack: dict[str, object] = field(default_factory=dict)
    compiler_result: dict[str, object] = field(default_factory=dict)
    source_pack: list[dict[str, object]] = field(default_factory=list)

    def __post_init__(self) -> None:
        _normalize_job_id(self.job_id)
        if not self.task_id.strip():
            raise ValueError("Wiki job task_id must be non-empty.")
        if self.action not in WIKI_JOB_ACTIONS:
            raise ValueError(f"Invalid wiki job action: {self.action}.")
        if self.status not in WIKI_JOB_STATUSES:
            raise ValueError(f"Invalid wiki job status: {self.status}.")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "WikiJobRecord":
        return cls(
            job_id=str(payload.get("job_id", "")).strip(),
            task_id=str(payload.get("task_id", "")).strip(),
            action=str(payload.get("action", "")).strip(),
            status=str(payload.get("status", "")).strip(),
            created_at=str(payload.get("created_at", "")).strip(),
            updated_at=str(payload.get("updated_at", "")).strip(),
            topic=str(payload.get("topic", "")).strip(),
            mode=str(payload.get("mode", "")).strip(),
            target_object_id=str(payload.get("target_object_id", "")).strip(),
            source_refs=[str(item).strip() for item in payload.get("source_refs", []) if str(item).strip()]
            if isinstance(payload.get("source_refs", []), list)
            else [],
            model=str(payload.get("model", "")).strip(),
            candidate_id=str(payload.get("candidate_id", "")).strip(),
            prompt_artifact=str(payload.get("prompt_artifact", "")).strip(),
            result_artifact=str(payload.get("result_artifact", "")).strip(),
            error=str(payload.get("error", "")).strip(),
            candidate=dict(payload.get("candidate", {})) if isinstance(payload.get("candidate", {}), dict) else {},
            prompt_pack=dict(payload.get("prompt_pack", {})) if isinstance(payload.get("prompt_pack", {}), dict) else {},
            compiler_result=dict(payload.get("compiler_result", {}))
            if isinstance(payload.get("compiler_result", {}), dict)
            else {},
            source_pack=[dict(item) for item in payload.get("source_pack", []) if isinstance(item, dict)]
            if isinstance(payload.get("source_pack", []), list)
            else [],
        )


def create_wiki_draft_job(
    base_dir: Path,
    *,
    task_id: str,
    topic: str,
    source_refs: list[str],
    model: str = "",
) -> WikiJobRecord:
    normalized_task_id = task_id.strip()
    load_state(base_dir, normalized_task_id)
    normalized_topic = topic.strip()
    if not normalized_topic:
        raise ValueError("Wiki draft topic must be non-empty.")
    return _persist_new_job(
        base_dir,
        task_id=normalized_task_id,
        action="draft",
        topic=normalized_topic,
        source_refs=_normalize_source_refs(source_refs),
        model=model,
    )


def create_wiki_refine_job(
    base_dir: Path,
    *,
    task_id: str,
    mode: str,
    target_object_id: str,
    source_refs: list[str],
    model: str = "",
) -> WikiJobRecord:
    normalized_task_id = task_id.strip()
    load_state(base_dir, normalized_task_id)
    normalized_mode = mode.strip()
    if normalized_mode not in {"supersede", "refines"}:
        raise ValueError("Wiki refine mode must be supersede or refines.")
    normalized_target = target_object_id.strip()
    if not normalized_target:
        raise ValueError("Wiki refine target_object_id must be non-empty.")
    return _persist_new_job(
        base_dir,
        task_id=normalized_task_id,
        action="refine",
        mode=normalized_mode,
        target_object_id=normalized_target,
        source_refs=_normalize_source_refs(source_refs),
        model=model,
    )


def load_wiki_job_record(base_dir: Path, job_id: str) -> WikiJobRecord:
    job_path = _find_wiki_job_path(base_dir, job_id)
    if job_path is None:
        raise FileNotFoundError(f"Unknown wiki job: {_normalize_job_id(job_id)}")
    return WikiJobRecord.from_dict(json.loads(job_path.read_text(encoding="utf-8")))


def load_wiki_job_result(base_dir: Path, job_id: str) -> dict[str, object]:
    job = load_wiki_job_record(base_dir, job_id)
    return {
        "job": job.to_dict(),
        "result_ready": job.status == "completed",
        "candidate": dict(job.candidate),
        "prompt_pack": dict(job.prompt_pack),
        "compiler_result": dict(job.compiler_result),
        "source_pack": [dict(item) for item in job.source_pack],
    }


def run_wiki_job(base_dir: Path, job_id: str) -> WikiJobRecord:
    job = load_wiki_job_record(base_dir, job_id)
    if job.status != "queued":
        return job

    running = _write_job_record(base_dir, replace(job, status="running", updated_at=utc_now()))
    try:
        if running.action == "draft":
            result = draft_wiki_command(
                base_dir,
                task_id=running.task_id,
                topic=running.topic,
                source_refs=list(running.source_refs),
                model=running.model,
            )
        else:
            result = refine_wiki_command(
                base_dir,
                task_id=running.task_id,
                mode=running.mode,
                target_object_id=running.target_object_id,
                source_refs=list(running.source_refs),
                model=running.model,
            )
    except Exception as exc:
        return _write_job_record(
            base_dir,
            replace(running, status="failed", updated_at=utc_now(), error=str(exc)),
        )

    candidate = result.candidate.to_dict() if result.candidate is not None else {}
    completed = replace(
        running,
        status="completed",
        updated_at=utc_now(),
        candidate_id=str(candidate.get("candidate_id", "")).strip(),
        prompt_artifact=_path_for_record(base_dir, result.prompt_artifact),
        result_artifact=_path_for_record(base_dir, result.result_artifact),
        error="",
        candidate=candidate,
        prompt_pack=dict(result.prompt_pack),
        compiler_result=dict(result.compiler_result),
        source_pack=[dict(item) for item in result.source_pack],
    )
    return _write_job_record(base_dir, completed)


def _persist_new_job(
    base_dir: Path,
    *,
    task_id: str,
    action: str,
    source_refs: list[str],
    topic: str = "",
    mode: str = "",
    target_object_id: str = "",
    model: str = "",
) -> WikiJobRecord:
    timestamp = utc_now()
    job = WikiJobRecord(
        job_id=_new_job_id(base_dir),
        task_id=task_id,
        action=action,
        status="queued",
        created_at=timestamp,
        updated_at=timestamp,
        topic=topic.strip(),
        mode=mode.strip(),
        target_object_id=target_object_id.strip(),
        source_refs=source_refs,
        model=model.strip(),
    )
    return _write_job_record(base_dir, job)


def _write_job_record(base_dir: Path, job: WikiJobRecord) -> WikiJobRecord:
    write_artifact(
        base_dir,
        job.task_id,
        f"wiki_jobs/{job.job_id}.json",
        json.dumps(job.to_dict(), indent=2, sort_keys=True),
    )
    return job


def _find_wiki_job_path(base_dir: Path, job_id: str) -> Path | None:
    normalized_id = _normalize_job_id(job_id)
    root = tasks_root(base_dir)
    if not root.exists():
        return None
    matches = sorted(root.glob(f"*/artifacts/wiki_jobs/{normalized_id}.json"))
    return matches[0] if matches else None


def _new_job_id(base_dir: Path) -> str:
    for _ in range(10):
        job_id = f"wiki-job-{uuid4().hex[:12]}"
        if _find_wiki_job_path(base_dir, job_id) is None:
            return job_id
    raise RuntimeError("Unable to allocate a unique wiki job id.")


def _normalize_job_id(job_id: str) -> str:
    normalized = str(job_id).strip()
    if not normalized.startswith("wiki-job-"):
        raise ValueError("Wiki job id must start with 'wiki-job-'.")
    if not all(char.isalnum() or char in {"-", "_"} for char in normalized):
        raise ValueError("Wiki job id contains unsupported characters.")
    return normalized


def _normalize_source_refs(source_refs: list[str]) -> list[str]:
    normalized = [str(item).strip() for item in source_refs if str(item).strip()]
    if not normalized:
        raise ValueError("At least one source_ref is required.")
    return normalized


def _path_for_record(base_dir: Path, path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return path.relative_to(base_dir).as_posix()
    except ValueError:
        return path.as_posix()
