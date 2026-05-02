---
author: codex
phase: governance-apply-handler-split
slice: lto10-plan
status: review
depends_on:
  - docs/roadmap.md
  - docs/active_context.md
  - current_state.md
  - docs/design/INVARIANTS.md
  - docs/design/DATA_MODEL.md
  - docs/design/SELF_EVOLUTION.md
  - docs/design/INTERACTION.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/GOF_PATTERN_ALIGNMENT.md
  - docs/engineering/TEST_ARCHITECTURE.md
  - docs/plans/governance-apply-handler-split/plan_audit.md
  - docs/plans/surface-cli-meta-optimizer-split/closeout.md
  - docs/plans/surface-cli-meta-optimizer-split/review_comments.md
---

TL;DR:
LTO-10 is a behavior-preserving split of the private governance apply path behind `apply_proposal`.
The public mutation boundary stays exactly the same; new modules may only serve that facade and must not expose a second canonical / route / policy write entry.
The highest-risk slice is route metadata review apply because it combines transaction semantics, route audit logs, in-memory refresh, and post-commit artifact output.
Plan audit concerns are absorbed in this revision: M1 gets a dedicated `tests/unit/truth_governance/` home, M3 uses direct owning-submodule helper imports with named rollback gates, guard allowlist moves stay same-commit with the code moves, and any `governance_models.py` file remains record-only.

# Governance Apply Handler Split Plan

## Frame

- track: `Architecture / Engineering`
- phase: `Governance Apply Handler Split / LTO-10`
- roadmap ticket: `Governance apply handler split`
- long-term goal: `LTO-10 Governance Apply Handler Maintainability`
- recommended implementation branch: `feat/governance-apply-handler-split`
- planning branch: `main`
- implementation mode: facade-first / behavior-preserving
- context brief: not produced this round; `docs/active_context.md` marks it optional, and this plan is based on `docs/roadmap.md`, design anchors, LTO-9 closeout, and direct code survey.
- plan audit status: `has-concerns`, 0 blockers / 5 concerns; concerns absorbed in this revision.

Public compatibility targets:

- `swallow.truth_governance.governance.apply_proposal`
- `swallow.truth_governance.governance.OperatorToken`
- `swallow.truth_governance.governance.ProposalTarget`
- `swallow.truth_governance.governance.ApplyResult`
- `swallow.truth_governance.governance.DuplicateProposalError`
- `swallow.truth_governance.governance.register_canonical_proposal`
- `swallow.truth_governance.governance.register_route_metadata_proposal`
- `swallow.truth_governance.governance.register_policy_proposal`
- `swallow.truth_governance.governance.register_mps_policy_proposal`
- `swallow.truth_governance.governance.load_mps_policy`

## Current Code Context

Current governance apply code is functionally stable but concentrated in `src/swallow/truth_governance/governance.py`:

| Area | Current shape |
|---|---|
| Public API and records | `OperatorToken`, `ProposalTarget`, `ApplyResult`, and registration functions all live in `governance.py`. |
| Proposal registry | private proposal payload records and `_PENDING_PROPOSALS` live beside public API dispatch. |
| Apply dispatch | `apply_proposal(...)` loads payloads, validates target types, dispatches to private handlers, then calls `_emit_event(...)`. |
| Canonical handler | `_apply_canonical(...)` calls `KnowledgeRepo()._promote_canonical(...)`. |
| Route metadata handler | `_apply_route_metadata(...)` calls `RouteRepo()._apply_metadata_change(...)` for direct payloads and delegates review-record apply to `_apply_route_review_metadata(...)`. |
| Route review handler | `_apply_route_review_metadata(...)` is the largest branch; it validates reviewed Meta-Optimizer entries, updates route weights / capability profiles, writes route change logs via `RouteRepo`, and writes an application artifact after SQLite truth commit. |
| Policy handler | `_apply_policy(...)` handles both audit trigger policy and MPS policy payloads through `PolicyRepo()._apply_policy_change(...)`. |
| Post-commit hook | `_emit_event(...)` is a no-op placeholder; tests currently prove caller/post-commit failure does not roll back already committed route truth. |

Existing guard/test anchors:

