---
author: claude
phase: lto-13-fastapi-local-web-ui-write-surface
slice: plan-audit
status: draft
depends_on:
  - docs/plans/lto-13-fastapi-local-web-ui-write-surface/plan.md
  - docs/design/INVARIANTS.md
  - src/swallow/surface_tools/web/api.py
  - src/swallow/application/commands/tasks.py
  - src/swallow/application/commands/knowledge.py
  - src/swallow/application/commands/proposals.py
  - tests/test_invariant_guards.py
  - tests/test_web_api.py
---

TL;DR: has-concerns — 4 slices + post-impl round 2 + framework-rejection round 3; 23 issues found (0 blockers, 14 concerns, 4 nits, 4 confirmed-OK anchors)

## Audit Verdict

Overall: has-concerns

No blockers were found. The plan is structurally sound and INVARIANTS-aligned. Round 1 surfaced 6
concerns + 1 nit; Round 2 (post-implementation deep re-read) surfaced 4 additional concerns + 2
nits, the most material being the long-running blocking nature of `POST .../run|retry|resume|rerun`
which the plan's "keep handlers synchronous" decision treats as a short-request pattern. Together
the unresolved findings include (1) proposal command path-parameter bridging (M2), (2) FastAPI dev
dependency / test environment, (3) DTO/Pydantic decision conflation, (4) long-running handler
contract gap, (5) run-style route semantic distinction, (6) response shape spec coverage, and
(7) `force` flag wire format and UX. Implementation has shipped against the original plan; these
findings require both plan-text revision and targeted impl follow-up before PR review.

---

## Issues by Slice

### Slice M1: HTTP Contract + Task Lifecycle Writes

- [OK] The `create_task_command` / `run_task_command` / `retry_task_command` / `resume_task_command` /
  `rerun_task_command` / `acknowledge_task_command` signatures are all present in
  `src/swallow/application/commands/tasks.py` and do not require new exception types. The blocked
  conditions (`blocked_kind`, `blocked_reason`) are returned as fields on the result dataclasses, not
  raised, so a `409` mapping is straightforward.

- [CONCERN] `workspace_root` is stored as an absolute path in Truth today.
  `orchestrator.create_task` calls `_resolved_path_string(workspace_root)` (line 2313,
  `orchestrator.py`) which calls `resolve_path()` and then `str()`, yielding an absolute path that is
  written to the `TaskState.workspace_root` field (a plain `str`, `orchestration/models.py:366`).
  INVARIANTS §7 requires `workspace_root` to store a relative path resolved at runtime.
  The plan says "do not persist user-supplied absolute paths as Truth fields" — this control is
  correct in intent but cannot be fully satisfied by the web adapter alone: even if the adapter
  derives `workspace_root` from `base_dir` rather than accepting it from the request body, the
  existing `create_task_command` → `create_task` path will call `resolve_path()` and produce an
  absolute path before it reaches the store. The plan does not call out that the absolute-path
  invariant is already violated in the existing CLI path, nor does it instruct Codex to fix or
  document this as a pre-existing gap. Without a note, Codex may either (a) silently carry over the
  violation, or (b) attempt to fix it inline and widen scope unexpectedly.
  Recommended action: add a scoped note to M1 that `workspace_root` absolute-path storage is a
  pre-existing condition, that the web adapter should not make it worse (i.e., do not accept raw
  client-supplied paths as `workspace_root`), and that the §7 cleanup is deferred to a later phase.

- [CONCERN] FastAPI and httpx (needed as the ASGI test client) are not declared in any dependency
  group in `pyproject.toml`. The existing `tests/test_web_api.py` avoids this by only calling
  `create_fastapi_app()` to inspect route metadata, gracefully skipping if FastAPI is absent. The
  new `tests/integration/http/` tests must actually exercise HTTP round-trips (that is their purpose),
  which requires `fastapi.testclient.TestClient` or `httpx.AsyncClient` backed by an ASGI transport.
  Both require `fastapi` and `httpx` to be installed. `httpx` is already a mandatory production
  dependency, but `fastapi` is not installed in the project venv (confirmed: `ModuleNotFoundError`
  when importing `fastapi` in `.venv`). The plan does not prescribe adding a `serve` or `web` extras
  group, nor does it say how `tests/integration/http/` should handle the missing-FastAPI case.
  If the new tests do not guard against the missing import, they will fail in any environment that
  does not have FastAPI installed, including the standard `pytest -q` gate.
  Recommended action: either add `fastapi` to the `dev` optional-dependency group in `pyproject.toml`
  (preferred — keeps CI consistent) or specify a `pytest.importorskip("fastapi")` convention for the
  new integration tests and document it explicitly in the plan.

