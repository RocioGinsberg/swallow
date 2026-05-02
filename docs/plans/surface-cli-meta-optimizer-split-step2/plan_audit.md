---
author: claude
phase: surface-cli-meta-optimizer-split-step2
slice: lto9-step2-plan-audit
status: review
depends_on:
  - docs/plans/surface-cli-meta-optimizer-split-step2/plan.md
  - docs/plans/surface-cli-meta-optimizer-split-step2/context_brief.md
  - docs/design/INVARIANTS.md
  - docs/design/INTERACTION.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/TEST_ARCHITECTURE.md
---

TL;DR: has-concerns — 5 slices audited, 0 blockers, 5 concerns found.
Plan is implementable as written. The concerns are silent correctness traps rather than ambiguities: two commands are misclassified between M4 and M5; `stage-reject` and `apply-suggestions` use direct writes without `apply_proposal` and need explicit acknowledgement in the plan; the same-commit rule for removing `apply_proposal` from `cli.py` is implied but not stated; and the M3 `stage-reject` path is incompletely described in the acceptance criteria.

## Audit Verdict

Overall: has-concerns

No slices are blocked. All concerns are of the type "implementer will need to make an assumption" — they are resolvable by a short plan annotation, not a redesign.

---

## Blockers

None.

---

## Concerns

### CONCERN-1: `canonical-reuse-evaluate` and `consistency-audit` are misclassified in M4

Location: `plan.md §M4 Acceptance` — scope list for `application/commands/tasks.py`.

Issue: Both `canonical-reuse-evaluate` and `consistency-audit` appear in the M4 write-command scope list. Code inspection shows `canonical-reuse-evaluate` calls `evaluate_task_canonical_reuse()` from `orchestrator.py` (which writes artifacts, events, and canonical reuse regression baselines) and `consistency-audit` calls `run_consistency_audit()` from `surface_tools/consistency_audit.py` (which invokes an LLM audit and writes an artifact). These ARE write/mutate commands — the classification as M4 is architecturally correct. However, neither function is in the brief's explicit M4 list (brief §2 names only `create`, `run`, `retry`, `resume`, `rerun`, `acknowledge`, `planning-handoff`, `knowledge-capture`, `knowledge-promote`, `knowledge-reject` as write). The plan's M4 scope list adds them without comment, while the brief §2 explicitly left them in the read section. An implementer reading the brief and plan together will notice the discrepancy and may move them back to M5.

Why it matters: If Codex follows the brief's classification and moves `canonical-reuse-evaluate` and `consistency-audit` to M5 as reads, they will land in a CLI adapter without an `application/commands/tasks.py` home, weakening the application command boundary for orchestrator-entry-point write actions.

Suggested resolution: Add one sentence to the M4 scope section confirming that `canonical-reuse-evaluate` and `consistency-audit` belong in M4 because they call Orchestrator / domain write functions (`evaluate_task_canonical_reuse`, `run_consistency_audit`) even though they look like read commands by name. This removes the ambiguity without restructuring the milestone split.

---

### CONCERN-2: `stage-reject` calls `update_staged_candidate` directly — not through `apply_proposal`

Location: `plan.md §M3 Acceptance` — "No direct `apply_proposal(` call remains in `surface_tools/cli.py` for `knowledge stage-promote`."

Issue: The M3 acceptance criteria correctly target `stage-promote` (which calls `register_canonical_proposal` + `apply_proposal`). However, `stage-reject` currently calls `update_staged_candidate(...)` directly from `cli.py:main()` — this is a direct staged knowledge writer, not going through `apply_proposal`. The plan's M3 scope lists `stage-reject` as a write command for `application/commands/knowledge.py`, but the acceptance criteria only check for `apply_proposal` removal. There is no acceptance criterion verifying that the application command for `stage-reject` does NOT call `update_staged_candidate` directly.

Why it matters: `update_staged_candidate` in `staged_knowledge.py` does a full file rewrite of the staged knowledge registry. If `application/commands/knowledge.py::reject_staged(...)` calls it directly, the knowledge command module is a private writer — violating the boundary established in M3's own source-text prohibition. The module-specific source-text guard (M3 already prohibits `append_canonical_record`, `persist_wiki_entry_from_record`, `_promote_canonical`) should also prohibit `update_staged_candidate` from appearing in the application command module, since staged knowledge mutation without a proposal registration is architecturally distinct from the `apply_proposal` path.

Suggested resolution: Either (a) add `update_staged_candidate` to the M3 source-text prohibition list for `application/commands/knowledge.py`, or (b) add a brief note clarifying that `stage-reject` is intentionally permitted to call `update_staged_candidate` directly because reject does not require a canonical proposal registration. Either choice is implementable; the plan just needs to be explicit so Codex doesn't have to guess.

---

### CONCERN-3: `apply-suggestions` calls a private knowledge writer directly — M3 boundary guard is incomplete

Location: `plan.md §M3 Acceptance` — source-text prohibition list for `application/commands/knowledge.py`.

