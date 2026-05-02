---
author: claude
phase: surface-cli-meta-optimizer-split-step2
slice: context-brief
status: draft
depends_on:
  - docs/roadmap.md
  - docs/plans/surface-cli-meta-optimizer-split/closeout.md
  - docs/plans/surface-cli-meta-optimizer-split/plan.md
  - docs/plans/surface-cli-meta-optimizer-split/plan_audit.md
  - docs/plans/surface-cli-meta-optimizer-split/review_comments.md
  - docs/design/INTERACTION.md
  - docs/design/SELF_EVOLUTION.md
  - docs/engineering/CODE_ORGANIZATION.md
  - src/swallow/surface_tools/cli.py
  - src/swallow/surface_tools/cli_commands/
  - src/swallow/application/commands/
  - src/swallow/application/queries/control_center.py
  - src/swallow/surface_tools/web/api.py
  - tests/test_invariant_guards.py
---

TL;DR: Step 1 (LTO-9 / LTO-5 first increment) is merged to main at `21c1884`. `cli.py` is 3653 lines — task family dispatch alone accounts for ~800 lines in `main()`, plus ~800 lines of helpers and ~650 lines of parser setup; knowledge family is ~130 lines parser + ~140 lines dispatch. Both families have direct `apply_proposal` calls mixed into `main()`, making them write-command candidates for the application/commands layer. FastAPI `web/api.py` is currently read-only (zero write routes); introducing write routes would be a new design point.

## 1. Step 1 Recap

Step 1 (merged `21c1884`) delivered: (a) six Meta-Optimizer focused read-only modules (`meta_optimizer_{snapshot,proposals,reports,lifecycle,agent,models}.py`), with `surface_tools/meta_optimizer.py` as a ~30-line compatibility facade; (b) three CLI command-family adapters under `surface_tools/cli_commands/` for `swl meta-optimize`, `swl proposal review/apply`, and `swl route weights show/apply` + `swl route capabilities show/update`; (c) `application/commands/` package seeded with `proposals.py` and `meta_optimizer.py`; (d) read-only Control Center query builders migrated from `web/api.py` to `application/queries/control_center.py`; (e) LTO-7 CONCERN-1 guard allowlist drift fixed with a positive assertion. `cli.py` reduced from 3790 → 3653 lines (~4%). Explicitly deferred: broad task / knowledge / artifact CLI command-family migration; five route subcommands (`swl route registry show/apply`, `swl route policy show/apply`, `swl route select`).

## 2. `cli.py` Current Shape (Factual Partition)

`cli.py` is 3653 lines as of `21c1884`. Structure:

| Region | Line range | Purpose |
|--------|-----------|---------|
| Imports + top-level data | 1–233 | Imports from all domain modules; `ARTIFACT_GROUPS` tuple; 3 delegating imports from `cli_commands/` (lines 67–69) |
| Shared helper functions | 234–1364 | Format/snapshot/report builders used by task, knowledge, and artifact commands; `build_task_control_snapshot` (1171–1266), `build_attempt_summaries` (1267–1330), `execute_task_run` (1332–1356), `ARTIFACT_PRINTER_DISPATCH` table (620–758), staged-knowledge helpers (811–1004), `build_task_staged_report` (884–918) |
| `build_parser()` | 1365–2481 | Argparse setup for all command families |
| `main()` dispatch | 2483–3653 | `if args.command == ...` dispatch chain |

**Command family partition within `build_parser()` and `main()`:**

**Task family** (`swl task <subcommand>`):

