---
author: claude
phase: 34
slice: all
status: draft
depends_on: [docs/plans/phase34/kickoff.md]
---

> **TL;DR**: Phase 34 实现质量整体良好，3 个 slice 均满足 kickoff 验收标准。0 BLOCK，3 CONCERN，1 NOTE。测试 244 passed。建议 commit 分 slice 拆分后合并。

# Phase 34 Review — Strategy Router + Dialect Adapters + Binary Fallback

## 审查范围

- **分支**: `feat/phase34-strategy-router`
- **Commits**: 2 (docs init + implementation)
- **变更量**: +1412 / -280 lines, 16 files
- **测试结果**: 244 passed, 5 subtests, 5.80s

---

## Slice 完成矩阵

| Slice | Kickoff 标准 | 实际交付 | 状态 |
|-------|-------------|---------|------|
| S1: RouteRegistry + Strategy Router | RouteRegistry 替代 BUILTIN_ROUTES；select_route 升级为能力匹配 | RouteRegistry class 实现 register/get/candidate_routes；四级匹配策略（exact → family+site → capability → summary fallback） | **[PASS]** |
| S2: Claude XML + Codex FIM Adapters | 两个 concrete adapter 实现并注册 | `dialect_adapters/` 子模块含 ClaudeXMLDialect + CodexFIMDialect；executor.py 注册并更新 resolve_dialect_name 为子串匹配 | **[PASS]** |
| S3: Binary Fallback + Integration | RouteSpec 含 fallback_route_name；executor 失败触发一次降级 | fallback_route_name 字段添加；_run_binary_fallback 实现单次降级 + 事件记录 + 产物前缀隔离 | **[PASS]** |

---

## 架构一致性审查

### S1: RouteRegistry

**[PASS] 设计一致性**
- `RouteRegistry` 封装了路由注册/查询/优先级排序，替代了原 `BUILTIN_ROUTES` dict
- 四级候选策略（exact_route_name → exact_executor → family_site → capability → summary_fallback）符合 kickoff 设计
- `_filter_capability_matches` 对 6 个能力字段逐项比较，语义清晰
- `ROUTE_REGISTRY` 模块级单例通过 `_build_builtin_route_registry()` 构建，5 条内置路由与旧版完全等价

**[PASS] 重构质量**
- `_apply_route_spec_to_state()` 抽取消除了 3 处 12 行重复赋值（create_task、acknowledge_task、run_task）
- `_dispatch_status_for_transport()` 抽取消除了 1 处 inline if-chain
- 所有既有路由保留了原始字段值，回归安全

### S2: Dialect Adapters

**[PASS] 设计一致性**
- `ClaudeXMLDialect` 使用 `xml.sax.saxutils.escape` 进行 XML 转义，防注入
- `CodexFIMDialect` 仅在 `execution_kind == "code_execution"` 时激活 FIM 格式，否则 passthrough raw prompt
- `resolve_dialect_name` 从 `==` 精确匹配改为 `in` 子串匹配，使 "claude-3-5-sonnet" 能匹配 "claude" hint
- `PlainTextDialect.supported_model_hints` 移除了 "codex"，避免与 CodexFIMDialect 冲突

**[PASS] 架构对齐**
- 新 `dialect_adapters/` 子模块符合 kickoff 提出的 "gateway 语义转换层" 定位
- 通过 `BUILTIN_DIALECTS` dict 注册，与既有 PlainText/StructuredMarkdown 一致

### S3: Binary Fallback

**[PASS] 设计一致性**
- `_run_binary_fallback` 在 executor_result.status == "failed" 时触发，位于 ReviewGate 之前
- 单次降级：fallback 路由自身无 fallback_route_name，不会链式降级
- 产物前缀隔离：primary → `fallback_primary_*`，fallback → `fallback_*`
- `task.execution_fallback` 事件记录包含完整上下文（previous/fallback 路由、状态、能力约束）

**[PASS] 与 Phase 33 SubtaskOrchestrator 边界**
- Fallback 仅在单卡路径触发（`_execute_task_card` 返回后检查），多卡路径通过 `_run_subtask_orchestration` 走 ReviewGate retry
- 这符合 kickoff 的 "executor 级别降级 vs review 级别重试" 分层设计

---

## 测试覆盖审查

