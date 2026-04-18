---
author: claude
phase: 41
slice: librarian-consolidation
status: final
depends_on:
  - docs/plans/phase41/kickoff.md
  - docs/plans/phase41/risk_assessment.md
---

> **TL;DR** Phase 41 review: 0 BLOCK / 0 CONCERN / 1 NOTE。Merge ready。S1 原子持久化 + 故障回滚验证完备，S2 debate loop 核心提取行为零变更。303 tests passed。

# Phase 41 Review Comments

## Review Scope

- 对照 `docs/plans/phase41/kickoff.md` 的方案拆解
- 对照 `docs/design/*.md` 架构原则一致性
- 测试覆盖充分性
- Phase scope 守界检查

## Checklist

### S1: Librarian 持久化原子化

- [PASS] `apply_atomic_text_updates()` 在 `store.py` 中实现为通用原子批量写入函数（write-tmp + os.replace），支持 updates + deletes
- [PASS] 故障回滚路径实现：replace 失败时逐步恢复已替换文件，使用 `.restore` 临时文件 + `os.replace` 回写
- [PASS] stale tmp 文件清理：入口处清理 `.tmp` 和 `.restore` 孤儿文件
- [PASS] `_persist_librarian_atomic_updates()` 将 state / knowledge_objects / evidence entries / wiki entries / partition / index / canonical_registry_index / canonical_reuse_policy 纳入同一批次原子提交
- [PASS] `_build_knowledge_store_write_plan()` 正确计算 knowledge store 的增量更新（新增/更新 entries）和删除（orphan entries）
- [PASS] `_apply_librarian_side_effects()` 中步骤 1-2（append 操作）保持不变，仅步骤 3-4 改为原子替换 — 符合 kickoff 设计
- [PASS] 回滚测试 `test_run_task_rolls_back_librarian_atomic_files_when_replace_fails`：模拟 `knowledge_index.json` 的 `os.replace` 失败，验证所有 6 个文件恢复到原始内容，无残留 `.tmp` / `.restore` 文件
- [PASS] 现有 Librarian 集成测试通过（promotion 端到端 + knowledge 晋升 + canonical record 写入）

### S2: Debate Loop 核心提取

- [PASS] `_debate_loop_core()` 提取完成，接收 7 个回调参数：`run_attempt` / `clear_feedback_state` / `store_feedback` / `apply_feedback` / `append_round_event` / `persist_exhausted` / `append_breaker_event`
- [PASS] `_build_debate_last_feedback()` 提取为共享 helper，消除单任务/子任务的 fallback feedback 构建重复
- [PASS] `_run_single_task_with_debate()` 现在通过准备回调后调用 `_debate_loop_core()` 实现
- [PASS] 子任务路径中的 `_run_subtask_debate_retries()` 已被移除/替换为通过 `_debate_loop_core()` 的统一实现
- [PASS] 现有 debate loop 测试全部通过：`test_debate_loop.py`（成功重试 + 熔断）+ `test_run_task_subtasks.py`（targeted retry + 熔断 waiting_human + executor failure 非 debate）— 行为零变更
- [PASS] 事件 payload 保持一致：`task.debate_round` / `task.debate_circuit_breaker` / `subtask.{idx}.debate_round` / `subtask.{idx}.debate_circuit_breaker` 的 payload 字段不变

### Concern 消化

- [PASS] Phase 36 C1（save_state → index 一致性）已从 Open 移入 Resolved，消化方式为 S1 原子批量提交
- [PASS] Phase 40 C1（debate 代码重复）已从 Open 移入 Resolved，消化方式为 S2 提取 `_debate_loop_core()`

### 架构一致性

- [PASS] Librarian side-effect 收口原则保持：LibrarianExecutor 仅返回 side_effects dict，orchestrator 接管全部持久化
- [PASS] 原子替换使用 `os.replace`（POSIX 原子 rename），不引入 WAL — 符合 kickoff 非目标
- [PASS] debate loop 行为语义不变（max_rounds / 熔断 / 事件类型）— 符合 kickoff 非目标

### Scope 守界

- [PASS] 无越界实现：不修改 LibrarianExecutor.execute()、不修改 ReviewGate/ReviewFeedback、不引入 WAL

## NOTE

### N1: 测试环境已就绪，自动测试已执行

全量 `pytest` 通过：303 passed, 5 subtests passed in 6.72s。无回归。

## 结论

**Merge ready**。S1 原子持久化覆盖了 kickoff 定义的故障恢复路径，回滚测试验证充分。S2 debate loop 提取为纯重构，行为零变更，现有 5 个 debate 测试零修改通过。两条 concern 已消化并记入 Resolved。当前 Open concern 剩余 2 条（Phase 38 C1 + Phase 40 C2），计划在 Phase 42 消化。
