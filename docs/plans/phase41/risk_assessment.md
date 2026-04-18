---
author: claude
phase: 41
slice: librarian-consolidation
status: draft
depends_on:
  - docs/plans/phase41/kickoff.md
---

> **TL;DR** Phase 41 整体风险 10/18（低-中）。两个 slice 互不耦合。S1 关注原子替换的故障路径覆盖，S2 为纯重构需确保行为零变更。

# Phase 41 Risk Assessment

## 风险矩阵

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 风险等级 |
|-------|---------|--------|-----------|------|---------|
| S1: Librarian 持久化原子化 | 2 — Librarian + store | 1 — 轻松回滚 | 2 — 多文件写入顺序 | **5** | 中 |
| S2: Debate loop 核心提取 | 2 — 单任务 + 子任务 | 1 — 轻松回滚 | 2 — 回调参数化 | **5** | 中 |

**总分: 10/18** — 无高风险 slice。两个 slice 互不依赖，风险互不传染。

## 各 Slice 风险详述

### S1: Librarian 持久化原子化

**关注点**：

1. **os.replace 的跨平台行为**：`os.replace()` 在 POSIX 上是原子操作（rename syscall），在 Windows 上也原子（ReplaceFile）。当前系统运行在 Linux WSL2 上，无跨平台问题。
2. **tmp 文件清理**：如果进程在 write-tmp 之后、os.replace 之前被 kill，会留下孤儿 `.tmp` 文件。这些文件不影响系统正确性（下次写入会覆盖），但建议在 `_apply_librarian_side_effects` 入口处清理 stale tmp 文件。
3. **append 操作的幂等性**：步骤 1-2（append knowledge_decision / canonical_record）不做原子化。重复 append 会多一条记录，但 canonical_registry 的 dedupe 机制（`build_staged_canonical_key`）会处理。需确认 append 操作的重复执行不会导致语义错误。

**缓解措施**：
- 测试应模拟 os.replace 在不同步骤失败的场景
- 验证重复 append 后 canonical dedupe 仍正常工作

### S2: Debate loop 核心提取

**关注点**：

1. **回调签名设计**：`_debate_loop_core()` 的回调参数需要足够灵活以覆盖单任务和子任务的差异，但不能过度参数化导致函数签名比原始代码更难理解。建议限制回调数量 ≤5。
2. **行为零变更验证**：重构后现有测试（`test_debate_loop.py` 的 2 个测试 + `test_run_task_subtasks.py` 的 3 个测试）必须零修改通过。如果需要修改测试才能通过，说明行为发生了变更。
3. **事件 payload 一致性**：提取后每个事件的 payload 字段必须与提取前完全一致（包括字段顺序不影响，但字段名和值必须不变），否则 Meta-Optimizer 的事件扫描会受影响。

**缓解措施**：
- S2 实现前先 snapshot 当前所有 debate 相关测试的输出，实现后 diff 验证
- 回调设计优先简单，如果 ≤5 个回调无法覆盖差异，允许保留少量 if-else 分支而非继续拆分

## 与历史 Concern 的交互

本 phase 直接消化两条 concern：

| Concern | 消化方式 | 验证 |
|---------|---------|------|
| Phase 36 C1: save_state → index 一致性 | S1 原子替换 | 模拟中间失败，验证文件不残留 |
| Phase 40 C1: debate 代码重复 | S2 提取共享函数 | 现有测试零修改通过 |

不影响其他 Open concern（Phase 38 C1、Phase 40 C2 留待 Phase 42 消化）。

## 整体判断

Phase 41 为低-中风险的内核优化工作。两个 slice 互不耦合，可并行实现但建议顺序推进以控制 review 复杂度。无需额外设计 gate。