Issue: `swl knowledge apply-suggestions` currently calls `apply_relation_suggestions(base_dir, task_id, ...)` from `knowledge_retrieval/knowledge_suggestions.py`. That function calls `create_knowledge_relation(...)` directly — it is not gated by `apply_proposal`. The M3 acceptance lists `apply-suggestions` as a write command for `application/commands/knowledge.py`, but the acceptance criteria's source-text prohibition only covers `append_canonical_record`, `persist_wiki_entry_from_record`, and `_promote_canonical`. The function `create_knowledge_relation` (a direct relation writer) is not on the prohibition list.

Why it matters: If `application/commands/knowledge.py` calls `apply_relation_suggestions` (and therefore transitively calls `create_knowledge_relation`), the knowledge application command module becomes a caller of a private domain writer. This would fail the spirit of the boundary test even if no listed token is found. The `test_proposal_commands_use_governance_boundary_not_route_store_writers` pattern in `test_command_boundaries.py` explicitly prohibits private writer tokens; an analogous check for knowledge commands needs to know which private writers to name.

Suggested resolution: Add `create_knowledge_relation` to the M3 source-text prohibition in `application/commands/knowledge.py` if the intent is for `apply-suggestions` to route through a higher-level function, or add an explicit note clarifying that `apply_relation_suggestions` is an accepted path because knowledge relation writes are not governed by `apply_proposal` (no `ProposalTarget.KNOWLEDGE_RELATION` exists). Either way, the acceptance criteria for M3 needs the same `why is this permitted` / `prohibited` clarity that `stage-promote` receives.

---

### CONCERN-4: Same-commit rule for `apply_proposal` removal from `cli.py` is not stated explicitly

Location: `plan.md §M2 Acceptance` — "No remaining direct `apply_proposal(` call in `surface_tools/cli.py` for route registry/policy, audit policy, or synthesis policy."

Issue: The M2 acceptance says the call must be gone from `cli.py`. It does not say the removal must happen in the same commit as the addition to `application/commands/*`. Step 1 audit CONCERN-3 surfaced the analogous rule for guard allowlists. For callsite migration, the same-commit rule matters more: if Codex removes the call from `cli.py` in one commit and adds it to the application command in a later commit, there is a window where the operation is silently broken (no `apply_proposal` call anywhere, no test failure because the characterization tests may pass if the output path is unchanged for a read-like code path). The `tests/test_invariant_guards.py:test_canonical_write_only_via_apply_proposal` allowlist guard is the backstop, but it is not verified to cover `application/commands/policies.py` or `application/commands/route_metadata.py` by name — those modules do not exist yet, so the allowlist will need updating when they are added.

Why it matters: A two-commit migration of `apply_proposal` callsites is a silent correctness gap. The invariant guard may catch it if allowlist maintenance is done correctly, but the plan does not tell Codex to update the allowlist atomically with the module creation.

Suggested resolution: Add a sentence to M2 acceptance: "Removing the `apply_proposal(` call from `cli.py` and adding it to the new `application/commands/*` module must occur in the same commit. Add new module paths to `tests/test_invariant_guards.py` allowlists (`test_canonical_write_only_via_apply_proposal`, `test_only_apply_proposal_calls_private_writers`) in the same commit as module creation."

---

### CONCERN-5: M1 baseline-tests-exist gate is acceptance-only, not enforced by milestone ordering

Location: `plan.md §M1 Acceptance` — "No production dispatch code is moved before baseline tests for that family exist."

Issue: M1 acceptance correctly requires characterization tests pass on pre-migration code. However, the plan states this as an M1 acceptance condition rather than as a precondition check embedded in each subsequent milestone's acceptance. M2, M3, M4, and M5 do not individually restate "baseline tests for this family must already pass on pre-migration code before any dispatch code in this family is touched." If Codex implements M2 and defers writing the characterization test file (perhaps because the synthesis test file needs a fixture that doesn't exist yet), the M2 acceptance will still pass because focused synthesis CLI tests are listed as a gate but the "on pre-migration code" verification window has already closed.

Why it matters: This is the same pattern that Step 1 audit CONCERN-2 flagged. The fix is the same: each milestone's acceptance should carry a line like "characterization test file for [family] passes on pre-migration code; this test file must have been committed before any dispatch code for this family was moved." M1 creates the tests but the verification that they run green against the old code must be checked at the boundary of each family's migration, not only at M1.

Suggested resolution: Add one sentence to each of M2, M3, M4, and M5 acceptance criteria: "Characterization tests for this family pass on pre-migration `cli.py` dispatch code (confirmed during M1 or at start of this milestone if a family was added to scope after M1)." This matches the Step 1 discipline that the brief describes and is already in the plan's goals implicitly.

---

## Validation

Cross-checks performed for this audit:

1. **Brief §9 question answers** — All six answers in plan §"Scope Decisions From context_brief.md §9" are concrete enough to start coding. Q1 (orchestrator-wrap pattern) confirmed against `meta_optimizer.py` precedent. Q2 (route remainder) confirmed: plan includes all five route subcommands. Q3 (FastAPI non-goal) is unambiguous. Q4 (ARTIFACT_PRINTER_DISPATCH move) confirmed per plan §M5. Q5 (audit/synthesis included) confirmed. Q6 (COMMAND_MODULES expansion) confirmed with module-specific prohibition example in M3.

