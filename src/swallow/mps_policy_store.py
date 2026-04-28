from __future__ import annotations

import json
from pathlib import Path

from .paths import mps_policy_path
from .store import apply_atomic_text_updates


MPS_ROUND_LIMIT_KIND = "mps_round_limit"
MPS_PARTICIPANT_LIMIT_KIND = "mps_participant_limit"
MPS_POLICY_KINDS = {MPS_ROUND_LIMIT_KIND, MPS_PARTICIPANT_LIMIT_KIND}


def normalize_mps_policy_kind(kind: str) -> str:
    normalized = kind.strip()
    if normalized not in MPS_POLICY_KINDS:
        expected = ", ".join(sorted(MPS_POLICY_KINDS))
        raise ValueError(f"unknown MPS policy kind: {kind!r}. Expected one of: {expected}")
    return normalized


def validate_mps_policy_value(kind: str, value: int) -> int:
    normalized_kind = normalize_mps_policy_kind(kind)
    try:
        normalized_value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{normalized_kind} value must be an integer.") from exc
    if normalized_value < 1:
        raise ValueError(f"{normalized_kind} value must be >= 1, got {normalized_value}")
    if normalized_kind == MPS_ROUND_LIMIT_KIND and normalized_value > 3:
        raise ValueError("mps_round_limit value must be <= 3 (ORCHESTRATION section 5.3 hard max)")
    return normalized_value


def _read_policy_payload(base_dir: Path) -> dict[str, int]:
    path = mps_policy_path(base_dir)
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"MPS policy file must contain a JSON object: {path}")
    policies: dict[str, int] = {}
    for raw_kind, raw_value in payload.items():
        kind = normalize_mps_policy_kind(str(raw_kind))
        try:
            value = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{kind} value must be an integer.") from exc
        policies[kind] = validate_mps_policy_value(kind, value)
    return policies


def read_mps_policy(base_dir: Path, kind: str) -> int | None:
    normalized_kind = normalize_mps_policy_kind(kind)
    return _read_policy_payload(base_dir).get(normalized_kind)


def save_mps_policy(base_dir: Path, kind: str, value: int) -> Path:
    normalized_kind = normalize_mps_policy_kind(kind)
    normalized_value = validate_mps_policy_value(normalized_kind, value)
    payload = _read_policy_payload(base_dir)
    payload[normalized_kind] = normalized_value
    path = mps_policy_path(base_dir)
    apply_atomic_text_updates({path: json.dumps(payload, indent=2, sort_keys=True) + "\n"})
    return path
