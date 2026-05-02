---
author: codex
phase: surface-cli-meta-optimizer-split
slice: lto9-step1-plan
status: review
depends_on:
  - docs/roadmap.md
  - docs/active_context.md
  - docs/concerns_backlog.md
  - docs/design/INVARIANTS.md
  - docs/design/INTERACTION.md
  - docs/design/SELF_EVOLUTION.md
  - docs/design/ORCHESTRATION.md
  - docs/design/HARNESS.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/TEST_ARCHITECTURE.md
  - docs/plans/orchestration-lifecycle-decomposition/closeout.md
  - docs/plans/orchestration-lifecycle-decomposition/review_comments.md
  - docs/plans/surface-cli-meta-optimizer-split/plan_audit.md
---

TL;DR:
LTO-9 Step 1 is a behavior-preserving surface decomposition: keep `swallow.surface_tools.cli.main` and current CLI output stable while extracting focused CLI command-family adapters and real `application/commands` entry points.
The highest-risk boundary is separating Meta-Optimizer's read-only specialist path from Operator proposal review/apply commands that may call `apply_proposal`.
This plan also absorbs the carried LTO-7 route metadata guard allowlist drift in `test_route_metadata_writes_only_via_apply_proposal`.

# Surface / CLI / Meta Optimizer Split Plan

## Frame

- track: `Architecture / Engineering`
- phase: `Surface / CLI / Meta Optimizer Split / LTO-9 Step 1`
- roadmap ticket: `Surface / CLI / Meta Optimizer split`
- long-term goals: `LTO-9 Surface / CLI / Meta Optimizer Modularity` + `LTO-5 Interface / Application Boundary`
- recommended implementation branch: `feat/surface-cli-meta-optimizer-split`
- planning branch: `main`
- implementation mode: facade-first / behavior-preserving
- public compatibility targets:
  - `swallow.surface_tools.cli.main`
  - `swallow.surface_tools.cli.build_parser`
  - `swallow.surface_tools.meta_optimizer`

## Current Code Context

Current surface code is still concentrated in a few files:

| File | Current shape |
|---|---|
| `src/swallow/surface_tools/cli.py` | about 3790 lines; owns parser construction, command dispatch, terminal formatting, and task / knowledge / route / proposal / audit / synthesis / serve command implementations |
| `src/swallow/surface_tools/meta_optimizer.py` | about 1320 lines; mixes read-only telemetry scan, proposal generation, proposal bundle IO, operator review/apply, report rendering, and MetaOptimizer agent/executor adapter |
| `src/swallow/surface_tools/web/api.py` | about 374 lines; already has a thin FastAPI adapter shape, but still owns several read-only Control Center payload builders |
| `src/swallow/application/queries/control_center.py` | query pilot only; no `application/commands/` package exists yet |
| `tests/test_cli.py` | historical aggregation point for many command families; new CLI tests should move into `tests/integration/cli/` when touched |

The next phase should start with the proposal / route / meta-optimizer surface because it sits exactly on the LTO-9 and LTO-5 intersection:

- Meta-Optimizer as a specialist is read-only and proposal-producing.
- Operator proposal review/apply is a surface command path and may call `apply_proposal`.
- Route metadata guard drift from LTO-7 is already targeted for LTO-9.

## Goals

1. Establish `application/commands/` as the shared command layer for touched operator actions.
2. Split Meta-Optimizer read-only scan/proposal generation from Operator proposal review/apply lifecycle.
3. Extract focused CLI command-family adapters for the in-scope command families while preserving `swl` behavior and output.
4. Keep `swallow.surface_tools.cli` and `swallow.surface_tools.meta_optimizer` as compatibility facades for existing imports.
5. Move or add touched CLI tests under `tests/integration/cli/` instead of growing `tests/test_cli.py`.
6. Fix the LTO-7 carried route metadata guard allowlist drift without weakening the `apply_proposal` invariant.

## Non-Goals

