---
author: codex
phase: orchestration-lifecycle-decomposition
slice: lto8-step1-plan
status: draft
depends_on:
  - docs/roadmap.md
  - docs/design/INVARIANTS.md
  - docs/design/ORCHESTRATION.md
  - docs/design/HARNESS.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/TEST_ARCHITECTURE.md
  - docs/plans/provider-router-split/closeout.md
---

TL;DR:
LTO-8 Step 1 is a behavior-preserving orchestration decomposition, not a task lifecycle redesign.
`run_task` / `run_task_async` remain the Control Plane entry; extracted helpers may organize lifecycle, attempts, retrieval, artifacts, and subtask glue but must not independently advance task state.
Implementation starts only after plan audit, Human Plan Gate, and branch switch to `feat/orchestration-lifecycle-decomposition`.

# Orchestration Lifecycle Decomposition Plan

## Frame

- track: `Architecture / Engineering`
- phase: `Orchestration Lifecycle Decomposition / LTO-8 Step 1`
- roadmap ticket: `Orchestration lifecycle decomposition`
- recommended branch: `feat/orchestration-lifecycle-decomposition`
- implementation mode: facade-first / behavior-preserving
- current planning branch: `main`

## Current Code Context

The current orchestration surface is concentrated in three large files:

| File | Current shape |
|---|---|
| `src/swallow/orchestration/orchestrator.py` | about 3853 lines; owns `create_task`, `run_task`, `run_task_async`, route application, retrieval phase, execution phase, review gate integration, waiting_human transition, artifact path map, and task knowledge operations |
| `src/swallow/orchestration/harness.py` | about 2077 lines; owns retrieval execution, artifact writing, summary/resume/report builders, policy artifact generation |
| `src/swallow/orchestration/executor.py` | about 1883 lines; owns executor registry, dialects, prompt execution, CLI/HTTP executor implementations, fallback output helpers |

This phase should start with `orchestrator.py` because LTO-8 is about lifecycle decomposition, but it must not move task advancement authority out of Orchestrator.

Existing extracted surfaces:

- `review_gate.py` already owns review-gate evaluation.
- `subtask_orchestrator.py` already owns subtask level scheduling and base subtask records.
- `task_semantics.py`, `dispatch_policy.py`, `execution_fit.py`, `retry_policy.py`, `stop_policy.py`, and `checkpoint_snapshot.py` already own adjacent focused policies.

## Goals

1. Reduce `orchestrator.py` by extracting focused orchestration helper modules with real ownership.
2. Keep `run_task` / `run_task_async` as the only public task-run advancement entry.
3. Preserve current sync / async behavior, route semantics, retry/debate behavior, subtask behavior, selective retry behavior, artifact names, and event payload compatibility.
4. Add focused tests under `tests/unit/orchestration/` for extracted helpers and retain integration regression coverage for `run_task`.
5. Strengthen the executable boundary that helpers do not become a second Control Plane.

## Non-Goals

- Do not introduce Planner / DAG / Strategy Router as first-class runtime components.
- Do not redesign task state schema or add SQLite migrations.
- Do not change route selection, Provider Router behavior, or executor registry behavior.
- Do not change Path A / B / C semantics.
- Do not move `create_task`, `run_task`, or `run_task_async` public ownership away from `orchestrator.py`.
- Do not let helper modules call `save_state(...)` or mutate task status as autonomous decisions unless the call remains clearly orchestrator-delegated and reviewed in plan audit.
- Do not split CLI / FastAPI / Meta Optimizer in this phase; those are LTO-9.
- Do not split `apply_proposal` private handlers; that is LTO-10.

## Design And Engineering Anchors

- `docs/design/INVARIANTS.md`
  - Control only in Orchestrator / Operator.
  - Execution never directly writes Truth.
  - Path A / B / C boundaries remain explicit.
  - `apply_proposal` remains the only canonical / route / policy mutation entry.
- `docs/design/ORCHESTRATION.md`
  - Validator and Review Gate stay separated.
  - Dynamic path switching remains Orchestrator decision, not executor autonomy.
  - Structured handoff remains artifact / truth based, not conversation based.
- `docs/design/HARNESS.md`
  - Harness provides controlled execution environment and artifact recovery, but does not decide task advancement.