- Parser setup: lines 1564–1565 (task subparser declaration) + 1796–2444 (all task subparser definitions, ~650 lines)
- Task subcommands: `create`, `run`, `retry`, `resume`, `rerun`, `acknowledge`, `list`, `queue`, `attempts`, `compare-attempts`, `control`, `intake`, `staged`, `inspect`, `review`, `checkpoint`, `policy`, `artifacts`, `planning-handoff`, `knowledge-capture`, `knowledge-promote`, `knowledge-reject`, `knowledge-review-queue`, `canonical-reuse-evaluate`, `consistency-audit`, `capabilities` — plus ~30 read-only artifact-print subcommands (`semantics`, `retrieval`, `topology`, `handoff`, `dispatch`, `route`, `memory`, and their JSON variants) served by `ARTIFACT_PRINTER_DISPATCH` table
- Dispatch: lines 2861–3610, ~750 lines. Key write subcommands calling domain functions directly in `main()`: `create` → `create_task()`; `run` → `execute_task_run()` → `run_task()`; `retry`/`resume`/`rerun` → orchestrator functions; `knowledge-promote`/`knowledge-reject` → `decide_task_knowledge()` (not `apply_proposal` directly); `planning-handoff` → `update_task_planning_handoff()`; `knowledge-capture` → `append_task_knowledge_capture()`. No `apply_proposal` calls in the task dispatch block.
- Status: **not migrated**; dispatch and formatting mixed in `main()`

**Knowledge family** (`swl knowledge <subcommand>`):

- Parser setup: lines 1566–1567 (knowledge subparser declaration) + 1676–1795 (~120 lines)
- Knowledge subcommands: `stage-list`, `stage-inspect`, `stage-promote`, `stage-reject`, `canonical-audit`, `ingest-file`, `link`, `unlink`, `links`, `apply-suggestions`, `migrate`
- Dispatch: lines 2498–2634, ~137 lines. Write subcommands with `apply_proposal` calls directly in `main()`:
  - `stage-promote` (line 2551): `register_canonical_proposal(...)` + `apply_proposal(..., ProposalTarget.CANONICAL_KNOWLEDGE)`
  - `apply-suggestions` (line 2616–2621): `apply_relation_suggestions()` (not `apply_proposal` — relation writer, verify scope)
  - `ingest-file` (2581): `ingest_local_file()` — no `apply_proposal`
- Status: **not migrated**; write-path `apply_proposal` calls in `main()`

**Audit family** (`swl audit`):

- Parser setup: lines 1378–1431 (~54 lines)
- Subcommands: `audit policy show`, `audit policy set`
- Dispatch: lines 2634–2666. `audit policy set` calls `register_policy_proposal(...)` + `apply_proposal(..., ProposalTarget.POLICY)` directly in `main()`
- Status: **not migrated**; small family (~30 dispatch lines)

**Synthesis family** (`swl synthesis`):

- Parser setup: lines 1432–1469 (~38 lines)
- Subcommands: `synthesis policy show`, `synthesis policy set`, `synthesis run`, `synthesis stage`
- Dispatch: lines 2667–2756. `synthesis policy set` calls `register_mps_policy_proposal(...)` + `apply_proposal(..., ProposalTarget.POLICY)` directly in `main()`
- Status: **not migrated**; small family (~90 dispatch lines)

**Route remainder** (explicitly kept in `cli.py` by Step 1 design):

- Subcommands: `swl route registry show`, `swl route registry apply`, `swl route policy show`, `swl route policy apply`, `swl route select`
- Parser: lines 1470–1563 (~94 lines, includes registry/policy/select and the already-migrated weights/capabilities parsers)
- Dispatch: lines 2757–2811. Registry apply (line 2764) and policy apply (line 2780) both call `register_route_metadata_proposal(...)` + `apply_proposal(...)` directly in `main()`
- Status: **intentionally deferred** by Step 1 closeout; decision open for Step 2

**Note / Ingest surface** (`swl note`, `swl ingest`):

- Parser: lines 1634–1667 (~34 lines)
- Dispatch: lines 2812–2850 (~39 lines). `swl note` → `ingest_operator_note()`; `swl ingest` → `run_ingestion_pipeline()` / `run_ingestion_bytes_pipeline()`. No `apply_proposal` calls.
- Status: **not migrated**; small, no governance write path

**Other surface** (`swl serve`, `swl migrate`, `swl doctor`):