- `tests/test_governance.py` covers public apply behavior and basic result contracts.
- `tests/test_phase65_sqlite_truth.py` covers route / policy transaction rollback, audit log writes, in-memory route refresh rollback, and post-commit artifact failure behavior.
- `tests/test_invariant_guards.py` enforces direct writer boundaries and currently allowlists `src/swallow/truth_governance/governance.py` as the only production caller of repository private writers.
- `docs/engineering/CODE_ORGANIZATION.md §5` already names the target direction: `proposal_registry.py`, `apply_canonical.py`, `apply_route_metadata.py`, `apply_policy.py`.

## Goals

1. Keep `apply_proposal(...)` as the only public canonical / route metadata / policy mutation entry.
2. Split private apply handlers into focused modules behind the existing governance facade.
3. Move proposal payload registration / lookup / validation into a focused proposal registry module without changing public imports.
4. Make the dispatch envelope explicit: load proposal, validate target, call exactly one private handler, then run post-commit hook / outbox logic.
5. Keep repository private writer calls narrowly allowlisted to handler modules owned by the `apply_proposal` path.
6. Preserve route metadata transaction behavior, audit log behavior, in-memory route refresh behavior, and route review artifact behavior.
7. Add or tighten persistent tests so future refactors cannot reintroduce direct writer calls, terminal surface coupling, or alternate mutation entries.
8. Leave a clear closeout record for any governance follow-up that is discovered but not safe to include.

## Non-Goals

- Do not change public governance API signatures or import paths.
- Do not add a new public mutation function, command, HTTP route, or alternate proposal apply API.
- Do not introduce new proposal target kinds.
- Do not change canonical / route / policy semantics, validation rules, or output record formats.
- Do not change SQLite schema, migrations, append-only table definitions, or `event_log` semantics.
- Do not implement authn / authz, multi-actor identity, remote sync, durable outbox tables, or cloud truth.
- Do not move route metadata physical writers out of `provider_router/route_metadata_store.py`.
- Do not change Provider Router route selection, route defaults, fallback behavior, or Path A/B/C semantics.
- Do not expand CLI, FastAPI, Control Center, Wiki Compiler, Planner/DAG, or harness decomposition scope.
- Do not edit `docs/design/*.md` semantics during this implementation phase.

## Design And Engineering Anchors

- `docs/design/INVARIANTS.md`
  - Control remains only with Orchestrator / Operator.
  - Execution never directly writes Truth.
  - `apply_proposal` is the only canonical / route / policy mutation entry.
  - Guard tests in §9 must not be deleted or weakened.
- `docs/design/DATA_MODEL.md`
  - Repository private writers remain private and may only be reached from the governance apply boundary.
  - Route / policy change logs remain append-only audit records.
- `docs/design/SELF_EVOLUTION.md`
  - Librarian / Meta-Optimizer produce staged candidates or proposals; Operator or controlled side-effect paths apply through `apply_proposal`.
  - `OperatorToken` remains a source marker, not authn.
- `docs/design/INTERACTION.md`
  - Operator surfaces may call governance functions, but must not fork truth-write logic.
- `docs/engineering/CODE_ORGANIZATION.md`
  - Governance target shape is `proposal_registry.py`, `apply_canonical.py`, `apply_route_metadata.py`, `apply_policy.py`.
  - Facade-first migration and public import preservation are required.
- `docs/engineering/GOF_PATTERN_ALIGNMENT.md`
  - Use Facade / Command Handler / Repository as responsibility language only where it removes real coupling.
  - No pattern may bypass `apply_proposal`.
- `docs/engineering/TEST_ARCHITECTURE.md`
  - Use focused unit tests for handler logic, `integration/sqlite`-style coverage for transaction behavior, and guard tests for invariant boundaries.

## Target Module Shape

The exact support-file names may be adjusted during implementation if review finds a cleaner cycle break, but the ownership boundaries below are the target.

