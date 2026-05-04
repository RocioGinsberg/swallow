from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from .. import sqlite_store
from swallow.application.services.consistency_audit import AUDIT_TRIGGER_POLICY_ID, load_audit_trigger_policy, save_audit_trigger_policy
from swallow.application.infrastructure.identity import local_actor
from swallow.orchestration.models import AuditTriggerPolicy
from swallow.orchestration.models import utc_now
from swallow.application.services.mps_policy_store import read_mps_policy, save_mps_policy


class PolicyRepo:
    def _apply_policy_change(
        self,
        *,
        base_dir: Path,
        audit_trigger_policy: AuditTriggerPolicy | None = None,
        mps_kind: str | None = None,
        mps_value: int | None = None,
        proposal_id: str | None = None,
    ) -> tuple[str, Path]:
        connection = sqlite_store.get_connection(base_dir)
        if audit_trigger_policy is not None:
            load_audit_trigger_policy(base_dir)
            target_kind = "audit_trigger_policy"
            target_id = AUDIT_TRIGGER_POLICY_ID
            before_payload = _policy_record_payload(connection, target_id)
            connection.execute("BEGIN IMMEDIATE")
            try:
                path = save_audit_trigger_policy(base_dir, audit_trigger_policy)
                after_payload = _policy_record_payload(connection, target_id)
                _write_policy_change_log(
                    connection,
                    proposal_id=proposal_id,
                    target_kind=target_kind,
                    target_id=target_id,
                    before_payload=before_payload,
                    after_payload=after_payload,
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
            return (target_kind, path)
        if mps_kind is not None and mps_value is not None:
            read_mps_policy(base_dir, mps_kind)
            target_kind = "mps_policy"
            target_id = f"mps:{mps_kind}"
            before_payload = _policy_record_payload(connection, target_id)
            connection.execute("BEGIN IMMEDIATE")
            try:
                path = save_mps_policy(base_dir, mps_kind, mps_value)
                after_payload = _policy_record_payload(connection, target_id)
                _write_policy_change_log(
                    connection,
                    proposal_id=proposal_id,
                    target_kind=target_kind,
                    target_id=target_id,
                    before_payload=before_payload,
                    after_payload=after_payload,
                )
                connection.execute("COMMIT")
            except Exception:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
            return (target_kind, path)
        raise ValueError("policy change requires audit_trigger_policy or mps policy fields.")


def _policy_record_payload(connection, policy_id: str) -> object | None:
    row = connection.execute(
        "SELECT payload FROM policy_records WHERE policy_id = ?",
        (policy_id,),
    ).fetchone()
    if row is None:
        return None
    try:
        return json.loads(str(row["payload"]))
    except json.JSONDecodeError:
        return None


def _write_policy_change_log(
    connection,
    *,
    proposal_id: str | None,
    target_kind: str,
    target_id: str,
    before_payload: object | None,
    after_payload: object | None,
) -> None:
    connection.execute(
        """
        INSERT INTO policy_change_log (
            change_id,
            proposal_id,
            target_kind,
            target_id,
            action,
            before_payload,
            after_payload,
            timestamp,
            actor
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"policy-change-{uuid4().hex}",
            proposal_id,
            target_kind,
            target_id,
            "upsert",
            json.dumps(before_payload, sort_keys=True),
            json.dumps(after_payload, sort_keys=True),
            utc_now(),
            local_actor(),
        ),
    )
