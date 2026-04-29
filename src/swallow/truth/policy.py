from __future__ import annotations

from pathlib import Path

from ..consistency_audit import save_audit_trigger_policy
from ..models import AuditTriggerPolicy
from ..mps_policy_store import save_mps_policy


class PolicyRepo:
    def _apply_policy_change(
        self,
        *,
        base_dir: Path,
        audit_trigger_policy: AuditTriggerPolicy | None = None,
        mps_kind: str | None = None,
        mps_value: int | None = None,
    ) -> tuple[str, Path]:
        if audit_trigger_policy is not None:
            return ("audit_trigger_policy", save_audit_trigger_policy(base_dir, audit_trigger_policy))
        if mps_kind is not None and mps_value is not None:
            return ("mps_policy", save_mps_policy(base_dir, mps_kind, mps_value))
        raise ValueError("policy change requires audit_trigger_policy or mps policy fields.")
