---
author: codex
phase: 62
slice: design-gate
status: review
created_at: 2026-04-28
depends_on:
  - docs/plans/phase62/kickoff.md
  - docs/plans/phase62/design_decision.md
  - docs/plans/phase62/risk_assessment.md
  - docs/plans/phase62/design_audit.md
reviewer: codex-second-review
verdict: BLOCK
---

TL;DR:
Codex second audit confirms the revised Phase 62 plan resolved the first audit's 3 structural BLOCKERs.
One new BLOCK remains: MPS Path A execution is specified as direct `run_http_executor(...)`, but Provider Router / `route_hint` semantics are not defined.
Human Design Gate should stay blocked until Claude revises that route-governance seam; the remaining items are implementation concerns, not phase blockers.

# Model Review

## Scope

Reviewed Phase 62 MPS design artifacts after the first design audit revision:

- `docs/plans/phase62/kickoff.md`
- `docs/plans/phase62/design_decision.md`
- `docs/plans/phase62/risk_assessment.md`
- `docs/plans/phase62/design_audit.md`
- `docs/design/INVARIANTS.md`
- `docs/design/ORCHESTRATION.md`
- Relevant implementation anchors in `src/swallow/executor.py`, `src/swallow/router.py`, `src/swallow/governance.py`, `src/swallow/models.py`, `src/swallow/paths.py`, `src/swallow/staged_knowledge.py`

This is a Human-requested Codex substitute for the unavailable external model channel. It is advisory design review only: no source code or design-decision正文 was modified.

## Verdict

BLOCK

The plan is close to implementable, but Design Gate should not pass yet because the MPS Path A / Provider Router boundary is underspecified. This is an invariant-level seam, not a local coding preference.

## Findings

- [PASS] **First audit BLOCKERs are materially addressed.** The revised `design_decision.md` replaces generic `_PolicyProposal` refactoring with a separate `_MpsPolicyProposal`, introduces `swl synthesis policy set` instead of overloading `swl audit policy set`, and maps `StagedCandidate` onto the actual fields (`text`, `source_task_id`, `source_kind`, `source_ref`, `source_object_id`). This removes the prior structural blockers for S1 and S4.

- [PASS] **Staged knowledge boundary is defensible for Phase 62.** `swl synthesis stage` is an Operator CLI action, and `synthesis.py` itself is guarded from importing or calling `submit_staged_candidate`. Deferring the pre-existing `orchestrator.py` stagedK path to backlog is acceptable because Phase 62 does not introduce that path and records it explicitly.

- [PASS] **No policy seed is the lower-risk choice.** Keeping MPS defaults as `synthesis.py` constants and writing policy only when Operator calls `swl synthesis policy set` preserves proposal-over-mutation. It avoids a hidden first-run write and keeps persistent policy truth tied to `apply_proposal`.

- [BLOCK] **Path A / Provider Router governance is not specified enough to implement safely.** `design_decision.md` says MPS calls Path A through existing `run_http_executor(..., prompt=composed)`, and `SynthesisParticipant` has an optional `route_hint`. However, `run_http_executor` is a low-level HTTP caller: it builds a payload from the current `TaskState.route_model_hint` and posts to the configured chat endpoint. It does not call `router.select_route`, does not interpret `SynthesisParticipant.route_hint`, and does not apply route capability guards. The default `TaskState` route is `local-aider` with model hint `aider`, so a direct call can also produce an HTTP payload with the wrong model hint unless synthesis first constructs a governed HTTP route state. This conflicts with INVARIANTS §4 / ORCHESTRATION §5, where MPS participant calls are Path A calls governed by Provider Router. Before implementation, Claude should revise `design_decision.md` to define a concrete route-resolution seam, for example: how `route_hint` is interpreted, what the default MPS HTTP route is when no hint is set, whether `select_route` or `route_by_name` is authoritative, how capability boundary failures are handled, and whether synthesis uses a cloned per-call `TaskState` instead of mutating the live task state.

