---
author: codex
phase: 34
slice: cognitive-router
status: final
depends_on:
  - docs/plans/phase34/kickoff.md
  - docs/plans/phase34/review_comments.md
---

## TL;DR
Phase 34 已完成实现、slice 拆 commit、review follow-up 与 PR 收口准备，当前状态为 **PR ready / Merge ready**。本轮把静态 executor 映射升级为 capability-aware `RouteRegistry`，落地 `ClaudeXMLDialect` / `CodexFIMDialect` 两个 concrete adapter，并为 `local-codex` 建立单次 binary fallback 到 `local-summary`；全量回归基线为 `244 passed in 5.79s`。

# Phase 34 Closeout

## 结论

Phase 34 `Cognitive Router + Dialect Framework + Binary Fallback` 已完成实现、测试、review follow-up 与 PR 收口准备，当前状态为 **PR ready / Merge ready**。

本轮围绕 kickoff 的 3 个 slice，完成了从静态 executor 选择到策略路由与受控降级的最小闭环：

- `Strategy Router`：将 `select_route()` 从硬编码 executor 映射升级为 `RouteRegistry` 驱动的候选匹配
- `Dialect Adapters`：落地 Claude XML / Codex FIM 两个 concrete adapter，并把默认 codex 路由切到 `codex_fim`
- `Binary Fallback`：在 primary executor failed 时切到预定义 fallback route，并保留 `fallback_*` 工件与 `task.execution_fallback` 事件

Claude review 初始结论为 **0 BLOCK / 3 CONCERN / 1 NOTE / Merge ready**。其中 C2、C3 与 N1 已在当前 branch 消化；C1 保持为非阻塞 backlog 项。

## 已完成范围

### Slice 1: RouteRegistry + Strategy Router

- `router.py` 引入 `RouteRegistry`，用内置注册表替代原 `BUILTIN_ROUTES` 静态 dict
- `select_route()` 现在按“精确 route / executor -> family + execution site -> capability -> summary fallback”顺序选路
- `models.py::RouteSpec` 新增 `fallback_route_name`
- `_apply_route_spec_to_state()` 抽出路由字段写回逻辑，减少 `create_task()` / `acknowledge_task()` / `run_task()` 中的重复赋值
- `tests/test_router.py` 覆盖 registry 查询、优先级与 fallback route 解析

对应 commit：

- `5d472ce` `feat(router): add route registry and strategy selection`

### Slice 2: Claude XML + Codex FIM Dialects

- 新增 `src/swallow/dialect_adapters/` 子模块
- `ClaudeXMLDialect` 负责 XML 标签重组并做 XML escaping
- `CodexFIMDialect` 仅在 `execution_kind == "code_execution"` 时激活 FIM prompt 结构
- `executor.py` 接入新的 dialect registry，并把默认 `local-codex` 路由切到 `codex_fim`
- `tests/test_dialect_adapters.py` 与 `tests/test_cli.py` 覆盖新方言解析和默认 codex 路径行为

对应 commit：

- `6a3c603` `feat(dialect): add claude xml and codex fim adapters`

### Slice 3: Binary Fallback + 集成

- `orchestrator.py` 在 primary executor `failed` 时触发一次 route-level fallback
- fallback 当前只对 `local-codex -> local-summary` 生效，不做链式降级
- primary 失败工件会保留为 `fallback_primary_*`，fallback 执行工件保留为 `fallback_*`
- 运行期新增 `task.execution_fallback` 事件，记录 previous/fallback route 与状态上下文
- `tests/test_binary_fallback.py` 与 `tests/test_cli.py` 覆盖成功降级、失败降级和 lifecycle 变化

对应 commit：

- `366cdae` `feat(fallback): add binary fallback for failed primary routes`

## Review Follow-up

- C1 `CodexFIMDialect` FIM 标记转义问题保持为 backlog 项，已登记到 `docs/concerns_backlog.md`
- C2 `create_task()` 中的 executor 覆盖顺序已修正为 `_apply_route_spec_to_state(..., update_executor_name=False)`，行为不变但语义清晰
- C3 关于 fallback 语义变更的提示已体现在 slice commit 标题和本收口文档 / PR 文案中
- N1 已通过 3 个 slice commit 的方式消化，不再保留单个大实现提交

补充 docs follow-up commit：

- `ca93f57` `docs(phase34): sync review follow-up status`

## 与 kickoff 完成条件对照

### 已完成的目标

