# Test Architecture

> **Document discipline**
> Owner: Human
> Updater: Human / Claude / Codex
> Trigger: test layout, TDD workflow, fixture strategy, guard/eval boundary, or pytest marker changes
> Anti-scope: 不维护测试运行流水账、不复制具体测试断言、不替代 phase closeout

This document fixes Swallow's long-term test organization standard. It is intended to make TDD practical as the runtime codebase is reorganized.

---

## 1. Target Shape

Tests should converge toward:

```text
tests/
  conftest.py
  helpers/
    builders.py
    workspace.py
    cli_runner.py
    assertions.py
    ast_guards.py

  unit/
    application/
    adapters/
    knowledge/
    retrieval/
    provider_router/
    truth_governance/
    orchestration/

  integration/
    cli/
    run_task/
    sqlite/
    knowledge_flow/
    route_metadata/

  guards/
    test_invariants.py

  eval/
    ...

  audits/
    audit_no_skip_drift.py
    audit_route_knowledge_to_staged.py
```

The exact file split may evolve, but new tests should choose an explicit layer.

---

## 2. Test Layers

| Layer | Purpose | Default use |
|---|---|---|
| `unit` | Small, deterministic tests for pure logic, model helpers, policy functions, adapters with mocked IO. | First choice for TDD when a narrow function can fail meaningfully. |
| `integration` | Cross-module behavior, CLI flows, task run lifecycle, SQLite transactions, knowledge flow, route metadata. | Use when behavior depends on multiple modules or persisted workspace state. |
| `guards` | Executable architecture / invariant checks. | Must remain prominent and hard to bypass. |
| `eval` | Quality evaluation fixtures and golden behavior. | Marked `eval`, deselected by default. |
| `audits` | Auxiliary audit scripts that are not ordinary pytest test cases. | Run explicitly when needed. |
| `helpers` | Shared builders, workspace setup, CLI runner, assertions, AST scan helpers. | Keep test bodies concise and consistent. |

---

## 3. TDD Workflow

For each slice:

1. Write the narrowest failing test that proves the intended behavior.
2. Prefer `unit` for pure domain or service logic.
3. Use `integration/cli` for CLI surface behavior, not root-level `test_cli.py`.
4. Use `integration/sqlite` for transaction / migration / repository behavior.
5. Use `guards` only for boundary rules that must never drift.
6. Use `eval` for quality signals, not for ordinary functional gates.
7. Run focused tests during implementation and full default pytest at milestone gate.

Recommended commands:

```bash
.venv/bin/python -m pytest tests/unit/<area> -q
.venv/bin/python -m pytest tests/integration/<area> -q
.venv/bin/python -m pytest tests/guards -q
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -m eval -q
```

---

## 4. Fixture Standards

Shared helpers should replace repeated local setup:

- `tmp_workspace` fixture for workspace roots and `.swl` layout.
- `run_cli` helper for invoking `swl` commands and capturing stdout/stderr.
- `make_task_state` / `make_route_spec` / `make_retrieval_item` builders for common models.
- `read_jsonl_events` / `assert_event_kind` assertions for event logs.
- `assert_artifact_exists` / `read_artifact` helpers for task artifacts.
- AST guard helpers should live outside individual guard tests once reused.

Avoid adding new copies of:

- repeated `sys.path.insert(...)`
- repeated `tempfile.TemporaryDirectory()` wrappers when `tmp_path` works
- repeated large `TaskState(...)` construction blocks
- deeply nested `patch(...)` trees when a helper or `monkeypatch` communicates intent better

---

## 5. CLI Test Standard

`tests/test_cli.py` is a historical aggregation point and should not keep growing.

New CLI tests should go to focused files under `tests/integration/cli/`, for example:

```text
tests/integration/cli/test_task_commands.py
tests/integration/cli/test_knowledge_commands.py
tests/integration/cli/test_route_commands.py
tests/integration/cli/test_proposal_commands.py
tests/integration/cli/test_doctor_commands.py
tests/integration/cli/test_artifact_commands.py
tests/integration/cli/test_ingestion_commands.py
```

When modifying old CLI behavior, prefer moving the touched tests into the appropriate focused file as part of the slice, as long as the move is behavior-preserving.

Pure logic that happens to be used by CLI should be tested in `unit`, not through CLI unless the surface contract itself matters.

---

## 6. Guard Test Standard

Guard tests enforce `docs/design/INVARIANTS.md` and related architecture boundaries.

Rules:

- Do not delete or weaken guard tests to make refactors pass.
- When module moves are legitimate, update guard allowlists narrowly.
- Keep guard names aligned with invariant wording where possible.
- Guard tests should fail loudly on boundary drift, even if ordinary behavior tests pass.
- `test_ui_backend_only_calls_governance_functions` and related interface guards should evolve with `docs/engineering/CODE_ORGANIZATION.md`.

---

## 7. Eval Test Standard

Eval tests are quality signals, not the default functional gate.

Rules:

- Eval tests stay marked with `pytest.mark.eval`.
- Default pytest keeps eval deselected.
- Golden fixtures belong under `tests/fixtures/`.
- Retrieval / LLM quality improvements should add eval coverage when deterministic enough.
- Eval failures should be triaged separately from core guard / unit / integration failures.

---

## 8. Migration Discipline

Use these rules when implementing candidate `AA`:

- Start with helpers and pytest configuration before broad file moves.
- Move tests by behavior family, not by historical phase.
- Keep collect-only passing after each batch.
- Do not combine test relocation with production behavior changes unless needed for a TDD slice.
- Preserve old assertions during moves; improve assertions in separate commits when possible.
- Keep `tests/eval/` deselected by default.
- Keep phase-named tests only as temporary waypoints; migrate them to domain names as touched.

---

## 9. Non-Goals

- No directory churn just to make the tree look tidy.
- No weakening invariant tests for faster refactors.
- No mandatory full-suite run after every keystroke; use focused TDD loops and full milestone gates.
- No eval tests in the default fast gate.
- No new monolithic test files replacing `test_cli.py`.
