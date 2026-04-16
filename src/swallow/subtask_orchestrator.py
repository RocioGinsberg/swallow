from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from .models import ExecutorResult, RetrievalItem, TaskCard, TaskState, utc_now
from .review_gate import ReviewGateResult


MAX_SUBTASK_WORKERS = 4

ExecuteCard = Callable[[Path, TaskState, TaskCard, list[RetrievalItem]], ExecutorResult]
ReviewCard = Callable[[ExecutorResult, TaskCard], ReviewGateResult]


@dataclass(slots=True)
class SubtaskRunRecord:
    card_id: str
    subtask_index: int
    goal: str
    depends_on: list[str] = field(default_factory=list)
    status: str = "completed"
    started_at: str = field(default_factory=utc_now)
    completed_at: str = field(default_factory=utc_now)
    executor_result: ExecutorResult | None = None
    review_gate_result: ReviewGateResult | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class SubtaskOrchestratorResult:
    status: str
    message: str
    records: list[SubtaskRunRecord] = field(default_factory=list)
    levels: list[list[str]] = field(default_factory=list)
    completed_count: int = 0
    failed_count: int = 0
    failed_card_ids: list[str] = field(default_factory=list)
    max_parallelism: int = 0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _clone_state(state: TaskState) -> TaskState:
    return TaskState.from_dict(state.to_dict())


def _failure_review_gate_result(detail: str) -> ReviewGateResult:
    return ReviewGateResult(
        status="failed",
        message="Subtask execution failed before review gate completed.",
        checks=[
            {
                "name": "subtask_execution",
                "passed": False,
                "detail": detail,
            }
        ],
    )


def _validate_cards(cards: list[TaskCard]) -> None:
    if not cards:
        return

    seen_card_ids: set[str] = set()
    known_card_ids = {card.card_id for card in cards}
    for card in cards:
        if card.card_id in seen_card_ids:
            raise ValueError(f"Duplicate task card id: {card.card_id}")
        seen_card_ids.add(card.card_id)
        for dependency in card.depends_on:
            if dependency == card.card_id:
                raise ValueError(f"Task card {card.card_id} cannot depend on itself.")
            if dependency not in known_card_ids:
                raise ValueError(f"Task card {card.card_id} depends on unknown card: {dependency}")


def build_subtask_levels(cards: list[TaskCard]) -> list[list[TaskCard]]:
    _validate_cards(cards)
    if not cards:
        return []

    cards_by_id = {card.card_id: card for card in cards}
    order_index = {card.card_id: index for index, card in enumerate(cards)}
    indegree = {card.card_id: len(card.depends_on) for card in cards}
    dependents: dict[str, list[str]] = {card.card_id: [] for card in cards}
    for card in cards:
        for dependency in card.depends_on:
            dependents[dependency].append(card.card_id)

    ready = [card.card_id for card in cards if indegree[card.card_id] == 0]
    levels: list[list[TaskCard]] = []
    processed_count = 0

    while ready:
        current_level_ids = sorted(ready, key=lambda card_id: order_index[card_id])
        levels.append([cards_by_id[card_id] for card_id in current_level_ids])
        ready = []
        for card_id in current_level_ids:
            processed_count += 1
            for dependent_id in dependents[card_id]:
                indegree[dependent_id] -= 1
                if indegree[dependent_id] == 0:
                    ready.append(dependent_id)

    if processed_count != len(cards):
        raise ValueError("Task cards contain cyclic dependencies.")
    return levels


class SubtaskOrchestrator:
    def __init__(
        self,
        execute_card: ExecuteCard,
        review_card: ReviewCard,
        *,
        max_workers: int = MAX_SUBTASK_WORKERS,
    ) -> None:
        self._execute_card = execute_card
        self._review_card = review_card
        self._max_workers = max(1, min(max_workers, MAX_SUBTASK_WORKERS))

    def _run_single_card(
        self,
        base_dir: Path,
        state: TaskState,
        card: TaskCard,
        retrieval_items: list[RetrievalItem],
    ) -> SubtaskRunRecord:
        started_at = utc_now()
        isolated_state = _clone_state(state)
        try:
            executor_result = self._execute_card(base_dir, isolated_state, card, retrieval_items)
            review_gate_result = self._review_card(executor_result, card)
        except Exception as exc:  # pragma: no cover - defensive path
            executor_result = ExecutorResult(
                executor_name="subtask-orchestrator",
                status="failed",
                message=f"Subtask execution raised {type(exc).__name__}.",
                failure_kind="subtask_exception",
                stderr=str(exc),
            )
            review_gate_result = _failure_review_gate_result(
                f"subtask raised {type(exc).__name__}: {exc}"
            )

        status = (
            "completed"
            if executor_result.status == "completed" and review_gate_result.status == "passed"
            else "failed"
        )
        return SubtaskRunRecord(
            card_id=card.card_id,
            subtask_index=card.subtask_index,
            goal=card.goal,
            depends_on=list(card.depends_on),
            status=status,
            started_at=started_at,
            completed_at=utc_now(),
            executor_result=executor_result,
            review_gate_result=review_gate_result,
        )

    def run(
        self,
        base_dir: Path,
        state: TaskState,
        cards: list[TaskCard],
        retrieval_items: list[RetrievalItem],
    ) -> SubtaskOrchestratorResult:
        levels = build_subtask_levels(cards)
        if not levels:
            return SubtaskOrchestratorResult(
                status="completed",
                message="No subtask cards were provided.",
                records=[],
                levels=[],
                completed_count=0,
                failed_count=0,
                failed_card_ids=[],
                max_parallelism=0,
            )

        records_by_id: dict[str, SubtaskRunRecord] = {}
        serialized_levels = [[card.card_id for card in level] for level in levels]
        for level in levels:
            if len(level) == 1:
                card = level[0]
                record = self._run_single_card(base_dir, state, card, retrieval_items)
                records_by_id[card.card_id] = record
                continue

            with ThreadPoolExecutor(max_workers=min(self._max_workers, len(level))) as executor:
                future_to_card = {
                    executor.submit(self._run_single_card, base_dir, state, card, retrieval_items): card
                    for card in level
                }
                for future in as_completed(future_to_card):
                    card = future_to_card[future]
                    records_by_id[card.card_id] = future.result()

        records = [records_by_id[card.card_id] for card in cards]
        failed_card_ids = [record.card_id for record in records if record.status != "completed"]
        failed_count = len(failed_card_ids)
        completed_count = len(records) - failed_count
        return SubtaskOrchestratorResult(
            status="completed" if failed_count == 0 else "failed",
            message="All subtasks completed successfully."
            if failed_count == 0
            else f"{failed_count} subtasks failed execution or review.",
            records=records,
            levels=serialized_levels,
            completed_count=completed_count,
            failed_count=failed_count,
            failed_card_ids=failed_card_ids,
            max_parallelism=max(len(level) for level in levels),
        )
