---
author: claude
phase: surface-cli-meta-optimizer-split-step2
slice: lto9-step2-pr-review
status: review
depends_on:
  - docs/plans/surface-cli-meta-optimizer-split-step2/plan.md
  - docs/plans/surface-cli-meta-optimizer-split-step2/plan_audit.md
  - docs/plans/surface-cli-meta-optimizer-split-step2/context_brief.md
  - docs/design/INVARIANTS.md
  - docs/design/INTERACTION.md
  - docs/engineering/CODE_ORGANIZATION.md
  - tests/unit/application/test_command_boundaries.py
  - tests/test_invariant_guards.py
---

TL;DR:
The CLI command-family migration landed cleanly. `cli.py` shrank from 3653 → 2672 lines (−981, −27%); 6 application commands and 6 CLI adapter modules carry the new ownership; `apply_proposal(...)` no longer appears in `cli.py` at all (only as a help-string mention); 5 plan_audit concerns are absorbed in code; Codex's full pytest claim of 721 passed reproduces independently. **However, three real issues require attention: (1) a missing `closeout.md`, (2) `pr.md` still contains LTO-10 content not LTO-9 Step 2, and (3) a load-bearing layering smell — `application/commands/tasks.py` reverse-imports `swallow.surface_tools.cli` to reach `run_task`, and `cli_commands/tasks.py` reverse-imports `cli.py` for utility functions.**

Recommendation: **`request-changes`** until closeout / pr.md / one layering smell decision are resolved. None of the three is a runtime correctness bug; all three are documentation/architecture-discipline issues that should not ride into main silently.

# LTO-9 Step 2 PR Review

## Scope

- track: `Architecture / Engineering`
- phase: `LTO-9 Step 2 — broad CLI command-family migration`
- branch: `refactor/cli_command_family_migration`
- base: `main` at `b3f7f43`
- commits reviewed: `b80d3b8`, `5bb4660`, `b067f02`, `cb7ac88`, `470d3ca`, `e7cef69`
- mode: behavior-preserving CLI command-family migration + LTO-5 application/commands write-side coverage
- inputs: `plan.md` (307 lines), `plan_audit.md`, `context_brief.md` (170 lines), full diff `git diff main..HEAD`

## Verdict

`request-changes`. Three issues must be resolved before merge:
- **BLOCKER-1**: missing closeout.md
- **BLOCKER-2**: stale pr.md (still LTO-10 content)
- **CONCERN-1**: reverse-import layering smell in `application/commands/tasks.py`

After these are addressed: `recommend-merge` with the remaining 3 non-blocking concerns.

## Blockers

### [BLOCKER-1] Missing `closeout.md`

**Location:** `docs/plans/surface-cli-meta-optimizer-split-step2/`

**What:** The directory contains `context_brief.md`, `plan.md`, `plan_audit.md`, but no `closeout.md`. Every prior phase in this project (LTO-7, LTO-8 Step 1, LTO-9 Step 1, LTO-10) shipped a final-status closeout describing actual deliverables, deferred items, and validation output. The closeout is the authoritative phase-end summary that future agents read instead of digging through commit history; without it, the LTO-9 Step 2 deliverable boundary is undocumented.

**Why it matters:**
1. `pr.md` is supposed to derive from `closeout.md` — without closeout, `pr.md` cannot be authoritative either.
2. Future post-merge `roadmap-updater` runs read `closeout.md` to update LTO-9 / LTO-5 row state.
3. The "what's actually deferred to the next phase" record is missing — for LTO-9 there is now no successor (LTO-9 closes here in Step 2 form), but for LTO-5 the repository ports / FastAPI write-route deferred items need explicit recording.

**Suggested resolution (before merge):** Codex creates `docs/plans/surface-cli-meta-optimizer-split-step2/closeout.md` with the standard structure (frontmatter, TL;DR, Scope, Completed Milestones, Implementation Notes, Boundary Confirmation, Deferred Work, Validation, Completion Status). Reference points are the prior phase's closeouts in `docs/plans/governance-apply-handler-split/closeout.md` and `docs/plans/surface-cli-meta-optimizer-split/closeout.md`.

---

### [BLOCKER-2] `pr.md` is stale — still describes LTO-10

**Location:** `pr.md` (root of repo)

**What:** The current `pr.md` is the LTO-10 Governance Apply Handler Split PR draft (`This PR implements 'Governance Apply Handler Split / LTO-10' on 'feat/governance-apply-handler-split'`). It was not updated for LTO-9 Step 2. If a PR is opened from this branch using current `pr.md`, the description will be wrong — the title says LTO-10, the slice list is M1 proposal-registry / M2 canonical+policy / etc., none of which match this branch's actual content.

**Why it matters:** This is a publication-side mistake; opening the PR now would publish incorrect context to reviewers.

