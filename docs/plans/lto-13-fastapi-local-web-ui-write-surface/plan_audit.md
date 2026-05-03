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

TL;DR: has-concerns — 4 slices audited, 6 issues found (0 blockers, 5 concerns, 1 nit, 4 confirmed-OK anchors)

## Audit Verdict

Overall: has-concerns

No blockers were found. The plan is structurally sound and INVARIANTS-aligned. Five concerns must be
addressed or explicitly logged before implementation begins — two of them (the proposal command
path-parameter impedance mismatch and the FastAPI/httpx test-environment gap) will force an
implementation decision in M2 and M1 respectively if left unresolved.

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
