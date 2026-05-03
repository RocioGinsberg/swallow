---
author: codex
phase: lto-13-fastapi-local-web-ui-write-surface
slice: phase-plan
status: review
depends_on:
  - docs/roadmap.md
  - docs/active_context.md
  - docs/design/INVARIANTS.md
  - docs/design/INTERACTION.md
  - docs/design/SELF_EVOLUTION.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/TEST_ARCHITECTURE.md
  - docs/plans/orchestration-lifecycle-decomposition-step2/closeout.md
  - docs/plans/surface-cli-meta-optimizer-split-step2/closeout.md
  - src/swallow/surface_tools/web/api.py
  - src/swallow/application/commands/tasks.py
  - src/swallow/application/commands/knowledge.py
  - src/swallow/application/commands/proposals.py
  - tests/test_web_api.py
  - tests/test_invariant_guards.py
  - docs/plans/lto-13-fastapi-local-web-ui-write-surface/plan_audit.md
---

TL;DR:
LTO-13 introduces Swallow's first local FastAPI write surface for the Control Center.
The HTTP adapter must call the same `application/commands/*` functions that CLI already uses; it must not become a second business layer, second Orchestrator, or direct Truth writer.
This phase starts with task lifecycle and review/apply operations, keeps browser file upload and route/policy admin writes deferred, and adds the minimal static UI controls needed to prove the local Web UI write loop.

# LTO-13 Plan: FastAPI Local Web UI Write Surface

## Frame

- track: `Interface / Application Boundary`
- phase: `LTO-13 — FastAPI Local Web UI Write Surface`
- roadmap ticket: `LTO-13 — FastAPI Local Web UI Write Surface`
- long-term goal: `LTO-13 FastAPI Local Web UI Write Surface`
- recommended implementation branch: `feat/lto-13-fastapi-local-web-ui-write-surface`
- planning branch: `main`
- implementation mode: adapter-first / local-only / shared-application-command boundary
- context brief: not produced this round; this plan is based on the updated roadmap, active context, design anchors, and direct code survey.
- plan audit: `has-concerns`, 0 blockers / 14 concerns / 4 nits; Round 1, Pydantic follow-up, Round 2, and Round 3 framework-default concerns absorbed in this revision.

This is not a full CLI parity phase. It establishes the write-route pattern and ships the first useful operator-facing write loop through local FastAPI and the existing static Control Center.

## Current Code Context

| Area | Current shape |
|---|---|
| `src/swallow/surface_tools/web/api.py` | Thin FastAPI adapter with `create_fastapi_app(base_dir)`, static dashboard serving, `/api/health`, and 9 read-only `@app.get(...)` routes. There are zero `POST` / `PUT` / `PATCH` / `DELETE` routes. |
| `src/swallow/application/queries/control_center.py` | Owns read-only Control Center payload builders for tasks, events, artifacts, knowledge, subtask tree, and execution timeline. |
| `src/swallow/application/commands/` | Existing shared command layer from LTO-9 Step 2: `tasks.py`, `knowledge.py`, `proposals.py`, `route_metadata.py`, `policies.py`, `synthesis.py`, and `meta_optimizer.py`. |
| `tests/test_web_api.py` | Covers current read-only payload builders, static index content, app factory routes, focus filters, artifact traversal rejection, diff payloads, subtask tree, and timeline behavior. |
| `tests/test_invariant_guards.py` | Includes `test_ui_backend_only_calls_governance_functions`, currently scanning `surface_tools/web/*.py` for forbidden write calls. |
| `pyproject.toml` | Does not declare FastAPI or Pydantic as mandatory dependencies. `swl serve` already treats FastAPI as an optional runtime dependency. |

LTO-13 should build on the existing `application/commands` layer, not add a parallel web-specific command layer.

## Goals

1. Add the first FastAPI write routes for local Control Center operator actions.
2. Route every write through existing `application/commands/*` functions, with no direct calls from the web layer into repositories, SQLite, private governance writers, or Orchestrator internals.
3. Preserve all current read-only `GET` routes and response payloads.
4. Define a repeatable HTTP write-route contract: request parsing, verb choice, response shape, and error mapping.
5. Keep `swallow.surface_tools.web.api` importable without FastAPI installed.
6. Extend persistent guard tests so future UI writes cannot drift into a hidden business layer.
7. Add minimal static Control Center controls for the in-scope write routes, using the same local FastAPI adapter.

