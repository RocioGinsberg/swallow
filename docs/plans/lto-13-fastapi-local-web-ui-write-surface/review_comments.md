---
author: claude
phase: lto-13-fastapi-local-web-ui-write-surface
slice: pr-review
status: final
depends_on:
  - docs/plans/lto-13-fastapi-local-web-ui-write-surface/plan.md
  - docs/plans/lto-13-fastapi-local-web-ui-write-surface/plan_audit.md
  - docs/plans/lto-13-fastapi-local-web-ui-write-surface/closeout.md
  - src/swallow/surface_tools/web/api.py
  - src/swallow/surface_tools/web/schemas.py
  - src/swallow/surface_tools/web/dependencies.py
  - src/swallow/surface_tools/web/exceptions.py
  - src/swallow/surface_tools/web/server.py
  - src/swallow/surface_tools/web/static/index.html
  - src/swallow/application/queries/control_center.py
  - src/swallow/application/commands/knowledge.py
  - tests/integration/http/test_web_write_routes.py
  - tests/test_invariant_guards.py
  - tests/test_web_api.py
  - tests/unit/surface_tools/test_web_server.py
---

TL;DR: recommend-merge — 0 blockers / 1 concern / 2 nits. The implementation cleanly absorbs all 14 plan_audit findings (R1 + Pydantic + R2 + R3) and the closeout claims hold up against the diff. One concern is a residual boundary leak in `schemas.py` that contradicts the Direction-decision constraint about not reaching `knowledge_retrieval.*` directly.

# LTO-13 PR Review

## Verdict

**recommend-merge** — the implementation milestone at `d4c25ac feat(web): harden local write API surface` is mergeable after acknowledging the 1 concern and 2 nits below. None of them block merge.

This is an unusually clean implementation given the audit history (14 concerns across three rounds). Codex absorbed every Round 1 / Pydantic / Round 2 / Round 3 finding, including the structural Round 3 framework-default principle which required a partial rewrite (introduction of `dependencies.py`, `exceptions.py`, removal of `http_models.py` and `WebRequestError`, rebuild of response side around `response_model=` and Pydantic envelopes).

## Verification of Plan Audit Absorption

I verified each of the 14 audit findings against the diff:

### Round 1 — original audit (5 concerns + 1 nit)

| ID | Finding | Status in diff | Evidence |
|---|---|---|---|
| R1-1 | `workspace_root` pre-existing absolute-path gap | **Acknowledged & guarded** | `api.py:142` derives `workspace_root=request_base_dir` from server-side state; `schemas.py:20` `CreateTaskRequest` has no `workspace_root` field; `extra="forbid"` (`schemas.py:17`) ensures any client-supplied `workspace_root` is rejected with 422; `tests/integration/http/test_web_write_routes.py:68` is the regression test |
| R1-2 | proposal command `Path` parameter HTTP bridge | **Resolved** | `dependencies.py:15` `resolve_workspace_relative_file()` resolves workspace-relative path against `base_dir`, rejects absolute / traversal / missing; `api.py:305, 321` use it; tested at `test_web_write_routes.py:234-249` for absolute / traversal / missing / valid paths |
| R1-3 | FastAPI dev dependency missing | **Resolved** | `pyproject.toml` adds `fastapi` to `[project.optional-dependencies] dev` |
| R1-4 | `apply_proposal` UI guard not enforced at M2 | **Resolved** | `tests/test_invariant_guards.py:104-111` `UI_FORBIDDEN_WRITE_CALLS` now includes `apply_proposal`, `create_task`, `run_task` |
| R1-5 | OperatorToken source value (`"web"` vs shared `"cli"`) | **Resolved by deferral** | Closeout records "force remains CLI-only"; the `OperatorToken` source is shared `cli` for now and any future split is a deliberate phase, not a silent decision |
| R1-nit | M3 static index test home | **Resolved** | New static index assertions live in `tests/test_web_api.py` alongside existing ones; integration HTTP tests live in `tests/integration/http/` per the cli/ sibling convention |
| R1-Pyd | Pydantic / DTO decision split (post-audit follow-up) | **Resolved** | `schemas.py` is fully Pydantic; `api.py:81-93` lazy-imports schemas only inside `create_fastapi_app()`; FastAPI 422 + field-level detail is preserved (verified by `test_task_create_rejects_field_type_errors_with_validation_status`) |

