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
- plan audit: `has-concerns`, 0 blockers / 5 concerns / 1 nit; concerns absorbed in this revision.

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
| Request body schema | Use small stdlib `dataclass` request DTOs plus explicit coercion / validation helpers at the HTTP boundary. Do not add a mandatory Pydantic dependency or top-level FastAPI import. |
| HTTP verbs | Use `POST` for all mutation commands, including action-style commands such as run / resume / retry / promote / apply. Existing `GET` routes remain read-only. |
| Error mapping | `400` for malformed payloads or invalid command arguments; `404` for unknown task / candidate / artifact / proposal records; `409` for blocked task recovery or state-conflict outcomes; unexpected errors remain ordinary `500` failures. |
| Sync vs async | Keep route handlers synchronous. Current application commands and local SQLite/filesystem paths are synchronous; do not introduce async wrappers in this phase. |
| Static UI | Add a narrow write-control panel to the existing static Control Center for the in-scope routes. The UI may call local `fetch(...)` routes and refresh existing read models after success. |
| Proposal artifact path bridge | HTTP proposal review/apply requests carry workspace-relative artifact paths, not absolute paths. The adapter resolves them under `base_dir`, rejects absolute paths and parent traversal, verifies existence, then passes `Path` objects to existing proposal application commands. |
| Test dependency strategy | Add `fastapi` to the `dev` optional dependency group before introducing HTTP round-trip tests. New `tests/integration/http/` tests should use FastAPI's test client without making `fastapi` a mandatory runtime dependency. |
| Operator token source | Do not add a new `OperatorToken(source="web")` in this phase. Existing application commands keep using `source="cli"` as the current generic local-operator source; changing token taxonomy requires separate design review. |

## Plan Audit Absorption

`docs/plans/lto-13-fastapi-local-web-ui-write-surface/plan_audit.md` raised 5 concerns and 1 nit. This revision absorbs them as follows:

- C-1 workspace root: M1 now treats absolute `workspace_root` storage as a pre-existing CLI/orchestrator gap. The web adapter must not accept client-supplied `workspace_root` or make the exposure worse; the §7 cleanup is deferred.
- C-2 FastAPI tests: M1 now requires adding `fastapi` to the `dev` optional dependency group before HTTP round-trip tests are added.
- C-3 proposal path bridge: M2 now defines the HTTP convention as workspace-relative artifact paths resolved under `base_dir`, with absolute paths and parent traversal rejected.
- C-4 UI guard: M2 now moves `apply_proposal` into `UI_FORBIDDEN_WRITE_CALLS` as part of the write-route milestone, instead of deferring that protection to M4.
- C-5 OperatorToken source: this phase keeps existing `source="cli"` semantics for all local operator writes through shared application commands; no `"web"` source is introduced.
- N-1 static index tests: M3 static markup and route-string assertions stay in `tests/test_web_api.py` beside the existing dashboard index assertions.

## Target Surface Shape

| Area | Target ownership |
|---|---|
| `surface_tools/web/api.py` | FastAPI adapter, route registration, local HTTP error mapping, and static file serving. It may call `application/commands` and `application/queries`, but not lower layers directly. |
| `surface_tools/web/http_models.py` or equivalent | Optional small request DTO / payload coercion helpers if keeping them in `api.py` would make the adapter hard to audit. No FastAPI or Pydantic import at module import time. |
| `application/commands/tasks.py` | Shared task lifecycle command functions for task create / run / retry / resume / rerun / acknowledge. |
| `application/commands/knowledge.py` | Shared staged knowledge promote / reject functions. |
| `application/commands/proposals.py` | Shared Meta-Optimizer proposal review / apply functions. |
| `surface_tools/web/static/index.html` | Existing dashboard plus minimal write controls and refresh behavior. |
| `tests/integration/http/` | New focused HTTP write-route contract tests. Existing `tests/test_web_api.py` remains the read-route / payload compatibility home unless a narrow move is clearly beneficial. |
| `tests/test_invariant_guards.py` | Expanded UI backend guard for direct writer / private repository / raw SQL drift in the web layer and any new web helper module. |

## In-Scope HTTP Routes

Task lifecycle:

- `POST /api/tasks`
- `POST /api/tasks/{task_id}/run`
- `POST /api/tasks/{task_id}/retry`
- `POST /api/tasks/{task_id}/resume`
- `POST /api/tasks/{task_id}/rerun`
- `POST /api/tasks/{task_id}/acknowledge`

Review / apply:

- `POST /api/knowledge/staged/{candidate_id}/promote`
- `POST /api/knowledge/staged/{candidate_id}/reject`
- `POST /api/proposals/review`
- `POST /api/proposals/apply`