## Non-Goals

- Do not implement a remote API, SaaS backend, authn/authz, multi-user sessions, or remote control plane.
- Do not make FastAPI a second Orchestrator or a second implementation of task / knowledge / proposal logic.
- Do not make normal CLI commands call HTTP. CLI and Web converge through `application/commands`, not through CLI-over-HTTP.
- Do not add browser file upload / `.swl/uploads` / staged source cleanup in this phase; `INTERACTION.md §4.2.4` makes that a separate storage and retention design point.
- Do not add route / policy admin write forms or route metadata policy editing routes in this first write-surface phase.
- Do not introduce schema migrations, new proposal target kinds, new Truth write paths, or new canonical / route / policy mutation entry points.
- Do not convert the static Control Center into a new frontend framework or separate SPA.
- Do not broaden LTO-6 knowledge facade migration beyond touched imports needed by this phase.

## Design Decisions

| Decision point | Decision |
|---|---|
| Framework-default principle | For capabilities FastAPI / Pydantic / uvicorn already provide, use the framework primitive by default: request models, response models, `response_model=`, dependency injection via `Depends`, centralized `@app.exception_handler`, OpenAPI generation, `TestClient`, and uvicorn serving controls. A hand-rolled equivalent requires a written reason in this plan or closeout. |
| Request body schema | Use FastAPI/Pydantic request models scoped strictly to `surface_tools/web`; keep them out of application/domain imports and keep FastAPI optional for the core runtime. |
| Response schema | Use Pydantic response models and `response_model=` for every new write route. Do not define response shape only through ad hoc `dict` converters. |
| Dependency injection | Store app-local runtime context such as `base_dir` on the FastAPI app and expose it through `Depends` dependencies. Avoid closure-only route dependencies where future request context, audit actor, artifact resolution, or operator token flow will need extension. |
| HTTP verbs | Use `POST` for all mutation commands, including action-style commands such as run / resume / retry / promote / apply. Existing `GET` routes remain read-only. |
| Error mapping | Let FastAPI/Pydantic emit `422` for malformed bodies and field-shape violations. Use centralized `@app.exception_handler` mappings for typed domain / adapter exceptions. Use `400` for adapter boundary or path-policy violations, `404` for unknown task / candidate / artifact / proposal records, and `409` for blocked task recovery or state-conflict outcomes. Do not classify errors by matching exception message strings. |
| Long-running write routes | For LTO-13, `run` / `retry` / `resume` / `rerun` intentionally use an accept-long-request contract: the HTTP request blocks until the existing synchronous application command completes, then returns the final response envelope. This avoids adding background task ownership, cancellation, and recovery semantics in the first write-surface phase. The UI must present these as long-running actions, disable duplicate submission while pending, and refresh read models after completion. Fire-and-poll / background execution is deferred to a dedicated phase. |
| Static UI | Add a narrow write-control panel to the existing static Control Center for the in-scope routes. The UI may call local `fetch(...)` routes and refresh existing read models after success, but it must consume backend-provided action eligibility instead of encoding task state-machine rules. |
| Proposal artifact path bridge | HTTP proposal review/apply requests carry workspace-relative artifact paths, not absolute paths. The adapter resolves them under `base_dir`, rejects absolute paths and parent traversal, verifies existence, then passes `Path` objects to existing proposal application commands. |
| Knowledge promote force | Do not expose `force=True` for staged knowledge promote in this phase. Web promote requests may include `note` and `refined_text`; failed preflight returns `409` with notices. CLI remains the escape hatch for force until a separate Web confirmation UX is designed. |
| Local serving boundary | Once write routes exist, `swl serve` must enforce loopback-only serving (`127.0.0.1`, `localhost`, `::1`) unless a future authenticated remote-control design changes this boundary. `0.0.0.0` / LAN exposure is out of scope for an unauthenticated write surface. |
| Test dependency strategy | Add `fastapi` to the `dev` optional dependency group before introducing HTTP round-trip tests. New `tests/integration/http/` tests should use FastAPI's test client without making `fastapi` a mandatory runtime dependency. |
| Operator token source | Do not add a new `OperatorToken(source="web")` in this phase. Existing application commands keep using `source="cli"` as the current generic local-operator source; changing token taxonomy requires separate design review. |

