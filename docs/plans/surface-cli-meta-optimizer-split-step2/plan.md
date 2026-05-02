---
author: codex
phase: surface-cli-meta-optimizer-split-step2
slice: phase-plan
status: review
depends_on:
  - docs/plans/surface-cli-meta-optimizer-split-step2/context_brief.md
  - docs/roadmap.md
  - docs/active_context.md
  - docs/plans/surface-cli-meta-optimizer-split/closeout.md
  - docs/plans/surface-cli-meta-optimizer-split/review_comments.md
  - docs/design/INVARIANTS.md
  - docs/design/INTERACTION.md
  - docs/design/SELF_EVOLUTION.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/TEST_ARCHITECTURE.md
---

TL;DR:
LTO-9 Step 2 completes the broad CLI command-family migration left by Step 1, with task / knowledge / artifact command paths moving behind focused CLI adapters and shared application commands where they mutate state.
This phase keeps behavior stable and does not introduce FastAPI write routes; UI write parity remains a future design point.
The highest risk is the task family split, because it touches Orchestrator entry points and many report/artifact printers; it gets its own milestone gate and characterization tests.

# LTO-9 Step 2 Plan: Broad CLI Command-Family Migration

## Frame

- track: `Architecture / Engineering`
- phase: `LTO-9 Step 2 — broad CLI command-family migration`
- roadmap ticket: `LTO-9 Step 2 — broad CLI command-family migration`
- long-term goals: `LTO-9 Surface / Meta Optimizer Modularity` + `LTO-5 Interface / Application Boundary`
- recommended_branch: `feat/surface-cli-meta-optimizer-split-step2`
- implementation mode: behavior-preserving / facade-first / milestone-gated
- planning branch: `main`

## Goals

1. Move broad remaining CLI command families out of `src/swallow/surface_tools/cli.py` into focused `surface_tools/cli_commands/` adapters.
2. Complete the LTO-5 application command pattern for touched write commands:
   - proposal-governed writes call existing registration helpers plus `apply_proposal`;
   - non-proposal task writes wrap Orchestrator / domain governance entry points directly.
3. Preserve all current CLI command names, flags, stdout/stderr shape, and exit codes for touched commands.
4. Expand persistent boundary tests so new `application/commands/*` modules stay terminal-format-free and do not call private writers.
5. Move new characterization and regression coverage into `tests/integration/cli/`, not root `tests/test_cli.py`.
6. Leave `swallow.surface_tools.cli.main` and `build_parser` as public compatibility entry points while shrinking their dispatch ownership.

## Non-Goals

- Do not add FastAPI write routes in this phase. `web/api.py` remains read-only.
- Do not implement Control Center UI write parity, request schemas, upload endpoints, or HTTP error contracts.
- Do not introduce repository ports, schema migrations, or a new persistence abstraction.
- Do not change `apply_proposal`, proposal target kinds, policy semantics, route selection behavior, task state schema, or event schema.
- Do not move `harness.py`, further split `orchestrator.py`, or touch LTO-8 Step 2 event-kind allowlist design.
- Do not resolve LTO-7 CONCERN-2 / CONCERN-3 unless a directly touched import makes a tiny hygiene fix unavoidable.
- Do not redesign CLI UX, rename commands, reword output intentionally, or normalize historical output inconsistencies.
- Do not convert `surface_tools/cli.py` into a package; keep import compatibility.

## Anchors

- `docs/design/INVARIANTS.md`
  - Control remains only in Orchestrator / Operator.
  - Execution entities do not advance task state or write Truth directly.
  - `apply_proposal` remains the only canonical / route / policy mutation entry.
- `docs/design/INTERACTION.md`
  - CLI is the primary operator entry.
  - CLI and future UI converge through shared application commands / queries.
  - FastAPI is an adapter, not a second business layer or Orchestrator.
- `docs/design/SELF_EVOLUTION.md`
  - Proposal-governed policy / route / canonical writes remain explicit Operator actions through `apply_proposal`.
- `docs/engineering/CODE_ORGANIZATION.md`
  - Target direction is `interfaces/cli` / `interfaces/http` -> `application/commands` / `application/queries` -> governance / orchestration / domain.
  - `surface_tools` is transitional and should shrink by facade-first migration.