The route names may be adjusted during implementation if FastAPI path matching or UI ergonomics make a nearby spelling clearer, but the semantics above are the bounded surface for this phase.

## Boundary Rules

- Web write routes call only shared application command functions for mutation behavior.
- Web handlers may validate request shape, coerce primitive JSON values, map exceptions to HTTP errors, and serialize command results.
- Web handlers must not call `save_state`, `append_event`, `apply_proposal`, repository private writer methods, SQLite connection helpers, or `run_task` / `create_task` directly.
- Web handlers must not import `truth_governance.governance.apply_proposal`; proposal and canonical writes reach it only through `application.commands.proposals` or `application.commands.knowledge`.
- Web handlers that accept filesystem references may only accept workspace-relative paths, resolve them under `base_dir`, reject absolute paths and `..` traversal, and verify existence before calling application commands.
- Application command modules remain terminal-format-free and continue to be covered by `tests/unit/application/test_command_boundaries.py`.
- The web layer must not import `knowledge_retrieval.*` implementation modules directly. If a new application command touch is required, prefer public application or facade exports and record any unavoidable LTO-6 follow-up in closeout.
- Existing read-only `GET` payload shapes are compatibility targets.
- Static UI write controls are UX adapters only; they must not encode task state machine rules or proposal apply policy in JavaScript.

## Milestones

| Milestone | Slice | Scope | Risk | Gate |
|---|---|---|---|---|
| M1 | HTTP contract + task lifecycle writes | Add dev FastAPI dependency, request DTO / coercion helpers, and task lifecycle `POST` routes; call `application.commands.tasks`; add focused HTTP tests for success and expected 400 / 404 / 409 paths. | high | `tests/integration/http` task write tests + `tests/test_web_api.py` read regression + UI guard |
| M2 | Knowledge and proposal write routes | Add staged promote / reject and proposal review / apply routes through `application.commands.knowledge` and `application.commands.proposals`; define workspace-relative proposal artifact path resolution; preserve `apply_proposal` as the only canonical / route mutation entry through those commands. | high | knowledge/proposal HTTP tests + governance and application command boundary tests + UI `apply_proposal` guard |
| M3 | Static Control Center write controls | Add a narrow task action / review action panel to `index.html`; wire local `fetch(...)` calls, success refresh, and visible error handling without adding a frontend framework. | medium-high | `tests/test_web_api.py` static index assertions + smoke tests for route names in UI + web route tests |
| M4 | Guard hardening, cleanup, closeout | Tighten `test_ui_backend_only_calls_governance_functions`, remove dead local helpers, run full gates, and record deferred file upload / route-policy admin items. | medium | full pytest + compileall + diff hygiene + closeout / PR material |

## M1 Acceptance: Task Lifecycle Write Routes

Scope:

- Introduce the route contract and request DTO pattern.
- Add `fastapi` to `pyproject.toml`'s `dev` optional dependency group before adding HTTP round-trip tests. Keep FastAPI optional for production/runtime imports.
- Implement task write routes for create, run, retry, resume, rerun, and acknowledge.
- Derive `workspace_root` from the local workspace by default for `POST /api/tasks`; do not accept `workspace_root` from the client request body.
- Treat current absolute `TaskState.workspace_root` persistence as a pre-existing CLI/orchestrator gap. LTO-13 must not widen it or add a second path input surface; fixing the underlying §7 storage issue is deferred to a later phase.
- Return compact JSON responses that include at minimum `task_id`, `status`, `phase`, and blocked/conflict details when applicable.
- Keep existing read-only payload builders and route behavior unchanged.

Acceptance:

- Focused HTTP tests prove each M1 route calls the expected application command path.
- `pyproject.toml` has a `dev` dependency entry for FastAPI, while `swallow.surface_tools.web.api` remains importable without FastAPI installed until `create_fastapi_app()` is called.
- Expected invalid payloads map to `400`.
- Unknown task IDs map to `404`.
- Blocked retry / resume / acknowledge flows map to `409` with a structured reason.
- `tests/test_web_api.py -q` still passes.
- `test_ui_backend_only_calls_governance_functions` passes without a broad allowlist.

## M2 Acceptance: Knowledge And Proposal Writes

Scope:

- Implement staged knowledge promote / reject routes.
- Implement proposal review / apply routes for the existing Meta-Optimizer proposal flow.
- Keep canonical and route metadata mutation behind `application.commands.knowledge` / `application.commands.proposals`, which in turn use existing governance APIs.
- For proposal review/apply requests, accept `bundle_path` / `review_path` as workspace-relative strings, resolve them under `base_dir`, reject absolute paths and parent traversal, verify the target exists, and then pass the resolved `Path` to `review_proposals_command` / `apply_reviewed_proposals_command`.
- Add `apply_proposal` to `UI_FORBIDDEN_WRITE_CALLS` in `tests/test_invariant_guards.py` in the same milestone that introduces proposal/canonical web write routes.
- Add HTTP tests for successful promote / reject / review / apply and representative missing-record failures.