- `docs/engineering/CODE_ORGANIZATION.md`
  - Orchestration target shape includes `task_lifecycle.py`, `execution_attempts.py`, `subtask_flow.py`, `knowledge_flow.py`, `retrieval_flow.py`, and `artifact_writer.py`.
- `docs/engineering/TEST_ARCHITECTURE.md`
  - New tests use `tests/unit/orchestration/` and focused integration tests rather than growing root aggregation files.

## Target Module Shape For This Phase

This phase does not need to complete the entire LTO-8 target. It should establish the first stable module ownership set:

| Module | Intended ownership |
|---|---|
| `task_lifecycle.py` | phase names, lifecycle checkpoint event payload helpers, selective-retry recovery descriptors, waiting-human/completion transition payload builders; no public task-run entry |
| `execution_attempts.py` | attempt metadata initialization and execution-attempt telemetry payload helpers; no executor invocation ownership |
| `retrieval_flow.py` | retrieval source policy family selection, retrieval request construction, previous retrieval artifact loading |
| `execution_flow.py` | previous executor artifact loading, parent executor artifact write helpers, fallback artifact prefix helpers, budget guard result builders |
| `knowledge_flow.py` | librarian side-effect application helpers and task knowledge write-plan helpers, behind Orchestrator calls |
| `artifact_index.py` | artifact path map construction for task run outputs |

`orchestrator.py` remains the facade and Control Plane owner. Existing callers keep importing from `swallow.orchestration.orchestrator`.

## Milestones

| Milestone | Scope | Risk | Default gate |
|---|---|---|---|
| M1 | Characterization tests and first pure lifecycle helpers | medium-high | `tests/unit/orchestration` focused tests + invariant guards |
| M2 | Extract retrieval flow and selective-retry loading helpers | medium | retrieval focused tests + `run_task` selective retry regression |
| M3 | Extract artifact index and execution artifact helpers | medium | artifact path/report regression + focused helper tests |
| M4 | Extract execution attempt / budget / debate helper ownership where safe | high | debate/retry/subtask focused regression + full orchestration tests |
| M5 | Extract knowledge-flow helper functions touched by task runs only if M1-M4 are stable | high | librarian/knowledge policy focused regression |
| M6 | Facade cleanup, closeout, PR body, full validation | medium | full pytest + compileall + diff hygiene |

## M1 Acceptance

M1 should be the first implementation slice after Plan Gate.

Scope:

- Add `tests/unit/orchestration/` if absent.
- Add characterization tests around lifecycle descriptors that do not require running a full task.
- Add `task_lifecycle.py` with pure helpers only.
- Keep `_set_phase(...)` or any direct `save_state(...)` phase transition inside `orchestrator.py` for M1 unless plan audit explicitly approves a delegated wrapper shape.
- Add a guard or focused assertion that extracted lifecycle helper module does not expose `run_task`, `run_task_async`, `create_task`, or a public state-advance entry.

Acceptance:

- No behavior change in `run_task`.
- No import churn outside orchestration tests and `orchestrator.py`.
- `tests/unit/orchestration -q` passes.
- `tests/test_invariant_guards.py -q` passes.
- `git diff --check` passes.

## M2 Acceptance

Scope:

- Move `_retrieval_policy_family`, `_select_source_types`, `build_task_retrieval_request`, and `_load_previous_retrieval_items` style logic into `retrieval_flow.py`.
- Preserve current default retrieval source policy:
  - autonomous CLI coding -> `knowledge`
  - API -> `knowledge`, `notes`
  - legacy local fallback -> `repo`, `notes`, `knowledge`
  - fallback -> `knowledge`, `notes`
- Keep Orchestrator deciding when retrieval is skipped or rerun.

Acceptance:

- Selective retry still falls back to retrieval when previous retrieval artifacts are missing or invalid.
- Existing retrieval source policy tests continue to pass.
- No retrieval source type or artifact path schema changes.

## M3 Acceptance

Scope:

- Extract artifact-path map construction into `artifact_index.py`.
- Extract parent executor artifact write / prefixed executor artifact copy helpers if they remain behavior-preserving.
- Preserve all artifact names currently produced by `run_task`.

Acceptance:

- Existing CLI / Web API artifact tests still pass.
- Focused artifact-index tests prove key paths remain stable.
- No `.swl/tasks/<task_id>/artifacts/*` filename changes.

## M4 Acceptance

Scope:

- Extract safe execution-attempt metadata helpers into `execution_attempts.py`.
- Evaluate whether budget guard result builders and debate-loop pure core can move without changing retry semantics.
- Keep executor invocation, review gate decision consumption, and status transition sequencing visibly orchestrator-owned.

Acceptance:

- Debate loop retry behavior remains unchanged.
- Budget-exhausted behavior still transitions to `waiting_human`.
- Subtask retry tests still pass.
- If a helper writes events, the plan audit must have approved its ownership and tests must prove it does not decide advancement independently.

## M5 Acceptance

Scope:

- Move librarian side-effect write-plan and report helpers only if the M1-M4 extraction leaves clear seams.
- Keep canonical / route / policy truth writes compliant with `apply_proposal`.
- Do not widen Specialist or Meta-Optimizer authority.

Acceptance:

- Librarian executor tests pass.
- Governance and canonical-write guard tests pass.
- No direct canonical / route / policy mutation entry is introduced.

## M6 Acceptance

Scope:

- Remove dead private implementations from `orchestrator.py` after facade delegation is stable.
- Update `closeout.md`, `current_state.md`, `docs/active_context.md`, and `pr.md`.
- Keep roadmap factual update for post-merge, not same-branch implementation churn.

Acceptance:

- Full default pytest passes.
- `compileall` passes.
- `git diff --check` passes.
- `orchestrator.py` remains the public compatibility facade for task creation/run entry points.

## Validation Plan

Focused gates selected by milestone:

```bash
.venv/bin/python -m pytest tests/unit/orchestration -q
.venv/bin/python -m pytest tests/test_invariant_guards.py -q
.venv/bin/python -m pytest tests/test_run_task_subtasks.py tests/test_subtask_orchestrator.py tests/test_review_gate.py -q
.venv/bin/python -m pytest tests/test_cli.py tests/test_web_api.py tests/test_consistency_audit.py -q
```

Milestone and PR gates:

```bash
.venv/bin/python -m compileall -q src/swallow
git diff --check
.venv/bin/python -m pytest -q
```

Eval:

- Not required for this phase. This is behavior-preserving orchestration decomposition, not quality-gradient retrieval / LLM output work.

## Risks And Controls

| Risk | Control |
|---|---|
| Helper module becomes a second Control Plane | Keep `run_task` / `run_task_async` public ownership in `orchestrator.py`; M1 helper is pure; audit any helper that calls `save_state` or `append_event` |
| Behavior changes hidden in extraction | Characterize current behavior before moving code; keep artifact names and event payload fields unchanged |
| Sync / async divergence widens | Extract shared pure builders first; do not split sync and async orchestration semantics into separate business paths |
| Subtask behavior regresses | Keep existing `subtask_orchestrator.py` as owner; LTO-8 only moves glue if tests prove parity |
| Knowledge writes drift across boundaries | Keep `apply_proposal` and repository write paths untouched; run governance guards |
| Over-broad branch | Stop at M6 closeout; do not include LTO-9 or LTO-10 work |

## Branch And Commit Strategy

- Plan branch/current branch: `main` is acceptable for this planning document and post-merge state sync.
- Implementation branch: `feat/orchestration-lifecycle-decomposition`.
- Human creates/switches branch after Plan Gate.
- Suggested milestone commits:
  - `test(orchestration): characterize lifecycle helpers`
  - `refactor(orchestration): extract retrieval flow`
  - `refactor(orchestration): extract artifact index`
  - `refactor(orchestration): extract execution attempt helpers`
  - `refactor(orchestration): extract knowledge flow helpers`
  - `docs(state): close orchestration lifecycle decomposition`

High-risk slices M4 and M5 should stay separate commits.

## Plan Gate Requirements

Before implementation:

1. `docs/plans/orchestration-lifecycle-decomposition/plan_audit.md` is produced.
2. No unresolved `[BLOCKER]` remains in `plan_audit.md`.
3. Human approves Plan Gate.
4. Current git branch matches `feat/orchestration-lifecycle-decomposition`.

## Completion Conditions

- `orchestrator.py` is materially smaller and delegates selected helper ownership to focused modules.
- Task run public APIs remain compatible.
- Control Plane authority remains inside Orchestrator / Operator.
- Existing run-task, review, subtask, retrieval, artifact, and governance tests pass.
- Closeout records module ownership, validation results, known follow-ups, and any deferred LTO-8 slices.
