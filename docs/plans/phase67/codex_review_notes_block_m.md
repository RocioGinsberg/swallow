---
author: codex
phase: phase67
slice: m2-io-helper-artifact-ownership
status: final
depends_on:
  - docs/plans/phase67/kickoff.md
  - docs/plans/phase67/design_decision.md
  - docs/plans/phase67/risk_assessment.md
  - docs/plans/phase67/context_brief.md
  - docs/plans/phase67/review_comments_block_l.md
  - docs/plans/phase66/audit_index.md
---

TL;DR: M2 implemented shared JSON / JSONL IO helper ownership and stopped at the audit gate. I intentionally added two helper variants beyond the literal design text: `read_json_lines_strict_or_empty(...)` preserves existing missing-empty + malformed-crash JSONL behavior in truth/orchestration paths, and `read_json_list_or_empty(...)` preserves `retrieval.json` list payload behavior in CLI inspect/review.

# Codex Review Notes: Phase 67 M2

## Scope Completed

- Created `src/swallow/_io_helpers.py` as the shared owner for JSON / JSONL read helpers.
- Deleted `cli.py` private `load_json_if_exists(...)` / `load_json_lines_if_exists(...)`; `src/swallow` has no remaining references to those names.
- Replaced M2-targeted JSON / JSONL callsites in:
  - `canonical_registry.py`
  - `cli.py`
  - `dialect_data.py`
  - `knowledge_store.py`
  - `knowledge_suggestions.py`
  - `librarian_executor.py`
  - `orchestrator.py`
  - `retrieval.py`
  - `staged_knowledge.py`
  - `store.py`
  - `truth/knowledge.py`
- Kept artifact-name ownership on the narrow path: no global artifact registry in M2. The remaining artifact-name registry concern stays open for M3 / a future design phase.
- Updated `docs/concerns_backlog.md` to mark the Phase 66 JSON/JSONL helper ownership concern resolved by M2.

## Helper Contracts Implemented

- `read_json_strict(path)`: missing file and malformed JSON both raise.
- `read_json_or_empty(path)`: missing file returns `{}`; malformed JSON raises; non-object payload returns `{}`.
- `read_json_list_or_empty(path)`: missing file returns `[]`; malformed JSON raises; non-list payload returns `[]`.
- `read_json_lines_or_empty(path)`: missing file returns `[]`; malformed / non-dict JSONL lines are skipped with warning.
- `read_json_lines_strict_or_empty(path)`: missing file returns `[]`; malformed JSONL raises; non-dict lines are ignored as before.

## Implementation Notes For Claude

1. Design text said the main JSONL paths were missing-empty + malformed-skip, but source inspection showed several were actually missing-empty + malformed-crash.
   I preserved the source behavior with `read_json_lines_strict_or_empty(...)` for store events, truth canonical derivative refresh, orchestrator decision / registry / eval reloads, librarian canonical reads, and staged knowledge registry reads. Using `read_json_lines_or_empty(...)` there would have silently hidden corruption in paths that previously crashed.

2. `canonical_registry.resolve_knowledge_object_id(...)` already skipped malformed registry lines.
   That callsite uses `read_json_lines_or_empty(...)`, matching the previous skip behavior.

3. `cli.py` needed a list-shaped JSON helper for `retrieval.json`.
   The first replacement pass used `read_json_or_empty(...)`, which turned list payloads into `{}` and broke inspect/review output (`retrieval_record_available` and reused-knowledge counts). `read_json_list_or_empty(...)` preserves the old `load_json_if_exists(...)` list behavior for those two retrieval callsites.

4. `store.py` keeps a private `_load_json_lines(...)` wrapper, but implementation ownership is still `_io_helpers.py`.
   `tests/test_sqlite_store.py` monkeypatches `swallow.store._load_json_lines` to assert that recent-event file fallback only loads file-only tasks. Removing that name created a test-only API break. The wrapper now delegates to `read_json_lines_strict_or_empty(...)`, and file recent-event paths call through it.

5. I did not migrate every remaining direct `json.loads(path.read_text(...))` in the repository.
   `store.py` state-file strict reads and `orchestrator.py` local grounding-evidence reads remain direct because they were outside the M2 mapping table and already have local strict semantics. M2 was scoped to helper ownership for the audited duplicate patterns, not a full JSON IO rewrite.

6. `_io_helpers.py` logging `extra` keys avoid reserved `LogRecord` fields.
   The warning payload uses `jsonl_path` / `line_no` rather than `path` / `line`, avoiding logging-field collisions.

## Artifact Ownership Decision

M2 keeps the narrow option from `design_decision.md`:

- No `_artifact_registry.py` or `paths.py` registry expansion in M2.
- M3 may consume a local table-driven mapping for read-only CLI artifact printers.
- Orchestrator / harness / retrieval artifact-name ownership remains a future design concern, not resolved by M2.

## Verification Completed

```bash
.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# passed

git diff -- docs/design
# no output

rg -n "load_json_if_exists|load_json_lines_if_exists" src/swallow
# no matches

.venv/bin/python -m pytest -q tests/test_cli.py tests/test_sqlite_store.py
# 256 passed, 10 subtests passed

.venv/bin/python -m pytest -q tests/test_cli.py tests/test_retrieval_adapters.py tests/test_sqlite_store.py tests/test_phase65_sqlite_truth.py tests/test_librarian_executor.py tests/test_planner.py tests/test_review_gate.py tests/test_cost_estimation.py
# 325 passed, 10 subtests passed

.venv/bin/python -m pytest -q -k "not test_run_task_times_out_one_parallel_subtask_without_canceling_other_work"
# 609 passed, 9 deselected, 10 subtests passed

.venv/bin/python -m pytest -q tests/test_run_task_subtasks.py::RunTaskSubtaskIntegrationTest::test_run_task_times_out_one_parallel_subtask_without_canceling_other_work
# 1 passed
```

## Verification Residual

Two direct full-suite runs failed on the same pre-existing wall-clock assertion:

```bash
.venv/bin/python -m pytest -q
# 1 failed, 609 passed, 8 deselected, 10 subtests passed
# failing test:
# tests/test_run_task_subtasks.py::RunTaskSubtaskIntegrationTest::test_run_task_times_out_one_parallel_subtask_without_canceling_other_work
```

Observed failure shape:

- expected elapsed `< 1.75s`
- observed elapsed around `3.06s` / `3.09s` in full-suite order
- the same test passes isolated in `1.66s` / `1.69s`
- `tests/test_run_task_subtasks.py` also passes as a file-level run

I did not change the test threshold because that is outside M2 IO-helper scope. Claude should decide whether this is acceptable as a known full-suite timing flake for this milestone or whether a separate test-stability fixup is required before M3.

## Review Checks To Re-run

```bash
rg -n "load_json_if_exists|load_json_lines_if_exists" src/swallow
rg -n "def _load_json_lines" src/swallow
git diff -- docs/design
git diff --check
.venv/bin/python -m pytest -q tests/test_cli.py tests/test_sqlite_store.py
.venv/bin/python -m pytest -q -k "not test_run_task_times_out_one_parallel_subtask_without_canceling_other_work"
.venv/bin/python -m pytest -q tests/test_run_task_subtasks.py::RunTaskSubtaskIntegrationTest::test_run_task_times_out_one_parallel_subtask_without_canceling_other_work
```

Expected residual for `def _load_json_lines`:

- `src/swallow/store.py`: compatibility wrapper only; delegates to `_io_helpers.read_json_lines_strict_or_empty(...)`.
