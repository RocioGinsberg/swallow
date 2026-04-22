---
author: codex
phase: 36
slice: all
status: final
depends_on:
  - docs/plans/phase36/kickoff.md
  - docs/plans/phase36/review_comments.md
  - docs/concerns_backlog.md
---

## TL;DR
Phase 36 已完成实现、slice 拆 commit、review 与 PR 收口准备，当前状态为 **merge ready / PR sync ready**。本轮集中消化了 `concerns_backlog` 中 5 条积压 Open concern：S1 将 `LibrarianExecutor` 的持久化副作用收回 orchestrator，S2 批量清理 `acknowledge_task route_mode`、`canonical_write_guard` 运行时审计、stage-promote preflight 返回类型说明和 Codex FIM 标记转义。Claude review 结论为 `0 BLOCK / 1 CONCERN / 0 NOTE / Merge ready`，唯一新增 C1 已记录回 backlog。全量回归基线为 `253 passed in 5.95s`。

# Phase 36 Closeout

## 结论

Phase 36 `Concern Cleanup + LibrarianExecutor Refactoring` 已完成实现、review 与验证，当前分支状态为 **merge ready / PR sync ready**。

本轮没有引入新功能，而是集中清理跨多个 phase 累积的内部 concern，并修正一处已经偏离 Phase 31 原则的实现：

- S1 将 `LibrarianExecutor.execute()` 从“直接落盘 + 修改 state”的模式收回为“只返回 `ExecutorResult + side_effects`”，由 orchestrator 统一应用持久化
- S2 将 4 条 API 级 concern 一次性消化，包括 `acknowledge_task` 的 `route_mode` 参数化、`canonical_write_guard` audit warning、preflight 返回类型说明与 Codex FIM 标记转义

Claude review 已完成，结论为 `0 BLOCK / 1 CONCERN / 0 NOTE / Merge ready`。唯一 concern 为 Librarian 持久化链路的原子性不足，属于既有 best-effort 模式的显式记录，不阻塞当前合并。

## 已完成范围

### Slice 1: LibrarianExecutor State Mutation 收口

- `src/swallow/models.py` 为 `ExecutorResult` 增加 `side_effects`
- `src/swallow/librarian_executor.py` 移除直接 `save_*` / `append_*` / `persist_*` 调用，改为返回结构化 side effects payload
- `src/swallow/orchestrator.py` 新增 `_apply_librarian_side_effects()`，统一执行知识决策、canonical 记录、wiki entry、state 与索引重建
- `tests/test_librarian_executor.py` 新增 executor 不直接落盘的断言，并保留端到端晋升路径等价性验证

对应 commit：

- `262dd71` `refactor(librarian): move promotion side effects into orchestrator`

### Slice 2: API Concern 批量消化

- `acknowledge_task(..., *, route_mode: str = "summary")` 现在支持 route mode override，默认行为保持兼容
- orchestrator 在非 librarian 且 `canonical_write_guard` 命中时写入 `task.canonical_write_guard_warning`
- `build_stage_promote_preflight_notices()` docstring 明确说明当前稳定返回 `list[dict[str, str]]`
- `CodexFIMDialect` 新增 `_escape_fim_markers()`，转义 task metadata 与 raw prompt 中的 FIM 标记
- `tests/test_cli.py` 与 `tests/test_dialect_adapters.py` 补齐上述 concern 的回归

对应 commit：

- `96d474a` `fix(api): clean up phase36 routing and dialect concerns`

## 与 kickoff 完成条件对照

### 已完成的目标

- `LibrarianExecutor.execute()` 内部不再调用任何 `save_*` / `append_*` / `persist_*`
- orchestrator 已接管 Librarian 路径全部持久化与 artifact/index 更新
- 新增测试验证 executor 本身不产生磁盘 side effect
- `acknowledge_task` 已支持可选 `route_mode`，默认 `"summary"` 保持兼容
- `canonical_write_guard` 已在运行时形成 audit warning event
- stage promote preflight 已具备明确 docstring 类型说明
- `CodexFIMDialect` 已对 `<fim_prefix>` / `<fim_suffix>` 做轻量转义
- 全量测试通过

