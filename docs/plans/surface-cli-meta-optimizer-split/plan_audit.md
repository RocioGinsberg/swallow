---
author: claude
phase: surface-cli-meta-optimizer-split
slice: plan-audit
status: draft
depends_on:
  - docs/plans/surface-cli-meta-optimizer-split/plan.md
  - docs/design/INVARIANTS.md
  - docs/design/INTERACTION.md
  - docs/design/SELF_EVOLUTION.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/GOF_PATTERN_ALIGNMENT.md
  - docs/engineering/TEST_ARCHITECTURE.md
  - docs/roadmap.md
  - docs/concerns_backlog.md
  - docs/plans/architecture-recomposition/plan.md
  - docs/plans/provider-router-split/review_comments.md
  - docs/plans/orchestration-lifecycle-decomposition/review_comments.md
---

TL;DR:
Plan scope is well-controlled for LTO-9: 5 milestones, targets correct in-scope surface, LTO-7 follow-up CONCERN-1 is explicitly absorbed. The critical invariant risk (Meta-Optimizer role) is correctly framed. Three concerns require Codex attention before implementation: (1) the read-only boundary enforcement mechanism in M2 needs a source-text guard equivalent to LTO-8's save_state check; (2) application/commands must be explicitly prohibited from formatting terminal output by a testable rule, not just prose; (3) M4's query-tightening scope trigger is conditional and may be dropped silently without a clear go/no-go rule. No BLOCKER found.

# Plan Audit: Surface / CLI / Meta Optimizer Split (LTO-9)

## 1. Scope Discipline (LTO-9 critical)

**Assessment: [PASS] with one [CONCERN]**

- [PASS] Goals (1–6) are bounded: application/commands seed, Meta-Optimizer split, CLI adapter split for proposal/meta-optimize/route subset, LTO-7 CONCERN-1 fix, facade closeout. Not pushing to full task/knowledge/artifact CLI migration.
- [PASS] Non-Goals explicitly exclude: full task/knowledge command migration, new FastAPI write APIs, new proposal target kinds, governance semantics changes, schema migrations, Provider Router behavior changes, LTO-1 Wiki Compiler.
- [PASS] Slice count is exactly 5 (M1–M5), consistent with LTO-7/LTO-8 discipline.
- [PASS] LTO-10 governance handler split is not touched; `apply_proposal` remains the only public mutation entry.
- [PASS] No Provider Router work (LTO-7 already done). The plan correctly says the M4 allowlist fix is about updating allowlist ownership, not changing the protected writer set.
- [CONCERN] M3 scope says "extract the meta-optimize, proposal, and the route metadata apply/show subset". The phrase "route metadata apply/show subset" is not explicitly bounded by file or command name. If Codex interprets this as including `swl route weights`, `swl route capabilities`, and related sub-commands broadly, M3 could expand significantly. The Non-Goals say "do not move all task / knowledge / artifact CLI commands" but does not specifically cap which route-metadata commands are in scope. Recommend Codex explicitly enumerate the in-scope `swl` subcommands for M3 (at minimum: `swl proposal review`, `swl proposal apply`, `swl meta-optimize`, and the specific route-metadata commands the meta-optimizer interacts with), to prevent M3 growing into a general route-command migration.

## 2. LTO-7 Follow-up Absorption (allowlist drift)

**Assessment: [PASS]**

- [PASS] CONCERN-1 from `docs/concerns_backlog.md` (Provider Router Split LTO-7 follow-up group item 1) is explicitly listed as a goal in the plan (Goal 6) and expanded in the Design And Engineering Anchors section.
- [PASS] M4 Acceptance criteria include: "The route metadata guard no longer carries the LTO-7 allowlist drift described in `docs/concerns_backlog.md`." This is a concrete, testable acceptance criterion.
- [PASS] M4 Scope correctly specifies the fix direction: make `route_metadata_store.py` the explicit physical writer owner and document any `provider_router/router.py` wrappers that still require special handling, rather than silently broadening the allowlist.
- [PASS] The fix is not mixed into CLI adapter churn (M3 handles CLI, M4 handles guard fix) — correct separation per plan §Branch And PR Recommendation.
- [PASS] Roadmap `§三` "默认下一步" requirement is fully absorbed.

