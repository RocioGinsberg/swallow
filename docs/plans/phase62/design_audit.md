---
author: claude
phase: 62
slice: design-audit
status: draft
created_at: 2026-04-28
depends_on:
  - docs/plans/phase62/design_decision.md
  - docs/plans/phase62/kickoff.md
  - docs/plans/phase62/risk_assessment.md
  - docs/plans/phase62/context_brief.md
---

TL;DR: has-blockers — 5 slices audited, 12 issues found (3 BLOCKERs, 9 CONCERNs)

## Audit Verdict

Overall: has-blockers

---

## Issues by Slice

### Slice S1: SynthesisConfig + Policy Guards (M1)

- [BLOCKER] **`_PolicyProposal` is typed to `audit_trigger_policy` only — `mps_round_limit` / `mps_participant_limit` cannot be registered through it without a structural change.**

  The design (design_decision.md §三 S1, lines 207-215) instructs Codex to "新增两条 policy kind dispatch: `mps_round_limit` / `mps_participant_limit`" through `register_policy_proposal()` → `apply_proposal(target=POLICY)`. However, the actual `_PolicyProposal` dataclass (`governance.py:83-85`) has exactly one field: `audit_trigger_policy: AuditTriggerPolicy`. The `register_policy_proposal` function (`governance.py:156-171`) accepts only an `AuditTriggerPolicy` object. The `_apply_policy` dispatch (`governance.py:553-567`) calls only `save_audit_trigger_policy`. There is no `kind` field, no kind-dispatch branching, and no way to carry `mps_round_limit` values through the current structure.

  To implement MPS policy kinds, Codex must either: (a) add a `kind: str` and `value: int` field pair to `_PolicyProposal` and update `register_policy_proposal` signature, or (b) create a separate `_MpsPolicyProposal` type with its own `register_*` and `_apply_*` functions, and extend `apply_proposal`'s dispatch. The design does not specify which approach to take. This is a structural design gap, not a coding choice — Codex cannot proceed on S1 without a decision here.

  The design_decision.md line 211 states "新增 CLI: `swl audit policy set --kind mps_round_limit --value <n>`" but `swl audit policy set` (`cli.py:1241-1285`) currently has no `--kind` or `--value` arguments, and the entire command is hardwired to `audit_trigger_policy` fields. Codex will need to either create new CLI subcommands or refactor `swl audit policy set` to be kind-generic — neither approach is specified.

- [CONCERN] **INVARIANTS §9 guard `test_mps_policy_writes_via_apply_proposal` (design_decision.md §五) is described as "聚合到 `test_only_apply_proposal_calls_private_writers`" — but `test_only_apply_proposal_calls_private_writers` is a source-level AST scan. Adding new policy kind writers will need to be added to whatever private-writer allowlist that test uses. The test's current scope is unspecified.** Codex needs to read the test first and confirm the aggregation works before writing the new guard.

- [CONCERN] **The design (design_decision.md §三 S1, line 209) says the default value `mps_round_limit=2` is injected "由 CLI 启动时通过 `apply_proposal` 注入,而非 hardcode" — but there is no spec for when this seed injection happens (first `swl synthesis run` invocation? on CLI init? on `swl setup`?).** Without a clear trigger, Codex cannot know how to implement "what happens if no policy record exists" in `run_synthesis`'s startup validation.

- [CONCERN] **The design says `mps_participant_limit` has no hard max (risk_assessment.md §R1, line 37: "设计上由 Operator 自主决策"), but design_decision.md §三 S1 guard `test_mps_participants_within_hard_cap` implies there is a participant hard cap enforced at governance layer.** These two documents contradict each other. Codex cannot write the governance dispatch without knowing whether to hard-reject participant values above some threshold.

---

### Slice S2: Single-Round Participant Loop + Artifact Persistence (M2)

- [OK] **`run_http_executor` signature** — executor.py:1184-1191 confirms the function accepts `prompt: str | None = None` as a keyword-positional argument; when a non-None prompt is passed, line 1192 uses it directly (`prompt = prompt or build_formatted_executor_prompt(...)`). The design's choice (design_decision.md §B, line 69) to pre-compose the full prompt in `synthesis.py` and pass it through this parameter is confirmed valid. No signature modification is required.