| Module | Intended ownership |
|---|---|
| `truth_governance/governance.py` | stable public facade: public records/functions, `apply_proposal(...)`, and compatibility re-exports only. |
| `truth_governance/governance_models.py` | optional shared public/private records if needed to avoid import cycles; public names remain re-exported from `governance.py`. |
| `truth_governance/proposal_registry.py` | proposal payload records, normalization, registration, lookup, and target validation around the existing `PendingProposalRepo`. |
| `truth_governance/apply_canonical.py` | canonical proposal handler; only this handler may call `KnowledgeRepo()._promote_canonical(...)`. |
| `truth_governance/apply_route_metadata.py` | direct route metadata and reviewed Meta-Optimizer route proposal handler; only this handler may call `RouteRepo()._apply_metadata_change(...)`. |
| `truth_governance/apply_policy.py` | audit trigger policy and MPS policy handler; only this handler may call `PolicyRepo()._apply_policy_change(...)`. |
| `truth_governance/apply_outbox.py` | optional post-commit hook / outbox helper for `_emit_event(...)` semantics; no durable schema or event-log write is added in this phase. |
| `truth_governance/truth/*.py` | repository layer remains the only owner of physical truth writes and audit log writes. |

## Boundary Rules

- `apply_proposal(...)` remains the only public function that applies canonical / route / policy mutations.
- New handler modules are private implementation details of that facade; ordinary callers should continue importing from `swallow.truth_governance.governance`.
- Registration functions may move physically, but public imports from `governance.py` must remain compatible.
- Handler modules may call repository private writers only because they are owned by the `apply_proposal` path. Guard tests must make this ownership explicit.
- When a private writer ownership move lands, update `tests/test_invariant_guards.py` in the same commit as the code move. Do not leave a mid-milestone guard failure or a temporary broad allowlist in the tree.
- No handler module may call raw SQL against task state or bypass repository methods.
- `apply_route_metadata.py` may write the Meta-Optimizer application artifact only after SQLite truth has committed, preserving current failure semantics.
- Post-commit hook / outbox failures must not roll back committed repository truth; existing route coverage must be preserved and policy/canonical coverage should be added if feasible.
- Any `source="system_auto"` handling remains governed by existing design rules; this phase does not introduce new automatic apply paths.
- If an implementation choice would require changing schema or public surface semantics, stop and revise the plan rather than hiding the behavior change inside the refactor.

## Milestones

| Milestone | Scope | Risk | Default gate |
|---|---|---|---|
| M1 | Baseline characterization + proposal registry extraction | high | governance tests + source boundary tests + import compatibility checks |
| M2 | Canonical and policy handler extraction | high | focused governance tests + policy transaction tests + invariant guards |
| M3 | Route metadata handler extraction, including reviewed proposal apply | high | route transaction tests + meta-optimizer proposal apply tests + invariant guards |
| M4 | Apply envelope / post-commit outbox helper tightening | medium-high | post-commit failure tests + audit log tests + focused source guards |
| M5 | Facade cleanup, compatibility audit, closeout / PR gate | medium | full pytest + compileall + diff hygiene |

## M1 Acceptance: Baseline And Proposal Registry

Scope:

- Create `tests/unit/truth_governance/` as the first unit-test home for this phase, and place the new governance boundary tests there before any production code moves.
- Preserve the public import surface from `swallow.truth_governance.governance`.
- Move private proposal payload records and `_PENDING_PROPOSALS` ownership into `truth_governance/proposal_registry.py`.
- Move or wrap registration / lookup / validation code so `governance.py` no longer owns proposal registry internals.
- Keep `truth_governance/truth/proposals.py` as the lower-level pending proposal store unless a narrower change proves necessary.
- If `ProposalTarget`, `OperatorToken`, or `ApplyResult` need a cycle-breaking home, move them to `governance_models.py` and re-export from `governance.py`.
- If `governance_models.py` is introduced, keep it record-only and re-export-only; `tests/unit/truth_governance/test_governance_boundary.py` must assert that it contains no handler logic, no repository calls, and no direct imports from handler modules.

Acceptance:

- Existing imports in tests and production still work from `swallow.truth_governance.governance`.
- Duplicate proposal ID behavior and unknown proposal behavior remain unchanged.
- `tests/test_governance.py -q` passes.
- `tests/unit/truth_governance/test_governance_boundary.py -q` passes and proves the governance facade stays public, registry extraction is isolated, and any `governance_models.py` file is record-only.
- `git diff --check` passes.

## M2 Acceptance: Canonical And Policy Handlers

Scope:

- Extract canonical apply behavior into `truth_governance/apply_canonical.py`.
- Extract audit trigger policy and MPS policy apply behavior into `truth_governance/apply_policy.py`.
- Keep result detail strings, `applied_writes`, and payload contracts unchanged.
- Update guard tests so repository private writer calls are allowlisted only in the extracted handler modules, not broadly across governance.
- Add positive guard assertions that `governance.py` dispatches to handlers and contains no direct `_promote_canonical`, `_apply_metadata_change`, or `_apply_policy_change` calls.
- Keep the canonical / policy writer allowlist update in the same commit as the corresponding handler move; do not leave `tests/test_invariant_guards.py` failing between commits.