## 3. CLI Behavior Preservation

**Assessment: [PASS] with one [CONCERN]**

- [PASS] Non-Goals explicitly state no redesign of CLI UX, command names, flags, exit codes, or output formats.
- [PASS] M3 Acceptance criteria verify: "Top-level `swl --help` still lists the same command names and help wording for in-scope commands" and "preserve current output and exit codes."
- [PASS] M5 Acceptance criteria verify public CLI behavior remains compatible end-to-end.
- [PASS] Compatibility facades for `swallow.surface_tools.cli.main`, `build_parser`, and `swallow.surface_tools.meta_optimizer` public imports are explicitly maintained.
- [PASS] The plan uses the same characterization-test-first pattern used in LTO-7 (move/add tests before or with each extraction).
- [CONCERN] The plan does not explicitly call for characterization tests at the M3 entry gate — that is, snapshot/golden tests capturing current `swl proposal review`, `swl proposal apply`, `swl meta-optimize`, and in-scope route command output before any code is moved. LTO-7 used characterization tests in `tests/unit/provider_router/` to freeze behavior before decomposition. For CLI output behavior, the equivalent would be thin integration tests capturing stdout/stderr/exit codes for the in-scope commands against a minimal fixture workspace. These tests should exist or be written in M3 before any dispatch code is moved. The plan implies this ("Move tests before or with each command-family extraction") but does not make it an explicit M3 precondition. If Codex skips the before-move step and moves tests simultaneously, a behavior regression could be introduced and immediately masked by the relocated assertions. Recommend making the pre-extraction baseline assertion step explicit in M3 scope or acceptance.

## 4. CLI Test Architecture Alignment

**Assessment: [PASS]**

- [PASS] Plan explicitly references `TEST_ARCHITECTURE.md §5` standard: "New CLI tests should move into `tests/integration/cli/` when touched."
- [PASS] M3 Scope enumerates the target files: `test_proposal_commands.py`, `test_route_commands.py`, `test_meta_optimizer_commands.py` under `tests/integration/cli/`.
- [PASS] M3 Acceptance criteria include: "New CLI tests live under `tests/integration/cli/`; root `tests/test_cli.py` does not grow for touched behavior." This is testable.
- [PASS] The plan correctly constrains the migration: "Do not move unrelated task / knowledge command blocks unless the implementation proves a small shared helper move is necessary" — avoids turning M3 into a broad `test_cli.py` migration.
- [PASS] Validation plan includes both `tests/test_cli.py -k "proposal or meta_optimizer or route_capabilities or route_weights or serve"` and `tests/integration/cli -q`, confirming the split is tested at the gate.

## 5. application/commands Boundary Setting (LTO-5 advancement)

**Assessment: [PASS] with one [CONCERN]**