- `swl serve` (parser line 1668, dispatch line 2851): starts FastAPI via `serve_control_center()`; single-line dispatch
- `swl migrate` (parser line 1575, dispatch line 3609): file-to-SQLite migration utilities; no `apply_proposal`
- `swl doctor` (parser line 1568, dispatch line 3617): diagnostics only; no write path

## 3. `application/commands/` Seed Pattern

Established by Step 1 in `src/swallow/application/commands/proposals.py` and `application/commands/meta_optimizer.py`:

- **Command result dataclasses**: frozen `@dataclass` returning structured data (`ProposalReviewCommandResult`, `ProposalApplyCommandResult`, `MetaOptimizerCommandResult`). No `print`, `sys.stdout`, `sys.stderr`, `argparse`, `click`, `rich`, or ANSI literals allowed; enforced by `tests/unit/application/test_command_boundaries.py` (11 forbidden-token assertions running in every full pytest).
- **Terminal-formatting boundary**: application command returns a dataclass; CLI adapter in `cli_commands/` calls the command and formats output. The boundary test uses source-text grep, not import-AST inspection.
- **Governance integration pattern for write commands**: `proposals.py` calls `register_route_metadata_proposal(base_dir, proposal_id, review_path)` then `apply_proposal(registered_proposal_id, OperatorToken(source="cli"), ProposalTarget.ROUTE_METADATA)`. No direct calls to `route_metadata_store` private writers.
- **Source-text boundary tests**: `tests/unit/application/test_command_boundaries.py` — `COMMAND_MODULES` tuple enumerates the modules under test; adding a new application command module requires updating this tuple to bring it under the boundary check.

## 4. `application/queries/` and FastAPI Pattern

`src/swallow/application/queries/control_center.py` (established by Step 1 M4): owns all read-only payload builders for Control Center HTTP routes — task list, task detail, events, artifacts, subtask tree, execution timeline. `web/api.py` (109 lines after Step 1) is a thin FastAPI adapter: each route calls exactly one query function from `application/queries/control_center.py` and maps exceptions to HTTP errors. All FastAPI routes are `@app.get(...)` — zero write routes (`POST`/`PUT`/`DELETE`/`PATCH`) exist anywhere in `web/api.py` as of `21c1884`.

**Query result shape**: query functions return `dict[str, object]` (JSON-serializable payload). Command result shape (from `application/commands/`): frozen dataclass with typed fields for CLI adapters to destructure.

**FastAPI write route gap**: INTERACTION.md §4.2.3 lists write operations (task create/run, proposal apply, knowledge promote/reject) as UI capabilities that should route through the same governance functions as CLI. No FastAPI write route exists today. Introducing write FastAPI routes would require: (a) a write-route framework decision (request body schema, HTTP verb choices, error mapping), (b) calling the same `application/commands/` functions already seeded for CLI, and (c) guard test updates (the `test_ui_backend_only_calls_governance_functions` guard mentioned in INTERACTION.md §4.2.1 exists but its current scope needs verification against `web/api.py`).

## 5. Invariant Boundaries That Constrain Step 2

- `apply_proposal` remains the only public canonical / route / policy mutation entry (INVARIANTS §0, SELF_EVOLUTION.md §3). Any write command migrated to `application/commands/` must call `apply_proposal` through the existing governance API, not repository private methods. `tests/test_invariant_guards.py:228–232` allowlist is the enforcement point.
- CLI adapters format and parse; they do not own business logic (INTERACTION.md §4.1, CODE_ORGANIZATION.md §2).
- Application command modules must not format terminal output — enforced by source-text boundary tests in `tests/unit/application/test_command_boundaries.py`.
- `web/api.py` must not implement independent state transitions, proposal mutation, or route policy logic (INTERACTION.md §4.2.1). Any write FastAPI route must call the same `application/commands/` function as the CLI adapter.
- Step 2 must NOT change CLI stdout/stderr/exit codes for any existing command. The Step 1 characterization test pattern (stdout/stderr/exit-code assertions in `tests/integration/cli/` before any dispatch code moves) is the mandatory pre-extraction gate.
- Meta-Optimizer read-only boundary: `tests/unit/surface_tools/test_meta_optimizer_boundary.py` guards against mutation API references in `meta_optimizer_*.py` modules; Step 2 must not weaken this guard.
- LTO-7 CONCERN-2 (`provider_router/router.py` private name coupling) and CONCERN-3 (fallback ownership): remain open in `docs/concerns_backlog.md`, touched-surface only. Step 2 may or may not reach them.