**Suggested resolution (before merge):** Codex rewrites `pr.md` for LTO-9 Step 2. Reference: `docs/plans/surface-cli-meta-optimizer-split/closeout.md`'s `pr.md` analog, the LTO-10 `pr.md` structure (which is the exact file that needs replacing), and BLOCKER-1's closeout once it lands.

---

## Concerns

### [CONCERN-1] Layering smell — `application/commands/tasks.py` reverse-imports `swallow.surface_tools.cli`

**Location:**
- `src/swallow/application/commands/tasks.py:193` — `state = import_module("swallow.surface_tools.cli").run_task(...)`
- `src/swallow/surface_tools/cli_commands/tasks.py:239` — `def _cli(): return import_module("swallow.surface_tools.cli")`, used at lines 230, 242, etc. for utility functions like `is_mock_remote_task`, `filter_task_states`, `format_*`.

**What:**
1. `application/commands/tasks.py:run_task_command` reaches up into `swallow.surface_tools.cli` to call `run_task`. That `run_task` is itself a re-export — `cli.py:56` does `from swallow.orchestration.orchestrator import run_task`. So the call chain is:
   ```
   application/commands/tasks.py → swallow.surface_tools.cli (re-export shim) → swallow.orchestration.orchestrator.run_task
   ```
   The middle hop is a no-op pass-through that happens to be in `cli.py`. The application layer is supposed to depend on `orchestration` directly, per `docs/engineering/CODE_ORGANIZATION.md` ("`interfaces/cli` / `interfaces/http` -> `application/commands` / `application/queries` -> governance / orchestration / domain").
2. `cli_commands/tasks.py` uses the same `import_module` trick to call back into `cli.py` for utility helpers. This is the same circular-shape relationship in the other direction.