- [OK] The `run_task_command` signature requires `executor_name: str | None`, `capability_refs:
  list[str] | None`, and `route_mode: str | None`. These are all optional primitive/list fields that
  a stdlib dataclass DTO can carry cleanly. No nested object complexity.

- [CONCERN] (post-audit follow-up, raised in plan-gate discussion 2026-05-03) The §Design Decisions
  row "Use small stdlib `dataclass` request DTOs ... Do not add a mandatory Pydantic dependency or
  top-level FastAPI import" conflates two unrelated constraints:
  (a) the real INVARIANTS-level hard rule that `surface_tools/web/api.py` must remain importable
  without FastAPI installed (so `swl serve` does not raise `ImportError` at module load), and
  (b) the schema/validation tooling choice for HTTP request bodies.
  Pydantic is FastAPI's own hard dependency — it is automatically installed whenever `fastapi` is
  installed (and `fastapi` is already declared in `pyproject.toml` `[project.optional-dependencies]
  dev`, line 19). The "do not add a mandatory Pydantic dependency" clause therefore prevents nothing
  on the dependency side; what it actually enforces is "do not use Pydantic at all", which is a
  separate and over-constrained decision derived from (a).
  Cost of the stdlib-dataclass-only path the plan currently mandates:
  • each route must hand-write a `from_json(data: dict)` parser plus per-field coercion (e.g., the
    `executor_name: str | None`, `capability_refs: list[str] | None`, `route_mode: str | None`
    combination on `POST /api/tasks/{task_id}/run` has multiple Optional/list edge cases — empty
    string vs null vs missing key — that Pydantic handles uniformly and the team will otherwise have
    to invent and test);
  • the plan's `400` for malformed payloads must be hand-mapped, while FastAPI+Pydantic returns a
    structured `422` with field-level detail by default, meaning the team has to either (i) reinvent
    the error body shape or (ii) override FastAPI's default behavior;
  • OpenAPI schema generation is lost (FastAPI derives it from Pydantic models);
  • each new write route in future phases will repeat the same hand-rolled coercion pattern, which
    is exactly the kind of shape drift INVARIANTS §6 cautions against.
  Resolution shape: split the rule into two independent constraints —
  (1) `surface_tools/web/api.py` top-level imports must not depend on FastAPI or Pydantic; both
      may only be imported inside `create_fastapi_app()` or in a dedicated module such as
      `surface_tools/web/http_models.py` that is itself imported only from inside the factory;
  (2) request body validation uses Pydantic models (lazy-imported through that module); error
      responses use FastAPI's default `422` for schema validation failures, with `api.py` only
      mapping domain-level outcomes (unknown record → `404`, blocked / state-conflict → `409`)
      to the plan's stated taxonomy.
  This change preserves the importable-without-FastAPI invariant while removing the hand-rolled
  coercion burden across M1 / M2 and any future write-route phase.

### Slice M2: Knowledge And Proposal Write Routes

- [BLOCKER — downgraded to CONCERN after full analysis] `review_proposals_command` and
  `apply_reviewed_proposals_command` both take filesystem `Path` arguments (`bundle_path` and
  `review_path` respectively). These are paths to artifact files on the local filesystem:
  `review_optimization_proposals(base_dir, bundle_path, ...)` loads the bundle from disk;
  `apply_reviewed_proposals_command(base_dir, review_path, ...)` loads the review record from disk.
  Over HTTP, the caller cannot pass a `Path` — they must pass an identifier the server resolves to a
  path. The plan names `POST /api/proposals/review` and `POST /api/proposals/apply` but does not
  specify how the route handler bridges the gap between a request body (which can carry a string ID
  or relative path) and the `Path` arguments the command functions require. The existing CLI uses
  `click.Path(exists=True)` to resolve these before calling the command. The web adapter has no
  equivalent mechanism defined in the plan.
  This is the single most implementation-blocking ambiguity in M2. Codex will have to invent a
  convention: either (a) the request body carries a relative artifact path that the handler resolves
  against `base_dir`, (b) the request body carries a proposal/review artifact ID that the handler
  maps to a filesystem path via a lookup function, or (c) a new application command variant is added
  that accepts an ID instead of a path. None of these options is called out, and each has different
  implications for the boundary rules. Classification kept as [CONCERN] rather than [BLOCKER] because
  a sensible default exists (option a: relative path string in the request body, resolved against
  `base_dir` in the handler), but the plan must state the convention explicitly or Codex will make an
  undocumented assumption.