- `RouteRegistry` 已替代原 `BUILTIN_ROUTES` 硬编码映射
- `select_route()` 已升级为基于注册表和 capability 的候选匹配
- `ClaudeXMLDialect` 与 `CodexFIMDialect` 已实现并接入 registry
- `RouteSpec.fallback_route_name` 已生效
- executor failed 时已触发一次 route-level fallback
- fallback artifact 与 event 已按约定写入
- 全量测试通过
- RouteRegistry、dialect adapters、binary fallback 的新增测试已补齐

### 未继续扩张的内容

以下方向仍保持为非目标或延后项，不应视为本 phase 遗失 bug：

- Gemini Context Caching adapter
- provider connector 层部署与 `new-api` / TensorZero 实际接入
- 多级 fallback matrix / 链式降级
- 运行时健康探测、成本感知或动态 capability negotiation
- ReAct 纯文本降级转化
- 多执行器竞速或 Debate Topology

## Stop / Go 判断

### Stop 判断

当前 phase 可以停止继续扩张，理由如下：

- kickoff 中定义的 S1、S2、S3 均已完成并独立落成 slice commit
- 路由、方言和 fallback 的作用边界清晰，没有把 scope 扩大到 provider connector 或 runtime negotiation
- Claude review 没有 BLOCK；除 backlog 项 C1 外，其余 concern / note 已被当前 branch 消化
- 全量测试通过，当前分支已具备 PR / merge gate 条件

### Go 判断

下一轮不应继续以“顺手再补一点路由 / 降级能力”为名扩张 Phase 34。merge 后应回到 `docs/roadmap.md` 选择新的正式 phase，再决定是否进入：

- provider connector / gateway 侧真实接入
- 更完整的 fallback matrix
- 运行时健康探测与动态 negotiation
- Gemini Context Caching 或其他 provider-specific adapter

## 当前稳定边界

Phase 34 closeout 后，以下边界应视为当前稳定 checkpoint：

- `RouteRegistry` 仍是代码内建注册表，不做动态 discovery / runtime registration
- `select_route()` 仍是规则驱动选路，不做健康探测、成本比较或延迟感知
- `local-codex` 是当前唯一声明 `fallback_route_name` 的内置路由
- binary fallback 只执行一次，且只在 executor failed 时触发，位于 ReviewGate 之前
- `CodexFIMDialect` 只在 `code_execution` 路径激活，其他场景保持 raw prompt passthrough
- 当前未接入 provider connector 层，因此 fallback 仍是本地 route-level 行为，不是 gateway failover

## 当前已知问题

- `CodexFIMDialect` 尚未转义任务文本中的 `<fim_prefix>` / `<fim_suffix>` 字符串；该问题已记录到 `docs/concerns_backlog.md`
- 当前路由升级仍停留在本地 orchestrator / gateway 语义层，不包含 provider API 直连、健康检查或动态权衡
- Phase 29 记录的 dialect 信息收集逻辑重复仍未消化；若继续增加第 3 个以上 dialect，应抽取公共数据收集层

以上问题均已在 review 或 backlog 中记录，不阻塞当前 merge。

## 测试结果

最终验证结果：

```text
244 passed in 5.79s
```

补充说明：

- `tests/test_router.py` 覆盖 RouteRegistry 与 capability 匹配策略
- `tests/test_dialect_adapters.py` 覆盖 Claude XML、Codex FIM 和非 code_execution passthrough
- `tests/test_binary_fallback.py` 覆盖 fallback 成功 / 失败、artifact 与 event 记录
- `tests/test_cli.py` 覆盖 route persistence、dialect resolution 与 fallback 后的 lifecycle 变化

## 规则文件同步检查

### 必查

- [x] `docs/plans/phase34/closeout.md`
- [x] `current_state.md`
- [x] `docs/active_context.md`
- [x] `./pr.md`

### 条件更新

- [ ] `AGENTS.md`
- [ ] `README.md`
- [ ] `README.zh-CN.md`

说明：

- 本轮未改变长期协作规则、入口读取顺序或对外使用方式，因此无需同步 `AGENTS.md` / README

## Git 收口建议

1. 保持当前 slice + docs 收口历史，不再压缩
2. 使用根目录 `pr.md` 作为 PR 描述
3. Human push `feat/phase34-strategy-router`
4. Human 创建或更新 PR，并确认 `review_comments.md`、`closeout.md`、`pr.md` 与 `docs/concerns_backlog.md` 已反映当前 review disposition
5. merge 后从 `docs/roadmap.md` 重新选择下一轮 kickoff

## 下一轮建议

merge 完成后，不要继续在 Phase 34 分支上扩张路由或 fallback 逻辑。应回到 `docs/roadmap.md` 选择新的正式 phase，并通过新的 kickoff 明确下一轮是否推进 provider connector、gateway failover 或更完整的策略协商能力。
