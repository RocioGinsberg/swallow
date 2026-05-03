---
author: codex
phase: surface-cli-meta-optimizer-split-step2
slice: closeout
status: final
depends_on:
  - docs/plans/surface-cli-meta-optimizer-split-step2/context_brief.md
  - docs/plans/surface-cli-meta-optimizer-split-step2/plan.md
  - docs/plans/surface-cli-meta-optimizer-split-step2/plan_audit.md
  - docs/plans/surface-cli-meta-optimizer-split-step2/review_comments.md
  - docs/design/INVARIANTS.md
  - docs/design/INTERACTION.md
  - docs/design/SELF_EVOLUTION.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/TEST_ARCHITECTURE.md
---

TL;DR:
LTO-9 Step 2 is complete on `refactor/cli_command_family_migration`: broad route/audit/synthesis/knowledge/task CLI command families moved out of `surface_tools/cli.py` into focused adapters, with write actions routed through application command modules.
The phase is behavior-preserving: no FastAPI write routes, schema changes, new proposal target kinds, or new mutation entries were added; `apply_proposal` remains the only canonical / route / policy mutation boundary.
Claude review blockers are addressed: this closeout exists, `pr.md` is rewritten for LTO-9 Step 2, and `application/commands/tasks.py` no longer reverse-imports `surface_tools.cli`.

# LTO-9 Step 2 Closeout: Broad CLI Command-Family Migration

## Scope

- track: `Architecture / Engineering`
- phase: `LTO-9 Step 2 — broad CLI command-family migration`
- branch: `refactor/cli_command_family_migration`
- mode: behavior-preserving CLI facade reduction and application command boundary completion
- base context: LTO-9 Step 1 had already split proposal / Meta-Optimizer / route weights / route capabilities surfaces; Step 2 completed the broad remaining CLI command-family migration.
- public compatibility targets:
  - `swallow.surface_tools.cli.main`
  - `swallow.surface_tools.cli.build_parser`
  - existing `swl` command names, flags, representative stdout/stderr shape, and exit codes

## Completed Milestones

| Milestone | Result |
|---|---|
| M1 Baseline and boundary hardening | Added focused CLI characterization coverage under `tests/integration/cli/` for route, audit, synthesis, knowledge, and task families before moving production dispatch. Expanded `tests/unit/application/test_command_boundaries.py` for command-module boundary checks. |
| M2 Governance-adjacent small families | Added `application/commands/route_metadata.py`, `application/commands/policies.py`, and `application/commands/synthesis.py`; moved route registry/policy/select, audit policy, and synthesis command adapters into focused `surface_tools/cli_commands/*` modules. |
| M3 Knowledge family migration | Added `application/commands/knowledge.py` and `surface_tools/cli_commands/knowledge.py`; moved staged candidate, canonical promotion, relation suggestion, link/unlink, ingest-file, and knowledge report command handling behind the new boundaries. |
| M4 Task write/control migration | Added task write/control application command functions for create/run/retry/resume/rerun/acknowledge/planning-handoff/knowledge-capture/knowledge decisions/canonical reuse/consistency audit; task state advancement remains through Orchestrator/domain entry points. |
| M5 Task read/report/artifact migration and cleanup | Moved task read/report/artifact handling and `ARTIFACT_PRINTER_DISPATCH` out of `surface_tools/cli.py`; kept `cli.py` as parser/bootstrap facade. Final cleanup removed direct migrated `apply_proposal` dispatch ownership from `cli.py`. |
| Review-fix closeout | Created this closeout, rewrote `pr.md`, removed the application-layer reverse import of `surface_tools.cli`, rephrased the last `cli.py` help-string `apply_proposal` mention, hardened command boundary tests to require the migrated modules, and updated legacy CLI tests to patch the application command boundary. |

## Implementation Notes

- `src/swallow/surface_tools/cli.py` remains the public CLI facade and parser owner. It now delegates migrated command families to focused adapter modules and is down to 2672 lines from the pre-phase 3653-line baseline.
- `src/swallow/surface_tools/cli_commands/route.py`, `audit.py`, `synthesis.py`, `knowledge.py`, and `tasks.py` own CLI adapter responsibilities: `argparse.Namespace` mapping, terminal output, and exit-code behavior.
- `src/swallow/application/commands/route_metadata.py` owns route registry / route policy governed writes through existing proposal registration helpers plus `apply_proposal(..., ProposalTarget.ROUTE_METADATA)`.
- `src/swallow/application/commands/policies.py` owns audit-trigger and MPS policy governed writes through existing registration helpers plus `apply_proposal(..., ProposalTarget.POLICY)`.
- `src/swallow/application/commands/knowledge.py` owns touched knowledge write actions. Canonical promotion remains proposal-governed; staged rejection and relation-suggestion application intentionally use their existing high-level domain helpers because they are not canonical proposal targets.
- `src/swallow/application/commands/tasks.py` owns touched task operator actions and wraps Orchestrator / domain entry points directly. After review, `run_task_command(...)` calls `swallow.orchestration.orchestrator.run_task` directly and no longer reaches through `swallow.surface_tools.cli`.
- `tests/test_cli.py` compatibility tests that patch task run behavior now patch `swallow.application.commands.tasks.run_task`, matching the new application command boundary rather than the old CLI re-export.
- `tests/unit/application/test_command_boundaries.py` now treats all migrated application command modules as required `COMMAND_MODULES`; the temporary `PLANNED_COMMAND_MODULES` silent-skip pattern and never-created `application/commands/ingestion.py` entry were removed.

