---
author: codex
phase: `<phase>`
slice: `<phase-plan>`
status: draft
depends_on:
  - docs/plans/<phase>/context_brief.md
  - docs/roadmap.md
---

TL;DR:
`<最多 3 行：本 phase 做什么、为什么现在做、最大风险 / gate 是什么>`

# Phase Plan

> 新 phase 默认使用本模板。它合并旧 `kickoff.md` / `design_decision.md` / `risk_assessment.md` / `breakdown.md` 的必要内容，避免在 `docs/plans/<phase>/` 中重复叙述。

## Frame

- phase: `<phase>`
- track: `<track>`
- recommended_branch: `feat/<phase-or-slice>`
- goal: `<一句话目标>`
- non_goals:
  - `<非目标 1>`
  - `<非目标 2>`

## Anchors

- `docs/design/INVARIANTS.md` — `<相关约束>`
- `docs/design/<file>.md` — `<相关约束>`
- `docs/engineering/<file>.md` — `<相关约束，如适用>`

## Plan

| Milestone | Slice | Scope | Risk | Validation | Gate |
|---|---|---|---|---|---|
| M1 | `<slice>` | `<涉及模块 / 文件>` | low / medium / high | `<pytest / guard / eval / smoke>` | Human review + commit |

## Material Risks

- `<风险>`: `<影响>` → `<缓解方式 / stop-go 信号>`

## Validation

- `.venv/bin/python -m pytest <target>`
- `<其他必要命令或手动检查>`

## Completion Conditions

1. `<可检查完成条件 1>`
2. `<可检查完成条件 2>`
3. `<可检查完成条件 3>`

## Notes

- 只记录会影响实现、审查、测试或 merge 的决策。
- 不复制 `context_brief.md` 的历史背景。
- 如需要额外文档，说明原因并只写增量信息。