## Plan Audit Absorption

`docs/plans/lto-13-fastapi-local-web-ui-write-surface/plan_audit.md` raised Round 1 concerns, a Pydantic follow-up, and two post-implementation audit rounds. This revision absorbs them as follows:

- C-1 workspace root: M1 now treats absolute `workspace_root` storage as a pre-existing CLI/orchestrator gap. The web adapter must not accept client-supplied `workspace_root` or make the exposure worse; the §7 cleanup is deferred.
- C-2 FastAPI tests: M1 now requires adding `fastapi` to the `dev` optional dependency group before HTTP round-trip tests are added.
- C-3 proposal path bridge: M2 now defines the HTTP convention as workspace-relative artifact paths resolved under `base_dir`, with absolute paths and parent traversal rejected.
- C-4 UI guard: M2 now moves `apply_proposal` into `UI_FORBIDDEN_WRITE_CALLS` as part of the write-route milestone, instead of deferring that protection to M4.
- C-5 OperatorToken source: this phase keeps existing `source="cli"` semantics for all local operator writes through shared application commands; no `"web"` source is introduced.
- N-1 static index tests: M3 static markup and route-string assertions stay in `tests/test_web_api.py` beside the existing dashboard index assertions.
- Pydantic follow-up: request validation now uses scoped FastAPI/Pydantic models while preserving top-level `api.py` import hygiene.
- R2-1 long-running routes: this plan explicitly chooses accept-long-request for `run` / `retry` / `resume` / `rerun` and defers fire-and-poll.
- R2-2 eligibility: task read models must expose backend-derived action eligibility so the static UI does not implement task state-machine rules.
- R2-3 response shape: write routes must use Pydantic response models and a uniform success envelope.
- R2-4 force flag: Web staged promote does not expose `force=True` in this phase.
- R2-5 host guard: serving is loopback-only for the unauthenticated write surface.
- R2-6 acknowledge blocked mapping: acknowledge blocked outcomes must be represented by typed error mapping or an explicit `blocked_kind="acknowledge"` equivalent; route-local ad hoc divergence is not acceptable.
- R3 framework-default: response models, exception handlers, `Depends`, OpenAPI contracts, and TestClient are now the default path; custom mirrors such as `WebRequestError`, message-string status classification, and `globals().update(...)` schema bridges are rejected unless explicitly justified.

## Target Surface Shape

| Area | Target ownership |
|---|---|
| `surface_tools/web/api.py` | FastAPI adapter, route registration, dependency wiring, centralized exception handlers, and static file serving. It may call `application/commands` and `application/queries`, but not lower layers directly. Its top-level import path remains FastAPI-free. |
| `surface_tools/web/schemas.py` | Pydantic request and response models for the HTTP adapter only; no application/domain imports. It may import Pydantic and should be imported by `create_fastapi_app()` or tests that explicitly exercise Web schemas. |
| `surface_tools/web/dependencies.py` or local equivalents | FastAPI dependency functions for `base_dir`, proposal/review path resolution, and future request context. Dependencies must stay adapter-scoped. |
| `surface_tools/web/http_models.py` or equivalent | Only keep small framework-free helpers if still justified after applying FastAPI/Pydantic primitives. Do not keep hand-rolled response converters, custom `HTTPException` mirrors, or message-string status classifiers. |
| `application/commands/tasks.py` | Shared task lifecycle command functions for task create / run / retry / resume / rerun / acknowledge. |
| `application/commands/knowledge.py` | Shared staged knowledge promote / reject functions. |
| `application/commands/proposals.py` | Shared Meta-Optimizer proposal review / apply functions. |
| `surface_tools/web/static/index.html` | Existing dashboard plus minimal write controls and refresh behavior. |
| `tests/integration/http/` | New focused HTTP write-route contract tests. Existing `tests/test_web_api.py` remains the read-route / payload compatibility home unless a narrow move is clearly beneficial. |
| `tests/test_invariant_guards.py` | Expanded UI backend guard for direct writer / private repository / raw SQL drift in the web layer and any new web helper module. |

