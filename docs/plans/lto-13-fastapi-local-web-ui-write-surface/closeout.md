---
author: codex
phase: lto-13-fastapi-local-web-ui-write-surface
slice: phase-closeout
status: final
depends_on:
  - docs/plans/lto-13-fastapi-local-web-ui-write-surface/plan.md
  - docs/plans/lto-13-fastapi-local-web-ui-write-surface/plan_audit.md
  - docs/plans/lto-13-fastapi-local-web-ui-write-surface/review_comments.md
  - docs/active_context.md
  - src/swallow/surface_tools/web/api.py
  - src/swallow/surface_tools/web/schemas.py
  - src/swallow/surface_tools/web/dependencies.py
  - src/swallow/surface_tools/web/exceptions.py
  - src/swallow/surface_tools/web/server.py
  - src/swallow/surface_tools/web/static/index.html
  - tests/integration/http/test_web_write_routes.py
  - tests/test_web_api.py
  - tests/test_invariant_guards.py
  - tests/unit/surface_tools/test_web_server.py
---

TL;DR:
LTO-13 implementation milestone is complete and committed at `d4c25ac feat(web): harden local write API surface`.
The local FastAPI Control Center now has an operator write surface for task lifecycle, staged knowledge review, and Meta-Optimizer proposal review/apply, while preserving the application-command boundary and Truth write invariants.
Claude PR review returned recommend-merge with 0 blockers / 1 concern / 2 nits; the concern and one nit were addressed in final closeout cleanup, and the remaining nit is deferred to the driven-port test strategy.

# LTO-13 Closeout: FastAPI Local Web UI Write Surface

## Outcome

Implemented Swallow's first local Web UI write surface:

- Added `POST` write routes for task create/run/retry/resume/rerun/acknowledge.
- Added staged knowledge promote/reject routes.
- Added Meta-Optimizer proposal review/apply routes.
- Wired the static Control Center to call the new local routes and refresh backend read models after writes.
- Preserved existing read-only `GET` routes and payload compatibility, with additive task action eligibility fields.

All writes flow through existing `application/commands/*` functions. The Web adapter does not call Orchestrator internals, raw Truth writers, repository private writers, raw SQLite helpers, or `apply_proposal` directly.

## Implementation Notes

The final implementation absorbed the original plan audit, the Pydantic follow-up, and Round 2 / Round 3 audit concerns:

- `surface_tools/web/schemas.py` now owns adapter-scoped Pydantic request and response models.
- New write routes declare `response_model=` and return a uniform success envelope:
  `{"ok": true, "data": ...}`.
- `surface_tools/web/api.py` uses FastAPI `Depends` for `base_dir` access and centralized `@app.exception_handler` mappings.
- `surface_tools/web/http_models.py` was removed; hand-written response converters, `WebRequestError`, `globals().update(...)`, and message-prefix status mapping were eliminated.
- `application.commands.knowledge.UnknownStagedCandidateError` replaces message-string classification for unknown staged candidates.
- `application/queries/control_center.py` adds backend-derived `action_eligibility` for task actions so UI JavaScript does not implement task state-machine rules.
- Web staged knowledge promote no longer exposes `force=True`; force remains CLI-only until a separate confirmation UX is designed.
- `surface_tools/web/server.py` now rejects non-loopback host binding for the unauthenticated write surface.
- Final review cleanup moved `StagedCandidate` consumption behind the application command public surface and simplified `_static_dir()` without `Path.cwd()`.

## Scope Delivered

| Plan area | Result |
|---|---|
| Task lifecycle writes | Delivered: create, run, retry, resume, rerun, acknowledge. |
| Knowledge staged review | Delivered: promote and reject through application commands; Web `force` bypass not exposed. |
| Proposal review/apply | Delivered: workspace-relative bundle/review paths resolved under `base_dir`; absolute, traversal, and missing paths rejected. |
| Framework-default principle | Delivered: request/response Pydantic models, `response_model=`, `Depends`, centralized exception handlers, OpenAPI response contracts, FastAPI TestClient coverage. |
| Static UI controls | Delivered: task create/actions, staged promote/reject, proposal review/apply, pending state for long-running task actions, backend eligibility consumption. |
| Guard hardening | Delivered: UI forbidden write calls include `apply_proposal`, `create_task`, `run_task`; web helper modules are scanned by existing guard. |
| Serve safety | Delivered: loopback-only host validation. |

## Validation

Final validation performed before implementation milestone commit:

```text
tests/integration/http/test_web_write_routes.py: 9 passed
tests/test_web_api.py + tests/unit/surface_tools/test_web_server.py: 12 passed
tests/test_invariant_guards.py + tests/unit/application/test_command_boundaries.py: 38 passed
tests/unit/application/test_control_center_queries.py: 1 passed
tests/test_cli.py: 242 passed
compileall -q src/swallow: passed
git diff --check: passed
full pytest: 745 passed, 8 deselected
```

Post-review cleanup revalidation after C1/N1 fixes:

```text
focused Web/Application/Invariant gate: 59 passed
compileall -q src/swallow: passed
git diff --check: passed
full pytest: 745 passed, 8 deselected
```

Implementation milestone commit:

```text
d4c25ac feat(web): harden local write API surface
```

## Deferred Follow-Ups

These remain intentionally out of LTO-13 scope:

- Browser file upload and `.swl/uploads` lifecycle.
- Route / policy admin write controls.
- Fire-and-poll / background task runner for long-running task actions.
- Dedicated Web confirmation UX for staged knowledge promote force.
- Underlying `TaskState.workspace_root` absolute-path storage cleanup.
- Broader LTO-6 knowledge facade migration beyond this touched surface.

## Review Status

Claude PR review is complete:

```text
docs/plans/lto-13-fastapi-local-web-ui-write-surface/review_comments.md
verdict: recommend-merge
findings: 0 blockers / 1 concern / 2 nits
```

Disposition:

- C1 (`schemas.py` direct `knowledge_retrieval.*` import): fixed by re-exporting `StagedCandidate` from `application.commands.knowledge` and importing it from the application command surface in Web schemas.
- N1 (`_static_dir()` used `Path.cwd()` as a dead base): fixed by using `Path(__file__).parent / "static"` without `Path.resolve()`, preserving invariant guard compliance.
- N2 (HTTP test runs real `local` executor): acknowledged and deferred until D2 driven ports make command-boundary stubbing cheaper and cleaner.

## Final State

LTO-13 is ready for Human merge gate.

Post-merge steps:

- Codex should update `current_state.md` and `docs/active_context.md`.
- Roadmap factual state should be updated after merge.
- Claude / Human should evaluate whether this user-visible Web write surface merits `v1.7.0`.