- Do not redesign CLI UX, command names, flags, exit codes, or output formats.
- Do not convert `swallow.surface_tools.cli` or `swallow.surface_tools.meta_optimizer` from modules into packages; keep import compatibility.
- Do not move all task / knowledge / artifact CLI commands in this step. Broad task/knowledge command migration can continue in later LTO-9 or touched-surface phases.
- Do not add new FastAPI write APIs or expand Control Center capabilities in this phase.
- Do not make FastAPI a business layer or second Orchestrator.
- Do not introduce new proposal target kinds, new governance semantics, schema migrations, or direct route / policy / canonical writers.
- Do not change Meta-Optimizer proposal heuristics or route scoring behavior except for behavior-preserving relocation.
- Do not change Provider Router selection behavior, route defaults, or Path A/B/C semantics.
- Do not update `docs/design/*.md` design semantics in this implementation phase.

## Design And Engineering Anchors

- `docs/design/INVARIANTS.md`
  - Control remains only in Orchestrator / Operator.
  - Execution never directly writes Truth.
  - Path A / B / C boundaries remain explicit.
  - `apply_proposal` remains the only canonical / route / policy mutation entry.
- `docs/design/INTERACTION.md`
  - CLI is the primary operator entry.
  - CLI normal commands should call shared application commands / queries in-process.
  - FastAPI remains an adapter, not a business layer or second Orchestrator.
- `docs/design/SELF_EVOLUTION.md`
  - Meta-Optimizer is read-only and proposal-producing.
  - Operator review/apply is explicit and ultimately goes through `apply_proposal`.
- `docs/engineering/CODE_ORGANIZATION.md`
  - Target direction is `interfaces/cli` and `interfaces/http` -> `application/commands` / `application/queries` -> governance / orchestrator / domain.
  - `surface_tools` is transitional and should shrink as application/interface layers become explicit.
- `docs/engineering/TEST_ARCHITECTURE.md`
  - New CLI tests should use `tests/integration/cli/`.
  - Guard tests must remain prominent and narrow; allowlists should be updated only when legitimate module ownership changes.
- `docs/concerns_backlog.md`
  - LTO-7 follow-up CONCERN-1: `test_route_metadata_writes_only_via_apply_proposal` allowlist names `provider_router/router.py`, while actual writers live in `route_metadata_store.py`; fix in LTO-9.

## Target Module Shape For This Phase

This phase is a first LTO-9 step, not the complete final surface architecture.

| Module / package | Intended ownership |
|---|---|
| `application/commands/__init__.py` | public home for shared application command entry points touched in this phase |
| `application/commands/proposals.py` | Operator proposal review/apply commands; allowed to call governance registration and `apply_proposal` because it is an Operator command path |
| `application/commands/meta_optimizer.py` | command wrapper for running Meta-Optimizer and returning structured CLI-ready results without formatting terminal output |
| `surface_tools/cli_commands/` | CLI adapter modules for in-scope command families; parse `argparse.Namespace`, call application commands / existing domain functions, format output |
| `surface_tools/meta_optimizer_snapshot.py` | event telemetry scan and snapshot value construction |
| `surface_tools/meta_optimizer_proposals.py` | deterministic proposal generation from snapshots |
| `surface_tools/meta_optimizer_lifecycle.py` | bundle load/save and proposal review record serialization, if not moved into application commands |
| `surface_tools/meta_optimizer_reports.py` | report rendering for snapshots, review records, and application records |
| `surface_tools/meta_optimizer_agent.py` | read-only MetaOptimizer agent/executor adapter; must not import or call `apply_proposal` |
| `surface_tools/meta_optimizer.py` | compatibility facade that re-exports existing public functions/classes while delegating to focused modules |
| `surface_tools/cli.py` | compatibility facade for `main`, `build_parser`, and legacy helper imports; should shrink but remain import-compatible |

Exact file names may be adjusted during implementation if a narrower ownership split is clearer. The non-negotiable ownership rule is: **MetaOptimizerAgent / executor code remains read-only; Operator proposal review/apply lives in application command code, not in the agent execution path.**

## Boundary Rules