## In-Scope HTTP Routes

Success responses use a uniform envelope:

```json
{"ok": true, "data": {"...": "..."}}
```

Error responses use FastAPI's normal `{"detail": ...}` shape, with `422` generated by request/response validation and `400` / `404` / `409` generated by centralized exception handlers.

| Route | Long-running | Response model data keys |
|---|---:|---|
| `POST /api/tasks` | no | `task` |
| `POST /api/tasks/{task_id}/run` | yes | `task` |
| `POST /api/tasks/{task_id}/retry` | yes when allowed | `task`, `previous_task` |
| `POST /api/tasks/{task_id}/resume` | yes when allowed | `task`, `previous_task` |
| `POST /api/tasks/{task_id}/rerun` | yes | `task` |
| `POST /api/tasks/{task_id}/acknowledge` | no | `task` |
| `POST /api/knowledge/staged/{candidate_id}/promote` | no | `candidate`, `notices` |
| `POST /api/knowledge/staged/{candidate_id}/reject` | no | `candidate` |
| `POST /api/proposals/review` | no | `review_record`, `record_path` |
| `POST /api/proposals/apply` | no | `application_record`, `record_path`, `proposal_id` |

The route names may be adjusted during implementation if FastAPI path matching or UI ergonomics make a nearby spelling clearer, but the semantics above are the bounded surface for this phase.

## Read Model Additions

The existing task read payload must add backend-derived action eligibility so the static UI can render controls without reimplementing command preconditions:

```json
{
  "action_eligibility": {
    "run": {"eligible": true, "reason": null},
    "retry": {"eligible": false, "reason": "retry policy is not satisfied"},
    "resume": {"eligible": false, "reason": "checkpoint is not resume-ready"},
    "rerun": {"eligible": true, "reason": null},
    "acknowledge": {"eligible": false, "reason": "task is not awaiting acknowledgement"}
  }
}
```

The exact reason strings are not user-contract stable, but the keys and boolean semantics are. Eligibility must be computed on the backend using the same policy inputs that the application commands use. JavaScript may enable/disable controls from these booleans; it must not infer eligibility from raw `status`, `phase`, or checkpoint fields.

## Boundary Rules

- Web write routes call only shared application command functions for mutation behavior.
- Web handlers may validate request shape, coerce primitive JSON values, map exceptions to HTTP errors, and serialize command results.
- Web route decorators for new write routes must declare `response_model=` using adapter-scoped Pydantic response models.
- Web error mapping should be centralized with `@app.exception_handler`; per-route `try/except` ladders are allowed only for a route-specific exception that cannot be represented centrally and must be documented in this plan or closeout.
- Web handlers and helpers must not classify HTTP status by parsing human-readable exception messages.
- Web handlers must not call `save_state`, `append_event`, `apply_proposal`, repository private writer methods, SQLite connection helpers, or `run_task` / `create_task` directly.
- Web handlers must not import `truth_governance.governance.apply_proposal`; proposal and canonical writes reach it only through `application.commands.proposals` or `application.commands.knowledge`.
- Web handlers that accept filesystem references may only accept workspace-relative paths, resolve them under `base_dir`, reject absolute paths and `..` traversal, and verify existence before calling application commands.
- Application command modules remain terminal-format-free and continue to be covered by `tests/unit/application/test_command_boundaries.py`.
- The web layer must not import `knowledge_retrieval.*` implementation modules directly. If a new application command touch is required, prefer public application or facade exports and record any unavoidable LTO-6 follow-up in closeout.
- Existing read-only `GET` payload shapes are compatibility targets.
- Static UI write controls are UX adapters only; they must not encode task state machine rules or proposal apply policy in JavaScript.
- The unauthenticated Web write surface is loopback-only. `swl serve --host 0.0.0.0` or any other non-loopback address must fail before uvicorn starts.

## Milestones