Acceptance:

- Canonical apply tests in `tests/test_governance.py` pass unchanged or with behavior-preserving import updates only.
- Policy and MPS policy tests in `tests/test_governance.py` and `tests/test_phase65_sqlite_truth.py` pass.
- `tests/test_invariant_guards.py -q` passes with a narrower, explicit allowlist for handler modules.
- No new public mutation function is introduced.
- `git diff --check` passes.

## M3 Acceptance: Route Metadata Handler

Scope:

- Extract direct route metadata apply behavior into `truth_governance/apply_route_metadata.py`.
- Extract reviewed Meta-Optimizer route proposal apply behavior from `_apply_route_review_metadata(...)` into the same handler module or a private support module owned by it.
- Import the reviewed-route support types directly from their owning LTO-9 submodules (`surface_tools.meta_optimizer_models`, `surface_tools.meta_optimizer_proposals`, `surface_tools.meta_optimizer_lifecycle`) rather than routing them through the `surface_tools.meta_optimizer` compatibility facade.
- Preserve current validation order for route weights, route capability profiles, unknown routes, missing task families, and unsupported proposal types.
- Preserve current rollback behavior for SQLite truth, route audit logs, and in-memory route registry / policy / weights / capability profile refresh.
- Preserve current post-commit application artifact behavior: SQLite truth may commit even if the artifact write fails, and the failure is logged.
- Keep the route metadata writer allowlist update in the same commit as the `_apply_metadata_change` move; do not leave `tests/test_invariant_guards.py` failing between commits.

Acceptance:

- Route metadata tests in `tests/test_governance.py` pass.
- Before the first M3 commit is pushed, these tests must pass individually:
  - `test_route_metadata_transaction_rolls_back_sqlite_audit_and_in_memory`
  - `test_route_metadata_transaction_rolls_back_when_audit_insert_fails_after_insert`
  - `test_route_metadata_commit_survives_caller_exception_after_commit`
  - `test_route_review_artifact_write_failure_logs_warning_after_sqlite_commit`
- Transaction and audit tests in `tests/test_phase65_sqlite_truth.py -q` pass at milestone close.
- Focused Meta-Optimizer review/apply tests pass, including proposal application record behavior.
- `tests/test_invariant_guards.py -q` passes with handler-module ownership explicit.
- No Provider Router selection or fallback behavior changes.
- No direct helper import from `swallow.surface_tools.meta_optimizer` remains in `apply_route_metadata.py` for the helper set above; the direct owning-submodule imports are the chosen path for this phase.
- `git diff --check` passes.

## M4 Acceptance: Apply Envelope And Outbox Helper

Scope:

- Make `apply_proposal(...)` read as a small envelope:
  - validate public inputs;
  - load proposal;
  - validate target / payload;
  - dispatch to one private handler;
  - run post-commit hook / outbox helper;
  - return the handler result.
- Extract `_emit_event(...)` semantics into `truth_governance/apply_outbox.py` or an equivalent focused helper if it reduces coupling.
- Keep post-commit hook behavior compatible: this phase does not add durable outbox persistence, event schema, or silent background processing.
- Add or preserve tests showing post-commit failure cannot roll back committed repository truth.
- If a shared transaction helper would require repository rewrites or schema changes, do not introduce it; record the narrowed M4 outcome in closeout.

Acceptance:

- `apply_proposal(...)` remains the single public mutation entry and is small enough to audit at a glance.
- Existing route post-commit failure coverage still passes.
- Policy/canonical post-commit failure coverage is added if feasible without artificial test coupling; if not, closeout records why route coverage remains the practical representative.
- Route and policy audit log tests still pass.
- No durable outbox or event-log schema is introduced.
- `tests/test_governance.py -q`, `tests/test_phase65_sqlite_truth.py -q`, and `tests/test_invariant_guards.py -q` pass.

## M5 Acceptance: Facade Cleanup And Closeout

Scope:

