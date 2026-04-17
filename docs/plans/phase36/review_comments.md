---
author: claude
phase: 36
slice: all
status: final
depends_on: [docs/plans/phase36/kickoff.md]
---

> **TL;DR**: Phase 36 实现质量良好，5 条 Open concern 全部消化。0 BLOCK，1 CONCERN，0 NOTE。测试 253 passed。concerns_backlog Open 清零。

# Phase 36 Review — Concern Cleanup + LibrarianExecutor State Mutation 收口

## 审查范围

- **分支**: `feat/phase36-concern-cleanup`
- **Commits**: 3 (docs init + S1 librarian refactor + S2 API cleanup)
- **变更量**: +474 / -66 lines, 10 files
- **测试结果**: 253 passed, 5 subtests, 6.15s

---

## Slice 完成矩阵

| Slice | Kickoff 标准 | 实际交付 | 状态 |
|-------|-------------|---------|------|
| S1: LibrarianExecutor 收口 | execute() 内部不再调用任何 save_*/append_*/persist_*；orchestrator 接管全部持久化 | execute() 返回 `ExecutorResult` + `side_effects` dict；新增 `_apply_librarian_side_effects()` 在 orchestrator 中执行 8 处持久化；测试验证 executor 不产生磁盘 side effect | **[PASS]** |
| S2a: acknowledge route_mode | 函数签名增加可选 route_mode 参数 | `acknowledge_task(..., *, route_mode: str = "summary")` keyword-only 参数，默认值保持兼容 | **[PASS]** |
| S2b: canonical_write_guard | 非 Librarian executor 路径触发 warning event | `_append_canonical_write_guard_warning()` 检查 `state.route_capabilities["canonical_write_guard"]`，非 librarian 时产生 `task.canonical_write_guard_warning` 事件 | **[PASS]** |
| S2c: preflight 返回类型 | 补充 docstring 说明 | docstring 明确记录 `list[dict[str, str]]` 返回类型及设计意图 | **[PASS]** |
| S2d: CodexFIMDialect 转义 | 对 task_id/title/goal 中的 FIM 标记转义 | `_escape_fim_markers()` 将 `<fim_prefix>` → `[fim_prefix]`，应用于 task_id/title/goal/raw_prompt | **[PASS]** |

---

## 架构一致性审查

### S1: LibrarianExecutor 收口

**[PASS] Phase 31 原则修正**
- `LibrarianExecutor.execute()` 现在返回 `ExecutorResult` + `side_effects` dict，包含 `updated_knowledge_objects` / `knowledge_decision_records` / `canonical_records` / `change_log_payload`
- executor 内部零 state mutation 调用——通过 `test_librarian_executor_returns_side_effect_plan_without_persisting` 验证磁盘无写入
- `_apply_librarian_side_effects()` 在 orchestrator 中按正确顺序执行：append_knowledge_decision → append_canonical_record + persist_wiki_entry → save_state → save_knowledge_objects → rebuild index/partition/reuse_policy
- 集成测试 `test_run_task_promotes_local_promotion_ready_evidence_with_librarian_executor` 验证端到端产出等价性

**[PASS] 防御性设计**
- `_apply_librarian_side_effects()` 在 executor_name != "librarian" 或 status != "completed" 时提前返回
- side_effects 中每个字段都有 `isinstance` 类型检查，防止 malformed payload

### S2: API Concern 批量

**[PASS] acknowledge route_mode**
- keyword-only 参数设计正确，防止位置参数误用
- 通过 `normalize_route_mode()` 处理，与既有 route_mode 处理一致

**[PASS] canonical_write_guard**
- 仅记录 warning event（audit mode），不阻断执行，与 concern 原始描述一致
- 事件 payload 包含完整上下文（executor_name / route_name / taxonomy 信息）

**[PASS] preflight docstring**
- 明确记录了返回类型变更的设计意图

**[PASS] FIM 转义**
- `_escape_fim_markers()` 简洁有效，覆盖 task_id / title / goal / raw_prompt
- 使用方括号替代尖括号（`[fim_prefix]`），不影响可读性

---

## 测试覆盖审查

| 文件 | 新增测试 | 覆盖评价 |
|------|---------|---------|
| test_librarian_executor.py | 2 (side effect 验证 + 端到端晋升) | 核心路径覆盖充分：executor 纯净性 + orchestrator 持久化等价性 |
| test_cli.py | ~10 (acknowledge 4 + route_mode 5 + write_guard 1 + preflight 2) | 覆盖面广，包含正常/异常/override/enforcement 场景 |
| test_dialect_adapters.py | 1 (FIM 转义) | 验证 user-controlled input 注入防护，断言精确 |

**总体**: 253 passed（较 Phase 35 的 249 新增 4 个测试），核心验收路径全覆盖。

---

## CONCERN

### C1: _apply_librarian_side_effects 中 save_state 与后续 index 重建的原子性 [CONCERN]

**位置**: `src/swallow/orchestrator.py:275-281`

`_apply_librarian_side_effects()` 按顺序执行 save_state → save_knowledge_objects → save_knowledge_partition → save_knowledge_index → save_canonical_registry_index → save_canonical_reuse_policy。如果中间某步失败（如磁盘空间不足），会导致 state 已持久化但 index/partition 未更新的不一致状态。

**当前影响**: 低。原 LibrarianExecutor 内部也是同样的顺序执行，无原子性保证；本次重构未改变这一行为模式。
**建议**: 记入 concerns_backlog，在引入事务性 checkpoint 或 WAL 机制时消化。当前为已知的 best-effort 持久化模式。

---

## 回归安全确认

- 253 tests passed, 0 skips, 0 xfails
- LibrarianExecutor 重构前后产出等价性通过端到端测试验证
- acknowledge_task 默认值 `"summary"` 保持向后兼容
- canonical_write_guard 为 audit-only，不影响既有执行路径
- FIM 转义仅作用于 code_execution 路径，non-code 路径 passthrough 不变

---

## Concerns Backlog 消化确认

| Backlog 条目 | 处置 | 状态 |
|-------------|------|------|
| Phase 32 S3: LibrarianExecutor state mutation | S1 直接消化 | → Resolved |
| Phase 21 Slice 2: acknowledge route_mode 硬编码 | S2a 参数化 | → Resolved |
| Phase 25 Slice 1: canonical_write_guard 无运行时执行 | S2b audit warning | → Resolved |
| Phase 28 Slice 3: preflight 返回类型变更 | S2c docstring + 确认无外部调用者 | → Won't Fix / By Design |
| Phase 34 S2: CodexFIMDialect FIM 转义 | S2d 轻量转义 | → Resolved |

**Open concern 从 5 条降为 0 条。** 本次 review 新增 1 条 C1（Librarian 持久化原子性），但优先级极低。

---

## 结论

**Merge ready — 0 BLOCK, 1 CONCERN, 0 NOTE**

Phase 36 完成了全部 5 条积压 concern 的消化，LibrarianExecutor 的 state mutation 已正确收回 orchestrator，Phase 31 架构原则得到修正。C1 为 pre-existing 行为模式的显式记录，不阻塞合并。

---

## Tag 评估

Phase 36 merge 后，建议**暂不打新 tag**。理由：

- Phase 36 是内部技术债清理，无用户可感知的能力增量
- 下一个 Phase 37 (Control Center) 将引入用户可感知的新入口（Web 控制台），更适合作为 v0.2.0 的里程碑
- 当前 v0.1.0 tag 仍准确描述系统的公共能力边界