## 6. Test Architecture Context

- `tests/test_cli.py`: 3034-line `unittest.TestCase`-based file, single class `CliLifecycleTest`, 242 test methods. No per-family selector exists — all 242 methods are in one class with mixed coverage (task lifecycle, knowledge staging, route select, serve, canonical reuse, retrieval). Step 1 policy: test_cli.py must not grow for touched behavior; new tests go to `tests/integration/cli/`.
- `tests/integration/cli/` seeded by Step 1: `test_proposal_commands.py` (108 lines), `test_route_commands.py` (151 lines), `test_meta_optimizer_commands.py` (65 lines), plus pre-existing `test_synthesis_commands.py`. Step 2 must add analogous characterization test files for each family it migrates, capturing stdout/stderr/exit codes before dispatch code moves.
- `tests/unit/application/test_command_boundaries.py`: `COMMAND_MODULES` tuple drives which application command modules are tested. Step 2 new modules must be added to `COMMAND_MODULES`.
- `tests/unit/application/test_control_center_queries.py`: covers the query layer; Step 2 should not disturb this.
- `tests/unit/surface_tools/test_meta_optimizer_boundary.py`: source-text boundary guard for read-only Meta-Optimizer modules.
- `tests/test_web_api.py` (409 lines): covers all existing FastAPI GET routes. Any new write route would require new coverage here.
- `tests/test_invariant_guards.py` (835 lines): contains allowlists for `apply_proposal` callers, private writer callers, and module import boundaries. Step 2 must update allowlists when new modules legitimately call governance functions.

## 7. Deferred Items Inherited

From Step 1 closeout and review_comments:

- **Broad task / knowledge / artifact CLI migration** — the primary deferred item; this IS the headline scope of Step 2.
- **Five route subcommands** (`swl route registry show/apply`, `swl route policy show/apply`, `swl route select`): explicitly kept in `cli.py` by Step 1 design. These also contain direct `apply_proposal` calls (registry apply at line 2764, policy apply at line 2780). Step 2 must decide: migrate these alongside the other families, or explicitly re-defer.
- **Audit and synthesis families** (`swl audit policy set`, `swl synthesis policy set`): small families not mentioned in the headline Step 2 scope, but both contain direct `apply_proposal` calls in `main()`. Decision: include or re-defer.
- **FastAPI write routes**: INTERACTION.md §4.2.3 describes write UI operations, but no write routes exist. Step 2 scope statement mentions "FastAPI write-route patterns" as in-scope; this would be the first write route introduction.
- **LTO-5 repository ports** (`local SQLite repository ports`): roadmap LTO-5 row lists this as remaining work alongside CLI command migration. Step 2 scope description does not explicitly include repository ports work.
- **LTO-7 CONCERN-2/3**: touched-surface only; no dedicated phase required.

## 8. Estimated Scope Size

Based on line counts in `cli.py`:

**Task family only**: Parser setup ~650 lines + helper functions ~700 lines (task control snapshot, attempt summaries, execute_task_run, filter_task_states, etc.) + dispatch ~800 lines = ~2150 lines to analyze; likely 400–600 lines moved out of `cli.py` into a new `cli_commands/task.py` adapter + 1–3 new `application/commands/task_*.py` modules. Subcommand count: ~40 (including read-only artifact printers served by `ARTIFACT_PRINTER_DISPATCH`). Characterization test file: 1 new file in `tests/integration/cli/`.