- [CONCERN] `apply_proposal` is NOT in `UI_FORBIDDEN_WRITE_CALLS`
  (`tests/test_invariant_guards.py:104-112`). The plan's M2 acceptance criterion says "No direct
  `apply_proposal(` call is introduced in `surface_tools/web/*.py`" — but the existing guard test
  will not catch a violation of this rule. `apply_proposal` is in `TRUTH_WRITE_CALLS` (line 98) but
  the UI guard set is a strict subset that omits it. If Codex accidentally imports or calls
  `apply_proposal` directly in `api.py` or `http_models.py`, the acceptance test named in the plan
  (`test_ui_backend_only_calls_governance_functions`) will still pass.
  M4 is supposed to harden the guard, but M2's acceptance criterion depends on it being enforced
  at M2 gate. Either move the guard hardening for `apply_proposal` forward to M2 acceptance, or
  note explicitly that the M2 check is manual/code-review-only (not automated).

- [OK] `promote_stage_candidate_command` and `reject_stage_candidate_command` in
  `application/commands/knowledge.py` take only `base_dir`, `candidate_id`, `note`, and optionally
  `refined_text` / `force` — all primitive fields. The stdlib dataclass DTO pattern handles these
  cleanly. The `StagePromotePreflightError` subclass carries a `notices` list which maps naturally to
  a structured `409` body. The error taxonomy is sufficient without new exception types.

### Slice M3: Static Control Center Write Controls

- [NIT] The M3 acceptance criterion requires "Static index tests assert the new form/control IDs and
  target route strings." The existing `test_control_center_static_index_contains_dashboard_sections`
  test in `test_web_api.py` is the home for these assertions. The plan does not say whether new M3
  static assertions live in `test_web_api.py` (alongside existing ones) or in a new file under
  `tests/integration/http/`. The wording "Static index tests" is ambiguous. This is a nit — Codex
  can decide at implementation time — but noting it avoids a review cycle.