- `docs/engineering/TEST_ARCHITECTURE.md`
  - New CLI tests belong under `tests/integration/cli/`.
  - Guard and source-text boundary tests must be narrowed, not weakened.

## Scope Decisions From `context_brief.md §9`

1. **Non-governance task write commands**: application commands should wrap Orchestrator / domain entry points directly. The proposal-registration pattern applies only to canonical / route / policy writes governed by `apply_proposal`.
2. **Route remainder**: include `swl route registry show/apply`, `swl route policy show/apply`, and `swl route select` in Step 2. They are small, still live in `cli.py`, and two apply commands still call `apply_proposal` directly from `main()`.
3. **FastAPI write routes**: out of scope. The roadmap phrase "FastAPI write-route patterns" is treated as a future LTO-5 design point, not a Step 2 requirement, because `active_context.md` classifies this phase as mechanical and no-new-invariant.
4. **`ARTIFACT_PRINTER_DISPATCH`**: move the dispatch table and artifact-printer helpers with the task read/artifact adapter. It is used only by task artifact-style subcommands and should no longer be owned by top-level `cli.py`.
5. **Audit and synthesis families**: include them. They are small, contain remaining direct `apply_proposal` policy writes in `main()`, and migrating them makes the CLI governance write boundary consistent.
6. **Boundary tests**: every new `application/commands/*` module is added to `COMMAND_MODULES` in `tests/unit/application/test_command_boundaries.py`, with module-specific private-writer prohibitions where needed.

## Plan Audit Absorption

`docs/plans/surface-cli-meta-optimizer-split-step2/plan_audit.md` returned `has-concerns` with 0 blockers and 5 concerns. This revision absorbs all five:

- C-1: M4 explicitly keeps `canonical-reuse-evaluate` and `consistency-audit` in task write/control scope because they call write-producing Orchestrator / domain functions despite read-like names.
- C-2: M3 explicitly permits `stage-reject` to use the existing staged review writer path; staged rejection is not a canonical promotion and does not use `apply_proposal`.
- C-3: M3 explicitly permits `apply-suggestions` to call the existing relation-suggestion application path; knowledge relation writes are not currently a proposal target, while direct private writer calls remain prohibited.
- C-4: M2/M3 require `apply_proposal` callsite migration and guard allowlist updates to happen in the same commit as new application command modules.
- C-5: M2-M5 each restate the pre-migration characterization gate for their command family.

## Target Module Shape

Exact names may be adjusted during implementation if a narrower ownership split is clearer, but the ownership boundaries below are the intended target.

| Area | Target files | Ownership |
|---|---|---|
| Task commands | `application/commands/tasks.py`, `surface_tools/cli_commands/tasks.py`, optionally `surface_tools/cli_commands/task_reports.py` / `task_artifacts.py` | Task operator actions, task report/adaptor formatting, artifact printers |
| Knowledge commands | `application/commands/knowledge.py`, `surface_tools/cli_commands/knowledge.py` | Staged review, promote/reject, ingest-file, links, relation suggestions, migration adapter |
| Route remainder | `application/commands/route_metadata.py`, `surface_tools/cli_commands/route.py` | Registry/policy show/apply and route select adapter |
| Audit / synthesis / ingest | `application/commands/policies.py`, `application/commands/ingestion.py`, `surface_tools/cli_commands/{audit,synthesis,ingestion}.py` as needed | Small remaining command families and policy writes |
| CLI facade | `surface_tools/cli.py` | Parser construction, top-level bootstrap, compatibility imports, delegating dispatch only |
| Boundary tests | `tests/unit/application/test_command_boundaries.py`, `tests/test_invariant_guards.py` | No terminal formatting in application commands; no private writer or state persistence drift |
| Integration tests | `tests/integration/cli/test_{task,knowledge,route,audit,ingestion}_commands.py` and existing synthesis/proposal/route files | Characterization and behavior-preservation coverage |

`surface_tools/cli.py` may still own `build_parser()` in this phase. Parser extraction is optional and should happen only when it reduces risk; the mandatory migration is dispatch / business ownership, not argparse file movement.

## Milestones