**Why it matters:**
1. Architectural direction: the plan's anchor (CODE_ORGANIZATION §5) says `application/*` must not depend on `surface_tools/*`. The current state inverts that for one call.
2. The `import_module(...)` pattern is a circular-import workaround that hides the dependency graph from static analysis. A future refactor that legitimately removes `cli.run_task` (because it's just a re-export) would silently break `application/commands/tasks.py` at runtime, not at import time.
3. The same pattern in `cli_commands/tasks.py` is more defensible (CLI adapters depending on CLI helpers is at least same-layer), but combined with the application reverse-import the picture is "the tasks family migration left layer boundaries unclear".

**Why non-blocking (but should be addressed):** Tests pass; behavior is preserved; the reverse imports are not a runtime bug. This is a discipline issue. It does, however, defeat one of the explicit Step 2 goals — to land the application/commands layer cleanly so LTO-5 can be considered closed.

**Suggested resolution (preferred path):**
- In `application/commands/tasks.py:run_task_command`, replace `import_module("swallow.surface_tools.cli").run_task(...)` with `from swallow.orchestration.orchestrator import run_task` at the top of the module and call it directly.
- For `cli_commands/tasks.py`, audit each `_cli()` callsite and decide per case: utility functions like `is_mock_remote_task` and `filter_task_states` should likely move into `cli_commands/tasks.py` (or a sibling `cli_commands/_helpers.py`) so the adapter is self-contained, not a back-reference into the parent file. This is a small additional commit, not a re-architecture.
- If Codex prefers to defer the cli_commands/tasks.py side, that is acceptable as a follow-up CONCERN in `concerns_backlog.md`, but the application-layer reverse import (the application → surface_tools direction) should not ship.

---

### [CONCERN-2] LTO-9 Step 1's `cli_commands/route_metadata.py` still calls `apply_proposal` directly — not migrated to the new application command pattern

**Location:** `src/swallow/surface_tools/cli_commands/route_metadata.py:73`, `:149`

**What:** The new `application/commands/route_metadata.py` exists (M2 deliverable) and is correctly used by the new `cli_commands/route.py` for registry/policy/select. But the LTO-9 Step 1 file `cli_commands/route_metadata.py` (which handles `swl route weights apply` and `swl route capabilities update`) still calls `apply_proposal(...)` and `register_route_metadata_proposal(...)` directly — bypassing the application command layer that this very phase introduced. Plan §"Goals" #2 says proposal-governed writes "call existing registration helpers plus `apply_proposal` through application command functions". The Step 1 file violates this for the route_metadata `apply_proposal` callsite (the only such direct callsite in `surface_tools/*` after this phase).

**Why it matters:** This leaves a single oddly-shaped exception to the otherwise consistent pattern. Either:
- the rule is "all CLI-originated `apply_proposal` calls go through `application/commands/*`" (then this file should be migrated), or
- the rule is "Step 1 already-migrated commands keep the inline call" (then plan §Goals #2 should explicitly carve out an exception).

The current state is silent inconsistency.

**Why non-blocking:** Behavior-preserving; the function works. Plan didn't include this file as in-scope for Step 2 either (the M2 acceptance lists "route registry/policy/select", not "route weights/capabilities").

**Suggested resolution:**
- Add a one-line note in the closeout's Deferred Work section: "LTO-9 Step 1's `cli_commands/route_metadata.py` (`route weights apply` / `route capabilities update`) retains direct `apply_proposal` calls; harmonization with the application command pattern is deferred to a touched-surface future change."
- Do NOT migrate now — that's scope creep beyond the plan.

---

### [CONCERN-3] `cli.py:1099` still has a help-string mention of `apply_proposal` for a now-deleted dispatch path

**Location:** `src/swallow/surface_tools/cli.py:1099` — `help="Update an MPS policy value via apply_proposal."`

**What:** The argparse help text for `swl synthesis policy set` still says "via `apply_proposal`". The dispatch is now in `application/commands/policies.py` (which does in fact call `apply_proposal`), so the help string is technically still true. But it's a leftover phrasing from when `cli.py` itself called `apply_proposal`; users do not need to know this implementation detail and it's the only `apply_proposal` mention left in `cli.py`.

**Why it matters:** Minor cosmetic. Future grep for `apply_proposal` in `cli.py` will continue to surface this string and confuse readers into thinking the migration is incomplete.

**Why non-blocking:** Help text only; no functional impact.

**Suggested resolution:** Optional. Either rephrase to "Update an MPS policy value (governed write)." or leave it. This is an editorial decision, not an architectural one.

---

### [CONCERN-4] `tests/unit/application/test_command_boundaries.py` uses a `PLANNED_COMMAND_MODULES` "optional" pattern that will silently skip if a future module is renamed

**Location:** `tests/unit/application/test_command_boundaries.py:12-19`

**What:** The boundary test divides modules into `COMMAND_MODULES` (always required) and `PLANNED_COMMAND_MODULES` (filtered through `_existing_command_modules` which returns only modules whose files actually exist). This was useful during M2-M5 migration where `application/commands/{tasks,knowledge,route_metadata,policies,synthesis,ingestion}.py` did not all exist yet. After M5, all six should be promoted to `COMMAND_MODULES` so a future rename or accidental deletion fails the test instead of silently passing.

**Why it matters:** Right now if someone deletes `application/commands/tasks.py` (or renames it), `_existing_command_modules()` simply omits it and the boundary test passes. The intent of boundary tests is to fail loudly when a load-bearing module disappears.

**Why non-blocking:** All six files exist today; tests do enforce the boundary on them. This is a hardening-after-migration cleanup.

**Suggested resolution:** After closeout, move `tasks.py`, `knowledge.py`, `route_metadata.py`, `policies.py`, `synthesis.py` from `PLANNED_COMMAND_MODULES` into `COMMAND_MODULES`. `ingestion.py` does not exist (Codex chose not to create it; ingestion logic stayed in `knowledge.py`) — remove that entry from `PLANNED_COMMAND_MODULES` rather than leave it as a permanent skip. This is one small commit, can be in the same closeout commit as BLOCKER-1.

---

## Validation

I independently re-ran the validation gates on the working tree (matching `e7cef69`):

- `.venv/bin/python -m pytest -q` — **721 passed, 8 deselected, 10 subtests passed** (matches Codex's claim, +19 tests vs LTO-10's 702 baseline — these are the new boundary + integration tests).
- `git diff --check` — clean.
- All 5 plan_audit concerns verified absorbed in code:

| plan_audit concern | Where absorbed | Verified |
|---|---|---|
| C-1 `canonical-reuse-evaluate` / `consistency-audit` M4 placement | M4 / M5 split: `evaluate_task_canonical_reuse_command` and `run_task_consistency_audit_command` are in `application/commands/tasks.py` lines 315-344 (write side, M4) | ✓ |
| C-2 `stage-reject` not via `apply_proposal` | `application/commands/knowledge.py:174-184` `reject_stage_candidate_command` directly calls `update_staged_candidate(...)`; M3 boundary test `MODULE_PRIVATE_WRITER_TOKENS["application/commands/knowledge.py"]` correctly prohibits canonical writers but permits staged-knowledge helper | ✓ |
| C-3 `apply-suggestions` not via `apply_proposal` | `application/commands/knowledge.py:220-222` `apply_relation_suggestions_command` calls `apply_relation_suggestions` directly; same boundary scope as C-2 | ✓ |
| C-4 `apply_proposal` migration same-commit rule | All `apply_proposal(...)` direct calls removed from `cli.py` in the same commit as the new application/commands modules. `grep` confirms zero direct `apply_proposal(` calls in `cli.py` post-merge (only a help-string reference at line 1099). | ✓ |
| C-5 baseline-pre-migration gate per milestone | Each migration commit (`b067f02`, `cb7ac88`, `470d3ca`, `e7cef69`) follows commit `5bb4660 test(cli): characterize broad command families` which seeded all family characterization tests first. Commit ordering enforces the discipline. | ✓ |

I also verified:

- `test_state_transitions_only_via_orchestrator` (`tests/test_invariant_guards.py:416`) allowlist still contains exactly `{orchestrator.py, sqlite_store.py, store.py}` — **no broadening to application/commands** (M4 acceptance constraint preserved).
- `application/commands/tasks.py` boundary token list (`save_state`, `_promote_canonical`, `_apply_metadata_change`, `_apply_policy_change`) confirmed in `MODULE_PRIVATE_WRITER_TOKENS`.
- `cli.py` zero direct `apply_proposal(` calls (only the help string at line 1099).
- `cli.py` size: 3653 → 2672 lines (`-981`, `-27%`). Plan said this would be "shrinking dispatch ownership" — confirmed.
- 6 new application command modules (`tasks`, `knowledge`, `route_metadata`, `policies`, `synthesis` + Step 1's `proposals`, `meta_optimizer`); 6 cli adapter modules (`tasks`, `knowledge`, `route`, `audit`, `synthesis` + Step 1's `meta_optimizer`, `proposals`, `route_metadata`).
- 5 new integration test files (`test_audit_commands`, `test_knowledge_commands`, `test_route_family_commands`, `test_task_commands`, expanded `test_synthesis_commands`).
- `tests/test_cli.py` did not grow for new behavior — confirmed via diff stat (untouched).
- `web/api.py` unchanged — confirmed no FastAPI write route added (plan non-goal preserved).

## Recommendations

1. **Before merge — required:**
   - **(BLOCKER-1)** Create `docs/plans/surface-cli-meta-optimizer-split-step2/closeout.md` per the standard structure.
   - **(BLOCKER-2)** Rewrite `pr.md` for LTO-9 Step 2 (LTO-10 content must be replaced).
   - **(CONCERN-1)** Replace `application/commands/tasks.py:193` `import_module("swallow.surface_tools.cli").run_task` with a direct `from swallow.orchestration.orchestrator import run_task` import. The `cli_commands/tasks.py:_cli()` reverse-import can be deferred to follow-up but should be acknowledged in closeout.

2. **Optional polish (non-blocking, defer or fold into closeout commit):**
   - **(CONCERN-2)** Add a closeout note acknowledging that LTO-9 Step 1's `cli_commands/route_metadata.py` direct `apply_proposal` calls are intentionally not harmonized in this phase.
   - **(CONCERN-3)** Optionally rephrase `cli.py:1099` help text to remove the `apply_proposal` mention.
   - **(CONCERN-4)** Promote the 5 existing application command modules from `PLANNED_COMMAND_MODULES` to `COMMAND_MODULES` and remove the never-created `ingestion.py` entry.

3. **Tag decision:** Continue deferring `v1.6.0` until LTO-8 Step 2 lands. LTO-9 Step 2 is behavior-preserving; bundling with LTO-8 Step 2's harness decomposition gives `v1.6.0` a single coherent "cluster C closure" narrative.

4. **LTO-5 status note:** With LTO-9 Step 2 merged, the application/commands write side is effectively complete for all CLI-originated commands. Per the user's earlier direction, FastAPI write-route work will be split into a new dedicated LTO entry in the post-merge roadmap update; LTO-5 then collapses to "Repository Ports — defer until real cross-backend trigger" status.

5. **Roadmap update after merge:** When `roadmap-updater` runs post-merge, it should:
   - Mark LTO-9 row as "Step 2 已完成 (cluster C 余项 LTO-8 Step 2 待启动)".
   - Update LTO-5 row to reflect application/commands closure; note repository ports as the remaining follow-up.
   - Promote LTO-8 Step 2 to current ticket (the LTO-8 Step 2 context_brief is already on disk).
   - Apply the agreed-upon FastAPI single-list change (new dedicated LTO entry) — this is a separate human-direction step we discussed but parked until phase completion.

## Acknowledgements

Five-milestone migration discipline held throughout: characterization tests landed in M1 before any production move, each subsequent milestone's commit followed its own family's baseline tests, all 5 plan_audit concerns absorbed in code, no cross-family scope creep, all non-goals preserved (no FastAPI write routes, no new mutation entry, no schema change, `test_state_transitions_only_via_orchestrator` allowlist not broadened). The `cli.py` reduction from 3653 to 2672 lines is the largest single-phase facade reduction the project has shipped. Once the three load-bearing items (closeout, pr.md, application reverse-import) are addressed, this PR closes LTO-9 cleanly.