**Knowledge family only**: Parser ~120 lines + helpers (staged-knowledge helpers at 811–1004, ~200 lines) + dispatch ~140 lines = ~460 lines to analyze; likely 100–200 lines moved. Subcommand count: 11. Key write commands: `stage-promote` (calls `apply_proposal` with `ProposalTarget.CANONICAL_KNOWLEDGE`). Characterization test: 1 new file.

**Audit + synthesis families**: Combined small scope (~200 lines parser + dispatch). Both have `apply_proposal` calls.

**Route remainder (registry/policy/select)**: ~90 lines parser + ~55 lines dispatch. Already has `apply_proposal` calls for apply subcommands.

**All three headline families (task + knowledge + route-remainder) at once**: ~2600–3000 lines to analyze across cli.py; estimated ~600–900 lines moved out, 3–5 new `cli_commands/` adapter modules, 2–4 new `application/commands/` modules, 3–4 new characterization test files in `tests/integration/cli/`, `test_command_boundaries.py` extended to cover new modules. Milestone count: likely 4–6 milestones (one per family or grouped as a 3-way M1/M2/M3 with shared M0 characterization + M4 guard/cleanup).

**Splitting task family first, then knowledge**: task family is significantly larger (40 subcommands vs. 11) and has deeper helper coupling; splitting by family is a sensible natural boundary because the helpers for task and knowledge are distinct (task: control snapshot, attempt summaries, execute_task_run; knowledge: staged-knowledge helpers, build_stage_canonical_record).

**FastAPI write routes scope question**: The task family's write commands (`create`, `run`, `retry`, `resume`, `rerun`, `acknowledge`, `knowledge-promote`, `knowledge-reject`) have no FastAPI surface today. Adding write routes would require new request/response schemas. This is the biggest scope wildcard — adding write routes roughly doubles the test surface for any migrated command.

## 9. Open Questions for Codex

1. **Non-governance task write commands**: `swl task create` calls `create_task()` and `swl task run` calls `run_task()` via `execute_task_run()`. Neither goes through `apply_proposal`. Should the application/commands layer for these commands wrap orchestrator functions directly, using the same pattern as `meta_optimizer.py` (which wraps `run_meta_optimizer()`)? Or does the proposal-based pattern from `proposals.py` apply only to governance write paths?

2. **Route remainder (registry/policy/select)**: Step 1 kept these in `cli.py` "by design." The registry apply and policy apply subcommands both contain direct `apply_proposal` calls in `main()`. Step 2 must decide: migrate these into a `cli_commands/route_registry_policy.py` adapter alongside the other families, or explicitly re-defer again. The human direction statement says "proposal lifecycle and report parsing alignment" and "5 route subcommands kept in cli.py" — ambiguous whether Step 2 should absorb them.

3. **FastAPI write routes in scope**: The human direction statement says "FastAPI write-route patterns" is in scope. Does this mean Step 2 must introduce at least one write route (e.g., `POST /api/tasks` for task create), or only establish the design pattern so a future phase can implement write routes? The answer changes the test surface substantially.

4. **ARTIFACT_PRINTER_DISPATCH table for task read-only subcommands**: The ~30 read-only task subcommands (`semantics`, `retrieval`, `topology`, `handoff`, their JSON variants) are currently served by a dispatch table rather than explicit `if args.task_command == ...` blocks. When migrating the task family, should this dispatch table be relocated to `cli_commands/task.py`, left in `cli.py`, or abstracted differently? This table currently lives at lines 620–758 in `cli.py` and is not family-specific — it is referenced by the `main()` task dispatch block.

5. **Audit and synthesis families**: Both have `apply_proposal` write paths in `main()` but are not mentioned in the Step 2 headline scope. Should they be migrated opportunistically as small families (combined ~200 lines) or explicitly re-deferred?

6. **Boundary test coverage expansion**: `test_command_boundaries.py` currently covers only `proposals.py` and `meta_optimizer.py`. Step 2 will add new `application/commands/` modules. Codex should decide whether the new modules are added to `COMMAND_MODULES` (source-text boundary checks) or get separate test functions; the LTO-8/LTO-9 discipline says they must be in the regular pytest run.
