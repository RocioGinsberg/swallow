---
author: codex
phase: phase67
slice: candidate-p-module-reorganization
status: review
created_at: 2026-04-30
depends_on:
  - docs/roadmap.md
  - docs/plans/phase66/audit_index.md
  - docs/plans/phase67/closeout.md
---

TL;DR: Candidate P is implemented as a mechanical module reorganization. `src/swallow/` root Python files dropped to `__init__.py` + `_io_helpers.py`; runtime code now sits under five semantic packages aligned with Phase 66 audit blocks. Full pytest passes: `610 passed, 8 deselected, 10 subtests passed`.

# Candidate P Codex Review Notes

## Scope

Human requested Candidate P before fully ending Phase 67. This was treated as a pragmatic pre-merge add-on to the cleanup branch, not as a new behavior phase.

Implemented:

- `truth_governance/`: proposal governance, task/file/sqlite stores, and truth repositories.
- `orchestration/`: orchestrator, executor, harness, planner, validation, synthesis, policies, and shared runtime models.
- `provider_router/`: provider router, LLM call helpers, HTTP helpers, capability enforcement, cost estimation, and default route JSON data.
- `knowledge_retrieval/`: retrieval, knowledge objects/stores/review/index/relation modules, canonical reuse/audit modules, ingestion, dialect data, and dialect adapters.
- `surface_tools/`: CLI, path/workspace/identity helpers, web API, doctor, consistency tools, MPS policy store, meta optimizer, and specialist executors.
- Root kept only `__init__.py` and `_io_helpers.py`.

Out of scope:

- No business logic rewrite.
- No compatibility shim layer for old root module import paths.
- No `docs/design/` edits.
- No raw-material / storage-backend split from Candidate O.
- No test directory restructuring.

## Implementation Notes

The reorganization is intentionally mechanical:

- Moved source modules according to Phase 66 audit block ownership.
- Rewrote absolute imports and patch-string references in tests to the new package paths.
- Converted moved root-relative imports to explicit package imports where dependencies now cross package boundaries.
- Updated the console script entry point from `swallow.cli:main` to `swallow.surface_tools.cli:main`; the public `swl` command remains the stable operator entry.
- Moved `routes.default.json` and `route_policy.default.json` into `provider_router/` because `router.py` owns those defaults and resolves them relative to its module file.
- Updated guard tests that encoded old file paths so they now enforce the same invariants on the new package layout.

## Deliberate Choices

No old-path shims were added. The goal of Candidate P is to make the source tree easy to navigate; keeping dozens of root compatibility wrappers would preserve old imports but recreate the same root-level noise the candidate is meant to remove.

`_io_helpers.py` stays at package root because it is cross-cutting by design and was explicitly positioned in M2 for truth, orchestration, knowledge/retrieval, and CLI callers.

The default route JSON files moved with `provider_router` rather than staying at root. This keeps router configuration ownership visible and avoids a hidden dependency from a subpackage back to package-root data files.

## Test Stability Fix

The repeated full-suite failure in `tests/test_synthesis.py::test_synthesis_does_not_mutate_main_task_state` was the known Phase 67 order-sensitive flake. I corrected the test baseline to compare persisted state before and after synthesis, instead of comparing SQLite-loaded state to the in-memory state timestamp after `save_state(...)`.

This does not change synthesis behavior; it makes the test assert the intended invariant directly: running synthesis does not mutate the persisted task state.

## Verification

Focused checks:

```bash
.venv/bin/python -m pytest -q tests/test_specialist_agents.py tests/test_web_api.py tests/test_doctor.py tests/test_meta_optimizer.py
# 54 passed

.venv/bin/python -m pytest -q tests/test_retrieval_adapters.py
# 20 passed

.venv/bin/python -m pytest -q tests/test_cli.py tests/test_phase65_sqlite_truth.py tests/test_sqlite_store.py tests/test_retrieval_adapters.py
# 297 passed, 10 subtests passed

.venv/bin/python -m pytest -q tests/test_synthesis.py::test_synthesis_does_not_mutate_main_task_state tests/test_invariant_guards.py
# 26 passed
```

Final checks:

```bash
.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# passed

.venv/bin/python -c "from swallow.surface_tools.cli import main; from swallow.provider_router.router import route_by_name; assert route_by_name('local-http') is not None; assert callable(main)"
# passed

.venv/bin/python -m swallow.surface_tools.cli --help
# passed

.venv/bin/python -m pytest -q
# 610 passed, 8 deselected, 10 subtests passed
```

## Review Guidance

Recommended review strategy:

- Review the directory mapping first; most code diff is path movement.
- Then inspect import rewrites in `src/swallow/**`.
- Then inspect `tests/test_invariant_guards.py` because it intentionally changed path allow-lists while preserving invariant semantics.
- Then inspect `tests/test_synthesis.py` for the isolated flake fix.

Suggested commit message:

```bash
refactor(phase67-p): reorganize modules by audit block
```