| 文件 | 新增测试数 | 覆盖评价 |
|------|-----------|---------|
| test_router.py | 5 | 四级匹配策略全覆盖，但缺少多候选排序/冲突场景 |
| test_dialect_adapters.py | 3 | Claude XML + Codex FIM + passthrough 验证，基本足够 |
| test_binary_fallback.py | 2 | 成功降级 + 失败降级，artifact 和 event 验证充分 |
| test_cli.py | ~15 处修改 | 既有测试适配新行为（codex failure → fallback → completed），回归安全 |

**总体**: 244 passed，无 skip/xfail，新功能核心路径有覆盖。

---

## CONCERN

### C1: CodexFIMDialect 缺少用户输入转义 [CONCERN]

**位置**: `src/swallow/dialect_adapters/codex_fim.py:30-37`

CodexFIMDialect 的 `format_prompt` 直接将 `state.task_id`、`state.title`、`state.goal` 等字段嵌入 FIM 结构，未做任何转义。虽然 FIM 标记 (`<fim_prefix>`, `<fim_suffix>`) 不是 XML 而是模型协议标记，但如果 task title 包含这些标记字符串，可能导致 prompt 结构混乱。

**当前影响**: 低。task title 由操作员创建，非外部用户输入。
**建议**: 记入 concerns_backlog，当引入外部用户输入的 task 创建路径时消费。

### C2: create_task 中 executor_name 覆盖顺序 [CONCERN]

**位置**: `src/swallow/orchestrator.py:910-911`

```python
_apply_route_spec_to_state(state, initial_route.route, initial_route.reason)
state.executor_name = normalize_executor_name(executor_name)
```

`_apply_route_spec_to_state` 会设置 `state.executor_name = route.executor_name`，随后立即被 `normalize_executor_name(executor_name)` 覆盖。虽然功能正确（用户传入的 executor_name 应优先），但语义上 `_apply_route_spec_to_state` 的 `update_executor_name` 参数存在正是为了这个场景，此处应使用 `update_executor_name=False`。

**当前影响**: 无功能缺陷，纯代码清晰度问题。
**建议**: Codex 在 commit 时修正为 `_apply_route_spec_to_state(..., update_executor_name=False)`。

### C3: 既有测试行为变更需确认意图 [CONCERN]

**位置**: `tests/test_cli.py` 多处

原先 codex binary 不存在时 task 结果为 `status: "failed"`，现在因 binary fallback 自动降级到 local-summary 变为 `status: "completed"`。这是设计意图的正确体现，但改变了以下语义：

- `test_codex_missing_binary_run_produces_failure_artifacts` → 现在产出 completed 而非 failed
- `test_run_task_lifecycle_events_are_complete` → 事件链多了 `executor.completed` + `task.execution_fallback`
- `test_run_task_resume_from_failure_replays_lifecycle` → 两次 run 均从 failed → completed

所有修改均与 binary fallback 语义一致，但建议在 commit message 中明确说明此行为变更，避免后续 oncall 审查时产生困惑。

---

## NOTE

### N1: 单 commit 包含全部 3 个 slice

当前实现 commit `8872e89` 包含 S1+S2+S3 全部变更（+1412/-280）。按 AGENTS.md 规范，建议拆分为：

1. **S1 commit**: `feat(router): replace BUILTIN_ROUTES with RouteRegistry and capability-matching selection` — router.py + models.py (fallback_route_name) + test_router.py
2. **S2 commit**: `feat(dialect): add ClaudeXMLDialect and CodexFIMDialect adapters` — dialect_adapters/ + executor.py 注册 + test_dialect_adapters.py
3. **S3 commit**: `feat(fallback): implement binary fallback on primary executor failure` — orchestrator.py fallback 逻辑 + test_binary_fallback.py + test_cli.py 修改

Human 可在 interactive rebase 中按文件拆分，或由 Codex 重新提交。

---

## 回归安全确认

- 244 tests passed, 0 skips, 0 xfails
- 5 条内置路由字段值与旧 `BUILTIN_ROUTES` 完全一致（除新增 `dialect_hint` 显式化和 `fallback_route_name`）
- `local-codex` 的 `dialect_hint` 从 `"structured_markdown"` 改为 `"codex_fim"` — 这是设计意图，非回归
- `PlainTextDialect.supported_model_hints` 移除 `"codex"` — 正确，避免与 CodexFIMDialect 冲突

---

## 结论

**Merge ready — 0 BLOCK, 3 CONCERN, 1 NOTE**

建议 Human 按 N1 指引决定 commit 拆分策略后合并。C1/C2 为低优先级代码清晰度问题，可在当前或后续 phase 消费。C3 要求 commit message 显式说明行为变更。