### Round 2 — post-impl deep re-read (4 concerns + 2 nits)

| ID | Finding | Status in diff | Evidence |
|---|---|---|---|
| R2-1 | Long-running route contract | **Resolved by explicit choice** | `plan.md:90` adds new "Long-running write routes" decision: accept-long-request contract, fire-and-poll deferred. UI consumes `pendingTaskAction` to disable duplicate submission (`index.html:742, 896-897, 1199-1204`). Closeout records the trade-off |
| R2-2 | run-style route eligibility surfaced to UI | **Resolved** | `application/queries/control_center.py:144` `build_task_action_eligibility()` returns `run / retry / resume / rerun / acknowledge` eligibility booleans + reasons; included in both `build_task_payload` and `build_tasks_payload` (`control_center.py:179, 200`); UI consumes via `task.action_eligibility` (`index.html:892`); state-machine rules now live in backend |
| R2-3 | Response shape contract for all 10 routes | **Resolved** | All write routes use `response_model=` Pydantic envelopes (`api.py:136, 166, 182, 199, 215, 232, 274, 290, 300, 316`); uniform `{"ok": true, "data": {...}}` shape; OpenAPI ref test at `test_web_write_routes.py:264` |
| R2-4 | `force` flag wire format & UX | **Resolved by exclusion** | `schemas.py:48-50` `StageDecisionRequest` does not declare `force`; `extra="forbid"` rejects any client-sent `force`; `api.py:286` hardcodes `force=False`; regression test at `test_web_write_routes.py:169-187` verifies 422 |
| R2-5 | `swl serve --host` non-loopback guard | **Resolved** | `server.py:11` `validate_loopback_host()`; `LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}`; tested at `tests/unit/surface_tools/test_web_server.py:14` |
| R2-6 | `TaskAcknowledgeCommandResult` `blocked_kind` asymmetry | **Resolved by adapter-side normalization** | `api.py:60-72` `_task_acknowledge_or_raise()` synthesizes `blocked_kind="acknowledge"` at the adapter boundary, raising the same `TaskActionBlockedError` as recovery flows. The application-layer dataclass field asymmetry remains (acceptable — domain doesn't need it), but the adapter-side mapping no longer has the silent 200 risk |

### Round 3 — framework-rejection pattern (5 concerns + 1 nit)

| ID | Finding | Status in diff | Evidence |
|---|---|---|---|
| R3-1 | Hand-rolled response converters; no `response_model=` | **Resolved** | `http_models.py` deleted; response logic lives in `schemas.py` Pydantic envelopes with `from_*` classmethods; all `@app.post` routes have `response_model=` |
| R3-2 | Per-route try/except ladders; `@app.exception_handler` unused | **Resolved** | `api.py:104-122` 5 centralized `@app.exception_handler` blocks (`FileNotFoundError`, `UnknownStagedCandidateError`, `StagePromotePreflightError`, `TaskActionBlockedError`, `ValueError`); zero per-route try/except in the diff |
| R3-3 | `WebRequestError` reinvents `HTTPException` | **Resolved** | `WebRequestError` deleted; `dependencies.py:18, 21, 23, 27, 29` raise `HTTPException` directly; `exceptions.py:7-14` only retains `TaskActionBlockedError` for the typed-409 path (legitimate use — domain-specific exception type) |
| R3-4 | `_status_for_value_error` string-matching | **Resolved** | `application/commands/knowledge.py:41` `UnknownStagedCandidateError(ValueError)` introduced; `knowledge.py:50` `resolve_stage_candidate` raises it; web adapter dispatches via type, not message text |
| R3-5 | `globals().update({...})` ABI surgery | **Resolved** | `globals().update` deleted; `api.py:100` `app.state.base_dir = base_dir` + `dependencies.py:8` `get_base_dir(request)` is the proper FastAPI pattern |
| R3-6 | `base_dir` closure capture; `Depends` unused | **Resolved** | All 19 routes accept `Depends(get_base_dir)`; closure-captured `base_dir` only retained for static dir mount and exception handler closures (correct scope) |

**14 / 14 concerns absorbed.** No silent regressions on Round 2 / Round 3 findings.

## Findings

### [CONCERN] C1 — `schemas.py` directly imports `knowledge_retrieval.staged_knowledge`

**File**: `src/swallow/surface_tools/web/schemas.py:12`

```python
from swallow.knowledge_retrieval.staged_knowledge import StagedCandidate
```

The web adapter reaches past the application layer to import a domain type from `knowledge_retrieval/`. This contradicts the Direction-decision constraint recorded in `docs/active_context.md`:

> LTO-13 plan 实施时显式约束新增 application 层调用走公共导出,避免直接 reach `knowledge_retrieval.*` 子模块。

**Why it matters**: every other write-path import in the web adapter is well-disciplined — `api.py` imports only from `application.commands` / `application.queries`, and `schemas.py` similarly imports `TaskRunCommandResult` / `ProposalApplyCommandResult` etc. from `application.commands`. This single line is the only place the boundary leaks in the LTO-13 diff. It also enlarges deviation D1 (`knowledge_plane.py` barrel-file bypass) recorded in `docs/engineering/ARCHITECTURE_DECISIONS.md §3.1`.

**Why it happened**: `StagedCandidate` is the typed parameter of `CandidateEnvelope.from_candidate()` (`schemas.py:150`). The application layer does not currently re-export `StagedCandidate` as a public type, so the path of least resistance was a direct `knowledge_retrieval` import.

**Resolution options** (any of the three is acceptable; none blocks merge):

- **(a) Re-export from `application.commands.knowledge`**: add `from ...staged_knowledge import StagedCandidate as StagedCandidate` (or equivalent) to `application/commands/knowledge.py`'s public surface; change `schemas.py:12` to import from there. Smallest patch, immediate fix.
- **(b) Use `dict[str, Any]` and lose the static type**: drop the import and type `from_candidate(cls, candidate: Any) -> ...`. Cheap but loses the typing benefit at the adapter boundary.
- **(c) Defer to LTO-6 / D1 repair**: leave as-is and add a `# LTO-6 follow-up` marker; ensure D1 (Knowledge Plane Facade Solidification) closes this when it lands.

**Recommendation**: option (a). It costs ~3 lines and immediately restores the boundary; option (c) accumulates entropy until D1 lands.

### [NIT] N1 — `_static_dir()` resolves with `Path.cwd()` as base, not `base_dir`

**File**: `src/swallow/surface_tools/web/api.py:35-36`

```python
def _static_dir() -> Path:
    return resolve_path(Path(__file__), base=Path.cwd()).parent / "static"
```

Using `Path.cwd()` makes the resolved static directory dependent on where the process was launched from rather than on the explicit `base_dir` injected through DI. In practice this works because `Path(__file__)` is already absolute on import, so `resolve_path` returns the same path regardless of `base`. But it is a smell:

- The `Path.cwd()` argument is functionally dead — it would only matter if `__file__` were relative, which it never is.
- It is the only place in the new web adapter that touches `Path.cwd()`, breaking the otherwise consistent "all paths flow from `base_dir`" pattern.

**Suggestion**: simplify to `Path(__file__).resolve().parent / "static"` (or equivalent); drop the `resolve_path` indirection here. Pure cosmetic — no behavior change. Defer to a future cleanup if not addressed in this phase.

### [NIT] N2 — `test_task_lifecycle_write_routes` exercises real `executor_name="local"` execution

**File**: `tests/integration/http/test_web_write_routes.py:53-56`

```python
run_response = client.post(f"/api/tasks/{task_id}/run", json={})
assert run_response.status_code == 200
assert run_response.json()["data"]["task"]["status"] == "completed"
```

The test runs a real synchronous task to completion through the HTTP route. This works for the local executor and gives end-to-end coverage, but it makes the test sensitive to:

- changes in the local executor's success contract;
- changes in synchronous task pipeline timing (the test currently completes in milliseconds because the local executor short-circuits, but any change to retrieval / synthesis defaults could push this over CI time budgets);
- the implicit assumption that `local` executor always produces `status == "completed"` immediately.

This is acceptable for the LTO-13 scope (local executor is part of the test fixture surface) but worth flagging as a future fragility. If `executor_name="local"` is ever removed or changed, this test breaks for non-obvious reasons. A unit-style test using a stub at the application command boundary would be more robust, but that requires D2 (driven ports for application commands) which is deferred.

**Suggestion**: leave as-is for now; revisit when D2 first phase lands.

## Confirmed Strengths

These are recorded so the implementation patterns are reusable for future write-surface phases:

- **Framework-default principle is fully observed**: `response_model=` on every write route, `@app.exception_handler` for cross-cutting error mapping, `Depends` for context injection, FastAPI `TestClient` for integration tests. Future adapter phases can copy this layout.
- **Adapter forbidden zone is honored**: zero state-machine logic in the web adapter; the eligibility computation lives in `application/queries/control_center.py` where it belongs and is shared with the future CLI / MCP equivalents.
- **Surface-identity is correctly contained**: `planning_source: str = Field(default="web", ...)` is a Pydantic schema default — identity flows from the adapter into the application command via parameters, not via global state or `OperatorToken` mutation.
- **OpenAPI contract is now first-class**: `test_write_routes_publish_response_models_in_openapi` (`test_web_write_routes.py:264`) verifies the OpenAPI schema actually carries the response models. This was free once `response_model=` was adopted; preserves it as a regression check.
- **Loopback enforcement happens before uvicorn starts**: `validate_loopback_host()` runs synchronously inside `serve_control_center` so the LAN-exposure path fails fast with a clear error rather than silently binding 0.0.0.0.
- **`force` exclusion uses `extra="forbid"` rather than silently dropping**: a client-sent `{"force": true}` returns 422 with the field name in the detail, instead of silently ignoring. This is the correct behavior for a safety-relevant bypass.
- **`TaskActionBlockedError` carries structured `detail`**: 409 responses include `blocked_kind`, `retry_policy`, `stop_policy`, `checkpoint_snapshot` when relevant — UI has enough information to render context-specific messages without a follow-up GET.

## Validation Replay

I did not re-run the test suite during review. The closeout records:

```text
tests/integration/http/test_web_write_routes.py: 9 passed
tests/test_web_api.py + tests/unit/surface_tools/test_web_server.py: 12 passed
tests/test_invariant_guards.py + tests/unit/application/test_command_boundaries.py: 38 passed
tests/test_cli.py: 242 passed
compileall -q src/swallow: passed
git diff --check: passed
full pytest: 745 passed, 8 deselected
```

The diff inspected for this review is consistent with these counts: new test files exist at the expected paths, the guard list addition is in place, and the integration tests cover the four representative happy / error / blocked / OpenAPI dimensions.

## Recommendation

**recommend-merge** with C1 acknowledged.

If the human merger wants, the merge can be sequenced as:

1. land the implementation milestone as-is (resolves the LTO-13 plan), then
2. open a tiny follow-up commit on `main` to fix C1 via option (a) (3-line patch in `application/commands/knowledge.py` + `schemas.py`).

Or the C1 fix can be folded into the LTO-13 merge commit if Codex prefers a single clean record. Either is acceptable; my preference is (1) because it keeps LTO-13 review chain intact and gives D1's eventual repair a clean "post-LTO-13 cleanup" anchor.

## Deferred Items Confirmed

The closeout's deferred list matches the plan_audit and the architectural deviations document:

- Browser file upload + `.swl/uploads` lifecycle — out of scope per plan §Non-Goals.
- Route / policy admin write controls — out of scope per plan §Non-Goals.
- Fire-and-poll / background task runner — explicit R2-1 deferral.
- Web confirmation UX for staged knowledge promote `force` — R2-4 deferral.
- `TaskState.workspace_root` absolute-path storage cleanup — R1-1 pre-existing-condition acknowledgment.
- Broader LTO-6 knowledge facade migration — deviation D1 in `ARCHITECTURE_DECISIONS.md`.

All deferrals are recorded in writing; none were silently absorbed.
