---
author: codex
phase: orchestration-lifecycle-decomposition
slice: m5-knowledge-flow-facade-closeout
status: final
depends_on:
  - docs/plans/orchestration-lifecycle-decomposition/plan.md
  - docs/plans/orchestration-lifecycle-decomposition/plan_audit.md
  - docs/plans/orchestration-lifecycle-decomposition/review_comments.md
  - docs/concerns_backlog.md
  - docs/active_context.md
  - docs/design/INVARIANTS.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/TEST_ARCHITECTURE.md
---

TL;DR:
LTO-8 Step 1 completed a behavior-preserving decomposition of `orchestrator.py` into focused orchestration helpers while keeping task advancement authority in `orchestrator.py`.
No helper imports or calls `save_state`; M4/M5 helpers also avoid event append and executor/harness dependencies.
Implementation and Claude PR review both passed full default pytest: `686 passed, 8 deselected, 10 subtests passed`; review recommends merge with 3 non-blocking concerns tracked in `docs/concerns_backlog.md`.

# Orchestration Lifecycle Decomposition Closeout

## Scope

- phase: `Orchestration Lifecycle Decomposition / LTO-8 Step 1`
- branch: `feat/orchestration-lifecycle-decomposition`
- implementation mode: facade-first / behavior-preserving decomposition
- public compatibility target: `swallow.orchestration.orchestrator`
- design docs changed: none
- task state schema changed: no
- route / Provider Router behavior changed: no
- live HTTP/API-key test required: no

## What Was Completed

1. M1 extracted lifecycle payload helpers into `task_lifecycle.py`.
2. M2 extracted retrieval request / previous retrieval loading helpers into `retrieval_flow.py`.
3. M3 extracted artifact path/copy helpers and subtask artifact glue into `artifact_writer.py` and `subtask_flow.py`.
4. M4 extracted execution attempt metadata, budget payload/result helpers, and pure debate-loop core into `execution_attempts.py`.
5. M5 extracted low-risk knowledge-flow helpers into `knowledge_flow.py`.
6. Focused unit tests were added under `tests/unit/orchestration/` for every new helper module.
7. `orchestrator.py` remains the facade and owner for `create_task`, `run_task`, `run_task_async`, state persistence, event append, executor invocation, review gate consumption, and proposal application.

## Final Module Ownership

| Module | Ownership |
|---|---|
| `task_lifecycle.py` | phase event/checkpoint/recovery fallback payload builders |
| `retrieval_flow.py` | retrieval source policy selection, retrieval request construction, previous retrieval artifact loading |
| `artifact_writer.py` | create/run artifact path maps, parent executor artifact writes, prefixed executor artifact copies |
| `subtask_flow.py` | subtask attempt artifact serialization, extra artifact collection, subtask artifact refs |
| `execution_attempts.py` | attempt metadata, budget exhausted payload/result helpers, generic sync/async debate-loop core |
| `knowledge_flow.py` | knowledge store write-plan construction, knowledge objects report preparation, knowledge event summary payloads |
| `orchestrator.py` | Control Plane facade and all task advancement / truth-write sequencing |

## Boundary Notes

- `run_task`, `run_task_async`, and `create_task` remain in `orchestrator.py`.
- All `save_state(...)` calls remain outside extracted helper modules.
- Helper modules do not call `append_event(...)`.
- M4 helper event append allowlist is `none`.
- `knowledge_flow.py` does not import or call `apply_proposal`.
- `_apply_librarian_side_effects(...)` remains in `orchestrator.py`.
- `decide_task_knowledge(...)` remains in `orchestrator.py`.
- Canonical / route / policy truth mutation remains governed by `apply_proposal`.
- `harness.py` migration was not part of this phase.
- Path A / B / C boundaries were not changed.

## Validation Commands Run

Focused validation:

```bash
.venv/bin/python -m pytest tests/unit/orchestration -q
# 35 passed

.venv/bin/python -m pytest tests/test_librarian_executor.py -q
# 6 passed

.venv/bin/python -m pytest tests/test_invariant_guards.py -q
# 25 passed

.venv/bin/python -m pytest tests/test_cli.py -k "knowledge or canonical_reuse or librarian" -q
# 50 passed, 192 deselected, 2 subtests passed

.venv/bin/python -m pytest tests/test_review_gate.py -q
# 13 passed
```

Final validation:

```bash
.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# passed

rg -n "save_state|append_event|apply_proposal|orchestration\.harness|orchestration\.executor" src/swallow/orchestration/knowledge_flow.py
# no matches

.venv/bin/python -c "import sys; import swallow.orchestration.knowledge_flow; print('swallow.orchestration.executor' in sys.modules); print('swallow.orchestration.harness' in sys.modules)"
# False
# False

.venv/bin/python -m pytest -q
# 686 passed, 8 deselected, 10 subtests passed
```

Earlier milestone validation is recorded in `docs/active_context.md`.

## Review Status

Claude PR review has been produced:

- review file: `docs/plans/orchestration-lifecycle-decomposition/review_comments.md`
- reviewed branch/head: `feat/orchestration-lifecycle-decomposition` @ `fe31d72`
- recommendation: merge
- blocking findings: none
- audit resolution: all 1 BLOCKER + 7 CONCERNs from `plan_audit.md` are resolved
- review validation: full default pytest reverified with `686 passed, 8 deselected, 10 subtests passed`
- follow-up concerns: 3 non-blocking concerns recorded in `docs/concerns_backlog.md`

## Deferred Follow-up

- Further reduction of `orchestrator.py` can continue in later LTO-8 slices, but should remain facade-first.
- `execution_attempts.debate_loop_core` / `debate_loop_core_async` callback shape should be revisited or documented so telemetry callbacks cannot be mistaken for a state-advancement control pattern.
- `harness.py` decomposition remains a separate future target.
- Public CLI / FastAPI / Meta Optimizer surface split remains LTO-9.
- LTO-7 route metadata guard allowlist drift should be fixed in LTO-9 rather than waiting for LTO-10.
- Governance handler split remains LTO-10.
- Any future move of `_apply_librarian_side_effects(...)` requires an explicit plan for the `apply_proposal` boundary.
- Post-merge roadmap update should mark LTO-8 as `Step 1 done`, not fully complete.

## Completion Status

Implementation, validation, and Claude PR review for LTO-8 Step 1 are complete. The branch is ready for Human PR submission / merge decision after the review-closeout docs are committed.
