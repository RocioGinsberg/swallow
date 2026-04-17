---
author: claude
phase: 36
slice: concern-cleanup
status: draft
depends_on: [docs/roadmap.md, docs/plans/phase35/closeout.md, docs/concerns_backlog.md]
---

> **TL;DR**: Phase 36 集中消化 concerns_backlog 中 5 条积压 Open concern。S1 将 LibrarianExecutor 的 8 处 state mutation 收回 orchestrator（Phase 31 原则修正）；S2 批量处理 4 条 API 级 concern（acknowledge route_mode 参数化、canonical_write_guard 运行时检查、preflight 返回类型标注、CodexFIMDialect FIM 标记转义）。不引入新功能，不扩张 scope。

# Phase 36 Kickoff — Concern Cleanup + LibrarianExecutor State Mutation 收口

## 基本信息

- **Phase**: 36
- **Primary Track**: Core Loop
- **Secondary Track**: Retrieval / Memory
- **Phase 名称**: Concern Cleanup + LibrarianExecutor Refactoring

---

## 前置依赖与现有基础

- `docs/concerns_backlog.md` 中 5 条 Open concern 跨越 Phase 21/25/28/32/34，已超过"每 3-5 个 phase 回顾"的规则上限
- Phase 31 确立原则："executor 只产出 result，state mutation 归 orchestrator"
- Phase 32 的 `LibrarianExecutor.execute()` 在 `librarian_executor.py:287-327` 直接执行 8 处 state mutation，违反上述原则
- Phase 39 (Ingestion Specialist) 将进一步依赖 Librarian 路径，如果 side effect 仍散落在 executor 内部，并发场景会产生不可预测的状态覆盖
- 其余 4 条 concern 均为低风险 API 清理，不影响核心执行路径

---

## Phase 36 目标

消化全部 5 条 Open concern，将 concerns_backlog Open 清零。

---

## 非目标（明确排除）

| 排除项 | 理由 |
|--------|------|
| Librarian 语义提纯 / 冲突仲裁 / 衰减管理 | 属于后续 Librarian 增强，不在本轮 scope |
| 新增 executor 类型或路由策略 | 本轮只修正既有实现 |
| Ingestion Specialist | 依赖本轮 LibrarianExecutor 收口，但实现在 Phase 39 |
| 新增 CLI 命令或 operator 入口 | 本轮仅修改内部 API |
| acknowledge_task 的 UI/CLI 入口改造 | 仅参数化函数签名，CLI 层面的暴露延后 |

---

## Slice 拆解

### S1: LibrarianExecutor State Mutation 收口

**消化 concern**: Phase 32 S3 — `LibrarianExecutor.execute()` 直接操作 state + 多层持久化

**目标**: LibrarianExecutor 只返回 `ExecutorResult` + 结构化 payload（待写入的 knowledge decisions / canonical records / wiki entries），由 orchestrator 执行所有持久化。

**改动范围**:
- `src/swallow/librarian_executor.py`：重构 `execute()` 方法
  - 移除 8 处直接 state mutation 调用（`save_state` / `save_knowledge_objects` / `save_knowledge_partition` / `save_knowledge_index` / `save_canonical_registry_index` / `save_canonical_reuse_policy` / `append_knowledge_decision` / `append_canonical_record`）
  - 将 `persist_wiki_entry_from_record()` 调用移出
  - 在 `ExecutorResult` 的 payload 或新增返回字段中携带待持久化的数据
- `src/swallow/orchestrator.py`：在调用 LibrarianExecutor 后，orchestrator 接管所有持久化
  - 从 executor result 中提取 knowledge decisions / canonical records / wiki entries
  - 按顺序执行 append_knowledge_decision → append_canonical_record → persist_wiki_entry → save_state → save_knowledge_objects → 重建 index / partition / reuse policy
- `tests/` 相关文件：验证重构后 Librarian 执行路径的产出物和状态一致性

**验收标准**:
- `LibrarianExecutor.execute()` 内部不再调用任何 `save_*` / `append_*` / `persist_*` 函数
- orchestrator 中 Librarian 调用路径的最终 state / knowledge_objects / canonical_records / wiki 产出与重构前完全等价
- 既有 Librarian 相关测试全部 pass
- 新增至少 1 个测试验证 executor 不产生 side effect（类似 Phase 35 meta_optimizer 只读验证模式）

**风险**: 5/9（impact 2, reversibility 2, dependency 1）
- Librarian 执行路径是知识晋升的唯一入口，重构需要严格保证产出等价性
- 缓解：通过 snapshot 前后对比断言验证（knowledge_objects + canonical_records + wiki entries 内容一致）

