---
author: codex
phase: surface-cli-meta-optimizer-split
slice: closeout
status: final
depends_on:
  - docs/plans/surface-cli-meta-optimizer-split/plan.md
  - docs/plans/surface-cli-meta-optimizer-split/plan_audit.md
  - docs/design/INVARIANTS.md
  - docs/design/INTERACTION.md
  - docs/design/SELF_EVOLUTION.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/TEST_ARCHITECTURE.md
  - docs/plans/surface-cli-meta-optimizer-split/review_comments.md
---

TL;DR:
LTO-9 Step 1 is complete on `feat/surface-cli-meta-optimizer-split`: proposal/meta-optimizer/route subset CLI surfaces now route through focused adapters and application command seeds, Meta-Optimizer read-only internals are split, and Control Center read queries moved into application queries.
The LTO-7 route metadata guard allowlist drift is resolved by naming `route_metadata_store.py` as the physical writer owner while documenting `provider_router/router.py` as a legacy facade exception.
Full default pytest, compileall, and diff hygiene passed; broad task/knowledge/artifact CLI migration remains deferred.

# Surface / CLI / Meta Optimizer Split Closeout

## Scope

- track: `Architecture / Engineering`
- phase: `Surface / CLI / Meta Optimizer Split / LTO-9 Step 1`
- branch: `feat/surface-cli-meta-optimizer-split`
- mode: behavior-preserving decomposition
- public compatibility targets:
  - `swallow.surface_tools.cli.main`
  - `swallow.surface_tools.cli.build_parser`
  - `swallow.surface_tools.meta_optimizer`

## Completed Milestones

| Milestone | Result |
|---|---|
| M1 Application command seed | Added `application/commands/` for touched proposal and meta-optimizer operator command paths. Proposal apply goes through `register_route_metadata_proposal(...)` + `apply_proposal(...)`; command modules remain terminal-format-free. |
| M2 Meta-Optimizer read-only split | Split snapshot construction, deterministic proposals, report rendering, lifecycle artifact IO, agent/executor adapter, and shared models into focused modules while keeping `surface_tools/meta_optimizer.py` as a compatibility facade. |
| M3 CLI command-family adapters | Added `surface_tools/cli_commands/` and moved dispatch/output adapters for `swl meta-optimize`, `swl proposal review/apply`, `swl route weights show/apply`, and `swl route capabilities show/update`. |
| M4 Query tightening and guard fix | Moved read-only Control Center artifact / subtask tree / execution timeline payload builders into `application/queries/control_center.py`; updated guard ownership so route metadata physical writers are explicitly owned by `provider_router/route_metadata_store.py`. |
| M5 Cleanup and closeout | Compatibility audit completed. No dead private wrappers were removed because the remaining facades still preserve public imports or test patch surfaces. Fixed one same-process proposal-id collision in the touched route metadata CLI adapter before final validation. |

## Implementation Notes

- `src/swallow/application/commands/proposals.py` owns structured operator proposal review/apply command results and calls governance through the existing proposal boundary.
- `src/swallow/application/commands/meta_optimizer.py` owns structured meta-optimizer command results; terminal formatting stays in CLI adapters.
- `src/swallow/surface_tools/cli_commands/` owns touched CLI adapter formatting and `argparse.Namespace` mapping.
- `src/swallow/surface_tools/meta_optimizer.py` is intentionally a re-export facade. Current tests and runtime paths still import public objects from it, including `MetaOptimizerExecutor`, `build_meta_optimizer_snapshot`, `run_meta_optimizer`, review/apply helpers, and report builders.
- `src/swallow/surface_tools/web/api.py` is now a thin FastAPI adapter for Control Center read routes. The moved builder names remain import-compatible through `web/api.py`.
- `src/swallow/truth_governance/truth/route.py` imports physical route metadata writers directly from `provider_router/route_metadata_store.py`; `provider_router/router.py` wrapper functions remain only as legacy compatibility surface.
- `src/swallow/surface_tools/cli_commands/route_metadata.py` now uses unique CLI proposal ids for `route weights apply` and `route capabilities update`, preventing global pending-proposal collisions when multiple CLI tests run in the same Python process. The proposal id is not part of command stdout/stderr.

## Boundary Confirmation

- No `docs/design/*.md` semantic changes.
- No task state schema change.
- No Provider Router selection behavior or route default behavior change.
- No new FastAPI write endpoint.
- No new proposal target kind.
- No direct route / policy / canonical writer outside the guarded repository / physical store ownership paths.
- `apply_proposal` remains the only canonical / route / policy mutation entry.
- MetaOptimizer agent/executor path remains read-only and proposal-producing; operator proposal apply lives in application command / CLI operator path.

## Deferred Work

- Broad `swl` task / knowledge / artifact command-family migration remains deferred.
- These route commands remain in `surface_tools/cli.py` by design:
  - `swl route registry show`
  - `swl route registry apply`
  - `swl route policy show`
  - `swl route policy apply`
  - `swl route select`
- `provider_router/router.py` still has hygiene-only private-name coupling and fallback ownership concerns from the LTO-7 follow-up group; only the route metadata guard allowlist drift was in scope for this phase.
- Durable cross-process proposal artifact lifecycle remains a broader governance/proposal follow-up, not part of this surface split.

## Validation

Focused M5 gates:

```bash
.venv/bin/python -m pytest tests/test_meta_optimizer.py tests/unit/application/test_command_boundaries.py tests/unit/surface_tools/test_meta_optimizer_boundary.py tests/integration/cli tests/test_web_api.py tests/test_invariant_guards.py -q
# 65 passed

.venv/bin/python -m pytest tests/test_cli.py -k "proposal or meta_optimizer or route_capabilities or route_weights or serve" -q
# 11 passed, 231 deselected
```

Final PR gate:

```bash
.venv/bin/python -m pytest -q
# 696 passed, 8 deselected, 10 subtests passed

.venv/bin/python -m compileall -q src/swallow
# passed

git diff --check
# passed
```

## Completion Status

- Plan audit concerns C-1 through C-5 were absorbed.
- LTO-7 route metadata guard allowlist drift is resolved.
- M4 query tightening proceeded safely; no skip rationale is needed.
- M5 compatibility audit found no safe facade removals.
- PR draft prepared at `pr.md`.
- Claude review is complete in `docs/plans/surface-cli-meta-optimizer-split/review_comments.md`.
- Review recommendation is **merge**.
- Review recorded 0 blockers and 2 follow-up concerns:
  - LTO-9 remains Step 1; broad task / knowledge / artifact CLI command-family migration is deferred.
  - LTO-7 hygiene items CONCERN-2 / CONCERN-3 remain deferred to touched-surface work.
- The follow-up concerns are non-blocking and already reflected in deferred work / concerns tracking.