2. **Knowledge `stage-promote` flow** — Confirmed via `cli.py` lines 2530–2559: calls `register_canonical_proposal(...)` then `apply_proposal(..., ProposalTarget.CANONICAL_KNOWLEDGE)`. M3 acceptance criterion "register a canonical proposal and call `apply_proposal`" accurately matches the current code.

3. **Task family write commands** — Confirmed: no `apply_proposal` calls exist anywhere in the `task` dispatch block (lines 2861–3610). Plan §Scope Decision §1 and M4 acceptance ("may call Orchestrator / domain governance functions") correctly reflect this. The plan correctly understands the non-proposal task write pattern.

4. **M4 command list completeness** — Confirmed against `cli.py` dispatch. All M4 commands (`create`, `run`, `retry`, `resume`, `rerun`, `acknowledge`, `planning-handoff`, `knowledge-capture`, `knowledge-promote`, `knowledge-reject`, `canonical-reuse-evaluate`, `consistency-audit`) are present in `cli.py`. One omission: `rerun` appears in `cli.py` at line 3029 but does not appear in the M4 scope list in `plan.md §M4 Scope`. Checking the M4 scope item list — it does appear in the `application/commands/tasks.py` write-actions list (line ~204). Confirmed present, no gap.

5. **M5 command list completeness** — Confirmed against `cli.py` dispatch. All M5 read commands (`list`, `queue`, `attempts`, `compare-attempts`, `control`, `intake`, `staged`, `knowledge-review-queue`, `inspect`, `review`, `checkpoint`, `policy`, `artifacts`, `dispatch`, `capabilities`) are present in `cli.py`. The `dispatch` command at line 3599 and `capabilities` at line 3394 are present; no missing commands observed.

6. **`ARTIFACT_PRINTER_DISPATCH` location** — Confirmed at `cli.py` lines 620–758 per brief §2. Plan §M5 correctly targets moving it with the task read/artifact adapter.

7. **`build_parser` extraction** — Confirmed: no milestone mandates parser file movement. M5 cleanup explicitly preserves `build_parser()` import compatibility and makes extraction optional.

8. **`test_state_transitions_only_via_orchestrator` guard** — Confirmed at `test_invariant_guards.py` line 416: the allowed-files set is `{orchestrator.py, sqlite_store.py, store.py}`. M4 acceptance correctly says this must not be broadened to include `application/commands/tasks.py`. The guard is an AST import-and-call scan, not a file-path scan, so adding the module to the allowlist would require an explicit change — the plan's discipline is correct and the acceptance language is unambiguous.

9. **Non-goals load-bearing check** — All eight non-goals are present and correctly scoped. No missing non-goal detected. The "no repo ports, no schema migration" non-goal correctly fences off LTO-5's repository-ports work.

10. **M2 scope size sanity** — Route remainder (~55 dispatch lines), audit (~30 dispatch lines), synthesis (~90 dispatch lines), note/ingest (~39 dispatch lines) = ~214 dispatch lines total. Per brief §8, each family is 30–90 lines with simple `apply_proposal` flows. M2 is not overloaded; the combined scope is smaller than knowledge (M3) or task writes (M4).

11. **Suspend / cancel commands** — Confirmed: `swl task suspend` and `swl task cancel` are NOT present as dispatch entries in `cli.py`. INTERACTION.md §4.2.3 lists them as UI capability equivalents, but they have no CLI dispatch today. No gap in plan coverage.

---

## Recommendations

These are non-blocking suggestions; none requires a plan revision to unblock implementation.

1. The M3 acceptance prohibition list for `application/commands/knowledge.py` should explicitly resolve the `update_staged_candidate` and `create_knowledge_relation` status (CONCERN-2, CONCERN-3). A two-line annotation in the acceptance list is sufficient.

2. The same-commit rule for `apply_proposal` callsite migration (CONCERN-4) is the highest-risk silence in the plan. Adding one sentence to M2 acceptance eliminates a class of hard-to-detect regression.

3. Consider adding the pre-migration baseline verification phrasing to M2/M3/M4/M5 (CONCERN-5) as a discipline reminder; the absence is a process gap, not a code gap.

4. The M4 description of `canonical-reuse-evaluate` and `consistency-audit` (CONCERN-1) would benefit from one sentence clarifying why they belong in M4 despite their read-like names. This prevents a re-classification during implementation review.

---

## Confirmed Ready

- M1 (Baseline and Boundary Hardening) — scope, acceptance, and gate are clear and implementable as written.
- M2 (Governance-Adjacent Small Families) — implementable as written; see CONCERN-4 for the same-commit annotation recommendation.
- M3 (Knowledge Family Migration) — implementable as written; see CONCERN-2, CONCERN-3 for boundary test coverage gaps that need one-line resolutions.
- M4 (Task Write / Control Migration) — implementable as written; see CONCERN-1 for the classification annotation recommendation.
- M5 (Task Read / Report / Artifact Migration) — implementable as written.
