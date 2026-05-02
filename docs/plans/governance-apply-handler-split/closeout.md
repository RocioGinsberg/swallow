---
author: codex
phase: governance-apply-handler-split
slice: closeout
status: final
depends_on:
  - docs/plans/governance-apply-handler-split/plan.md
  - docs/plans/governance-apply-handler-split/plan_audit.md
  - docs/plans/governance-apply-handler-split/review_comments.md
  - docs/design/INVARIANTS.md
  - docs/design/DATA_MODEL.md
  - docs/design/SELF_EVOLUTION.md
  - docs/design/INTERACTION.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/TEST_ARCHITECTURE.md
---

TL;DR:
LTO-10 is complete on `feat/governance-apply-handler-split`: `governance.py` is now a 45-line public facade around `apply_proposal`, with proposal registry, canonical, route metadata, policy, and outbox behavior split into focused private modules.
The public governance import surface and the unique `apply_proposal` mutation boundary are preserved; no schema, CLI, FastAPI, provider-router selection, or durable outbox behavior changed.
Full default pytest, compileall, and diff hygiene passed; Claude implementation review recommends merge with 0 blockers and 2 non-blocking commit-hygiene / placeholder-scope concerns.

# Governance Apply Handler Split Closeout

## Scope

- track: `Architecture / Engineering`
- phase: `Governance Apply Handler Split / LTO-10`
- branch: `feat/governance-apply-handler-split`
- mode: behavior-preserving governance apply decomposition
- public compatibility targets:
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

## Completed Milestones

| Milestone | Result |
|---|---|
| M1 Baseline + proposal registry | Added `tests/unit/truth_governance/test_governance_boundary.py`, moved public record types to `governance_models.py`, and moved pending proposal payload ownership / validation / registration into `proposal_registry.py`. |
| M2 Canonical + policy handlers | Added `apply_canonical.py` and `apply_policy.py`; moved `_promote_canonical` and `_apply_policy_change` callers behind focused handler modules; split private writer guard ownership accordingly. |
| M3 Route metadata handler | Added `apply_route_metadata.py`; moved direct route metadata and reviewed Meta-Optimizer route proposal apply logic; changed reviewed-route helper imports to owning LTO-9 submodules instead of the `surface_tools.meta_optimizer` compatibility facade. |
| M4 Apply envelope / outbox helper | Added `apply_outbox.py` for the current `_emit_event(...)` no-op hook; no durable outbox, event schema, or background worker was introduced. |
| M5 Facade cleanup / closeout | Confirmed `governance.py` has no bulky private handler definitions and remains the stable public facade. Prepared closeout and PR draft, then ran the full final validation gate. |

## Implementation Notes

- `src/swallow/truth_governance/governance.py` is now the public facade and `apply_proposal(...)` envelope. It validates inputs, loads the proposal, validates target / payload shape, dispatches to one private handler, runs the outbox hook, and returns the handler result.
- `src/swallow/truth_governance/governance_models.py` contains public cycle-breaking records only: `ProposalTarget`, `OperatorToken`, and `ApplyResult`.
- `src/swallow/truth_governance/proposal_registry.py` owns proposal payload records, pending proposal storage, proposal registration, lookup, target validation, and typed accessors.
- `src/swallow/truth_governance/apply_canonical.py` is the canonical proposal handler and the only production governance caller of `KnowledgeRepo()._promote_canonical(...)`.
- `src/swallow/truth_governance/apply_policy.py` is the audit-trigger and MPS policy handler and the only production governance caller of `PolicyRepo()._apply_policy_change(...)`.
- `src/swallow/truth_governance/apply_route_metadata.py` is the route metadata handler and the only production governance caller of `RouteRepo()._apply_metadata_change(...)`.
- `src/swallow/truth_governance/apply_outbox.py` owns the current post-handler hook placeholder. It remains intentionally non-durable in this phase.
- Guard tests now name the exact handler modules that may call repository private writers; `governance.py` itself no longer calls repository private writers.

## Boundary Confirmation