---

### S2: API Concern 批量消化

**消化 concern**: Phase 21 / 25 / 28 / 34 的 4 条 API 级 concern

#### S2a: acknowledge_task route_mode 参数化（Phase 21）

**位置**: `src/swallow/orchestrator.py:837`

**当前**:
```python
state.route_mode = "summary"  # 硬编码
```

**改为**:
```python
def acknowledge_task(base_dir: Path, task_id: str, *, route_mode: str = "summary") -> TaskState:
```

默认值 `"summary"` 保持向后兼容，但允许调用方传入其他 mode。

#### S2b: canonical_write_guard 运行时检查（Phase 25）

**位置**: orchestrator 中 executor dispatch 前

**改动**: 在 `_execute_task_card()` 或等效位置增加 guard check：
- 如果 route 标记了 `canonical_write_guard` 且当前 executor 不是 LibrarianExecutor → 记录 warning event，不阻断执行（defensive audit，与当前 concern 描述一致——审计标记而非硬阻断）

#### S2c: preflight 返回类型标注（Phase 28）

**位置**: `src/swallow/cli.py` `build_stage_promote_preflight_notices()`

**改动**: 
- 补充函数 docstring 说明返回类型变更历史（`list[str]` → `list[dict[str, str]]`）
- 确认当前无外部调用者 → 在 concerns_backlog 中标记 Won't Fix / By Design（返回类型已稳定，无兼容性问题）

#### S2d: CodexFIMDialect FIM 标记转义（Phase 34）

**位置**: `src/swallow/dialect_adapters/codex_fim.py`

**改动**: 在 `format_prompt()` 中，对注入到 `<fim_prefix>` ... `<fim_suffix>` 区间内的用户可控字段（task_id / title / goal）进行 FIM 标记转义：
```python
# 将 "<fim_prefix>" → "[fim_prefix]"、"<fim_suffix>" → "[fim_suffix]"
escaped_title = title.replace("<fim_prefix>", "[fim_prefix]").replace("<fim_suffix>", "[fim_suffix]")
```

轻量转义，仅处理 FIM 协议标记，不做通用 HTML escaping。

**S2 整体验收标准**:
- `acknowledge_task` 接受可选 `route_mode` 参数，默认行为不变
- canonical_write_guard 在非 Librarian executor 路径触发时产生 warning event
- preflight 函数有 docstring 说明返回类型
- CodexFIMDialect 对 title/goal 中的 FIM 标记进行转义
- 既有测试全部 pass + S2 各项至少 1 个新增测试

**风险**: 2/9（impact 1, reversibility 1, dependency 0）—— 均为低风险 API 调整

---

## 依赖关系

```
S1 (LibrarianExecutor 收口) — 独立
S2 (API Concern 批量)       — 独立
```

S1 和 S2 无代码级依赖，可并行或按任意顺序执行。推荐先 S1 后 S2（S1 影响面更大，先验证稳定性）。

---

## 风险总览

| 维度 | S1 | S2 | 总体 |
|------|----|----|------|
| Impact Scope | 2 | 1 | — |
| Reversibility | 2 | 1 | — |
| Dependency Complexity | 1 | 0 | — |
| **Slice Total** | **5/9** | **2/9** | **7/18** |

**Phase 总体风险**: 低（7/18）

**R1**: S1 Librarian 重构回归 — 缓解：snapshot 前后对比断言（knowledge_objects + canonical_records + wiki entries）
**R2**: S2b canonical_write_guard 误触发 — 缓解：仅记录 warning event，不阻断执行

---

## Concerns Backlog 消化计划

| Backlog 条目 | 本轮处置 | Slice |
|-------------|---------|-------|
| Phase 32 S3: LibrarianExecutor state mutation | S1 直接消化 → Resolved | S1 |
| Phase 21 Slice 2: acknowledge route_mode 硬编码 | S2a 参数化 → Resolved | S2 |
| Phase 25 Slice 1: canonical_write_guard 无运行时执行 | S2b 增加 audit warning → Resolved | S2 |
| Phase 28 Slice 3: preflight 返回类型变更 | S2c 标注 + 确认无外部调用者 → Won't Fix / By Design | S2 |
| Phase 34 S2: CodexFIMDialect FIM 转义 | S2d 轻量转义 → Resolved | S2 |

**预期结果**: Open concern 从 5 条降为 0 条。
