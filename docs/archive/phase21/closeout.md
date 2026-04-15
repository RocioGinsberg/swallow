---
author: codex
phase: 21
slice: dispatch-policy-gate-and-mock-topology-visibility
status: final
depends_on:
  - docs/plans/phase21/context_brief.md
  - docs/plans/phase21/design_decision.md
  - docs/plans/phase21/risk_assessment.md
  - docs/plans/phase21/review_comments.md
---

**TL;DR**: Phase 21 已完成并已合并到 `main`。仓库现在具备 dispatch 前语义校验、`acknowledge` 人工放行路径，以及 `[MOCK-REMOTE]` 视图区分，但没有引入真实 remote execution、RPC 或自动 dispatch 扩张。

# Phase 21 Closeout

This note records the stop/go judgment for the completed Phase 21 `Dispatch Policy Gate & Mock Topology Visibility` slice.

It keeps the system inside the existing local-first execution model while tightening the operator-facing remote-handoff workflow introduced by earlier phases.

## Judgment

Phase 21 is complete enough to stop by default.

The repository now has:

- a semantic dispatch-policy layer that validates `context_pointers` before dispatch proceeds
- a reusable blocked-dispatch path that persists semantic failures through the existing `dispatch_blocked` lifecycle
- an explicit `swl task acknowledge <task_id>` operator recovery action for blocked dispatch
- a controlled local reentry path for acknowledged tasks that avoids mock-remote loops
- explicit `[MOCK-REMOTE]` operator-facing labels in `inspect`, `review`, and `dispatch` output for real mock-remote dispatched runs

## What Phase 21 Established

Phase 21 completed the missing behavior layer between Phase 20 mock dispatch gating and any future operator-approval or richer execution-policy work.

The completed baseline now includes:

- contract-aware semantic validation, not just schema validation
- a human-operated unblock path for dispatch decisions that fail before execution
- clear CLI separation between real local runs, blocked remote candidates, and mock-remote dispatched runs
- tests that cover the full loop:
  - semantic validation pass/fail behavior
  - blocked dispatch acknowledgement
  - acknowledge -> resume -> completed recovery
  - mock-remote labeling without mislabeling blocked or acknowledged states

This means the system is no longer only:

- deciding local vs blocked vs mock_remote from contract truth
- persisting blocked dispatch events

It is now also:

- validating whether remote-handoff context pointers actually resolve
- giving operators a deliberate manual recovery path when dispatch is blocked
- distinguishing mock-remote topology in operator views without implying production remote support

## Review Outcome

`docs/plans/phase21/review_comments.md` concludes **PASS, mergeable**.

Review recorded:

- `146 passed, 5 subtests passed in 5.55s`
- no `[BLOCK]` items
- one non-blocking concern:
  - `acknowledge_task()` currently hard-codes `route_mode="summary"` as the safest local fallback

This concern is intentionally deferred; it does not block Phase 21 closeout.

## What It Did Not Establish

Phase 21 did not establish:

- real remote worker execution
- cross-machine transport or RPC
- automatic operator approval or policy mutation
- remote dispatch queues or hosted orchestration
- configurable operator-selected reentry route modes

Those remain future planning questions rather than implied next steps for this slice.

## Stop / Go Judgment

Stop:

- do not reinterpret semantic dispatch validation as real remote execution readiness
- do not widen `acknowledge` into automatic policy bypass or approval automation without a fresh kickoff
- do not treat `[MOCK-REMOTE]` labeling as evidence of production remote transport support

Go:

- start from a fresh kickoff if the next step should deepen:
  - richer dispatch-policy semantics beyond file existence
  - operator-selectable acknowledge/reentry policy
  - true remote execution design that replaces the mock path
  - broader execution-policy or workbench UX follow-up work

## Recommended Next Step

Use this closeout as the stop/go boundary for the completed Phase 21 slice.

If work continues, begin from:

1. `AGENTS.md`
2. `docs/active_context.md`
3. `current_state.md`
4. `docs/system_tracks.md`
5. `docs/plans/phase21/closeout.md`

Then write a fresh kickoff note before starting the next implementation slice.