| Milestone | Slice | Scope | Risk | Gate |
|---|---|---|---|---|
| M1 | HTTP contract + task lifecycle writes | Add dev FastAPI dependency, scoped Pydantic request/response models, `Depends` base-dir wiring, centralized exception handlers, and task lifecycle `POST` routes; call `application.commands.tasks`; add focused HTTP tests for success and expected 422 / 404 / 409 paths. | high | `tests/integration/http` task write tests + response-model/OpenAPI assertions + `tests/test_web_api.py` read regression + UI guard |
| M2 | Knowledge and proposal write routes | Add staged promote / reject and proposal review / apply routes through `application.commands.knowledge` and `application.commands.proposals`; define workspace-relative proposal artifact path resolution through adapter dependencies; preserve `apply_proposal` as the only canonical / route mutation entry through those commands; do not expose promote `force`. | high | knowledge/proposal HTTP tests + governance and application command boundary tests + UI `apply_proposal` guard |
| M3 | Static Control Center write controls | Add a narrow task action / review action panel to `index.html`; render task actions from backend eligibility flags; wire local `fetch(...)` calls, long-request pending state, success refresh, and visible error handling without adding a frontend framework. | medium-high | `tests/test_web_api.py` static index assertions + smoke tests for route names in UI + web route tests |
| M4 | Guard hardening, serve safety, cleanup, closeout | Tighten `test_ui_backend_only_calls_governance_functions`, enforce loopback-only `swl serve`, remove dead local helpers, run full gates, and record deferred file upload / route-policy admin / background-runner items. | medium | full pytest + compileall + diff hygiene + closeout / PR material |

## M1 Acceptance: Task Lifecycle Write Routes

Scope:

- Introduce the route contract and scoped Pydantic request/response schema pattern.
- Add `fastapi` to `pyproject.toml`'s `dev` optional dependency group before adding HTTP round-trip tests. Keep FastAPI optional for production/runtime imports.
- Implement task write routes for create, run, retry, resume, rerun, and acknowledge.
- Implement `response_model=` for all task write routes using the uniform success envelope.
- Wire `base_dir` through FastAPI dependency injection rather than route closure capture alone.
- Centralize task HTTP exception mapping; remove repeated route-local exception ladders where a framework exception handler can express the mapping.
- Derive `workspace_root` from the local workspace by default for `POST /api/tasks`; do not accept `workspace_root` from the client request body.
- Treat current absolute `TaskState.workspace_root` persistence as a pre-existing CLI/orchestrator gap. LTO-13 must not widen it or add a second path input surface; fixing the underlying §7 storage issue is deferred to a later phase.
- Return success envelopes whose `data.task` includes at minimum `task_id`, `status`, `phase`, `title`, `goal`, `executor_name`, `route_name`, `attempt_id`, and `attempt_number`.
- Add backend-derived task action eligibility to read payloads.
- Keep existing read-only payload builders and route behavior unchanged.

Acceptance:

- Focused HTTP tests prove each M1 route calls the expected application command path.
- `pyproject.toml` has a `dev` dependency entry for FastAPI, while `swallow.surface_tools.web.api` remains importable without FastAPI installed until `create_fastapi_app()` is called.
- OpenAPI or app route tests prove write routes declare response models.
- Body-shape and field-type validation errors map to FastAPI/Pydantic `422`.
- Unknown task IDs map to `404`.
- Blocked retry / resume / acknowledge flows map to `409` with a structured reason.
- `run` / `retry` / `resume` / `rerun` tests reflect the accept-long-request contract: route returns only after the command completes or returns a typed blocked conflict.
- Tests cover task action eligibility fields in the read model.
- `tests/test_web_api.py -q` still passes.
- `test_ui_backend_only_calls_governance_functions` passes without a broad allowlist.

## M2 Acceptance: Knowledge And Proposal Writes

Scope:

- Implement staged knowledge promote / reject routes.
- Implement proposal review / apply routes for the existing Meta-Optimizer proposal flow.
- Keep canonical and route metadata mutation behind `application.commands.knowledge` / `application.commands.proposals`, which in turn use existing governance APIs.
- For proposal review/apply requests, accept `bundle_path` / `review_path` as workspace-relative strings, resolve them under `base_dir`, reject absolute paths and parent traversal, verify the target exists, and then pass the resolved `Path` to `review_proposals_command` / `apply_reviewed_proposals_command`.
- Resolve proposal paths through FastAPI dependency functions where practical, not per-route inline path parsing.
- Do not expose `force=True` for staged knowledge promote. Remove `force` from the Web request schema and static UI for this phase; a preflight failure returns `409` with notices.
- Introduce typed exceptions or adapter-local typed exception wrappers for known candidate/path/preflight failures; do not map `ValueError` by checking message prefixes.
- Add `apply_proposal` to `UI_FORBIDDEN_WRITE_CALLS` in `tests/test_invariant_guards.py` in the same milestone that introduces proposal/canonical web write routes.
- Add HTTP tests for successful promote / reject / review / apply and representative missing-record failures.

Acceptance:

- No direct `apply_proposal(` call is introduced in `surface_tools/web/*.py`.
- `test_ui_backend_only_calls_governance_functions` fails on direct web-layer `apply_proposal` imports or calls.
- Absolute proposal artifact paths, missing relative paths, and parent traversal paths are covered by HTTP tests and map to `400` or `404` as appropriate.
- Promote preflight conflict maps to `409` and includes notices; Web force bypass is absent from schema, OpenAPI, and UI.
- No direct private writer tokens or SQLite mutation strings appear in the web layer.
- Existing governance tests and application command boundary tests still pass.
- Route responses use the uniform success envelope and Pydantic response models.

## M3 Acceptance: Static UI Write Controls

Scope:

- Add minimal write controls to the current Control Center page rather than replacing the page.
- Keep task creation and task action controls visually and behaviorally separate from read-only inspection panels.
- After a successful write, refresh the relevant existing read payloads instead of inventing frontend state as truth.
- Use backend `action_eligibility` booleans to enable or disable task action controls.
- Treat `run` / `retry` / `resume` / `rerun` as long-running requests: show pending state, prevent duplicate submission for the selected action while pending, and refresh the read model when the request completes.
- Show HTTP error details in the UI without encoding backend state-machine rules in JavaScript.

Acceptance:

- Existing dashboard sections remain present.
- Static index assertions for new form/control IDs and target route strings live in `tests/test_web_api.py` beside the existing Control Center dashboard assertions.
- UI JavaScript writes use local `fetch(...)` to the in-scope `POST` routes only.
- UI JavaScript does not branch on raw task `status` / `phase` to infer retry/resume/rerun availability; it consumes backend eligibility fields.
- No new frontend package, build step, or asset pipeline is introduced.

## M4 Acceptance: Guard And Closeout

Scope:

- Expand `test_ui_backend_only_calls_governance_functions` so it covers any new web helper module, not only `api.py`.
- Add positive guard assertions where useful: web routes import from `application.commands` / `application.queries`, not from `orchestration`, `truth_governance.store`, repository private writer modules, or SQLite helpers.
- Enforce loopback-only serving in `surface_tools/web/server.py` or the CLI entrypoint before uvicorn starts.
- Remove framework-rejection leftovers: no `globals().update(...)` schema bridge, no custom `WebRequestError` that mirrors `HTTPException`, no hand-rolled response converters where `response_model=` applies, and no `_status_for_value_error` message-prefix status classifier.
- Record deferred follow-ups explicitly:
  - browser file upload and `.swl/uploads` lifecycle;
  - route / policy admin write controls;
  - fire-and-poll / background task runner for long-running task actions;
  - any touched-surface LTO-6 knowledge facade migration left open.
- Prepare closeout / PR material after implementation review.

Acceptance:

- `tests/test_invariant_guards.py -q` passes.
- `tests/unit/application/test_command_boundaries.py -q` passes.
- Focused HTTP and web tests pass.
- A serve safety test covers rejection of a non-loopback host such as `0.0.0.0`.
- Full default pytest, compileall, and diff hygiene pass at PR gate.

## Material Risks