- [CONCERN] **`run_http_executor` fallback mutates `TaskState` in memory.** Executor-level fallback can call `_apply_route_spec_for_executor_fallback`, which mutates route fields on the passed state object. If `run_synthesis` passes the live task state through multiple participant calls, one participant failure can leak fallback route fields into later participant calls or event payloads. This is probably solvable by using a defensive copy per participant / arbiter call, but the design should say so and add a guard that MPS does not persist task-state transitions.

- [CONCERN] **The `_MpsPolicyProposal` path must update `_validate_target`, not only `_apply_policy`.** Current `governance._validate_target` accepts only `_PolicyProposal` for `ProposalTarget.POLICY`. The revised design focuses on `_apply_policy` isinstance dispatch, but `apply_proposal` validates before dispatch. Implementation must explicitly accept both `_PolicyProposal` and `_MpsPolicyProposal`, and tests should cover that `apply_proposal(target=POLICY)` reaches the MPS branch.

- [CONCERN] **Policy storage path should be centralized.** The plan introduces `.swl/policy/mps_policy.json`, while current path helpers expose `audit_policy_path(base_dir)` and other policy/report paths but no `.swl/policy/` namespace helper. This is not a blocker, but adding `mps_policy_path(base_dir)` in `paths.py` will reduce raw-path drift and make the apply-proposal writer guard clearer.

- [CONCERN] **Design artifacts still contain small drift from the audit revision.** `kickoff.md` still mentions `.swl/artifacts/<task_id>/` and a participant "hard cap" guard, while `design_decision.md` correctly uses `paths.artifacts_dir(base_dir, task_id)` and `test_mps_participants_within_policy_cap`. `design_decision.md` also says the revised guard list has 6 tests, but the table contains 7 rows and then states total guards increase from 17 to 24. This does not block implementation if `design_decision.md` is treated as authoritative, but it should be cleaned before Human Gate to avoid Codex implementing stale kickoff wording.

- [CONCERN] **`swl synthesis stage` idempotency is unspecified.** The plan maps arbitration output into `StagedCandidate`, but it does not say what happens if Operator runs `swl synthesis stage --task <id>` twice. The CLI should either reject when a pending candidate already exists for the same `source_ref` / `source_object_id`, or explicitly allow duplicates and print the new candidate id. Rejection is the safer default.

- [CONCERN] **MPS event semantics need narrow tests given existing §7 drift.** The codebase does not currently have `Event.actor`, `swallow.identity.local_actor()`, or `swallow.workspace.resolve_path()`, and this drift is already logged as backlog. Phase 62 should not fix that whole topic, but it should avoid adding new `"local"` literals and add focused tests that MPS events are append-only, use `event_type`, include useful route/config/artifact ids in payload, and do not silently advance task status.

- [CONCERN] **Arbitration artifact validation should include content, not just file existence.** `test_mps_arbiter_artifact_required` should assert a non-empty `arbiter_decision.synthesis_summary`, schema version, config id, round artifact refs, and participant result statuses. A zero-byte or partial JSON artifact would currently satisfy a weak existence-only guard and then break `swl synthesis stage`.

## Claude Follow-Up

Design revision is required before Human Design Gate:

- Clarify the MPS Path A route-governance seam: participant `route_hint`, default route, Provider Router selection, fallback handling, and defensive state cloning.
- Add implementation notes or tests for no task-state persistence during synthesis, especially around HTTP fallback mutation.
- Update the policy proposal validation note so `_validate_target` accepts `_MpsPolicyProposal`.
- Clean stale kickoff / guard-count wording so the phase has one authoritative implementation plan.

No source implementation should start until the `[BLOCK]` item is resolved.

## Human Gate Note

Do not approve Phase 62 Design Gate yet. The first audit's blockers are handled, but the remaining `[BLOCK]` touches INVARIANTS §4 and ORCHESTRATION §5. The cheapest resolution is a narrow Claude patch to `design_decision.md` defining MPS route resolution and a matching test expectation; after that, Codex can start M1 without reopening the whole phase design.