- Remove dead private functions from `governance.py` only after import compatibility is proven.
- Keep `governance.py` as the stable facade for public callers.
- Keep new private handler modules out of broad `__all__` exports unless tests require a narrow source import for guard inspection.
- Keep any `governance_models.py` file record-only and re-export-only if it survives past M1/M2; do not let it become a general shared-models module.
- Update `docs/plans/governance-apply-handler-split/closeout.md`, `docs/active_context.md`, `current_state.md`, and `pr.md` after implementation and validation.
- Record any deferred governance cleanup explicitly.

Acceptance:

- Public imports listed in this plan still work.
- `governance.py` no longer owns bulky apply handler logic.
- Guard tests remain at least as strict as before the phase.
- Full validation passes:
  - `.venv/bin/python -m pytest -q`
  - `.venv/bin/python -m compileall -q src/swallow`
  - `git diff --check`
- Closeout and PR draft are ready for Claude review and Human PR decision.

## Risks And Controls

| Risk | Control |
|---|---|
| New handler modules accidentally look like new public mutation APIs. | Keep public imports through `governance.py`; avoid broad exports; source guard asserts no alternate public apply function is introduced. |
| Guard allowlist update weakens the `apply_proposal` invariant. | Update allowlists narrowly to exact handler modules and add positive assertions about `governance.py` dispatch / no private writer calls. |
| Route review apply extraction changes transaction or post-commit artifact behavior. | Run `tests/test_phase65_sqlite_truth.py` and focused Meta-Optimizer review/apply tests at M3. |
| Import cycles appear after moving records and handlers. | Use `governance_models.py` only as a cycle breaker; public names remain re-exported from `governance.py`. |
| Over-abstracting transaction / outbox helpers creates fake architecture. | M4 may stay narrow if shared helper extraction does not remove real duplication; no schema or durable outbox table in this phase. |
| Canonical apply lacks rollback coverage comparable to route / policy. | Do not invent behavior changes; add representative post-commit coverage only if it does not require artificial coupling. |
| Existing Orchestrator / CLI paths break due to public import movement. | M1 and M5 must run import compatibility checks plus existing orchestration / CLI focused tests if touched. |

## Validation Plan

Focused gates by milestone:

```bash
.venv/bin/python -m pytest tests/test_governance.py -q
.venv/bin/python -m pytest tests/test_phase65_sqlite_truth.py -q
.venv/bin/python -m pytest tests/test_invariant_guards.py -q
```

Additional focused checks if touched:

```bash
.venv/bin/python -m pytest tests/test_meta_optimizer.py -k "review or apply" -q
.venv/bin/python -m pytest tests/unit/application/test_command_boundaries.py -q
.venv/bin/python -m pytest tests/test_cli.py -k "proposal or route_capabilities or route_weights or mps" -q
```

Final PR gate:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src/swallow
git diff --check
```

Eval tests are not required for this phase because the work is deterministic governance refactor, not quality-gradient extraction, ranking, or operator-facing proposal quality.

## Branch And PR Recommendation

- Plan and audit may stay on `main` until Human Plan Gate.
- After `plan.md` and `plan_audit.md` pass Human Plan Gate, create:

```bash
git switch -c feat/governance-apply-handler-split
```

- Suggested commit grouping:
  - `docs(plan): add governance apply handler split plan`
  - `refactor(governance): extract proposal registry`
  - `refactor(governance): extract canonical and policy handlers`
  - `refactor(governance): extract route metadata apply handler`
  - `refactor(governance): clarify apply envelope`
  - `docs(state): close governance apply handler split`
- M1-M4 should each reach a reviewable milestone with focused validation before proceeding.
- M3 route metadata extraction is high risk and should not be mixed with M4 cleanup if it already produces a large diff.

## Completion Conditions

- `docs/plans/governance-apply-handler-split/plan_audit.md` exists and has no unresolved `[BLOCKER]`.
- Human Plan Gate has approved the phase scope.
- Implementation branch matches `docs/active_context.md`.
- `apply_proposal(...)` remains the only public mutation entry for canonical / route / policy.
- Public imports from `swallow.truth_governance.governance` remain compatible.
- Private repository writer calls are confined to extracted handler modules owned by the `apply_proposal` path.
- Route / policy transaction and audit behavior remain unchanged.
- Full default pytest, compileall, and diff hygiene pass.
- Closeout, PR draft, and state docs are synchronized before PR review.
