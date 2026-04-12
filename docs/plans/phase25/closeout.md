---
author: codex
phase: 25
slice: taxonomy-driven-capability-enforcement
status: final
depends_on:
  - docs/plans/phase25/context_brief.md
  - docs/plans/phase25/design_decision.md
  - docs/plans/phase25/risk_assessment.md
  - docs/plans/phase25/review_comments.md
---

**TL;DR**: Phase 25 已完成实现与评审，当前处于可合并状态。仓库现在具备 taxonomy→capability 的静态降级规则、运行时 capability enforcement，以及 operator-facing enforcement 可视化，但没有引入动态策略引擎或新的 executor 家族。

# Phase 25 Closeout

This note records the stop/go judgment for the completed Phase 25 `Taxonomy-Driven Capability Enforcement` slice.

Phase 25 established the execution-time least-privilege layer on top of the taxonomy baseline introduced in earlier phases.

## Judgment

Phase 25 is complete enough to stop by default.

The repository now has:

- a taxonomy-driven capability enforcement mapping table
- runtime capability downgrade before execution begins
- enforcement behavior shared by `run_task()` and `acknowledge_task()`
- explicit audit events and CLI visibility when capability downgrades are applied

## What Phase 25 Established

Phase 25 completed the missing runtime safety layer between route assignment and actual executor prompt assembly.

The completed baseline now includes:

- static enforcement rules for:
  - `validator/*`
  - `*/stateless`
  - `*/canonical-write-forbidden`
- strict downgrade ordering for:
  - `filesystem_access`
  - `network_access`
  - `supports_tool_loop`
- an orchestrator enforcement seam that rewrites `state.route_capabilities` before execution
- capability enforcement coverage on acknowledge-based local re-entry paths
- event-level audit truth via `task.capability_enforced`
- inspect-level operator visibility of whether capability downgrades were applied
- tests that cover:
  - pure enforcement logic
  - validator downgrade behavior
  - stateless downgrade behavior
  - default general-executor no-op behavior
  - acknowledge re-entry enforcement
  - event emission and inspect rendering

This means the system is no longer only:

- validating whether a task may be routed to a given entity
- persisting taxonomy metadata for dispatch and review surfaces

It is now also:

- reducing the actual execution capability surface before prompt assembly
- enforcing least privilege at runtime even when a route is already selected
- exposing those downgrades to operators as an explicit audit trail

## Review Outcome

`docs/plans/phase25/review_comments.md` concludes **PASS, mergeable**.

Review recorded:

- `178 passed, 5 subtests passed in 4.74s`
- no `[BLOCK]` items
- one non-blocking concern:
  - `canonical_write_guard` is currently injected as an audit marker into the capabilities dict, but is not a native `RouteCapabilities` field and does not itself enforce writes

This concern is intentionally deferred; actual restricted knowledge write interception is already handled by the Phase 24 staged knowledge path.

## What It Did Not Establish

Phase 25 did not establish:

- dynamic policy loading or OPA-style policy engines
- manifest-level pruning of capability refs
- new executor types or runtime backends
- richer UI or policy dashboarding
- additional write-path enforcement beyond the existing staged knowledge controls

Those remain future planning questions rather than implied next steps for this slice.

## Stop / Go Judgment

Stop:

- do not reinterpret this slice as a full policy engine
- do not widen it into dynamic runtime policy configuration without a fresh kickoff

Go:

- merge the reviewed feature branch
- use Phase 25 as the new stop/go boundary for runtime least-privilege enforcement
- begin a new phase only if there is a clearly scoped next capability/policy slice

## Recommended Next Step

Use this closeout as the stop/go boundary for the completed Phase 25 slice.

Immediate next action:

1. Human merges `feat/phase25-capability-enforcement`
2. Repository entry docs switch to `Phase 25` as the latest stable checkpoint
3. The next round begins from a fresh kickoff rather than extending Phase 25 in place