Acceptance:

- No direct `apply_proposal(` call is introduced in `surface_tools/web/*.py`.
- `test_ui_backend_only_calls_governance_functions` fails on direct web-layer `apply_proposal` imports or calls.
- Absolute proposal artifact paths, missing relative paths, and parent traversal paths are covered by HTTP tests and map to `400` or `404` as appropriate.
- No direct private writer tokens or SQLite mutation strings appear in the web layer.
- Existing governance tests and application command boundary tests still pass.
- Route responses include enough structured fields for the static UI to refresh the relevant read model without parsing CLI text.

## M3 Acceptance: Static UI Write Controls

Scope:

- Add minimal write controls to the current Control Center page rather than replacing the page.
- Keep task creation and task action controls visually and behaviorally separate from read-only inspection panels.
- After a successful write, refresh the relevant existing read payloads instead of inventing frontend state as truth.
- Show HTTP error details in the UI without encoding backend state-machine rules in JavaScript.

Acceptance:

- Existing dashboard sections remain present.
- Static index assertions for new form/control IDs and target route strings live in `tests/test_web_api.py` beside the existing Control Center dashboard assertions.
- UI JavaScript writes use local `fetch(...)` to the in-scope `POST` routes only.
- No new frontend package, build step, or asset pipeline is introduced.

## M4 Acceptance: Guard And Closeout

Scope:

- Expand `test_ui_backend_only_calls_governance_functions` so it covers any new web helper module, not only `api.py`.
- Add positive guard assertions where useful: web routes import from `application.commands` / `application.queries`, not from `orchestration`, `truth_governance.store`, repository private writer modules, or SQLite helpers.
- Record deferred follow-ups explicitly:
  - browser file upload and `.swl/uploads` lifecycle;
  - route / policy admin write controls;
  - any touched-surface LTO-6 knowledge facade migration left open.
- Prepare closeout / PR material after implementation review.

Acceptance:

- `tests/test_invariant_guards.py -q` passes.
- `tests/unit/application/test_command_boundaries.py -q` passes.
- Focused HTTP and web tests pass.
- Full default pytest, compileall, and diff hygiene pass at PR gate.

## Material Risks

| Risk | Control |
|---|---|
| Web API becomes a hidden business layer | Route handlers are constrained to request validation, command invocation, error mapping, and response serialization. Guard tests scan for direct writes and private lower-layer imports. |
| Write-route scope balloons into full CLI parity | This phase explicitly starts with task lifecycle plus staged knowledge / proposal review. File upload and route / policy admin writes are deferred. |
| Request schema grows a new dependency surface | Use stdlib dataclasses and explicit coercion helpers; keep FastAPI optional imports localized. |
| HTTP tests fail in default dev environments | Add FastAPI to the `dev` optional dependency group before introducing `tests/integration/http/`; runtime `swl serve` still handles missing FastAPI as an optional dependency error. |
| Proposal path inputs become path traversal risk | Accept only workspace-relative proposal artifact paths, resolve them under `base_dir`, reject absolute paths and parent traversal, and cover both failures in HTTP tests. |
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
git diff --check -- pyproject.toml src/swallow/surface_tools/web tests/integration/http tests/test_web_api.py tests/test_invariant_guards.py
```

Final PR gate:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src/swallow
git diff --check
```

## Branch And Commit Recommendation

- Plan / audit stay on `main` until Human Plan Gate.
- Implementation branch after Plan Gate: `feat/lto-13-fastapi-local-web-ui-write-surface`.
- Suggested milestone commits:
  - `docs(plan): add lto13 fastapi write surface plan`
  - `feat(web): add task lifecycle write routes`
  - `feat(web): add knowledge and proposal write routes`
  - `feat(web): wire control center write controls`
  - `test(web): harden control center write guards`
  - `docs(state): sync lto13 closeout state`

## Completion Conditions

1. The local FastAPI adapter exposes the in-scope `POST` write routes.
2. All write routes call existing `application/commands` functions and do not directly write Truth.
3. Existing read-only Control Center `GET` routes and payload shapes remain compatible.
4. Static Control Center exposes minimal operator controls for the new write routes.
5. UI backend guard tests cover the expanded web layer.
6. Browser file upload, route / policy admin write controls, and broad LTO-6 facade cleanup are recorded as deferred rather than silently absorbed.
7. Focused HTTP tests, web API tests, invariant guards, full default pytest, compileall, and diff hygiene pass before PR review.