- `swallow.surface_tools.cli.main(argv)` remains the only public CLI execution entry in this phase.
- CLI adapter modules may format output and map `argparse.Namespace` fields, but should not become business logic owners.
- Application command functions may call Orchestrator or governance functions, but must not format terminal output.
- Application command modules touched in this phase must be covered by source-text boundary tests proving they do not import/use terminal formatting or direct output APIs (`click`, `rich`, `argparse`, ANSI escape literals, `print`, `sys.stdout`, `sys.stderr`).
- Meta-Optimizer read-only modules must not call `apply_proposal`, `save_state`, repository private methods, or direct SQL.
- Meta-Optimizer read-only modules touched in this phase must be covered by persistent source-text boundary tests, not only a manual `rg` milestone check.
- Proposal apply may call `apply_proposal` only from an Operator command path using `OperatorToken(source="cli")`.
- `application/commands/proposals.py` must not introduce a second public canonical / route / policy mutation entry; it should call the existing governance API.
- Route metadata guard updates must make the actual writer ownership explicit without broadening allowed direct writer callers.
- `web/api.py` must remain read-only unless a later plan revision explicitly introduces shared write commands and tests.

## Milestones

| Milestone | Scope | Risk | Default gate |
|---|---|---|---|
| M1 | Application command seed for proposal lifecycle | high | focused unit tests + application command boundary tests + proposal CLI regression |
| M2 | Meta-Optimizer read-only module split | high | meta optimizer tests + persistent read-only boundary tests |
| M3 | CLI command-family adapter split for proposal / meta-optimize / explicitly bounded route subset | high | pre-extraction characterization tests + integration CLI tests + current CLI regressions |
| M4 | Optional-if-safe Control Center query tightening and required LTO-7 guard allowlist fix | medium-high | explicit go/no-go + web API tests + invariant guards |
| M5 | Facade cleanup, compatibility audit, closeout / PR gate | medium | full pytest + compileall + diff hygiene |

## M1 Acceptance: Application Command Seed

Scope:

- Add `src/swallow/application/commands/`.
- Move or wrap operator proposal review/apply command logic behind `application/commands/proposals.py`.
- Add `application/commands/meta_optimizer.py` as a structured, terminal-format-free command wrapper before the CLI `meta-optimize` adapter is extracted; it may delegate to existing Meta-Optimizer behavior until M2 finishes.
- Keep existing imports from `swallow.surface_tools.meta_optimizer` working through a compatibility facade.
- Preserve structured record formats:
  - `meta_optimizer_proposal_review_v1`
  - `meta_optimizer_proposal_application_v1`
- Preserve current CLI output for:
  - `swl proposal review`
  - `swl proposal apply`
- Add focused tests proving the application command path calls governance through the existing `apply_proposal` boundary and does not directly call route metadata store writers.
- Add `tests/unit/application/test_command_boundaries.py` source-text checks for `application/commands/proposals.py` and `application/commands/meta_optimizer.py`:
  - no `click`, `rich`, or `argparse` imports/usages;
  - no ANSI escape literals such as `\033[` or `\x1b[`;
  - no direct `print(`, `sys.stdout`, or `sys.stderr`.

Acceptance:

- `tests/test_meta_optimizer.py` proposal review/apply tests still pass.
- Focused proposal CLI tests pass.
- No new public mutation entry is introduced.
- Application command modules return structured results for adapters to format; they do not own terminal formatting.
- `tests/unit/application/test_command_boundaries.py -q` passes and enforces the no-terminal-formatting rule for touched application command modules.
- Existing `swallow.surface_tools.meta_optimizer.review_optimization_proposals` and `apply_reviewed_optimization_proposals` imports remain compatible.
- `git diff --check` passes.

## M2 Acceptance: Meta-Optimizer Read-Only Split

Scope:

