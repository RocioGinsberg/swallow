from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from swallow.orchestration.models import (
    ExecutorResult,
    META_OPTIMIZER_MEMORY_AUTHORITY,
    META_OPTIMIZER_SYSTEM_ROLE,
    TaskCard,
    TaskState,
)
from swallow.application.services.meta_optimizer_lifecycle import load_optimization_proposal_bundle, save_optimization_proposal_bundle
from swallow.application.services.meta_optimizer_models import (
    META_OPTIMIZER_AGENT_NAME,
    META_OPTIMIZER_EXECUTOR_NAME,
    META_OPTIMIZER_SNAPSHOT_KIND,
    MetaOptimizerSnapshot,
)
from swallow.application.services.meta_optimizer_reports import build_meta_optimizer_report
from swallow.application.services.meta_optimizer_snapshot import build_meta_optimizer_snapshot
from swallow.application.infrastructure.paths import latest_optimization_proposal_bundle_path, optimization_proposals_path

class MetaOptimizerAgent:
    """Stateful specialist entity for read-only optimization telemetry analysis."""

    agent_name = META_OPTIMIZER_AGENT_NAME
    system_role = META_OPTIMIZER_SYSTEM_ROLE
    memory_authority = META_OPTIMIZER_MEMORY_AUTHORITY

    def _resolve_last_n(self, card: TaskCard) -> int:
        raw_last_n = card.input_context.get("last_n", 100)
        if isinstance(raw_last_n, bool):
            raise ValueError("MetaOptimizerAgent input_context.last_n must be a positive integer.")
        try:
            last_n = int(raw_last_n)
        except (TypeError, ValueError) as exc:
            raise ValueError("MetaOptimizerAgent input_context.last_n must be a positive integer.") from exc
        if last_n <= 0:
            raise ValueError("MetaOptimizerAgent input_context.last_n must be greater than 0.")
        return last_n

    def _build_prompt(self, state: TaskState, card: TaskCard, *, last_n: int) -> str:
        return "\n".join(
            [
                "# Meta-Optimizer Agent Task",
                "",
                f"- task_id: {state.task_id}",
                f"- agent_name: {self.agent_name}",
                f"- executor_role: {self.system_role}",
                f"- memory_authority: {self.memory_authority}",
                f"- task_limit: {last_n}",
                f"- route_name: {state.route_name or 'pending'}",
                f"- executor_name: {state.executor_name or self.agent_name}",
                f"- goal: {card.goal or state.goal}",
                "- workflow: scan recent task telemetry, summarize route and workflow signals, emit structured proposals, persist read-only proposal artifacts",
            ]
        )

    def execute(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[object],
    ) -> ExecutorResult:
        del retrieval_items

        last_n = self._resolve_last_n(card)
        prompt = self._build_prompt(state, card, last_n=last_n)
        started_at = time.perf_counter()
        snapshot, artifact_path, _report = run_meta_optimizer(base_dir, last_n=last_n)
        bundle_path = latest_optimization_proposal_bundle_path(base_dir)
        bundle = load_optimization_proposal_bundle(bundle_path)
        output_payload = {
            "kind": META_OPTIMIZER_SNAPSHOT_KIND,
            "agent_name": self.agent_name,
            "system_role": self.system_role,
            "memory_authority": self.memory_authority,
            "report_artifact": str(artifact_path),
            "bundle_path": str(bundle_path),
            "bundle_id": bundle.bundle_id,
            "snapshot": snapshot.to_dict(),
        }
        proposal_count = len(snapshot.proposals)
        scanned_task_count = len(snapshot.scanned_task_ids)
        latency_ms = int(round((time.perf_counter() - started_at) * 1000))
        return ExecutorResult(
            executor_name=META_OPTIMIZER_EXECUTOR_NAME,
            status="completed",
            message=(
                f"MetaOptimizerAgent generated {proposal_count} proposal(s) from "
                f"{scanned_task_count} scanned task(s)."
            ),
            output=json.dumps(output_payload, indent=2, sort_keys=True) + "\n",
            prompt=prompt,
            dialect="plain_text",
            latency_ms=max(latency_ms, 0),
            side_effects={
                "kind": META_OPTIMIZER_SNAPSHOT_KIND,
                "bundle_path": str(bundle_path),
                "report_artifact": str(artifact_path),
                "proposal_count": proposal_count,
                "scanned_task_count": scanned_task_count,
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


class MetaOptimizerExecutor(MetaOptimizerAgent):
    """Compatibility wrapper that preserves the historical executor name while delegating to MetaOptimizerAgent."""


def run_meta_optimizer(base_dir: Path, last_n: int = 100) -> tuple[MetaOptimizerSnapshot, Path, str]:
    snapshot = build_meta_optimizer_snapshot(base_dir, last_n=last_n)
    report = build_meta_optimizer_report(snapshot)
    artifact_path = optimization_proposals_path(base_dir)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(report, encoding="utf-8")
    save_optimization_proposal_bundle(base_dir, snapshot, artifact_path)
    return snapshot, artifact_path, report