- No `docs/design/*.md` semantic changes.
- No SQLite schema, migration, append-only table, or event-log change.
- No durable outbox table or event schema was added.
- No new public mutation function, CLI command, HTTP route, or proposal target kind.
- No Provider Router selection, fallback, route default, route weight, route capability, or route policy semantics changed.
- No raw SQL was added to handler modules.
- `apply_proposal(...)` remains the only public canonical / route / policy mutation entry.
- Public imports from `swallow.truth_governance.governance` remain available and are covered by `tests/unit/truth_governance/test_governance_boundary.py`.
- `governance_models.py` remains record-only and is guarded against handler logic, repository calls, registry calls, and handler imports.

## M4 Narrowing Note

M4 stayed intentionally narrow. The current post-commit hook is a no-op placeholder, so extracting a larger transaction or durable outbox abstraction would have created architecture without behavior. Existing route post-commit coverage remains the practical representative because route apply exercises committed SQLite truth, audit log writes, in-memory route refresh, and post-handler failure behavior. Additional canonical / policy post-commit tests were not added because they would only patch the same target-independent no-op hook without increasing behavioral coverage.

## Deferred Work

- Durable governance outbox persistence remains deferred until there is an explicit event schema and consumer.
- Canonical apply rollback semantics remain file-oriented and are not changed in this phase.
- `apply_route_metadata.py` is still the largest handler because reviewed Meta-Optimizer proposal apply is stateful; a future phase may split private route-review support if it adds real readability without weakening transaction coverage.

## Review Absorption

Claude implementation / PR review is recorded in `docs/plans/governance-apply-handler-split/review_comments.md`.

- Verdict: `recommend-merge`.
- Blockers: none.
- Withdrawn blocker: deletion of `.claude/skills/model-review/SKILL.md` was initially flagged as out of scope, then withdrawn after Human confirmed the skill is obsolete and unused. No restore is required.
- CONCERN-1: commit `9018e25` is titled `refactor(governance): extract route metadata handler` but contains M4 outbox extraction. This is commit-message hygiene only; code and validation are correct. It should be handled by rewriting the commit message before merge or noting the mismatch in the PR / merge commit body.
- CONCERN-2: `apply_outbox.py` is currently a minimal no-op placeholder. This remains acceptable for LTO-10 because M4 intentionally stayed narrow and did not introduce a durable outbox schema. No code change is needed in this PR.

Review independently re-ran the focused gate and full default pytest:

```bash
.venv/bin/python -m pytest tests/test_invariant_guards.py tests/unit/truth_governance/ tests/test_governance.py tests/test_phase65_sqlite_truth.py -q
# 62 passed

.venv/bin/python -m pytest -q
# 702 passed, 8 deselected, 10 subtests passed

.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# clean
```

## Validation

Focused gates during milestones:

```bash
.venv/bin/python -m pytest tests/unit/truth_governance/test_governance_boundary.py -q
# 5 passed

.venv/bin/python -m pytest tests/test_governance.py -q
# 10 passed

.venv/bin/python -m pytest tests/test_phase65_sqlite_truth.py -q
# 21 passed

.venv/bin/python -m pytest tests/test_invariant_guards.py -q
# 26 passed
```

Named M3 route rollback / post-commit gates:

```bash
.venv/bin/python -m pytest tests/test_phase65_sqlite_truth.py::test_route_metadata_transaction_rolls_back_sqlite_audit_and_in_memory tests/test_phase65_sqlite_truth.py::test_route_metadata_transaction_rolls_back_when_audit_insert_fails_after_insert tests/test_phase65_sqlite_truth.py::test_route_metadata_commit_survives_caller_exception_after_commit tests/test_phase65_sqlite_truth.py::test_route_review_artifact_write_failure_logs_warning_after_sqlite_commit -q
# 4 passed
```

Final PR gate:

```bash
.venv/bin/python -m pytest -q
# 702 passed, 8 deselected, 10 subtests passed

.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# passed
```

## Completion Status

- Plan audit concerns C-1 through C-5 were absorbed.
- Claude review completed with `recommend-merge`, 0 blockers, 2 non-blocking concerns, and 1 withdrawn blocker.
- M1 through M5 are complete.
- `governance.py` no longer owns bulky apply handler logic.
- Guard allowlists moved in the same implementation commits as the corresponding writer ownership moves.
- Closeout and `pr.md` are prepared.
- Next workflow step: Human closeout / review state commit, PR create/update from `pr.md`, then merge decision.
