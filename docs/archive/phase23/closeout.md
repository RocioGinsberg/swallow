---
author: codex
phase: 23
slice: taxonomy-visibility-in-cli
status: final
depends_on:
  - docs/plans/phase23/context_brief.md
  - docs/plans/phase23/design_decision.md
  - docs/plans/phase23/risk_assessment.md
---

**TL;DR**: Phase 23 已完成并进入收口。仓库现在在 `inspect` 与 `review` 两个核心 CLI 入口中暴露 route taxonomy，可直接显示 `system_role / memory_authority`，但没有引入新的路由决策、dispatch policy 或额外执行语义。

# Phase 23 Closeout

This note records the stop/go judgment for the completed Phase 23 `Taxonomy Visibility in CLI Surfaces` slice.

Phase 23 intentionally stayed narrow: it only surfaced already-persisted taxonomy data in operator-facing CLI views.

## Judgment

Phase 23 is complete enough to stop by default.

The repository now has:

- taxonomy visibility in `swl task inspect`
- taxonomy visibility in `swl task review`
- backward-compatible fallback rendering for older task state files that do not carry taxonomy fields

## What Phase 23 Established

Phase 23 completed the missing operator-facing visibility layer on top of the Phase 22 taxonomy baseline.

The completed baseline now includes:

- a compact taxonomy label in the `Route And Topology` section of `inspect`
- the same taxonomy label in the `Handoff` section of `review`
- a shared formatting path so the two surfaces stay consistent
- tests that cover:
  - default route taxonomy rendering
  - specialist route taxonomy rendering on `local-note`
  - backward-compatible `taxonomy: -` behavior for old state files

This means the system is no longer only:

- persisting taxonomy metadata in `TaskState`
- using taxonomy metadata in defensive dispatch checks

It is now also:

- exposing that identity-and-authority metadata directly to operators at inspection time
- making approval and monitoring workflows less blind without changing task behavior

## Validation Outcome

Phase 23 was handled as a low-risk direct-closeout slice and did not go through a separate PR review document.

Implementation verification recorded:

- `.venv/bin/python -m pytest tests/test_cli.py -k "task_inspect_shows_compact_overview_for_latest_attempt or task_inspect_marks_mock_remote_routes or task_inspect_does_not_mark_local_routes_as_mock_remote or task_inspect_keeps_blocked_dispatch_unmarked or task_inspect_shows_specialist_taxonomy_for_local_note_route or task_review_prints_resume_ready_snapshot"`
- `.venv/bin/python -m pytest tests/test_cli.py -k "create_task_persists_selected_executor or select_route_assigns_specialist_taxonomy_to_local_note"`

Recorded result:

- `7 passed`

## What It Did Not Establish

Phase 23 did not establish:

- taxonomy-aware route selection changes
- richer dispatch reports or approval workflows
- new CLI commands, TUI surfaces, or UI redesign
- deeper policy semantics beyond exposing existing metadata

Those remain future planning questions rather than implied next steps for this slice.

## Stop / Go Judgment

Stop:

- do not reinterpret CLI taxonomy visibility as a policy engine upgrade
- do not widen this slice into route selection or dispatch-policy changes without a fresh kickoff

Go:

- merge the completed feature branch into `main`
- reset the repository entry state to fresh-kickoff mode
- start a new phase only if there is a clearly scoped next slice

## Recommended Next Step

Use this closeout as the stop/go boundary for the completed Phase 23 slice.

Immediate next action:

1. Human merges `feat/phase23-taxonomy-cli-visibility` into `main`
2. Repository entry docs switch to `Phase 23` as the latest stable checkpoint
3. The next round begins from a fresh kickoff rather than extending Phase 23 in place