- [CONCERN] **`run_http_executor` does not trigger any state machine transitions internally** — confirmed by reading executor.py:1184-1217. The function returns `ExecutorResult`, it does not call `append_event` or advance task state. However, the design (design_decision.md §三 S3, line 233) says "Orchestrator 在 event_log 写一条 `kind = "mps_completed"` 的事件". This event write must happen in `synthesis.py` (or in the CLI dispatch layer), not inside the executor. The design does not specify where the `append_event` call lives — in `run_synthesis` itself, or in the CLI `swl synthesis run` handler. Codex must decide this; whichever location is chosen must have access to `base_dir`, `task_id`, and a valid `Event` object. The `Event` class requires `task_id` and `event_type` fields (models.py:432). This is implementable but the location of the write is unspecified.

- [CONCERN] **design_decision.md §四 接合点 (line 269) references `swallow.workspace.resolve_path` as the path resolution function, but `swallow.workspace` does not exist as a module in the codebase.** `find /home/rocio/projects/swallow/src/swallow/ -name workspace.py` returned no results. The codebase uses `artifacts_dir(base_dir, task_id)` from `paths.py:49` directly, and orchestrator.py uses `.resolve()` inline (lines 2612-2627) when storing absolute path strings. Similarly, `swallow.identity.local_actor()` is referenced in design_decision.md §四 (line 270) but `identity.py` does not exist in the codebase. These are fictional module references. Codex must use the existing `paths.artifacts_dir` and, for actor identity, look at how orchestrator.py currently populates `actor` fields.

---

### Slice S3: Multi-Round + Arbiter (M2)

- [CONCERN] **Artifact naming for re-runs is ambiguous.** risk_assessment.md §R3 (line 67-70) describes a mitigation where re-run arbitration produces `synthesis_arbitration_<config_id>.json`, but design_decision.md §E (line 146) only specifies `synthesis_arbitration.json` as the filename. The risk assessment text says "单 task 单次 MPS 跑完后不允许重跑" as the Phase 62 default — but if that is enforced, what is the rejection mechanism? A task state guard? An artifact-existence check? This needs specification or Codex will make an unreviewed assumption.

- [OK] **Arbiter call reuses `run_http_executor`** — same as S2 analysis. The arbiter is just another participant call with a different prompt. No structural gap.

- [CONCERN] **design_decision.md §三 S3, line 231: "`run_synthesis` 启动前查询 `mps_round_limit` / `mps_participant_limit` 当前 policy 值"** — but there is no `load_policy_value(kind)` or equivalent reader function in governance.py or any other module. `save_audit_trigger_policy` / `load_audit_trigger_policy` are specific to the audit policy. Codex must write a new policy reader function. The design does not specify where this reader lives (governance.py? a new `policy_store.py`?) or what it returns when no policy record exists (raises? returns None? returns the documented default?).

---

### Slice S4: Staged-Knowledge CLI Bridge (M3)

- [BLOCKER] **design_decision.md §D describes `swl synthesis stage` as a safe, INVARIANTS-compliant path because "CLI 层 = Operator(via CLI) = INVARIANTS §5 stagedK W". However, `orchestrator.py:3145` already calls `submit_staged_candidate` directly — inside the Orchestrator path, not a CLI path. This existing call violates the INVARIANTS §5 matrix as described (Orchestrator has no stagedK W). The proposed new guard `test_stagedk_write_only_from_specialist_or_cli` (risk_assessment.md §R5, line 101) would immediately fail on the existing code.**

  This is not a Phase 62 regression — it pre-exists. But it means: (a) the proposed AST-based guard cannot be written as designed without either accepting that orchestrator.py:3145 is a known exception, or fixing that pre-existing call first; and (b) the design_decision's claim that "the stagedK write boundary is clean" is false for the current codebase. Codex cannot implement the guard as specified without a design decision on how to treat the pre-existing orchestrator.py call.