| Milestone | Slice | Scope | Risk | Validation | Gate |
|---|---|---|---|---|---|
| M1 | Baseline and boundary hardening | Add or verify characterization tests for all in-scope families before moving dispatch; expand application command boundary test scaffolding | high | focused `tests/integration/cli` characterization + `tests/unit/application/test_command_boundaries.py` | Human review + commit |
| M2 | Governance-adjacent small families | Move route remainder, audit policy, synthesis policy, note/ingest small surfaces behind adapters/application commands | high | route/audit/synthesis/ingestion CLI tests + invariant guards | Human review + commit |
| M3 | Knowledge family migration | Move `swl knowledge` dispatch and staged/canonical/relation/ingest-file command logic behind knowledge adapter/application command module | high | knowledge CLI tests + command boundary tests + governance tests | Human review + commit |
| M4 | Task write/control migration | Move task create/run/retry/resume/rerun/acknowledge/planning-handoff/knowledge-capture/promote/reject and close write/control variants behind task commands | high | task write/control CLI tests + orchestrator/state guard tests | Human review + commit |
| M5 | Task read/report/artifact migration and cleanup | Move task list/queue/attempts/compare/control/intake/staged/review/inspect/policy/artifacts/dispatch/artifact-printer table; clean direct dispatch from `cli.py` | medium-high | task read/artifact CLI tests + full default pytest + compileall + diff hygiene | Human review + commit, then Claude PR review |

## M1 Acceptance: Baseline and Boundary Hardening

Scope:

- Add focused characterization tests under `tests/integration/cli/` before moving dispatch for:
  - `swl route registry show/apply`, `swl route policy show/apply`, `swl route select`;
  - `swl audit policy show/set`;
  - `swl synthesis policy set`, `swl synthesis run`, and `swl synthesis stage` where current fixture cost is reasonable;
  - representative `swl knowledge` write and read commands;
  - representative task write/control/read/artifact commands.
- Use `tests/helpers/cli_runner.py` instead of adding to `tests/test_cli.py`.
- Expand `tests/unit/application/test_command_boundaries.py` so new application command modules can be added incrementally to `COMMAND_MODULES`.
- Add any needed helper assertions that make stdout/stderr/exit-code checks concise.

Acceptance:

- New characterization tests pass on current pre-migration code.
- `tests/test_cli.py` does not grow for touched behavior.
- Boundary tests remain green before new modules are added.
- No production dispatch code is moved before baseline tests for that family exist.

## M2 Acceptance: Governance-Adjacent Small Families

Scope:

- Move route remainder:
  - `swl route registry show`
  - `swl route registry apply`
  - `swl route policy show`
  - `swl route policy apply`
  - `swl route select`
- Move audit policy:
  - `swl audit policy show`
  - `swl audit policy set`
- Move synthesis policy write path and adjacent synthesis commands:
  - `swl synthesis policy set`
  - `swl synthesis run`
  - `swl synthesis stage`
- Move `swl note` and top-level `swl ingest` only if they can share a small ingestion command module without touching ingestion internals.
- Proposal-governed route / policy writes must call existing registration helpers plus `apply_proposal` through application command functions using `OperatorToken(source="cli")`.
- CLI adapters format reports and map `argparse.Namespace`; application commands return dataclasses or structured values.

Acceptance:

- Characterization tests for M2 command families pass on pre-migration `cli.py` dispatch code before dispatch code for those families is moved.
- No remaining direct `apply_proposal(` call in `surface_tools/cli.py` for route registry/policy, audit policy, or synthesis policy.
- Removing an `apply_proposal(` call from `surface_tools/cli.py`, adding the replacement call to `application/commands/*`, and updating any required `tests/test_invariant_guards.py` allowlist or assertion must happen in the same commit.
- New application command modules are included in `COMMAND_MODULES`.
- Application command modules do not import `argparse`, `click`, `rich`, `sys.stdout`, `sys.stderr`, or call `print`.
- Route / policy application commands do not import provider router private writer modules or call `save_route_*`, `save_audit_trigger_policy`, or `save_mps_policy` directly.
- Focused CLI tests for route/audit/synthesis/ingestion pass.
- `tests/test_invariant_guards.py -q` passes.

## M3 Acceptance: Knowledge Family Migration

Scope:

- Move `swl knowledge` dispatch behind `surface_tools/cli_commands/knowledge.py`.
- Introduce `application/commands/knowledge.py` for write actions:
  - `stage-promote`
  - `stage-reject`
  - `ingest-file`
  - `link`
  - `unlink`
  - `apply-suggestions`
  - `migrate` if it remains a command-like mutation surface.