- Extract read-only scan and snapshot construction from `meta_optimizer.py`.
- Extract deterministic proposal generation rules from `meta_optimizer.py`.
- Extract report rendering from `meta_optimizer.py` if it remains behavior-preserving.
- Keep `MetaOptimizerAgent` / `MetaOptimizerExecutor` compatible and visibly read-only.
- Keep `run_meta_optimizer(base_dir, last_n)` behavior and return contract unchanged.
- Add `tests/unit/surface_tools/test_meta_optimizer_boundary.py` as a persistent source-text guard for read-only Meta-Optimizer modules.
- The read-only boundary test should cover, at minimum:
  - `surface_tools/meta_optimizer_snapshot.py`;
  - `surface_tools/meta_optimizer_proposals.py`;
  - `surface_tools/meta_optimizer_reports.py`;
  - `surface_tools/meta_optimizer_agent.py`.
- If `surface_tools/meta_optimizer_lifecycle.py` stays limited to proposal bundle / review record artifact IO, include it in the same boundary test with documented allowances for file IO, but still prohibit Truth mutation APIs.
- Source-text boundary assertions must prohibit `apply_proposal`, `save_state`, `_apply_metadata_change`, `save_route_registry`, `save_route_policy`, `save_route_weights`, `save_route_capability_profiles`, and direct SQL mutation strings (`INSERT`, `UPDATE`, `DELETE`) in read-only modules.

Acceptance:

- `MetaOptimizerAgent.execute(...)` and `execute_async(...)` still return the same structured snapshot payload contract.
- `run_meta_optimizer(...)` still writes the same report artifact and latest structured proposal bundle.
- `tests/test_meta_optimizer.py -q` passes.
- `tests/unit/surface_tools/test_meta_optimizer_boundary.py -q` passes and persists the read-only source-text checks in regular pytest.
- A manual `rg -n "apply_proposal|save_state|_apply_metadata_change|save_route_registry|save_route_policy|save_route_weights|save_route_capability_profiles" src/swallow/surface_tools/meta_optimizer_*.py` may still be used as a review aid, but the persistent unit test is the gate.
- `MetaOptimizerAgent` implementation module has no `apply_proposal` reference.

## M3 Acceptance: CLI Command-Family Adapter Split

Scope:

- Add `src/swallow/surface_tools/cli_commands/` for in-scope CLI adapters.
- Extract only the following command adapters in this milestone:
  - `swl meta-optimize`
  - `swl proposal review`
  - `swl proposal apply`
  - `swl route weights show`
  - `swl route weights apply`
  - `swl route capabilities show`
  - `swl route capabilities update`
- Keep these route commands out of the M3 adapter extraction; if M4 later touches guard tests or shared helpers, that must not become a route registry / policy CLI migration:
  - `swl route registry show`
  - `swl route registry apply`
  - `swl route policy show`
  - `swl route policy apply`
  - `swl route select`
- Keep `build_parser()` and `main()` in `cli.py` for public compatibility, delegating parser/dispatch chunks to the adapter modules where safe.
- Before any parser or dispatch code is moved, write or verify characterization assertions under `tests/integration/cli/` for every in-scope command above against a minimal fixture workspace. These assertions must capture stdout, stderr, and exit code, and any assertion moved from `tests/test_cli.py` should be copied verbatim first.
- Only after the pre-extraction characterization tests pass should parser or dispatch code move into `cli_commands/`.
- Move touched tests from root `tests/test_cli.py` into focused files under `tests/integration/cli/` where feasible:
  - `test_proposal_commands.py`
  - `test_route_commands.py`
  - `test_meta_optimizer_commands.py`
- Do not move unrelated task / knowledge command blocks unless the implementation proves a small shared helper move is necessary.

Acceptance:

- Top-level `swl --help` still lists the same command names and help wording for in-scope commands.
- Pre-extraction characterization tests exist for all in-scope M3 commands and pass before adapter extraction begins.
- `swl meta-optimize`, `swl proposal review`, `swl proposal apply`, `swl route weights show/apply`, and `swl route capabilities show/update` preserve current stdout, stderr, and exit codes.
- Existing direct imports from `swallow.surface_tools.cli` used by tests remain valid.
- New CLI tests live under `tests/integration/cli/`; root `tests/test_cli.py` does not grow for touched behavior.
- `tests/test_cli.py` focused in-scope tests and `tests/integration/cli -q` pass.