## Boundary Confirmation

- No `docs/design/*.md` semantic changes.
- No SQLite schema, event schema, repository port, or migration change.
- No FastAPI write route, Control Center write path, request schema, or HTTP error contract was added.
- No new public mutation function, proposal target kind, task state transition owner, or Provider Router behavior was added.
- `apply_proposal(...)` remains the only public mutation entry for canonical knowledge / route metadata / policy.
- `surface_tools/cli.py` has no direct migrated `apply_proposal(` calls and no remaining `apply_proposal` help-string mention.
- Application command modules do not own terminal formatting and do not call prohibited private writer tokens.
- Existing invariant guard `test_state_transitions_only_via_orchestrator` still passes without allowlisting `application/commands/*`.
- `swallow.surface_tools.cli.main` and `build_parser` remain import-compatible.

## Deferred Work

- LTO-9 Step 1's `src/swallow/surface_tools/cli_commands/route_metadata.py` still directly calls `apply_proposal(...)` for `swl route weights apply` and `swl route capabilities update`. This was outside Step 2 scope and should be harmonized with the application command pattern only when that touched surface is next changed.
- `src/swallow/surface_tools/cli_commands/tasks.py` still uses an adapter-level `_cli()` import for legacy report helper functions such as task queue, attempts, artifact index, and mock-remote formatting. This is same-layer compatibility debt, not an application-layer reverse import; it can be retired when task read/query helpers are split into application queries or adapter helpers.
- FastAPI write-route parity remains a separate future LTO entry. This phase intentionally kept `web/api.py` read-only.
- LTO-5 application command write-side coverage is effectively complete for CLI-originated commands after this phase. Repository ports remain deferred until a real cross-backend trigger exists.
- LTO-8 Step 2 remains the next cluster-C closure phase: `harness.py` decomposition, further `orchestrator.py` reduction, and event-kind allowlist design.
- `v1.6.0` should remain deferred until LTO-8 Step 2 lands, so the tag can represent complete cluster-C closure.

## Review Absorption

Claude review is recorded in `docs/plans/surface-cli-meta-optimizer-split-step2/review_comments.md`.

- Initial verdict: `request-changes`.
- BLOCKER-1: missing `closeout.md` is resolved by this file.
- BLOCKER-2: stale root `pr.md` is resolved by rewriting it for LTO-9 Step 2.
- CONCERN-1: `application/commands/tasks.py` reverse-imported `swallow.surface_tools.cli` only to reach `run_task`; it now calls the already-imported Orchestrator function directly.
- CONCERN-2: Step 1 `cli_commands/route_metadata.py` direct `apply_proposal` calls are documented under Deferred Work rather than migrated out of scope.
- CONCERN-3: `swl synthesis policy set` help text now says "governed write" instead of exposing `apply_proposal`.
- CONCERN-4: migrated command modules are now required boundary-test inputs; the temporary optional module list was removed.

## Validation

Codex M5 final validation before Claude review:

```bash
.venv/bin/python -m pytest -q
# 721 passed, 8 deselected, 10 subtests passed

.venv/bin/python -m pytest tests/test_cli.py -q
# 242 passed, 10 subtests passed

.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# passed
```

Claude independently reproduced the full pytest result during review:

```bash
.venv/bin/python -m pytest -q
# 721 passed, 8 deselected, 10 subtests passed

git diff --check
# clean
```

Review-fix validation after addressing blockers and concerns:

```bash
.venv/bin/python -m pytest tests/unit/application/test_command_boundaries.py tests/test_invariant_guards.py tests/test_cli.py -q
# 279 passed, 10 subtests passed

.venv/bin/python -m pytest -q
# 721 passed, 8 deselected, 10 subtests passed

.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# passed
```

## Completion Status

- Plan audit concerns C-1 through C-5 were absorbed in plan and implementation.
- Implementation milestones M1 through M5 are complete and committed.
- Claude review request-changes items are addressed in this review-fix pass.
- `surface_tools/cli.py` no longer owns broad migrated command-family business logic.
- Application command write-side coverage for CLI-originated route/policy/knowledge/task commands is in place.
- Closeout and `pr.md` are prepared.
- Next workflow step: Human review and commit the review-fix / closeout materials, then create or update the PR from `pr.md` and decide merge readiness.
