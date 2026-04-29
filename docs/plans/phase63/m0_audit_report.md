---
author: codex
phase: phase63
slice: M0-pre-implementation-audit
status: final
depends_on:
  - docs/plans/phase63/kickoff.md
  - docs/plans/phase63/design_decision.md
  - docs/plans/phase63/risk_assessment.md
  - docs/plans/phase63/model_review.md
  - tests/audit_no_skip_drift.py
  - tests/audit_route_knowledge_to_staged.py
---

TL;DR: M0 audit found 2 NO_SKIP red signals, not a broad red-light set. Built-in production routes currently have 0 blocked memory-authority routes; static test-only blocked routes are Specialist routes, with no General Executor example. S5's SQLite `BEGIN IMMEDIATE` plan does not match current route/policy storage, which is filesystem JSON + in-memory route registry, so S5 needs Claude / Human path clarification before implementation.

## Scope

M0 was run as read-only / report-only audit. No production code was changed.

Artifacts added:

- `tests/audit_no_skip_drift.py` — report-only scan for the 8 NO_SKIP guards.
- `tests/audit_route_knowledge_to_staged.py` — report-only scan for blocked route taxonomy and `_route_knowledge_to_staged` call sites.

Validation commands:

```bash
.venv/bin/python tests/audit_no_skip_drift.py
.venv/bin/python tests/audit_route_knowledge_to_staged.py
.venv/bin/python -m pytest tests/test_invariant_guards.py
.venv/bin/python -m pytest
.venv/bin/python -m pytest tests/test_run_task_subtasks.py::RunTaskSubtaskIntegrationTest::test_run_task_times_out_one_parallel_subtask_without_canceling_other_work
git diff --check
```

Results:

- `tests/audit_no_skip_drift.py`: completed, 6 green / 2 red.
- `tests/audit_route_knowledge_to_staged.py`: completed.
- `tests/test_invariant_guards.py`: 9 passed.
- full pytest: 558 passed / 1 failed / 8 deselected; failure was `tests/test_run_task_subtasks.py::RunTaskSubtaskIntegrationTest::test_run_task_times_out_one_parallel_subtask_without_canceling_other_work`, elapsed 2.87s vs 1.75s threshold.
- targeted rerun of the failing test: 1 passed in 1.49s.
- `git diff --check`: passed.

The full-suite failure is a known timing-sensitive test shape rather than an M0 production-code regression: M0 changed no production code, and the failed timing test passed when rerun alone.

## Audit 1: NO_SKIP Guards

Report-only scan summary:

| Guard | Status | Findings |
|---|---:|---|
| `test_no_executor_can_write_task_table_directly` | green | none |
| `test_state_transitions_only_via_orchestrator` | green | none |
| `test_validator_returns_verdict_only` | green | none |
| `test_path_b_does_not_call_provider_router` | red | `src/swallow/executor.py:510` imports `fallback_route_for`; `src/swallow/executor.py:512` calls `fallback_route_for` |
| `test_specialist_internal_llm_calls_go_through_router` | red | `src/swallow/agent_llm.py:57` calls `httpx.post` directly; `literature_specialist.py` and `quality_reviewer.py` import / call `call_agent_llm` |
| `test_canonical_write_only_via_apply_proposal` | green | none |
| `test_only_apply_proposal_calls_private_writers` | green | none |
| `test_route_metadata_writes_only_via_apply_proposal` | green | none |

Interpretation:

- The pre-scan does **not** show a broad NO_SKIP failure set. It found 2 red signals.
- Both red signals are real boundary questions, not mechanical one-line drift:
  - `executor.py` owns route fallback logic inside executor execution paths. S4 needs a precise definition of whether this is a prohibited Path B Provider Router call or an allowed orchestrator-selected fallback helper currently placed in executor code.
  - Specialist-internal LLM calls currently go through `agent_llm.call_agent_llm`, which directly uses the HTTP completion endpoint. That does not currently pass through a route/provider governance seam.
- Existing Phase 61 / 62 invariant guards still pass: `tests/test_invariant_guards.py` -> 9 passed.

M0 scope implication:

- The design threshold says `<= 2` red signals can keep Phase 63 in the current plan, but these 2 are governance-boundary issues. S4 enforcement should not start until Claude / Human decide whether to repair them in Phase 63 or split them into Phase 63.5.

## Audit 2: Store Connection Mode

The S5 design asks whether route / policy store functions support a shared SQLite connection for `BEGIN IMMEDIATE` transaction wrapping. Current implementation does not use SQLite for these writes.

| Function | Current storage behavior | External connection support | Internal transaction |
|---|---|---:|---:|
| `save_route_weights(base_dir, weights)` | writes `.swl/config/route_weights.json` via `Path.write_text` | no | no |
| `apply_route_weights(base_dir, registry=None)` | reads route weights JSON and mutates in-memory `ROUTE_REGISTRY` / provided registry | no | no |
| `save_route_capability_profiles(base_dir, profiles)` | writes `.swl/config/route_capabilities.json` via `Path.write_text` | no | no |
| `apply_route_capability_profiles(base_dir, registry=None)` | reads route capability JSON and mutates in-memory route profiles | no | no |
| `append_canonical_record(base_dir, payload)` | rewrites canonical registry JSONL file | no | no |
| `save_audit_trigger_policy(base_dir, policy)` | writes policy file via `apply_atomic_text_updates` | no | filesystem atomic helper |
| `save_mps_policy(base_dir, kind, value)` | writes MPS policy file via `apply_atomic_text_updates` | no | filesystem atomic helper |
| `apply_atomic_text_updates(updates, deletes=())` | stages temp files, uses `os.replace`, restores touched files on exception | no | filesystem-level best effort |

