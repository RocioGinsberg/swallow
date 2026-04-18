---
author: codex
phase: 29
slice: Provider Dialect Baseline
status: final
depends_on:
  - docs/plans/phase29/context_brief.md
  - docs/plans/phase29/design_decision.md
  - docs/plans/phase29/risk_assessment.md
  - docs/plans/phase29/review_comments.md
---

## TL;DR
Phase 29 已完成实现、测试与 review 收口，当前状态为 **merge ready**。本轮在不改动路由选择逻辑和 provider API 边界的前提下，引入了最小 provider dialect adapter 层，并补齐了 prompt artifact、事件和 operator 视图中的 dialect 可观测性。

# Phase 29 Closeout

## 结论

Phase 29 `Provider Dialect Baseline` 已完成实现、测试验证与 review 收口准备，当前状态为 **merge ready**。

本轮在 `build_executor_prompt()` 与 executor dispatch 之间建立了最小 dialect adapter 闭环：

- 引入 `DialectSpec` / `DialectAdapter` / registry
- 保持 `plain_text` 为默认 identity dialect
- 引入首个非默认 `structured_markdown` dialect
- 将 dialect 信息落到 route state、prompt artifact、executor event 与 operator-facing CLI

## 已完成范围

### Slice 1: DialectAdapter 接口与 Registry

- 在 `models.py` 中新增 `DialectSpec`
- 在 `executor.py` 中新增：
  - `DialectAdapter` Protocol
  - `BUILTIN_DIALECTS`
  - `resolve_dialect_name()`
  - `resolve_dialect()`
- `RouteSpec` 新增 `dialect_hint`
- `TaskState` 新增 `route_dialect`
- `ExecutorResult` 新增 `dialect`

### Slice 2: plain_text 默认 Dialect 提取

- 新增 `PlainTextDialect`
- 新增 `build_formatted_executor_prompt()` 作为统一入口
- `run_executor_inline()` 和 `run_detached_executor()` 均改为通过 dialect adapter 生成 prompt
- `plain_text` 保持严格 identity transform，确保零回归

### Slice 3: structured_markdown Dialect 实现

- 新增 `StructuredMarkdownDialect`
- 以 markdown sections 方式重组 executor prompt：
  - `Task`
  - `Route`
  - `Task Semantics`
  - `Knowledge`
  - `Reused Verified Knowledge`
  - `Prior Persisted Context`
  - `Prior Retrieval Memory`
  - `Retrieved Context`
  - `Instructions`
- `local-codex` route 默认设置 `dialect_hint="structured_markdown"`
- detached route 正确透传 `dialect_hint`

### Slice 4: CLI 可观测性

- executor prompt artifact 顶部新增 `dialect: <name>`
- executor event payload 新增 `dialect`
- route record / route report / summary 中新增 dialect
- `task inspect` 输出新增 `dialect`
- `task review` 输出新增 `dialect`

## 评审结论

- Claude review：**PASS**
- 无 `[BLOCK]`
- 一个 `[CONCERN]`：
  - `StructuredMarkdownDialect.format_prompt()` 与 `build_executor_prompt()` 之间存在一定程度的信息收集重复
  - 当前规模下可接受，但如果后续再增加更多 dialect，应考虑提取公共的数据收集层

## 测试结果

本轮最终验证结果：

```text
180 passed in 4.54s
```

补充说明：

- Phase 29 dialect 定向测试已通过
- 完整 `tests/test_cli.py` 也已保持全绿

## Stop / Go 边界

### 本轮 stop 在这里

- dialect adapter 层已经建立并可被 route 配置驱动
- 默认 plain_text 路径已稳定保留
- `structured_markdown` 已提供首个非默认 provider-native prompt 变体
- operator 已能在 artifact、event、inspect、review 中看到 dialect
- 再继续扩张会开始跨到更复杂的 provider negotiation / 模板系统 / provider API 集成，不再属于本轮 baseline

### 本轮不继续扩张到

- provider API 直连
- Claude XML / 其他 provider-specific dialect 扩张
- prompt 模板系统
- runtime dialect 自动协商
- 路由选择逻辑重构

## 与 design_decision 的对照

### 已完成的目标

- DialectAdapter 接口与 registry
- `plain_text` 默认 dialect 提取
- `structured_markdown` dialect
- `local-codex` route dialect 配置
- prompt artifact / event / inspect / review 的 dialect 可观测性

### 未完成但已明确延后的目标

- 更多 provider-specific dialect
- Claude XML dialect
- 公共 prompt 数据收集层抽取
- dialect 自动协商
- 更复杂的 provider negotiation 逻辑

这些项目均属于明确延后，不应视为本轮遗失 bug。

## 当前稳定边界

- route 可以静态持久化并暴露 `route_dialect`
- `build_formatted_executor_prompt()` 已成为 executor prompt 的统一入口
- `plain_text` 继续作为默认安全回退 dialect
- `structured_markdown` 已作为 `local-codex` 的默认 dialect 生效
- prompt artifact 和 operator-facing CLI 已能稳定反映 dialect

## 当前已知问题

- `StructuredMarkdownDialect` 与 `build_executor_prompt()` 仍存在信息收集重复；当前不阻塞 closeout，但后续如果 dialect 数量继续增长，建议单独立项做 executor prompt assembly refactor
- 本轮只验证了一个非默认 dialect，尚未扩展到更多 provider-native formats

## 规则文件同步检查

### 必查
- [x] `docs/plans/phase29/closeout.md`
- [ ] `current_state.md`
- [x] `docs/active_context.md`

### 条件更新
- [ ] `AGENTS.md`
- [ ] `.codex/session_bootstrap.md`
- [ ] `.codex/rules.md`
- [ ] `README.md`
- [ ] `README.zh-CN.md`

说明：

- `current_state.md` 建议在 Human 完成提交 / PR / merge 决策后再按真实 checkpoint 更新
- 本轮未改变长期规则、读取顺序或对外使用方式，因此其余文件无需同步

## Git 收口建议

1. Human 提交本轮实现与测试改动
2. 将 `docs/plans/phase29/closeout.md` 与 `pr.md` 一并纳入收口材料
3. Human push 当前分支，并基于 `pr.md` 创建或更新 PR
4. PR 合并后，再更新 `current_state.md` 与入口状态文档

## 下一轮建议

- 合并完成前，不继续把 Phase 29 扩张为更广义的 provider negotiation phase
- 合并完成后，从 `docs/roadmap.md` 继续选择下一轮正式 phase
- 如继续沿 Execution Topology 前进，应保持“provider dialect baseline”与更复杂的 provider negotiation / remote execution 边界分离
