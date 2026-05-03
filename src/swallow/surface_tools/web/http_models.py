from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from swallow.application.commands.tasks import (
    TaskAcknowledgeCommandResult,
    TaskRecoveryCommandResult,
    TaskRunCommandResult,
)
from swallow.orchestration.models import TaskState


JsonMap = dict[str, object]


@dataclass(frozen=True)
class WebRequestError(ValueError):
    message: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.message


def resolve_workspace_relative_file(base_dir: Path, raw_path: str) -> Path:
    path_text = raw_path.strip()
    if not path_text:
        raise WebRequestError("Path must be a non-empty workspace-relative path.")
    relative_path = Path(path_text)
    if relative_path.is_absolute():
        raise WebRequestError("Path must be relative to the workspace.")
    if any(part == ".." for part in relative_path.parts):
        raise WebRequestError("Path must not contain parent traversal segments.")

    candidate = base_dir / relative_path
    if not candidate.exists():
        raise WebRequestError(f"Path not found: {path_text}", status_code=404)
    if not candidate.is_file():
        raise WebRequestError(f"Path is not a file: {path_text}")
    return candidate


def task_response(state: TaskState) -> JsonMap:
    return {
        "task_id": state.task_id,
        "status": state.status,
        "phase": state.phase,
        "title": state.title,
        "goal": state.goal,
        "executor_name": state.executor_name,
        "route_name": state.route_name,
        "attempt_id": state.current_attempt_id,
        "attempt_number": state.current_attempt_number,
    }


def task_run_response(result: TaskRunCommandResult) -> JsonMap:
    return {"task": task_response(result.state)}


def task_acknowledge_response(result: TaskAcknowledgeCommandResult) -> JsonMap:
    if result.blocked:
        raise WebRequestError(result.blocked_reason, status_code=409)
    return {"task": task_response(result.state)}


def task_recovery_response(result: TaskRecoveryCommandResult) -> JsonMap:
    if result.blocked:
        payload: JsonMap = {
            "blocked": True,
            "blocked_kind": result.blocked_kind,
            "task": task_response(result.state),
        }
        if result.retry_policy is not None:
            payload["retry_policy"] = result.retry_policy
        if result.stop_policy is not None:
            payload["stop_policy"] = result.stop_policy
        if result.checkpoint_snapshot is not None:
            payload["checkpoint_snapshot"] = result.checkpoint_snapshot
        raise WebRequestError(_json_error_message(payload), status_code=409)
    return {
        "task": task_response(result.run_state or result.state),
        "previous_task": task_response(result.state),
    }


def stage_decision_response(candidate: Any) -> JsonMap:
    return {"candidate": candidate.to_dict()}


def stage_promote_response(result: Any) -> JsonMap:
    return {
        "candidate": result.candidate.to_dict(),
        "notices": list(result.notices),
    }


def proposal_review_response(result: Any, base_dir: Path) -> JsonMap:
    return {
        "review_record": result.review_record.to_dict(),
        "record_path": _relative_or_absolute(base_dir, result.record_path),
    }


def proposal_apply_response(result: Any, base_dir: Path) -> JsonMap:
    return {
        "application_record": result.application_record.to_dict(),
        "record_path": _relative_or_absolute(base_dir, result.record_path),
        "proposal_id": result.proposal_id,
    }

def _relative_or_absolute(base_dir: Path, path: Path) -> str:
    try:
        return path.relative_to(base_dir).as_posix()
    except ValueError:
        return path.as_posix()


def _json_error_message(payload: JsonMap) -> str:
    blocked_kind = str(payload.get("blocked_kind", "")).strip()
    return f"Task action is blocked: {blocked_kind or 'unknown'}"
