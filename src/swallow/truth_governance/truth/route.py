from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from .. import sqlite_store
from swallow.application.infrastructure.identity import local_actor
from swallow.orchestration.models import utc_now
from swallow.provider_router.router import (
    apply_route_capability_profiles,
    apply_route_registry,
    apply_route_policy,
    apply_route_weights,
    route_metadata_snapshot,
)
from swallow.provider_router.route_metadata_store import (
    save_route_capability_profiles,
    save_route_registry,
    save_route_policy,
    save_route_weights,
)


class RouteRepo:
    def _apply_metadata_change(
        self,
        *,
        base_dir: Path,
        route_registry: dict[str, dict[str, object]] | None = None,
        route_policy: dict[str, object] | None = None,
        route_weights: dict[str, float] | None = None,
        route_capability_profiles: dict[str, dict[str, object]] | None = None,
        proposal_id: str | None = None,
    ) -> tuple[str, ...]:
        connection = sqlite_store.get_connection(base_dir)
        before_snapshot = route_metadata_snapshot(base_dir)
        applied_writes: list[str] = []
        connection.execute("BEGIN IMMEDIATE")
        try:
            if route_registry is not None:
                save_route_registry(base_dir, route_registry)
                apply_route_registry(base_dir)
                applied_writes.append("route_registry")

            if route_policy is not None:
                save_route_policy(base_dir, route_policy)
                apply_route_policy(base_dir)
                applied_writes.append("route_policy")

            if route_weights is not None:
                save_route_weights(base_dir, route_weights)
                apply_route_weights(base_dir)
                applied_writes.append("route_weights")

            if route_capability_profiles is not None:
                save_route_capability_profiles(base_dir, route_capability_profiles)
                apply_route_capability_profiles(base_dir)
                applied_writes.append("route_capability_profiles")

            after_snapshot = route_metadata_snapshot(base_dir)
            _write_route_change_logs(
                connection,
                proposal_id=proposal_id,
                before_snapshot=before_snapshot,
                after_snapshot=after_snapshot,
                applied_writes=applied_writes,
            )
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            apply_route_registry(base_dir)
            apply_route_policy(base_dir)
            apply_route_weights(base_dir)
            apply_route_capability_profiles(base_dir)
            raise

        return tuple(applied_writes)


def _write_route_change_logs(
    connection,
    *,
    proposal_id: str | None,
    before_snapshot: dict[str, object],
    after_snapshot: dict[str, object],
    applied_writes: list[str],
) -> None:
    for target_kind in applied_writes:
        connection.execute(
            """
            INSERT INTO route_change_log (
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
                f"route-change-{uuid4().hex}",
                proposal_id,
                target_kind,
                target_kind,
                "upsert",
                json.dumps(before_snapshot.get(target_kind), sort_keys=True),
                json.dumps(after_snapshot.get(target_kind), sort_keys=True),
                utc_now(),
                local_actor(),
            ),
        )