| Risk | Control |
|---|---|
| Web API becomes a hidden business layer | Route handlers are constrained to request validation, command invocation, error mapping, and response serialization. Guard tests scan for direct writes and private lower-layer imports. |
| FastAPI is used only as a router while framework features are reimplemented | Framework-default principle requires Pydantic response models, `response_model=`, centralized exception handlers, `Depends`, and TestClient unless a documented exception exists. |
| Write-route scope balloons into full CLI parity | This phase explicitly starts with task lifecycle plus staged knowledge / proposal review. File upload and route / policy admin writes are deferred. |
| Request schema grows a new dependency surface | Keep Pydantic schemas inside `surface_tools/web/schemas.py`; keep FastAPI/Pydantic imports localized to FastAPI app construction and out of application/domain modules. |
| Long-running task routes make the UI look hung | LTO-13 accepts long requests deliberately, shows pending state in the UI, prevents duplicate submission, and records fire-and-poll as a separate phase rather than hiding the tradeoff. |
| UI encodes backend state-machine rules | Backend read models expose action eligibility. JavaScript consumes eligibility booleans and does not infer retry/resume/rerun semantics from raw task fields. |
| HTTP tests fail in default dev environments | Add FastAPI to the `dev` optional dependency group before introducing `tests/integration/http/`; runtime `swl serve` still handles missing FastAPI as an optional dependency error. |
| Proposal path inputs become path traversal risk | Accept only workspace-relative proposal artifact paths, resolve them under `base_dir`, reject absolute paths and parent traversal, and cover both failures in HTTP tests. |
| Knowledge promote bypass is too cheap over HTTP | Do not expose `force=True` in the Web request schema or UI in this phase; return `409` notices and leave force to CLI until a dedicated confirmation UX exists. |
| Unauthenticated write surface is exposed on LAN | Enforce loopback-only host values for `swl serve` before uvicorn starts. |
| Existing absolute workspace_root storage is mistaken for an LTO-13 regression | Document it as a pre-existing gap and prevent the web adapter from accepting client-supplied workspace roots; defer the underlying storage cleanup. |
| Static UI starts storing truth-like state | After writes, refresh existing backend read models. JavaScript must not own task state transitions or proposal policy. |
| LTO-6 facade migration leaks into this phase | New application-layer touches should prefer public exports. If broader knowledge facade cleanup is needed, record it as a follow-up rather than expanding LTO-13. |

## Validation

Focused implementation gates:

```bash
.venv/bin/python -m pytest tests/integration/http -q
.venv/bin/python -m pytest tests/test_web_api.py -q
.venv/bin/python -m pytest tests/unit/application/test_command_boundaries.py -q
.venv/bin/python -m pytest tests/test_invariant_guards.py -q
.venv/bin/python -m pytest tests/unit/surface_tools/test_web_server.py -q
git diff --check -- pyproject.toml src/swallow/surface_tools/web tests/integration/http tests/test_web_api.py tests/test_invariant_guards.py
```

Final PR gate:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src/swallow
git diff --check
```

## Branch And Commit Recommendation

- Current implementation branch: `feat/lto-13-fastapi-local-web-ui-write-surface`.
- Because Round 2 / Round 3 audit materially changed the implementation contract after the first code pass, do not commit the current implementation as the milestone until the follow-up work above lands.
- Suggested milestone commits after follow-up:
  - `docs(plan): absorb lto13 web audit follow-ups`
  - `feat(web): add task lifecycle write routes`
  - `feat(web): add knowledge and proposal write routes`
  - `feat(web): wire control center write controls`
  - `test(web): harden control center write guards`
  - `docs(state): sync lto13 closeout state`

## Completion Conditions

1. The local FastAPI adapter exposes the in-scope `POST` write routes.
2. All write routes call existing `application/commands` functions and do not directly write Truth.
3. Existing read-only Control Center `GET` routes and payload shapes remain compatible.
4. New write routes use Pydantic request and response models, `response_model=`, FastAPI dependencies, and centralized exception handlers unless an exception is explicitly documented.
5. Task read models expose backend-derived action eligibility consumed by the static UI.
6. Static Control Center exposes minimal operator controls for the new write routes, including pending state for long-running task actions.
7. The unauthenticated write surface refuses non-loopback `swl serve` hosts.
8. UI backend guard tests cover the expanded web layer.
9. Browser file upload, route / policy admin write controls, background fire-and-poll execution, and broad LTO-6 facade cleanup are recorded as deferred rather than silently absorbed.
10. Focused HTTP tests, web API tests, invariant guards, full default pytest, compileall, and diff hygiene pass before PR review.