### 未继续扩张的内容

以下方向仍明确不在本 phase 范围内：

- Librarian 事务性持久化 / WAL / checkpoint 机制
- Librarian 语义提纯、冲突仲裁、衰减管理
- acknowledge CLI surface 的额外 operator 体验扩展
- 新增 executor 类型、动态路由策略或更复杂的 runtime policy engine
- Ingestion Specialist 或其他依赖 Librarian 基线的新角色实现

## Stop / Go 判断

### Stop 判断

当前 phase 应停止继续扩张，理由如下：

- kickoff 定义的 S1 / S2 均已完成，并已按 slice 独立提交
- 5 条历史 Open concern 已全部被消化或明确落入 `Won't Fix / By Design`
- review 没有阻断项，唯一 concern 已记入 backlog
- 全量测试通过，当前分支已具备 PR sync / merge gate 条件

### Go 判断

下一步不应继续在 Phase 36 分支上顺手追加新的 Librarian 增强或控制面能力。应按如下顺序推进：

1. Human 用当前 `pr.md` 同步 PR 描述
2. Human 决定 merge
3. merge 完成后再切回 roadmap / system tracks 选择下一阶段

## 当前稳定边界

Phase 36 closeout 后，以下边界应视为当前实现候选的稳定 checkpoint：

- executor 只负责产出结果；Librarian 特殊路径的副作用统一由 orchestrator 应用
- `canonical_write_guard` 当前为 audit-only 事件，不是阻断式 enforcement
- `build_stage_promote_preflight_notices()` 仍是 CLI 内部稳定接口，不额外扩展兼容层
- Codex FIM 转义只处理协议标记本身，不做通用 HTML/XML escaping
- Librarian 持久化链路当前仍是 best-effort 顺序写入，不提供事务性恢复保证

## 当前已知问题

- `_apply_librarian_side_effects()` 的持久化与索引重建仍是顺序执行，如果中途失败可能出现 state 与 index 不一致；该项已记入 `docs/concerns_backlog.md`
- Phase 36 本身不引入新的 operator-facing 能力，因此当前不建议单独打 tag
- 真正的 codex 执行在当前环境中仍可能受 outbound network / WebSocket 限制影响

以上问题均不阻塞当前进入 merge 阶段。

## 测试结果

最终验证结果：

```text
253 passed in 5.95s
```

补充说明：

- `tests/test_librarian_executor.py` 覆盖 executor 纯净性与 orchestrator 持久化等价性
- `tests/test_cli.py` 覆盖 acknowledge override、canonical write guard warning 与 preflight structured notices
- `tests/test_dialect_adapters.py` 覆盖 Codex FIM 标记转义

## 规则文件同步检查

### 必查

- [x] `docs/plans/phase36/closeout.md`
- [x] `docs/plans/phase36/review_comments.md`
- [x] `docs/plans/phase36/kickoff.md`
- [x] `docs/active_context.md`
- [x] `current_state.md`
- [x] `./pr.md`

### 条件更新

- [ ] `AGENTS.md`
- [ ] `README.md`
- [ ] `README.zh-CN.md`

说明：

- 本轮不改变长期协作规则与对外使用方式，因此无需同步 `AGENTS.md` / README
- `docs/concerns_backlog.md` 已包含 review 唯一 concern 的状态同步

## Git / PR 建议

1. 使用当前根目录 `pr.md` 作为 PR 描述草案
2. Human push `feat/phase36-concern-cleanup`
3. PR 描述同步当前 review disposition 与 C1 backlog 记录
4. Human 继续 merge 决策

## 下一轮建议

如果 Phase 36 merge 完成，下一轮应回到 `docs/roadmap.md` / `docs/system_tracks.md` 选择新的正式 phase，而不是继续在当前分支上扩张 Librarian 或 concern cleanup 主题。