- Keep read/report formatting in the CLI adapter:
  - `stage-list`
  - `stage-inspect`
  - `canonical-audit`
  - `links`
- `stage-promote` must still register a canonical proposal and call `apply_proposal(..., ProposalTarget.CANONICAL_KNOWLEDGE)` through the application command boundary.
- `stage-reject` is intentionally not an `apply_proposal` flow. It may use the existing staged review mutation path because rejecting a staged candidate does not write canonical knowledge.
- `apply-suggestions` is intentionally not an `apply_proposal` flow. It may use the existing relation-suggestion application path because knowledge relation writes are not currently represented by a `ProposalTarget`.
- Supersede preflight behavior, `--force`, refined text, notes, and stdout lines must remain unchanged.

Acceptance:

- Characterization tests for the knowledge family pass on pre-migration `cli.py` dispatch code before knowledge dispatch code is moved.
- No direct `apply_proposal(` call remains in `surface_tools/cli.py` for `knowledge stage-promote`.
- Removing the `stage-promote` `apply_proposal(` call from `surface_tools/cli.py`, adding the replacement call to `application/commands/knowledge.py`, and updating any required invariant guard allowlist or assertion must happen in the same commit.
- `application/commands/knowledge.py` is in `COMMAND_MODULES`.
- Knowledge command module has a source-text assertion prohibiting private canonical writers such as `append_canonical_record`, `persist_wiki_entry_from_record`, and `_promote_canonical`.
- Knowledge command module may call high-level staged / relation application helpers needed for `stage-reject` and `apply-suggestions`; it must not directly call lower-level canonical writers or bypass the existing staged / relation helper functions.
- Focused knowledge CLI characterization tests pass.
- Existing governance / knowledge tests pass:
  - `.venv/bin/python -m pytest tests/test_governance.py tests/unit/application/test_command_boundaries.py tests/integration/cli/test_knowledge_commands.py -q`

## M4 Acceptance: Task Write / Control Migration

Scope:

- Move task write/control dispatch behind `surface_tools/cli_commands/tasks.py`.
- Introduce `application/commands/tasks.py` for non-proposal task operator actions:
  - `create`
  - `run`
  - `retry`
  - `resume`
  - `rerun`
  - `acknowledge`
  - `planning-handoff`
  - `knowledge-capture`
  - `knowledge-promote`
  - `knowledge-reject`
  - `canonical-reuse-evaluate`
  - `consistency-audit`
- Non-proposal task commands may call Orchestrator / domain governance functions such as `create_task`, `run_task`, `acknowledge_task`, `decide_task_knowledge`, `append_task_knowledge_capture`, and `update_task_planning_handoff`.
- `canonical-reuse-evaluate` and `consistency-audit` belong in M4 even though their names look read-like: they call `evaluate_task_canonical_reuse` / `run_consistency_audit`, which produce artifacts, events, or audit outputs through existing Orchestrator / domain paths.
- They must not import or call `save_state`, execute SQL, or directly mutate task tables.
- Preserve blocked command behavior and exit codes for `acknowledge`, `retry`, and `resume`.

Acceptance:

- Characterization tests for task write/control commands pass on pre-migration `cli.py` dispatch code before task write/control dispatch code is moved.
- `application/commands/tasks.py` is in `COMMAND_MODULES`.
- A task-command boundary test asserts no `save_state`, direct SQL mutation strings, or repository private writer calls in `application/commands/tasks.py`.
- Existing invariant guard `test_state_transitions_only_via_orchestrator` passes without broadening its allowlist to application command modules.
- Focused task write/control CLI tests pass.
- `surface_tools/cli.py` no longer owns task write/control business logic; it delegates.

## M5 Acceptance: Task Read / Report / Artifact Migration and Cleanup

Scope:

- Move task read/report dispatch out of `surface_tools/cli.py`:
  - `list`
  - `queue`
  - `attempts`
  - `compare-attempts`
  - `control`
  - `intake`
  - `staged`
  - `knowledge-review-queue`
  - `inspect`
  - `review`
  - `checkpoint`
  - `policy`
  - `artifacts`
  - `dispatch`
  - `capabilities`
