---
author: claude/consistency-checker
phase: phase64
slice: route-externalization-consistency-check
status: draft
depends_on:
  - "docs/plans/phase64/commit_summary.md"
  - "docs/plans/phase64/kickoff.md"
  - "docs/plans/phase64/design_decision.md"
  - "docs/plans/phase64/design_audit.md"
  - "docs/design/INVARIANTS.md"
---

TL;DR: 7 consistent, 0 inconsistent, 1 not-covered — all seven check points pass; one loading-order gap in `cli.py:route select` merits a note but does not violate an invariant.

## Consistency Report

### 检查范围

- 对比对象: `git diff main...HEAD` 中 900c38b + c404f3e 两个 follow-up commit vs `docs/plans/phase64/commit_summary.md` §外部化分层 + `docs/design/INVARIANTS.md` §0/§4/§5/§9
- 核查文件: `src/swallow/cli.py`, `src/swallow/governance.py`, `src/swallow/truth/route.py`, `src/swallow/router.py`, `src/swallow/orchestrator.py`, `src/swallow/models.py`, `tests/test_invariant_guards.py`

---

### 一致项

- [CONSISTENT] **CP1 — apply_proposal 是 route metadata 写入唯一入口**。`save_route_registry` / `save_route_policy` 仅在 `src/swallow/router.py` 与 `src/swallow/truth/route.py` 内定义或调用。`test_route_metadata_writes_only_via_apply_proposal` 与 `test_only_apply_proposal_calls_private_writers` 均将 `save_route_policy` 纳入 `protected_names`，且两个守卫的 `allowed_files` 与实际代码调用图完全匹配（`test_invariant_guards.py` line 192–200 / line 218–236）。CLI 未直接调用任何 save 函数，确认符合 INVARIANTS §0 第 4 条。

- [CONSISTENT] **CP2 — Phase 63 Repository 写边界守卫保持有效**。`test_only_governance_calls_repository_write_methods`、`test_no_module_outside_governance_imports_store_writes`、`test_only_apply_proposal_calls_private_writers` 三条守卫均在 `tests/test_invariant_guards.py`（line 207–214 / line 216–252 / line 196–204）中 active，无 `pytest.skip`。`save_route_policy` 已加入全部相关 `protected_names` 集合。commit_summary 验证记录显示 66 passed。

- [CONSISTENT] **CP3 — 无新增 ProposalTarget 枚举值**。`governance.py:23–26` 中 `ProposalTarget` 仍只有三个值：`CANONICAL_KNOWLEDGE` / `ROUTE_METADATA` / `POLICY`。`route_policy` 写入路径为 `register_route_metadata_proposal(..., route_policy=...) -> apply_proposal(..., ProposalTarget.ROUTE_METADATA)` (`cli.py:2662–2667`)，与 commit_summary 第 88 行描述完全一致，未引入 `ProposalTarget.POLICY` 或新值。

- [CONSISTENT] **CP4 — INVARIANTS.md / DATA_MODEL.md 未改动**。`git diff main...HEAD -- docs/design/INVARIANTS.md docs/design/DATA_MODEL.md` 无输出，与 commit_summary 验证记录 "git diff -- docs/design/INVARIANTS.md docs/design/DATA_MODEL.md -> no output" 一致。

- [CONSISTENT] **CP5 — Phase 64 S1/S2 主线边界未破坏**。`executor.py` 只 import `lookup_route_by_name`（line 513），未出现 `select_route` / `route_by_name` / `fallback_route_for` / `route_for_mode`。`agent_llm.py:21` 中 `call_agent_llm` 退化为 `invoke_completion` thin caller。`test_path_b_does_not_call_provider_router`（`test_invariant_guards.py` line ~340）与 `test_specialist_internal_llm_calls_go_through_router`（line ~380）均 active 且通过。

- [CONSISTENT] **CP6 — Registry / Policy 加载顺序正确**。在 `orchestrator.py`（line 2492–2496、2632–2636、3326–3330）与 `cli.py`（line 2347–2351、2776–2780）中，调用顺序均为 `apply_route_registry` → `apply_route_policy` → `apply_route_weights` → `apply_route_fallbacks` → `apply_route_capability_profiles`，与 commit_summary 描述的 "registry 先于 weights / fallback / capability overlay 加载，policy 在 registry 之后" 完全一致。

- [CONSISTENT] **CP7 — 无新 OperatorToken source、无 RouteSpec schema 变化、无新 SQLite 表**。`models.py` diff 只增加 `fallback_route_chain: tuple[str, ...] = ()` 字段于 `TaskState`（非 `RouteSpec`）；`routes.default.json` 字段集合（`name`, `executor_name`, `backend_kind`, `model_hint`, `dialect_hint`, `fallback_route_name`, `quality_weight`, `task_family_scores`, `unsupported_task_types`, `executor_family`, `execution_site`, `remote_capable`, `transport_kind`, `capabilities`, `taxonomy`）与 `models.py:988` 处 `RouteSpec` 字段定义完全对应，schema 无新增字段。未发现新 SQLite `CREATE TABLE` 语句。`OperatorToken(source="cli")` 为既有用法，未引入新 source 值。

---

### 不一致项

无。

---

### 未覆盖项

- [NOT_COVERED] **`cli.py:route select` 子命令中 `apply_route_policy` 的注入时机晚于 `apply_route_registry`**。在 `cli.py:2776–2780` 的 `route select` 路径中，`apply_route_policy` 位于 `apply_route_registry` 之后第二位，顺序正确。然而 commit_summary §外部化分层 Layer 3 只描述了 "CLI apply 路径通过 apply_proposal 写入 `.swl/route_policy.json`"，未显式说明 `route select` 子命令中需要同步加载 policy。实际代码已正确实装，但 commit_summary 对该点未作明确说明，属文档未覆盖而非实现问题。