- [BLOCKER] **design_decision.md §S4 (line 246) constructs `StagedCandidate(content=arbiter_decision.synthesis_summary, source="synthesis", origin_artifact_ids=[...])`.** The actual `StagedCandidate` dataclass (`staged_knowledge.py:15-28`) has no `content` field (it has `text`), no `source` field (it has `source_kind`), and no `origin_artifact_ids` field. The `validate()` method (line 51-62) enforces `candidate_id` must start with `"staged-"` and `text` must be non-empty and `source_task_id` must be non-empty. The design uses field names that do not exist and omits required fields (`source_task_id`). Codex will get a `TypeError` or `ValueError` at construction time. The design must specify the correct field mapping before S4 can begin.

- [CONCERN] **design_decision.md §S4 (line 248) says "在 task event_log 写 `kind = "synthesis_staged"`". `Event` uses `event_type`, not `kind`, as the field name (models.py:432, confirmed by orchestrator.py event calls e.g. line 271: `event_type="task.consistency_audit_scheduled"`).** The design uses the wrong field name throughout S3 and S4. Both `mps_completed` and `synthesis_staged` event descriptions should use `event_type`. This is a minor field-name error but will cause a runtime error if copied verbatim.

---

### Slice S5: Guard Completeness + Documentation Sync (M3)

- [CONCERN] **design_decision.md §五 (lines 280-285) specifies 5 guards. The guard `test_mps_rounds_within_hard_cap` is described with two enforcement mechanisms: (a) governance dispatch rejection for `value>3`, and (b) AST scan to ensure all callers walk the policy check.** The AST scan component (b) implies scanning synthesis.py for a call to `fetch_policy_value("mps_round_limit")` or equivalent before calling `run_synthesis_round`. Without a standard `fetch_policy_value` API (see S3 CONCERN above), the AST scan target is undefined. Codex cannot write a meaningful AST guard without knowing the canonical query function name.

- [CONCERN] **A guard for `test_stagedk_write_only_from_specialist_or_cli` is described in risk_assessment.md §R5 (line 101) but does not appear in design_decision.md §五 guard list.** This guard is implied but not formally in the slice plan. If Codex adds it, the guard will fail on the pre-existing `orchestrator.py:3145` call (see S4 BLOCKER above). It should either be formally added to §五 with a scope note about the orchestrator.py pre-existing exception, or deferred.

---

## Questions for Claude

1. **S1 BLOCKER — Policy plumbing architecture**: Must Codex extend `_PolicyProposal` to be a generic `(kind, value)` carrier, or introduce a separate `_MpsPolicyProposal` type? The `register_policy_proposal` function signature and `_apply_policy` dispatch both need to change. Which approach is intended?

2. **S1 BLOCKER — CLI command design**: Is `swl audit policy set --kind mps_round_limit --value 2` the intended interface (requiring `swl audit policy set` to become kind-generic), or should there be new dedicated commands like `swl synthesis policy set --rounds <n>`? The current `swl audit policy set` is hardwired to `AuditTriggerPolicy` fields.

3. **S1 CONCERN — Participant hard cap contradiction**: risk_assessment.md §R1 line 37 says `mps_participant_limit` has no hard max. design_decision.md §三 S1 line 214 implies `test_mps_participants_within_hard_cap` enforces a governance-layer hard max on participant count. Which is correct — is there a participant hard cap or not? If not, what does `test_mps_participants_within_hard_cap` actually test?

4. **S1 CONCERN — Policy default seed timing**: When does the system write the seed value for `mps_round_limit=2` / `mps_participant_limit=4`? On first `swl synthesis run`? On CLI initialization? What does `run_synthesis` do if no policy record exists?

5. **S3 CONCERN — Policy reader API**: What function does `run_synthesis` call to read the current `mps_round_limit` / `mps_participant_limit` values? This function does not exist in governance.py. Where should it live and what should its signature and behavior be when no record exists?

