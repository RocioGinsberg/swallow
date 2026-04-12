---
author: claude
phase: 23
slice: taxonomy-visibility-in-cli
status: draft
depends_on:
  - docs/plans/phase23/context_brief.md
  - docs/plans/phase22/closeout.md
---

**TL;DR**: Phase 23 只有 2 个 slice：① inspect 命令的 Route And Topology 区域新增 taxonomy 行；② review 命令的 Handoff 区域同步新增。纯 CLI 渲染变更，不改任何底层逻辑，极低风险。

# Design Decision: Phase 23

## 方案总述

Phase 23 将 Phase 22 已持久化到 TaskState 的 `route_taxonomy_role` 和 `route_taxonomy_memory_authority` 字段，暴露到 CLI 的 `inspect` 和 `review` 输出中。操作员在审批或监控任务时，能直接看到当前执行实体的系统角色和记忆权限。采用紧凑单行格式 `taxonomy: general-executor / task-state`，不破坏现有版面。

## 非目标

- 不修改底层路由逻辑或 dispatch policy（Phase 22 已完成）
- 不引入 TUI 框架或富文本渲染
- 不新增 CLI 命令或子命令
- 不修改 dispatch 报告输出（taxonomy guard 的拦截信息已在 dispatch_blocked event 中，无需重复）

## Slice 拆解

### Slice 1: inspect 命令 taxonomy 展示

**目标**：在 `swl task inspect` 的 Route And Topology 区域新增 taxonomy 信息行。

**影响范围**：
- 修改 `src/swallow/cli.py`
  - inspect 命令的 Route And Topology 区域（约 `route_label` 行之后），新增一行：
    ```
    taxonomy: {state.route_taxonomy_role} / {state.route_taxonomy_memory_authority}
    ```
  - 如果两个字段均为空字符串（兼容旧状态文件），显示 `taxonomy: -`
- 新增测试
  - inspect 一个正常任务 → 输出包含 `taxonomy: general-executor / task-state`
  - inspect 一个 specialist 路由任务（local-note）→ 输出包含 `taxonomy: specialist / task-memory`

**风险评级**：
- 影响范围: 1（仅 CLI 渲染层）
- 可逆性: 1（纯展示变更）
- 依赖复杂度: 1（无外部依赖）
- **总分: 3 — 低风险**

**依赖**：无前置依赖。

**验收条件**：
- inspect 输出中 Route And Topology 区域有 taxonomy 行
- 值与 TaskState 中的 taxonomy 字段一致
- 已有 inspect 测试不破

---

### Slice 2: review 命令 taxonomy 展示

**目标**：在 `swl task review` 的 Handoff 区域新增 taxonomy 信息行。

**影响范围**：
- 修改 `src/swallow/cli.py`
  - review 命令的 Handoff 区域（约 `route_label` 行之后），新增同样格式的 taxonomy 行
- 新增测试
  - review 一个正常任务 → 输出包含 `taxonomy: general-executor / task-state`

**风险评级**：
- 影响范围: 1（仅 CLI 渲染层）
- 可逆性: 1（纯展示变更）
- 依赖复杂度: 1（无外部依赖）
- **总分: 3 — 低风险**

**依赖**：无硬依赖，可与 Slice 1 并行或顺序实现。

**验收条件**：
- review 输出中 Handoff 区域有 taxonomy 行
- 已有 review 测试不破

---

## 实现顺序

```
Slice 1: inspect taxonomy 展示
Slice 2: review taxonomy 展示
```

无顺序依赖，可并行实现。建议顺序做以便统一格式。

## Branch Advice

- 当前分支: `main`
- 建议操作: 新建分支
- 建议分支名: `feat/phase23-taxonomy-cli-visibility`
- 理由: 2 个 slice 简单紧密，单分支单 PR
- PR 策略: 单 PR 合入

## Phase-Guard 检查

- [x] 方案未越出 context_brief 定义的 goals（仅做 CLI 展示）
- [x] 方案未触及 non-goals（无 TUI 框架、无路由逻辑修改）
- [x] Slice 数量 = 2，在建议上限 ≤5 内
- 无 `[SCOPE WARNING]`