- [PASS] Plan correctly frames application/commands as a shared layer used by both CLI and FastAPI: "CLI adapter modules may format output and map `argparse.Namespace` fields, but should not become business logic owners."
- [PASS] Boundary Rules explicitly state: "Application command functions may call Orchestrator or governance functions, but must not format terminal output." This is the correct division analogous to CODE_ORGANIZATION.md §2 Layer Duties.
- [PASS] `application/commands/proposals.py` is correctly defined to call the existing governance API via `apply_proposal(OperatorToken(source="cli"))` — no second public mutation entry.
- [PASS] `application/commands/meta_optimizer.py` returns "structured CLI-ready results without formatting terminal output" — correct adapter-layer separation.
- [PASS] `web/api.py` is constrained to read-only unless a later plan revision explicitly introduces write commands — prevents FastAPI from becoming a hidden business layer.
- [CONCERN] The Boundary Rules state "Application command functions... must not format terminal output" as a prose rule, but there is no analogous automated enforcement check planned (unlike LTO-8's `assert "save_state" not in source` per-helper source-text tests). An application/commands module that accidentally imports `click` or contains ANSI escape sequences would violate this rule but pass all functional tests. Recommend adding a source-text boundary check (e.g., `assert "click" not in source`, `assert "rich" not in source`, `assert "\033[" not in source`) as part of the M1 unit test for `application/commands/proposals.py` and `application/commands/meta_optimizer.py`. This is the direct LTO-8 lesson applied: source-text checks catch the class of violations that import-AST guards cannot.

## 6. Meta Optimizer Boundary

**Assessment: [PASS]**

- [PASS] Plan correctly identifies the invariant-critical split: Meta-Optimizer is a proposer/read-only specialist; Operator proposal review/apply lives in application commands, not in the agent execution path.
- [PASS] M2 Acceptance criteria include an explicit grep check: `rg -n "apply_proposal|save_state|_apply_metadata_change|save_route_weights|save_route_capability_profiles" src/swallow/surface_tools/meta_optimizer_*.py` must have no hits in read-only modules. This is a concrete, runnable boundary check.
- [PASS] `surface_tools/meta_optimizer_agent.py` is explicitly scoped to: "read-only MetaOptimizer agent/executor adapter; must not import or call `apply_proposal`." This is the INVARIANTS §5 Truth writes matrix constraint for Meta-Optimizer (`truth_writes = {event_log, proposal_artifact}`; no route/policy write).
- [PASS] `MetaOptimizerAgent` implementation module has no `apply_proposal` reference — this is an M2 Acceptance criterion.
- [PASS] The plan does not introduce a new `truth_writes` permission or new public mutation entry for Meta-Optimizer.
- [PASS] SELF_EVOLUTION.md §6.1 constraint ("Only reads: event truth, route telemetry; Outputs: proposal artifacts") is preserved by the module split design: snapshot.py and proposals.py are read-only, lifecycle.py manages bundle IO, reports.py does rendering.
- [PASS] The plan acknowledges that `meta_optimizer_lifecycle.py` (bundle load/save and proposal review record serialization) "if not moved into application commands" — this hedge is correctly conservative; the lifecycle IO around proposal bundles is not a Truth write and does not need to be in application commands.

## 7. Invariant Boundary

**Assessment: [PASS]**

- [PASS] `apply_proposal` remains the only canonical/route/policy mutation entry. Plan explicitly prohibits `application/commands/proposals.py` from introducing "a second public canonical / route / policy mutation entry."
- [PASS] `OperatorToken(source="cli")` is correctly specified for the proposal apply path — consistent with SELF_EVOLUTION.md §3.1.1.
- [PASS] INVARIANTS §5 Truth writes matrix respected: Meta-Optimizer stays as proposer-only (`truth_writes = {event_log, proposal_artifact}`), no route/policy write authority.
- [PASS] INVARIANTS §0 "Control only in Orchestrator / Operator" preserved: the CLI adapter remains the Operator's surface; application commands do not gain independent state-advancement authority.
- [PASS] INVARIANTS §0 "Execution never directly writes Truth" preserved: `surface_tools/meta_optimizer_agent.py` is constrained from calling `apply_proposal`, `save_state`, or repository private methods.
- [PASS] INTERACTION.md §4.2.1 constraint preserved: `web/api.py` must remain read-only; no new FastAPI write endpoint.
- [PASS] No Path A/B/C semantic changes. Meta-Optimizer uses Path C (Specialist Internal → Provider Router). This is unchanged.
- [PASS] No schema migration planned. Proposal record formats `meta_optimizer_proposal_review_v1` and `meta_optimizer_proposal_application_v1` are preserved.

## 8. Milestone / Slice Executability

**Assessment: [PASS] with one [CONCERN]**

- [PASS] M1, M2, M3 are sequenced correctly: M1 creates application/commands foundation before M3 extracts CLI adapters that will call it. M2 splits Meta-Optimizer read-only internals independently.
- [PASS] M4 (guard fix + query tightening) correctly decoupled from M3 (CLI adapter churn) per §Branch And PR Recommendation.
- [PASS] M5 (facade cleanup) is correctly gated on M1–M4 completion — only removes dead private wrappers when "import compatibility is proven."
- [PASS] Each milestone has concrete Acceptance criteria. The acceptance criteria reference specific test files and commands, not vague qualities.
- [PASS] The Target Module Shape table names specific file paths, which is sufficient for Codex to start coding without another planning pass.
- [CONCERN] M4 Scope says "Move low-risk read-only Control Center payload builders from `surface_tools/web/api.py` into `application/queries/` **if** the move keeps `web/api.py` a thinner adapter without widening scope." The "if" here introduces a conditional scope that has no explicit go/no-go decision point. If Codex evaluates the move at M4 time and decides it widens scope, the entire query-tightening part of M4 might be skipped, and only the allowlist fix gets done. That outcome is acceptable, but M4's Acceptance criteria do not reflect this — they include `tests/test_web_api.py -q` as a milestone gate regardless. Recommend adding explicit language: either (a) the query tightening move is optional-if-safe (and the acceptance criteria drop the web API restructuring assertion), or (b) the conditional is resolved during plan gate based on a code review of `web/api.py` payload builders, so it is not a runtime decision during implementation. As written, M4's scope is slightly ambiguous about what "done" looks like if the optional move is skipped.

## 9. LTO-7 / LTO-8 Lessons Applied

**Assessment: [PASS] with one [CONCERN]**

**LTO-7 lessons:**

- [PASS] Guard allowlist drift is addressed explicitly (M4, Goal 6) — the primary LTO-7 lesson applied correctly.
- [PASS] The plan requires updating the guard's allowlist to reflect actual writer ownership, not just patching the test to pass. The direction (make `route_metadata_store.py` the explicit physical writer owner) is correct.
- [PASS] New modules (`meta_optimizer_*.py`, `cli_commands/`) will not be in the `test_state_transitions_only_via_orchestrator` allowlist by default — correct security posture (same as LTO-8 lesson).
- [PASS] Cross-layer import audit: the plan correctly constrains `surface_tools/meta_optimizer_agent.py` from importing `apply_proposal` or repository private methods — this is the cross-layer import direction guard for the Meta-Optimizer boundary.

**LTO-8 lessons:**

- [PASS] Closure-injection of mutating callables: the plan's application/commands boundary rule ("must not format terminal output"; proposal apply only from Operator command path) is structurally analogous to the save_state closure prohibition. The plan does not introduce a callable-injection pattern between CLI adapter and application commands.
- [PASS] Conservative is right: the plan explicitly defers full task/knowledge/artifact CLI migration ("later LTO-9 or touched-surface phases"), following LTO-8's "Step 1 not Final" posture.
- [CONCERN] LTO-8 introduced source-text checks in per-module unit tests (assert "save_state" not in source) as the strongest enforcement layer for the boundary prohibition that AST guards cannot catch. The LTO-9 plan's M2 uses a grep command in the acceptance criteria (`rg -n "apply_proposal|save_state..."`) but does not require this check to live inside a unit test as a persistent guard. If the rg command is only run manually at M2 gate time, future code changes to `meta_optimizer_*.py` modules could silently reintroduce prohibited references without a test catching it. The LTO-8 lesson is: put the grep-equivalent inside a focused unit test file (`tests/unit/surface_tools/test_meta_optimizer_module.py` or similar) so it runs with every full pytest. Recommend Codex add source-text boundary assertions as actual test cases (not just milestone gate commands) for the read-only meta_optimizer modules.

## 10. Phase-Guard (Scope vs Program Plan)

**Assessment: [PASS]**

- [PASS] Program plan (`docs/plans/architecture-recomposition/plan.md`) authorizes LTO-9 as the surface/CLI/meta-optimizer subtrack. This plan is correctly scoped to that authorization.
- [PASS] LTO-10 (Governance apply handler split) is not touched. `apply_proposal` private handlers remain undisturbed.
- [PASS] LTO-8 follow-up (harness.py decomposition, further orchestrator.py reduction) is not touched.
- [PASS] LTO-1 (Wiki Compiler) is not touched.
- [PASS] LTO-7 carryover (CONCERN-2 `_apply_route_policy_payload` private name leak, CONCERN-3 `_BUILTIN_ROUTE_FALLBACKS` relocation) is not addressed — correct, because those are hygiene items deferred to touched-surface basis, and this plan only touches route metadata guard ownership (CONCERN-1).
- [PASS] No new LLM call paths, no new Provider Router selection logic, no new debate-loop patterns.
- [PASS] Slice count of 5 respects the program plan discipline.

## 11. BLOCKER Summary

None found. Plan is implementable as written with the concerns below addressed.

## 12. CONCERN Summary (must address before or during implementation)

| # | Milestone | Severity | Description | Recommended Fix |
|---|-----------|----------|-------------|-----------------|
| C-1 | M3 | CONCERN | "Route metadata apply/show subset" is not bounded by specific `swl` subcommand names. | Enumerate in-scope `swl` subcommands explicitly in M3 Scope (e.g., `swl proposal review`, `swl proposal apply`, `swl meta-optimize`, plus list specific route subcommands). |
| C-2 | M3 | CONCERN | No explicit pre-extraction baseline assertion step (characterization tests capturing stdout/stderr/exit codes before any dispatch code is moved). | Add an explicit M3 precondition: write or verify integration assertions for all in-scope commands against a fixture workspace **before** any dispatch code is extracted, not simultaneously. |
| C-3 | M1 | CONCERN | "Application command functions must not format terminal output" is a prose rule with no automated enforcement. | Add source-text boundary assertions (e.g., assert no `click`/`rich`/ANSI imports) as actual unit tests for `application/commands/proposals.py` and `application/commands/meta_optimizer.py`, analogous to LTO-8's per-helper `"save_state" not in source` checks. |
| C-4 | M4 | CONCERN | M4 query-tightening move is conditional ("if the move keeps `web/api.py` a thinner adapter") with no explicit go/no-go rule, yet acceptance criteria imply a fixed scope. | Add explicit language: either declare the move optional (and mark its acceptance criteria as optional), or resolve the conditional at plan gate time via a quick `web/api.py` payload builder audit. |
| C-5 | M2 | CONCERN | The `rg` read-only boundary check in M2 Acceptance is a manual gate step, not a persistent test. Future changes to `meta_optimizer_*.py` won't be caught by CI. | Add source-text boundary assertions as actual test cases in a focused unit test file (e.g., `tests/unit/surface_tools/test_meta_optimizer_boundary.py`), so the grep runs inside every full pytest run. |

## 13. PASS Summary

- LTO-7 follow-up CONCERN-1 (allowlist drift) absorbed — explicit, correctly scoped.
- Meta-Optimizer role boundary correctly framed: proposer-only, read-only modules, Operator apply path separated.
- `apply_proposal` invariant boundary correctly maintained throughout.
- CLI behavior preservation criteria are concrete and testable.
- CLI test architecture alignment with `TEST_ARCHITECTURE.md §5` is explicit (new files named, old file not to grow).
- application/commands correctly defined as shared layer (CLI + FastAPI converge).
- 5-milestone structure respects program plan discipline; no LTO-10 / LTO-8-follow-up / LTO-1 scope creep detected.
- Facade-first migration discipline applied: compatibility facades retained for both `cli.py` and `meta_optimizer.py`.
- Risks and Controls table covers the key vectors (big-bang rewrite prevention, import compatibility, guard weakening).

## 14. Overall Conclusion

**Verdict: has-concerns — 5 slices audited (M1–M5), 5 concerns found, 0 blockers**

**Recommended path: address C-3 and C-5 by adding enforcement tests to M1 and M2 acceptance criteria; address C-1 by enumerating in-scope subcommands in M3 scope; address C-2 by making the pre-extraction baseline step explicit in M3 preconditions; address C-4 by resolving the M4 conditional. Then proceed to implementation.**

The plan is structurally sound and well-aligned with both the project constitution and the lessons from LTO-7/LTO-8. The concerns are implementation-discipline gaps — not design errors — and can be absorbed directly into the plan before or early in implementation without a plan rewrite. Codex can start M1 once C-3 is absorbed (add source-text test assertion to M1 acceptance). M2 can start once C-5 is absorbed (add boundary test to M2 acceptance). M3 can start once C-1 and C-2 are absorbed (enumerate subcommands and add baseline assertion precondition). M4 can start with C-4 resolved as a go/no-go statement.

The LTO-9 invariant risk is correctly framed and mitigated: the plan neither weakens `apply_proposal` nor blurs the Meta-Optimizer proposer role. No SCOPE WARNING is required.