6. **S4 BLOCKER — Pre-existing `orchestrator.py:3145` `submit_staged_candidate` call**: The proposed `test_stagedk_write_only_from_specialist_or_cli` guard would fail on this pre-existing call. Is this call to be treated as a known exception (add to the AST guard's allowlist), moved to a different path, or addressed by a separate concern before Phase 62 begins?

7. **S4 BLOCKER — `StagedCandidate` field mapping**: design_decision.md §S4 uses `content=`, `source=`, `origin_artifact_ids=[]`. The actual class uses `text=`, `source_kind=`, and has no `origin_artifact_ids`. What is the correct field mapping, and is `origin_artifact_ids` a new optional field to be added in S4?

8. **S2/S3 CONCERN — `swallow.workspace.resolve_path` and `swallow.identity.local_actor()`**: These modules do not exist. Should Codex use `paths.artifacts_dir(base_dir, task_id)` for path resolution (matching current orchestrator.py patterns)? And for actor identity, should the event be written with a hardcoded `"local"` string (as orchestrator.py currently does in many places) or is there a different convention?

9. **S3 CONCERN — Re-run guard mechanism**: If a task has already run MPS once (arbitration artifact exists), how is a second `swl synthesis run` on the same task rejected? Is it an existence check on `synthesis_arbitration.json`? A task state check? This needs to be specified so Codex can implement it without guessing.

---

## Confirmed Ready

- **ORCHESTRATION §5.2 mechanic (prompt assembly + `run_http_executor` reuse)**: executor.py:1184-1192 confirms the `prompt` parameter path works as designed. No signature change needed.
- **Phase 61 dispatch non-regression (R8)**: The `_apply_policy` dispatch is a single-branch function. Adding a new elif for MPS kinds is purely additive. Phase 61 `audit_trigger_policy` path is not at risk of regression once the structural plumbing gap (S1 BLOCKER) is resolved.
- **artifact directory**: `paths.artifacts_dir(base_dir, task_id)` returns `.swl/tasks/<task_id>/artifacts/` — MPS per-round artifact files can be written here with no new path infrastructure.
- **event writing**: `append_event(base_dir, Event(...))` from store.py is the correct API; the design's intent to write `mps_completed` / `synthesis_staged` events is sound, only the field name `kind` should be `event_type`.
- **`StagedCandidate` `source_kind` field**: The existing `source_kind: str = ""` field in `StagedCandidate` (staged_knowledge.py:21) can carry `"synthesis"` without a schema change — the `content` / `source` / `origin_artifact_ids` naming in design_decision.md §S4 must be corrected, but the underlying data model is compatible.
- **Slice ordering M1 → M2 → M3**: The dependency ordering is correct. S1 schema + governance must land before S2/S3 can validate config, and S4 can only work once S3 produces arbitration artifacts.

---

## Recommended Codex Starting Point

Start with **S1**, but only after Questions 1 and 2 above are answered by Claude. S1 is the foundation that all other slices depend on (SynthesisConfig schema + governance policy plumbing). The schema part (models.py dataclasses) is unblocked and can begin immediately. The governance policy plumbing cannot begin until the structural approach (generic `_PolicyProposal` vs separate type) is decided.

Within S1, the recommended order is:
1. Add `SynthesisConfig` / `SynthesisParticipant` to models.py (unblocked).
2. Resolve Q1/Q2, then implement governance policy plumbing.
3. Add CLI command for policy kind set.
4. Write the 3 S1 guard tests.

---

## Missing Slice / Additional Tests Recommended

**Missing scope item — policy reader function**: The design assumes a `fetch_policy_value(kind) -> int` function exists but it does not. This function needs to be implemented as part of S1 (or early S2), as it is called by `run_synthesis` before entering the participant loop. It should be added explicitly to the S1 or S2 slice scope.

**Additional test recommended — `test_synthesis_run_rejects_if_arbitration_exists`**: The re-run guard (re-using the same task with an existing `synthesis_arbitration.json`) is described in risk_assessment.md §R3 as the "default behavior" but has no corresponding guard test in design_decision.md §五. This should be added.

**Additional test recommended — `test_run_http_executor_not_triggered_with_state_advances`**: Since MPS calls `run_http_executor` multiple times within a single `swl synthesis run` invocation, there is a risk that the retry fallback path inside `run_http_executor` (line 1210: `_apply_executor_route_fallback`) could make unanticipated state changes. A test confirming that each participant `run_http_executor` call does not trigger state transitions (task state remains unchanged) would close this gap.

**Additional test recommended — `test_mps_event_log_actor_field`**: The new `mps_completed` / `synthesis_staged` events need to be verified to include the `actor` field (per INVARIANTS §7 guard `test_event_log_has_actor_field`). A specific test for the MPS event writes would give Codex clarity on the expected actor value.