## M4 Acceptance: Query Tightening And Guard Fix

Scope:

- Required deliverable: fix the LTO-7 carried route metadata guard allowlist drift.
- Optional-if-safe deliverable: move low-risk read-only Control Center payload builders from `surface_tools/web/api.py` into `application/queries/` only if the move keeps `web/api.py` a thinner adapter without widening scope.
- M4 go/no-go checkpoint:
  - At M4 start, inspect the payload builders in `surface_tools/web/api.py`.
  - Proceed with query tightening only if it preserves HTTP response shape, does not require broad test rewrites, and does not expand any write-command surface.
  - If moving a builder would change API response shape, require broad fixture rewrites, or blur read/write boundaries, skip the query move and record `M4 query tightening skipped as not-safe` with rationale in closeout.
- Keep `create_fastapi_app(...)` and HTTP route behavior unchanged.
- Fix LTO-7 carried concern:
  - Update `test_route_metadata_writes_only_via_apply_proposal` so the allowlist reflects actual route metadata writer ownership.
  - Do not weaken the protected writer set.
  - Prefer making `route_metadata_store.py` the explicit physical writer owner and `truth_governance/truth/route.py` the governance repository caller.
  - If `provider_router/router.py` compatibility wrappers still require special handling, document it in test comments and closeout rather than silently broadening the allowlist.

Acceptance:

- The route metadata guard fix is completed regardless of whether query tightening is skipped.
- `tests/test_web_api.py -q` passes.
- `tests/test_invariant_guards.py -q` passes.
- If query tightening happens, `web/api.py` is thinner, `application/queries/` owns the moved read-only payload builders, and `tests/test_web_api.py -q` passes without response-shape changes.
- If query tightening is skipped, `tests/test_web_api.py -q` still passes unchanged and closeout records the skip rationale.
- The route metadata guard no longer carries the LTO-7 allowlist drift described in `docs/concerns_backlog.md`.
- No new FastAPI write endpoint or direct repository write is introduced.

## M5 Acceptance: Facade Cleanup And Closeout

Scope:

- Remove dead private wrappers left behind by M1-M4 only when import compatibility is proven.
- Keep compatibility facades for `cli.py` and `meta_optimizer.py`.
- Update `docs/plans/surface-cli-meta-optimizer-split/closeout.md`, `docs/active_context.md`, `current_state.md`, and `pr.md` after implementation and validation.
- Record any deferred command-family migrations explicitly.

Acceptance:

- Public CLI behavior remains compatible.
- `swallow.surface_tools.meta_optimizer` public imports used by current tests remain compatible.
- MetaOptimizer read-only agent path is separated from Operator proposal apply path.
- LTO-7 route metadata guard concern is either resolved or explicitly blocked with a concrete reason.
- Full default pytest passes.
- `compileall` passes.
- `git diff --check` passes.

## Validation Plan

Focused gates selected by milestone:

```bash
.venv/bin/python -m pytest tests/test_meta_optimizer.py -q
.venv/bin/python -m pytest tests/unit/application/test_command_boundaries.py -q
.venv/bin/python -m pytest tests/unit/surface_tools/test_meta_optimizer_boundary.py -q
.venv/bin/python -m pytest tests/integration/cli -q
.venv/bin/python -m pytest tests/test_cli.py -k "proposal or meta_optimizer or route_capabilities or route_weights or serve" -q
.venv/bin/python -m pytest tests/test_web_api.py -q
.venv/bin/python -m pytest tests/test_invariant_guards.py -q
```

Milestone and PR gates:

```bash
.venv/bin/python -m compileall -q src/swallow
git diff --check
.venv/bin/python -m pytest -q
```

Eval:

- Not required by default for this phase because the intended work is behavior-preserving decomposition.
- Existing eval coverage for Meta-Optimizer proposal quality should remain untouched unless the implementation changes proposal heuristics; changing heuristics is out of scope for this plan.

## Risks And Controls