- [OK] The boundary rule that "UI JavaScript must not encode task state machine rules or proposal
  apply policy" is enforceable and reviewable via code review of the static HTML/JS. The plan's
  description ("show HTTP error details in the UI without encoding backend state-machine rules in
  JavaScript") is concrete enough to implement: display the HTTP error body verbatim or as a message
  string; do not add conditional JS branches on task status. No guard test is needed for this; visual
  code review is the right gate.

### Slice M4: Guard Hardening, Cleanup, Closeout

- [OK] The plan's M4 description of expanding `test_ui_backend_only_calls_governance_functions` to
  cover any new helper modules (e.g. `http_models.py`) is implementable: the existing test already
  uses `rglob("*.py")` over `surface_tools/web/` (line 829, `test_invariant_guards.py`), so new
  files in that directory are automatically covered by the existing scan. No new scan logic is
  required, only ensuring the forbidden-call set is correct.

---

## Questions for Codex / Human

1. **M1 workspace_root**: The plan says "do not persist user-supplied absolute paths as Truth
   fields." Confirmed that `create_task` already resolves and stores an absolute path today
   (`orchestrator.py:2313`). Does the plan intend to fix this in LTO-13, or only to ensure the web
   adapter does not introduce additional absolute-path exposure? A one-line scoping note in M1 would
   remove ambiguity.

2. **M2 proposals path parameters**: `review_proposals_command` takes `bundle_path: Path` and
   `apply_reviewed_proposals_command` takes `review_path: Path`. How should the HTTP adapter
   supply these? Options are (a) relative path string in request body resolved against `base_dir`,
   (b) artifact ID mapped to path via a lookup, (c) new command variant. Which convention should
   Codex use? This must be decided before M2 implementation.

3. **FastAPI in test environment**: Should `fastapi` be added to the `dev` optional-dependency
   group so `tests/integration/http/` can run without special setup? Or should the new tests use
   `pytest.importorskip("fastapi")` and be skipped in environments without it?

4. **M2 guard coverage for `apply_proposal`**: Should the `apply_proposal` symbol be added to
   `UI_FORBIDDEN_WRITE_CALLS` as part of M2 (not deferred to M4), since the M2 acceptance criterion
   explicitly requires no direct `apply_proposal` call in the web layer?

5. **OperatorToken source for web-initiated writes**: All existing application commands that call
   governance write functions hardcode `OperatorToken(source="cli")`. The valid sources are `"cli"`,
   `"system_auto"`, `"librarian_side_effect"` — there is no `"web"` source. This is not a blocker
   (it is a single-user local tool), but should a `"web"` source value be added to `OperatorToken`
   in this phase, or is the `"cli"` source intentionally shared for all operator-initiated writes
   regardless of surface?

6. **DTO / Pydantic decision split**: The §Design Decisions row currently bans Pydantic outright.
   Since Pydantic is FastAPI's own hard dependency and rides in via `dev` extras automatically,
   the ban does not save any dependency surface — it only forces hand-rolled `from_json` /
   coercion / error-mapping per route. Should the rule be rewritten as two independent
   constraints (top-level import hygiene + use Pydantic models inside a lazy-imported
   `http_models.py`), recovering FastAPI's default `422` field-level validation and OpenAPI
   schema generation while preserving the importable-without-FastAPI invariant?

---

## Confirmed Ready

- M1 task lifecycle route mapping: command function signatures, blocked-state result shape, and error
  taxonomy are all present and sufficient for the plan's stated M1 scope.
- M2 knowledge promote/reject routes: `promote_stage_candidate_command` and
  `reject_stage_candidate_command` signatures are clean, error handling is well-typed, no new
  exception types required.
- M3 static UI contract: the boundary (no state machine in JS, refresh from backend read models) is
  specific enough to implement and review without a UI polish risk.
- M4 guard expansion: the existing `rglob("*.py")` scan in `test_ui_backend_only_calls_governance_functions`
  automatically covers new helper modules in `surface_tools/web/`; no structural test change is
  needed beyond updating the forbidden-call set.
- INVARIANTS alignment: no plan content contradicts the four cardinal rules in §0. The plan
  correctly identifies `apply_proposal` as the only canonical/route mutation entry and routes all
  writes through `application/commands`. The non-goal list directly mirrors the §6 accretion
  boundary rules.
- Test directory convention: `tests/integration/http/` follows the same subdirectory pattern as the
  existing `tests/integration/cli/`, which itself contains focused command-layer tests. No
  convention conflict.

---

## Round 2 — Post-Implementation Deep Re-Read (2026-05-03)

Trigger: human asked for a careful second-pass after Round 1 + Pydantic concern were absorbed and
implementation had shipped. Findings below were verified by reading the actual command / orchestrator
source, not just the plan text. Plan-gate has already passed; these are documented for plan-text
revision and targeted impl follow-up before PR review.

### R2-1 [CONCERN, critical] `run` / `retry` / `resume` / `rerun` are minute-scale blocking routes; plan treats them as short requests

`src/swallow/application/commands/tasks.py:192` `run_task_command` calls
`swallow.orchestration.orchestrator.run_task` which at `orchestrator.py:3273` is
`_run_orchestrator_sync(run_task_async(...))` — the entire LLM task pipeline runs to completion
before the call returns. Typical durations are minutes to tens of minutes.

Plan §Design Decisions row "Sync vs async" ("Keep route handlers synchronous. Current application
commands and local SQLite/filesystem paths are synchronous; do not introduce async wrappers in this
phase.") is correct for `create` / `acknowledge` / `promote` / `reject` (fast filesystem / SQLite
ops). It is wrong-by-omission for `run` / `retry` / `resume` / `rerun`, where the same sync handler
will block:

- the FastAPI threadpool slot for the full task duration (default ~40 threads → 40 concurrent
  long-running tasks before subsequent reads queue);
- the browser `fetch` connection for the full duration (no client-side timeout in default fetch,
  but any reverse proxy / corporate network will cut it);
- any visibility into intermediate progress — the route returns only the final `TaskState`, while
  plan §M3 acceptance does not specify how the UI shows in-flight progress for long writes.

Two coherent designs exist; the plan picks neither:

- (a) **fire-and-poll**: `POST .../run` returns 200 + `task_id` + `phase=pending` immediately;
  background thread (or task queue) drives `run_task`; UI polls existing `GET /api/tasks/{id}` /
  `GET /api/events` to refresh. Requires cancellation / ownership story for the background thread.
- (b) **accept long requests as the contract**: plan explicitly states fetch-side must use a long
  timeout, threadpool size is the concurrency cap, and document the operational trade.

Without a choice in plan text, both implementation and tests will silently land on whatever Codex
typed first; neither path gets reviewed for its real cost. Recommend plan §Design Decisions adds a
new row "Long-running write routes" and pins one of (a) / (b) explicitly.

### R2-2 [CONCERN] `run` / `retry` / `resume` / `rerun` semantic distinction is not surfaced to UI; backend doesn't expose eligibility flags

Reading the four command bodies in `src/swallow/application/commands/tasks.py`:

| Route | Command | Pre-conditions checked |
|---|---|---|
| `POST /api/tasks/{id}/run` | `run_task_command:182` | none — direct orchestrator entry |
| `POST /api/tasks/{id}/retry` | `retry_task_command:213` | `retry_policy.retryable=True` AND `stop_policy.checkpoint_kind ∈ {retry_review, detached_retry_review}`; otherwise returns `blocked_kind="retry"` |
| `POST /api/tasks/{id}/resume` | `resume_task_command:259` | `checkpoint_snapshot.resume_ready=True` AND `recommended_path="resume"`; otherwise returns `blocked_kind="resume"` |
| `POST /api/tasks/{id}/rerun` | `rerun_task_command:294` | none — always runs with `reset_grounding=True` |

The plan lists all four routes but does not specify when the UI should present which to the
operator. `acknowledged-dispatch reentry` further blurs `retry` and `resume` (both fall back to
`run_task_command` when `is_acknowledged_dispatch_reentry(state)` is true).

Plan §Boundary Rules forbids "encoding task state machine rules in JavaScript" — but if the backend
read model does not expose `retry_eligible` / `resume_eligible` / `rerun_eligible` boolean fields,
the UI has no choice but to encode the rules itself or expose all four buttons unconditionally and
let users hit `409 blocked`.

Recommendation: extend `application/queries/control_center.py` task payload (or one of its callers)
with eligibility booleans derived from the same retry/resume/checkpoint policy reads the commands
already perform; UI then renders only enabled buttons. Plan §Target Surface Shape and §M3
Acceptance should reference this contract.

### R2-3 [CONCERN] response-shape contract specced for only 1 of 10 routes

§M1 Acceptance specifies "Compact JSON responses include at minimum `task_id`, `status`, `phase`,
and blocked/conflict details when applicable." This is the only route response shape pinned in the
plan. The other 9 routes (`acknowledge`, four task-creation/run variants, `promote`, `reject`,
`review`, `apply`) have no committed response shape.

Practical consequences:

- Tests can only assert "the keys the implementation chose to emit"; review becomes circular.
- UI has to do a follow-up `GET` to refresh state instead of using the response body, which
  contradicts §M3 Acceptance "after a successful write, refresh the relevant existing read payloads
  instead of inventing frontend state as truth" — this language reads as "always GET again", but
  it leaves on the table the cheaper "use the POST response if it carries enough info" path.
- A future second-write-surface phase (e.g., file upload, route policy admin) has no precedent to
  follow on response envelope shape, so each phase reinvents.

Recommendation: in plan §HTTP Routes (or §Design Decisions), pin a uniform envelope, e.g.
`{"ok": bool, "data": {...domain fields...}, "blocked_kind": str | null, "blocked_reason": str | null}`
and per-route `data` field list. Or for each row in §HTTP Routes, add a `response keys` column.

### R2-4 [CONCERN] `force` flag on knowledge promote — wire format + UX implication unaddressed

`promote_stage_candidate_command(... force: bool = False)` (`application/commands/knowledge.py`)
bypasses `StagePromotePreflightError` checks when `force=True`. This is a safety-relevant bypass.
Plan §M2 lists `POST /api/knowledge/staged/{candidate_id}/promote` but says nothing about:

- wire format — does the request body carry `force` as a field, or is `force` exposed as a separate
  route (`/promote/force`), or is it intentionally not exposed at all in the web surface?
- UX — if `force` is exposed, must the UI require a second confirmation step? A bare
  `{"force": true}` POST from `curl` should not be cheaper than the CLI's confirmation flow.

This is a single-user local tool, but "I might curl this myself" is exactly when a missed safety
gate bites. Recommendation: plan §M2 Acceptance must take a position — either `force` is not
exposed in this phase (preferred conservative default; CLI keeps the escape hatch), or it is
exposed with a documented UX requirement (separate confirmation, audit-event, banner in UI).

### R2-5 [NIT] `swl serve --host` accepts non-loopback addresses with no guard

`src/swallow/surface_tools/web/server.py:8` defaults `host="127.0.0.1"`, but the `serve_control_center`
signature accepts arbitrary host strings, and `swl serve` exposes this on the CLI. Plan §Non-Goals
explicitly excludes authn/authz and remote API. There is no current guard preventing
`swl serve --host 0.0.0.0`, which exposes the entire local Truth + write surface to the LAN with no
authentication.

This is a low-cost hardening that fits LTO-13's "first write surface" framing: the moment writes
exist, the loopback assumption stops being a default and becomes a security invariant. A two-line
guard — `if host not in {"127.0.0.1", "localhost", "::1"}: raise RuntimeError("write surface
refuses non-loopback host")` — makes the design intent enforceable.

Recommendation: add this as an explicit acceptance bullet under M4 (guard hardening), or as a new
row in §Boundary Rules.

### R2-6 [NIT] `TaskAcknowledgeCommandResult` lacks `blocked_kind`; error-mapping helper will diverge

`TaskRecoveryCommandResult` (used by `retry` / `resume`) carries `blocked_kind: str | None` — the
plan's M1 acceptance says "Blocked retry / resume / acknowledge flows map to 409 with a structured
reason."

But `TaskAcknowledgeCommandResult` (`application/commands/tasks.py:209`) only has `blocked_reason:
str | None`, no `blocked_kind`. A unified `_map_command_result_to_http_response` helper that checks
`result.blocked_kind is not None` will fail to map acknowledge's blocked path to 409, silently
returning 200.

Recommendation: either (a) add `blocked_kind="acknowledge"` to `TaskAcknowledgeCommandResult` (one
line in `application/commands/tasks.py`) for symmetry with the recovery result type, or (b) plan
explicitly documents the asymmetry and the per-route mapping branch. Option (a) is cleaner and
keeps future write routes from re-tripping the same gap.

---

## Round 2 Summary for Codex

Plan revisions needed:

1. §Design Decisions — add explicit "long-running write routes" row pinning fire-and-poll vs
   accept-long-requests.
2. §HTTP Routes / §M1 / §M3 — surface eligibility booleans in the read model so UI does not encode
   state-machine rules.
3. §HTTP Routes (or §Design Decisions) — pin a uniform response envelope or per-route response key
   list.
4. §M2 Acceptance — take a position on `force` flag exposure (preferred: not exposed in this
   phase).
5. §M4 / §Boundary Rules — add the `swl serve` non-loopback host guard.

Implementation follow-ups:

- Add `blocked_kind="acknowledge"` to `TaskAcknowledgeCommandResult` for symmetry, or split the
  HTTP error-mapping helper.
- Verify (or implement) the host guard in `surface_tools/web/server.py`.
- Whichever choice is made on R2-1, ensure `tests/integration/http/` tests reflect the contract
  (timeout-tolerant if (b); polling shape if (a)).

---

## Round 3 — Framework-Rejection Pattern (2026-05-03)

Trigger: human raised a strategic worry — "Pydantic 那条问题有点明显了,我担心后续还有用一堆自写逻辑搞一些没必要的设计,导致返工." Round 3 verifies whether the Pydantic concern was an isolated mistake or part of a systematic pattern, by reading the actual implementation files.

### The Meta-Finding

The plan and implementation share a recurring pattern: **for every FastAPI/Pydantic capability, the
default decision is "write our own helper", not "use the framework primitive"**. Each instance is
small and looks reasonable in isolation; together they amount to using FastAPI as a router and
re-implementing the rest of the framework.

### Direct Answer to the Standing Question (adapter-only Pydantic, is it standard?)

**Yes, Pydantic confined to the web adapter is the standard pattern** (Hexagonal Architecture /
Ports & Adapters). Each adapter owns its own validation tooling: web → Pydantic, CLI → click,
future MCP/gRPC → its own. The application core (`application/commands/*`) stays primitive-typed
and framework-free, which is what allows multiple surfaces to share it. Pushing Pydantic into
`application/commands` would couple the domain to a web-framework dependency and is the genuine
anti-pattern.

The smell the human is sensing is not *where* Pydantic lives — it is that Pydantic was adopted
**asymmetrically**: only on the request-parsing side, not on the response, error, or
dependency-injection sides. The instances below document this.

### R3-1 [CONCERN] Response side hand-rolls 8 converters; FastAPI `response_model=` is unused

`src/swallow/surface_tools/web/http_models.py` contains 8 functions that flatten command result
objects into dicts: `task_response`, `task_run_response`, `task_acknowledge_response`,
`task_recovery_response`, `stage_decision_response`, `stage_promote_response`,
`proposal_review_response`, `proposal_apply_response`. `grep` over `api.py` shows zero
`response_model=` arguments on `@app.post(...)`.

Cost of the current approach:

- `task_response` (line 45-56) emits 9 of `TaskState`'s many fields. If `TaskState` ever gains a
  field that the UI needs, **silent omission** — there is no compile-time or runtime signal.
- 8 converters duplicate the response-shape contract; each route's response is implicitly defined
  by which converter it calls. R2-3 (response shape underspec) is a *symptom* of this — the
  shape is hidden in helper functions instead of being a typed contract.
- OpenAPI schema for response bodies is empty (FastAPI generates it from `response_model=` Pydantic
  classes; without them, `/openapi.json` only describes request shapes).
- Future client / SDK generation is impossible until response Pydantic models exist.

What the framework gives for free:

```python
class TaskResponse(BaseModel):
    task_id: str
    status: str
    phase: str
    title: str
    # ...

@app.post("/api/tasks", response_model=TaskRunResponse, status_code=201)
def create_task(...): ...
```

→ automatic JSON serialization, OpenAPI contract, response validation, no `task_response()` helper.

### R3-2 [CONCERN] 11+ replicated `try/except` blocks per route; `@app.exception_handler` is unused

`api.py:123-220` shows the same 4-line `except` ladder pasted into every write route:

```python
except FileNotFoundError as exc:
    raise HTTPException(status_code=404, detail=str(exc)) from exc
except WebRequestError as exc:
    raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
except ValueError as exc:
    raise HTTPException(status_code=_status_for_value_error(exc), detail=str(exc)) from exc
```

`grep` confirms zero `@app.exception_handler` decorators in the file. Each new route copies the
ladder; each new domain exception requires editing N routes.

What the framework gives for free:

```python
@app.exception_handler(FileNotFoundError)
def _fnf(request, exc): return JSONResponse(status_code=404, content={"detail": str(exc)})

@app.exception_handler(StagePromotePreflightError)
def _preflight(request, exc):
    return JSONResponse(status_code=409, content={"detail": str(exc), "notices": exc.notices})
```

Defined once. All routes inherit. Adding a new route adds zero exception code; adding a new
exception type adds one handler block, not N edits.

R2-6 (acknowledge result asymmetry) becomes a non-issue under this pattern: if commands raise typed
exceptions on blocked states instead of returning result objects with optional blocked fields, the
exception handler centralizes the 409 mapping and the `TaskAcknowledgeCommandResult` /
`TaskRecoveryCommandResult` field difference disappears.

### R3-3 [CONCERN] `WebRequestError` reinvents `HTTPException`

`http_models.py:18-24` defines `WebRequestError(ValueError)` with `message` and `status_code`
fields and a `__str__` returning `message`. This is structurally identical to FastAPI's built-in
`HTTPException(status_code=..., detail=...)`.

The reason `WebRequestError` exists is the self-imposed rule that `http_models.py` (a sibling of
`api.py`) should not import FastAPI at module load time. But:

- `schemas.py` already imports Pydantic at module load (line 5) — the lazy-import rule was already
  partially abandoned for request models;
- `api.py` is the only consumer of `WebRequestError`; it could just raise `HTTPException` directly
  from inside the `create_fastapi_app` closure, since FastAPI is already imported there;
- the 2-step pattern (`raise WebRequestError` in helper → catch in route → re-raise as
  `HTTPException`) accomplishes nothing the framework primitive doesn't.

Resolution: delete `WebRequestError`, raise `HTTPException` directly from inside `create_fastapi_app`.

### R3-4 [CONCERN] Error classification by exception-message string-matching (`_status_for_value_error`)

`api.py:49-53`:

```python
def _status_for_value_error(exc: ValueError) -> int:
    message = str(exc)
    if message.startswith("Unknown staged candidate:"):
        return 404
    return 400
```

This parses the *human-readable text* of an exception to decide HTTP status. Failure modes:

- A future maintainer rewords the upstream error message → 404 silently becomes 400.
- Localization or i18n of error messages → entire mapping breaks.
- Multiple call sites that throw "Unknown ... candidate" with different prefixes → silent 400s.

Standard practice: raise typed exceptions (`UnknownStagedCandidateError(ValueError)` defined in
`application/commands/knowledge.py`) and route them via `@app.exception_handler`. The
classification then lives in the type, not in the message. This also benefits `application/commands`
in general — typed errors propagate cleanly to CLI output too.

### R3-5 [NIT] `globals().update({...})` to expose lazy-imported Pydantic models to tests

`api.py:74-82`:

```python
globals().update(
    {
        "CreateTaskRequest": CreateTaskRequest,
        "TaskActionRequest": TaskActionRequest,
        ...
    }
)
```

This pattern is a workaround for the lazy-import rule applied to `schemas.py`: the test files want
to refer to `swallow.surface_tools.web.api.CreateTaskRequest`, but `CreateTaskRequest` is only
imported inside the `create_fastapi_app` factory. The `globals().update` makes the names visible
on the module after `create_fastapi_app` has been called once.

This is a code smell:

- Tests now have an order dependency — `create_fastapi_app` must be invoked before the names
  exist. Forgetting this gives `AttributeError` at import time.
- IDEs / static analyzers cannot resolve these names.
- The pattern signals that the lazy-import rule is being fought rather than served.

Resolution options:

- (a) Move Pydantic schema imports to `api.py` top level (Pydantic is in `dev` extras alongside
  FastAPI; if FastAPI loaded, Pydantic loaded). The "must remain importable without FastAPI" rule
  applies to FastAPI-using symbols, not necessarily to Pydantic-only symbols.
- (b) If the rule is kept strict, tests should import `from swallow.surface_tools.web.schemas
  import CreateTaskRequest` directly, removing the need for the `globals().update` bridge.

Either way, `globals().update` should not survive review.

### R3-6 [CONCERN] `base_dir` and `OperatorToken` flow through closure capture; FastAPI `Depends` is unused

`api.py:56` `create_fastapi_app(base_dir: Path)` captures `base_dir` in closure for every route.
There is no `Depends(get_base_dir)` injection point. Round 1 concern 5 (OperatorToken `source`
field) and the proposal artifact-ID resolution (Round 1 concern 2) both naturally fit `Depends`:

```python
def get_base_dir() -> Path: return _APP_BASE_DIR
def get_operator_token() -> OperatorToken: return OperatorToken(source="web", actor="local")
def resolve_proposal_path(req: ProposalApplyRequest, base_dir: Path = Depends(get_base_dir)) -> Path:
    ...

@app.post("/api/proposals/apply")
def apply(path: Path = Depends(resolve_proposal_path), ...): ...
```

The closure-capture approach works for one variable. As soon as future phases add per-request
context (request ID, audit actor, tenant, auth token, current user), the closure pattern breaks
and a partial migration to `Depends` becomes mandatory. Doing it from day one is cheaper than the
later partial migration.

### Round 3 Summary for Codex

The Pydantic-vs-stdlib reversal is correct in spirit but incomplete in execution. To finish the
job:

1. **Add Pydantic response models** in `schemas.py` (or a sibling `response_schemas.py`) and use
   `response_model=` on every `@app.post(...)` and write-relevant `@app.get(...)`. Delete the 8
   hand-rolled converters in `http_models.py`. (R3-1)
2. **Centralize error mapping** with `@app.exception_handler` for `FileNotFoundError`,
   `StagePromotePreflightError`, `UnknownStagedCandidateError`, etc. Delete the per-route
   `try/except` ladders. (R3-2)
3. **Delete `WebRequestError`**; raise `HTTPException` directly from inside `create_fastapi_app`.
   (R3-3)
4. **Replace `_status_for_value_error` string-matching** with typed exceptions defined in
   `application/commands/knowledge.py` (and elsewhere as needed). (R3-4)
5. **Remove `globals().update({...})`** by either moving schema imports to top level (preferred,
   given Pydantic rides with FastAPI) or by having tests import from `schemas.py` directly. (R3-5)
6. **Migrate to `Depends`** for `base_dir`, `OperatorToken`, and any per-request context that
   future phases will add. (R3-6)

### Proposed New Plan §Design Decision Row: Framework-Default Principle

Plan should add this as an explicit row in §Design Decisions:

> **Framework-Default Principle** — for any capability provided by FastAPI / Pydantic / uvicorn
> (request schema, response schema, dependency injection via `Depends`, exception handling via
> `@app.exception_handler`, background tasks, OpenAPI auto-generation, `TestClient`), use the
> framework primitive by default. A documented reason is required to write a hand-rolled
> equivalent. "We don't want to depend on FastAPI features" is not a sufficient reason once
> FastAPI is already a dev dependency — the cost saving is illusory and the per-route boilerplate
> compounds across phases.

This rule, had it been in place at plan-drafting time, would have prevented all six R3 findings.
Adding it now prevents the same shape of issue from re-emerging in future write-surface phases
(file upload, route policy admin, MCP integration, etc.).
