---
author: claude
phase: 20
slice: mock-dispatch-and-execution-gating
status: draft
depends_on:
  - docs/plans/phase20/design_decision.md
---

**TL;DR**: Phase 20 整体中风险。核心风险在 Slice 2（orchestrator 拦截点），因为 orchestrator.py 是 49KB 大文件，插入拦截逻辑可能影响现有 local 执行路径。无高风险项，关键缓解措施是"local 路径零改动"原则。

---

# Risk Assessment — Phase 20

## 风险矩阵

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 等级 |
|-------|---------|--------|-----------|------|------|
| 1: Dispatch decision function | 1 (新增纯函数) | 1 (轻松回滚) | 1 (无外部依赖) | 3 | 低 |
| 2: Orchestrator interception | 2 (单模块) | 1 (轻松回滚) | 2 (依赖内部模块) | 5 | 中 |
| 3: MockRemoteExecutor + 测试 | 2 (双模块) | 1 (轻松回滚) | 2 (依赖内部模块) | 5 | 中 |

**无高风险项（≥7 分）。**

---

## Slice 2 中风险详细分析

### 风险点
- `orchestrator.py` 是 49KB 大文件，`run_task()` 是核心执行路径
- 插入 dispatch 拦截逻辑的位置选择不当可能导致现有 local 任务流程回归
- Gemini 在 context_brief 中也标注了此风险："极易对原有的纯本地同步执行工作流造成破坏"

### 缓解措施
1. **零改动原则**：`evaluate_dispatch_verdict()` 返回 `local` 时，代码路径必须与 Phase 19 完全一致——用 early return 或 if 分支实现，不要重构现有流程
2. **单一插入点**：拦截逻辑应集中在一个函数调用中（如 `check_dispatch_verdict(state)`），不要在 orchestrator 中散布多个判断
3. **现有测试全量回归**：Slice 2 完成后，115+ 现有测试必须全部通过，任何失败都是 blocker
4. **Codex 实现前应先定位 run_task() 中 route selection 和 executor 调用之间的确切位置**

### 最坏情况
- 拦截逻辑误判 local 任务为 blocked → 现有测试会立即捕获
- 完全可通过 revert 单个 commit 回滚

---

## Slice 3 中风险详细分析

### 风险点
- MockRemoteExecutor 可能诱导后续开发者在上面堆积行为，从测试工具变成伪 remote executor
- 新增 `mock-remote` route 可能与现有 route selection 逻辑产生冲突

### 缓解措施
1. **明确标注**：MockRemoteExecutor 的 docstring 和 design_decision 都标注它是测试工具
2. **不修改现有 route**：`mock-remote` 是新增 route，不修改 `local-codex` / `local-mock` / `local-note` / `local-summary` 的任何行为
3. **接口一致性**：MockRemoteExecutor 必须遵循现有 Executor 抽象接口，不为 mock 修改接口定义

### 最坏情况
- mock route 被误选中 → route selection 默认仍是 local-codex，mock-remote 只在显式指定时使用
- 完全可通过 revert 回滚

---

## Gemini 标注风险的补充回应

### 风险 1："本地执行回归风险"
→ 已纳入 Slice 2 的零改动原则和全量测试回归要求

### 风险 2："Executor 接口散逸"
→ 已纳入 Slice 3 的接口一致性约束

### 补充风险 3："MockRemoteExecutor 温床化"
→ 已在 design_decision 非目标中显式标注"测试工具，不是演进路径"

---

## 整体评估

Phase 20 的风险主要集中在"不要破坏现有东西"。三个 slice 都是新增逻辑，不删改现有代码，回滚成本极低。只要守住"local 路径零改动"和"现有测试全量通过"两条底线，风险可控。