| Risk | Control |
|---|---|
| MetaOptimizer agent appears to own mutation | Split read-only agent/snapshot/proposal generation from Operator proposal review/apply; add persistent source-text boundary tests for prohibited mutation APIs in read-only modules |
| Application command layer starts formatting terminal output | Add source-text boundary tests prohibiting terminal formatting dependencies, ANSI literals, and direct stdout/stderr writes in touched `application/commands` modules |
| CLI output drift | Build pre-extraction characterization tests for stdout/stderr/exit code before moving dispatch code; keep current output assertions |
| Big-bang CLI rewrite | Only extract in-scope command families first; keep `cli.py` facade and defer task/knowledge/artifact broad migration |
| Application layer becomes another facade with no value | Move only touched operator actions that actually cross CLI/Web/governance boundaries; each command returns structured data consumed by adapters |
| Route metadata guard weakened while fixing allowlist drift | Keep protected writer set unchanged and update allowed ownership narrowly |
| Import compatibility break | Keep `swallow.surface_tools.cli` and `swallow.surface_tools.meta_optimizer` as compatibility modules; add import tests where needed |
| Test relocation hides coverage loss | Move assertions verbatim first; assertion improvements are separate from relocation unless required for the slice |
| Optional M4 query tightening disappears silently | Use the M4 go/no-go checkpoint and record skipped-as-not-safe rationale in closeout when the move is not safe |

## Branch And PR Recommendation

- Planning may remain on `main`.
- Implementation branch after Plan Gate: `feat/surface-cli-meta-optimizer-split`.
- Recommended initial docs commit:
  - `docs(plan): revise surface split plan after audit`
- Recommended implementation milestone commits:
  - `refactor(surface): seed application proposal commands`
  - `refactor(surface): split meta optimizer lifecycle modules`
  - `refactor(cli): extract proposal and route command adapters`
  - `test(guards): tighten route metadata writer allowlist`
  - `docs(state): update surface split closeout`

High-risk milestones M1-M3 should be reviewed separately. M4 guard tightening should not be mixed with unrelated CLI adapter churn unless the implementation proves the guard change is directly caused by the adapter move.

## Completion Conditions

1. `application/commands/` exists and owns at least the touched Operator proposal lifecycle command path.
2. MetaOptimizer read-only specialist path is visibly separated from Operator proposal apply/review path.
3. `cli.py` remains import-compatible and delegates at least the in-scope command families to focused adapters.
4. `meta_optimizer.py` remains import-compatible and delegates to focused read-only / lifecycle modules.
5. CLI behavior, output, and exit codes for in-scope commands remain unchanged.
6. Application command modules are covered by source-text boundary tests proving they do not own terminal formatting.
7. Meta-Optimizer read-only modules are covered by persistent source-text boundary tests proving they do not reference Truth mutation APIs.
8. LTO-7 route metadata guard allowlist drift is resolved or explicitly documented as a blocker with a concrete follow-up.
9. No design semantics, task schema, route behavior, Provider Router behavior, or `apply_proposal` semantics change.
10. Focused tests, invariant guards, compileall, full pytest, and diff hygiene pass.
11. `docs/active_context.md`, closeout material, and PR draft reflect the final module split and deferred follow-ups.

## Plan Audit Notes

- `context_brief.md` is not present because Human asked Codex to start the next phase planning directly after roadmap update. A separate context brief can still be requested before or during plan audit if Human / Claude wants a fact-only coupling summary.
- This plan intentionally treats LTO-9 as Step 1. Full migration of all task / knowledge / artifact CLI command families is deferred unless it is needed by the in-scope proposal/meta/route work.
- `plan_audit.md` verdict is `has-concerns` with 0 blockers. The five concerns were absorbed here as bounded M1/M2 source-text tests, M3 explicit command scope and characterization precondition, and M4 query-tightening go/no-go rules.
- Because this phase touches public CLI surface and the `apply_proposal` operator path, Human Plan Gate is still required before implementation. Model review can be requested if audit finds unresolved governance-boundary risk.
