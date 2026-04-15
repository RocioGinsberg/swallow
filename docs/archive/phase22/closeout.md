---
author: codex
phase: 22
slice: taxonomy-aware-routing-baseline
status: final
depends_on:
  - docs/plans/phase22/context_brief.md
  - docs/plans/phase22/design_decision.md
  - docs/plans/phase22/risk_assessment.md
  - docs/plans/phase22/review_comments.md
---

**TL;DR**: Phase 22 的实现与评审已完成，当前处于可合并状态。仓库现在具备 taxonomy 元数据定义、route-level taxonomy 挂载与 taxonomy-aware dispatch guard，但尚未引入 RBAC、动态注册或新的 executor 家族。

# Phase 22 Closeout

This note records the stop/go judgment for the completed Phase 22 `Taxonomy-Aware Routing Baseline` slice.

At the time of writing, implementation and review are complete on the feature branch and the phase is ready for merge.

## Judgment

Phase 22 is complete enough to stop by default.

The repository now has:

- code-level taxonomy definitions for `system_role` and `memory_authority`
- `TaxonomyProfile` as an explicit serialized routing concept
- default taxonomy assignments on all built-in routes
- taxonomy propagation from route selection into `TaskState`
- a taxonomy-aware dispatch guard that can block dispatch when role or memory authority mismatches the contract intent

## What Phase 22 Established

Phase 22 completed the missing identity-and-authority layer between the existing route topology model and future policy-aware dispatch decisions.

The completed baseline now includes:

- explicit taxonomy truth in code, not only in design docs
- route-local taxonomy declarations for all built-in routes
- task-state persistence of selected route taxonomy
- a conservative dispatch-time enforcement seam for obvious role / authority mismatches
- tests that cover:
  - taxonomy profile validation
  - route taxonomy propagation
  - default specialist taxonomy on `local-note`
  - taxonomy-based dispatch blocking for validator / promotion / stateless cases

This means the system is no longer only:

- choosing routes by executor brand, route mode, and execution topology
- validating dispatch by contract schema and handoff semantics

It is now also:

- carrying role / memory-authority metadata on selected routes
- persisting that metadata into the task record
- using taxonomy metadata to reject dispatches that obviously target the wrong type of agent

## Review Outcome

`docs/plans/phase22/review_comments.md` concludes **PASS, mergeable**.

Review recorded:

- `154 passed, 5 subtests passed in 4.73s`
- no `[BLOCK]` items
- one non-blocking concern:
  - `validate_taxonomy_dispatch()` currently runs for all contracts, including local-only contracts

This concern is intentionally deferred; because built-in routes default to `general-executor / task-state`, the guard remains effectively inactive for existing normal paths.

## What It Did Not Establish

Phase 22 did not establish:

- RBAC or distributed authorization
- dynamic taxonomy registration or discovery
- new executor families or new agent entities
- runtime enforcement of canonical promotion authority beyond the initial heuristic guard
- route selection changes based on taxonomy preference

Those remain future planning questions rather than implied next steps for this slice.

## Stop / Go Judgment

Stop:

- do not reinterpret taxonomy metadata as a full authorization system
- do not widen the heuristic taxonomy guard into comprehensive policy governance without a fresh kickoff
- do not add new agent taxonomies ad hoc outside the design process

Go:

- merge the reviewed feature branch into `main`
- start from a fresh kickoff if the next step should deepen:
  - stricter taxonomy policy semantics
  - dynamic capability / taxonomy negotiation
  - richer operator-facing visibility of taxonomy in CLI surfaces
  - future RBAC-like or policy-pack evolution

## Recommended Next Step

Use this closeout as the stop/go boundary for the completed Phase 22 slice.

Immediate next action:

1. Human merges the reviewed Phase 22 PR into `main`
2. `docs/active_context.md` is switched to the next kickoff-ready state
3. `current_state.md` is updated only after merge confirms the new stable checkpoint