- Move `ARTIFACT_PRINTER_DISPATCH`, text/json artifact printer helpers, and canonical reuse artifact printers into a task artifact/report adapter module.
- Keep report formatting in CLI adapter modules unless a pure query helper is clearly reusable by FastAPI; do not start a broad application query migration in this phase.
- Remove now-unused imports from `surface_tools/cli.py`.
- Keep `build_parser()` and `main()` import-compatible.

Acceptance:

- Characterization tests for task read/report/artifact commands pass on pre-migration `cli.py` dispatch code before task read/report/artifact dispatch code is moved.
- `surface_tools/cli.py` top-level `main()` has no large per-task dispatch body; task handling is delegated to a focused adapter.
- `ARTIFACT_PRINTER_DISPATCH` no longer lives in `surface_tools/cli.py`.
- Focused task read/artifact CLI tests pass.
- Public CLI behavior remains compatible for representative task report/artifact commands.
- Final gates pass:
  - `.venv/bin/python -m pytest tests/integration/cli tests/unit/application/test_command_boundaries.py tests/test_invariant_guards.py -q`
  - `.venv/bin/python -m pytest -q`
  - `.venv/bin/python -m compileall -q src/swallow`
  - `git diff --check`

## Material Risks

- **Task family blast radius**: task commands mix Orchestrator calls, report formatting, artifact paths, and blocked-flow exit codes. Mitigation: split task writes and task reports into separate milestones; require characterization tests before each move.
- **Accidental second control plane**: application task commands could be mistaken for independent state-transition owners. Mitigation: they wrap Orchestrator/domain entry points only; guard tests must not allow `save_state` from application command modules.
- **`apply_proposal` boundary drift**: moving route/policy/canonical writes can accidentally call private writers. Mitigation: module-specific source-text boundary tests plus existing invariant guards.
- **CLI output drift**: moving formatting can change whitespace or stderr. Mitigation: stdout/stderr/exit-code characterization tests for each touched family before dispatch moves.
- **Plan overreach into FastAPI write routes**: adding HTTP write routes would require schemas and new UI/backend guard design. Mitigation: explicit non-goal; any FastAPI write work requires a later plan revision or new phase.
- **Parser extraction churn**: moving parser construction at the same time as dispatch increases review cost. Mitigation: parser extraction is optional; dispatch ownership is the mandatory target.

## Validation Plan

Focused commands will be refined per milestone, but the minimum gates are:

```bash
.venv/bin/python -m pytest tests/unit/application/test_command_boundaries.py -q
.venv/bin/python -m pytest tests/integration/cli -q
.venv/bin/python -m pytest tests/test_invariant_guards.py -q
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src/swallow
git diff --check
```

No eval coverage is required. This phase is behavior-preserving CLI/application boundary work, not quality-gradient retrieval, extraction, or operator report quality tuning.

## Branch, Review, and Commit Gates

- Recommended implementation branch after Human Plan Gate: `feat/surface-cli-meta-optimizer-split-step2`.
- Milestones are commit gates. Human should review and commit after each milestone before Codex proceeds.
- Suggested milestone commit scopes:
  - `test(cli): characterize broad command families`
  - `refactor(cli): migrate governance-adjacent command families`
  - `refactor(cli): migrate knowledge command family`
  - `refactor(cli): migrate task write commands`
  - `refactor(cli): migrate task report commands`
- Claude `plan_audit.md` is required before Human Plan Gate.
- Claude PR review is required after implementation before merge.

## Completion Conditions

1. `plan_audit.md` has no unresolved `[BLOCKER]`, and Human Plan Gate passes before implementation begins.
2. Remaining broad CLI command-family dispatch is moved out of `surface_tools/cli.py` according to milestone scope.
3. All touched write commands route through `application/commands/*` and existing governance / Orchestrator boundaries.
4. `surface_tools/cli.py` no longer owns direct `apply_proposal` calls for CLI operator command families migrated in this phase.
5. `application/commands/*` boundary tests cover all new command modules.
6. `tests/integration/cli/` contains focused coverage for touched command families; root `tests/test_cli.py` does not grow for new behavior.
7. No FastAPI write endpoint is added.
8. Full default pytest, compileall, invariant guards, and diff hygiene pass.
9. Closeout records actual moved command families, deferred items, validation output, and next step toward LTO-8 Step 2.