Existing SQLite usage is centered in `sqlite_store.py` for task / event / knowledge evidence / knowledge relations. Route metadata and policy writes audited here are filesystem-backed, and route application mutates process-local in-memory registry objects.

S5 path implication:

- **Path A is not available** as written: the relevant route / policy functions do not accept a SQLite connection or cursor.
- **Path B is not sufficient** as written: adding `conn: sqlite3.Connection | None` would not help unless route metadata / policy persistence is first moved into SQLite.
- **Path C or a revised path is required** if the S5 goal remains "reader cannot observe partial route/policy state."
- A possible revised path would be filesystem-level atomic multi-file staging plus delayed in-memory registry mutation, but that is **not** the current S5 design. This needs Claude / Human design clarification before Codex starts S5.

## Audit 3: `_route_knowledge_to_staged`

Current call surface:

- `_route_knowledge_to_staged(...)` is defined in `src/swallow/orchestrator.py`.
- It is called once at `src/swallow/orchestrator.py:3688`, after execution artifacts are written and final state status is calculated.
- It gates only on `state.route_taxonomy_memory_authority in {"canonical-write-forbidden", "staged-knowledge"}` and then directly calls `submit_staged_candidate(...)`.
- It is route-taxonomy generic; it is not tied to `LibrarianExecutor`.

Built-in production route table:

- `ROUTE_REGISTRY` currently has **0** built-in routes whose taxonomy memory authority is `canonical-write-forbidden` or `staged-knowledge`.
- Built-in routes are currently `task-state` or `task-memory`.

Static blocked route specs found outside built-in production registry:

| Source | Route | Executor | Family | Taxonomy |
|---|---|---|---|---|
| `tests/test_cli.py:8839` | `restricted-specialist` | `note-only` | `cli` | `specialist / canonical-write-forbidden` |
| `tests/test_meta_optimizer.py:692` | `meta-optimizer-local` | `meta-optimizer` | `cli` | `specialist / canonical-write-forbidden` |

Specialist authority constants in production:

| Path | Constant | Value |
|---|---|---|
| `src/swallow/ingestion/pipeline.py:28` | `DEFAULT_INGESTION_TAXONOMY_MEMORY_AUTHORITY` | `staged-knowledge` |
| `src/swallow/ingestion_specialist.py:12` | `INGESTION_SPECIALIST_MEMORY_AUTHORITY` | `staged-knowledge` |
| `src/swallow/models.py:57` | `META_OPTIMIZER_MEMORY_AUTHORITY` | `canonical-write-forbidden` |

Interpretation:

- Current production built-in routing does not trigger `_route_knowledge_to_staged`.
- The current known blocked route examples are Specialist routes, not General Executor routes.
- No current production or test route was found with `general-executor / canonical-write-forbidden` or `general-executor / staged-knowledge`.
- The function's placement in `orchestrator.py` is still broader than the observed trigger set: any future route with blocked memory authority, including a General Executor route, would be routed through this Orchestrator-side stagedK write unless S2 constrains or moves the behavior.

S2 path implication:

- The factual audit leans toward **方案 D** for current known usage: blocked-memory routes are Specialist-shaped, and there is no current General Executor trigger.
- Because built-in routes currently have 0 blocked authorities, S2 should not be treated as behavior-preserving evidence for all possible future routes. If Claude / Human choose方案 D, the design should specify which Specialist hook owns each blocked authority path.
- If Claude / Human want to support future General Executor blocked-memory routes without moving the side effect into Specialists, that is a policy decision closer to 方案 A and would require explicit §5 alignment.

## Additional Implementation Fact

`librarian_side_effect` already exists in `src/swallow/governance.py`:

- `_VALID_OPERATOR_SOURCES` includes `"librarian_side_effect"`.
- `OperatorSource` includes `"librarian_side_effect"`.
- `_apply_librarian_side_effects(...)` in `orchestrator.py` already uses `OperatorToken(source="librarian_side_effect")` when applying canonical knowledge proposals from the Librarian executor.

Therefore, S2 方案 A would not be "add a new token" in the current codebase. It would be "extend an existing token source from canonical knowledge apply to stagedK apply" plus add `ProposalTarget.STAGED_KNOWLEDGE` and related staged proposal handling. That distinction should be reflected before S2 implementation.

## Decision Points For Claude / Human

1. **NO_SKIP scope**: keep Phase 63 as-is with 2 known red signals, or split the two LLM-route-boundary red signals into Phase 63.5 before strict S4 enforcement.
2. **S2方案选择**: current evidence supports方案 D for known usage, but方案 D still needs a concrete Specialist hook design because the current call site is Orchestrator-side.
3. **S5 path**: current storage does not support SQLite transaction wrapping for route/policy writes. S5 needs a revised implementation path before Codex starts it.
