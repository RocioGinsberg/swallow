---
author: codex
phase: orchestration-lifecycle-decomposition
slice: m5-knowledge-flow-facade-closeout
status: review
depends_on:
  - docs/plans/orchestration-lifecycle-decomposition/plan.md
  - docs/plans/orchestration-lifecycle-decomposition/plan_audit.md
  - docs/active_context.md
  - docs/design/INVARIANTS.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/TEST_ARCHITECTURE.md
---

TL;DR:
LTO-8 Step 1 completed a behavior-preserving decomposition of `orchestrator.py` into focused orchestration helpers while keeping task advancement authority in `orchestrator.py`.
No helper imports or calls `save_state`; M4/M5 helpers also avoid event append and executor/harness dependencies.
Implementation validation passed with full default pytest: `686 passed, 8 deselected, 10 subtests passed`; Human M5 commit and Claude PR review are still pending.

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

Claude PR review has not been produced yet. Per `.agents/workflows/feature.md`, the next steps are:

1. Human reviews and commits M5 if accepted.
2. Claude reviews the completed feature branch and writes `docs/plans/orchestration-lifecycle-decomposition/review_comments.md`.
3. Codex updates `pr.md` if review findings change the merge summary.
4. Human decides the merge gate.

## Deferred Follow-up

- Further reduction of `orchestrator.py` can continue in later LTO-8 slices, but should remain facade-first.
- `harness.py` decomposition remains a separate future target.
- Public CLI / FastAPI / Meta Optimizer surface split remains LTO-9.
- Governance handler split remains LTO-10.
- Any future move of `_apply_librarian_side_effects(...)` requires an explicit plan for the `apply_proposal` boundary.

## Completion Status

Implementation and validation for LTO-8 Step 1 are complete. The branch is waiting for Human M5 review / commit before Claude PR review.
