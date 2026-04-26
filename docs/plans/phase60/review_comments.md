---
author: claude
phase: 60
slice: review
status: draft
depends_on:
  - docs/plans/phase60/design_decision.md
  - docs/plans/phase60/risk_assessment.md
  - docs/plans/phase60/kickoff.md
---

## TL;DR

Phase 60 实现与 design_decision 高度对齐，3 个 slice 全部完成，capability-based policy 判定 + Specialist guard + explicit override 三层语义清晰，长期设计文档（KNOWLEDGE/AGENT_TAXONOMY/ARCHITECTURE）同步刷新。1 个 BLOCK：`test_failed_task_events_include_failure_payloads` 因 CLI policy 收紧（`local-aider` 不再返回 notes/repo chunk）导致 `validation.completed` 状态从 `passed` 变成 `warning`，断言未同步更新。2 条 pre-existing 失败（`test_meta_optimizer.py` 中 `test_review_and_apply_approved_route_*`）是 Phase 59 alias 清理遗留，不属于 Phase 60。修复 BLOCK 后可直接进入收口。

# Phase 60 Review Comments

## 评审范围

- **分支**: `feat/phase60-retrieval-policy`（7 commits, 14 files, +1124/-65 lines）
- **对比基线**: `main`
- **设计文档**: `docs/plans/phase60/design_decision.md` + `risk_assessment.md` + `kickoff.md`
- **测试执行**: `.venv/bin/python -m pytest tests/ --ignore=tests/eval` — 532 passed / 3 failed（1 Phase 60 BLOCK + 2 pre-existing Phase 59 遗留）

---

## S1: Policy 表定义 + 自主 CLI coding path 收紧

### [PASS] `_RETRIEVAL_SOURCE_POLICY` 常量与 design 一致

`orchestrator.py:187-192`：
```python
_RETRIEVAL_SOURCE_POLICY: dict[tuple[str, str], tuple[str, ...]] = {
    ("autonomous_cli_coding", "*"): ("knowledge",),
    ("api", "*"): ("knowledge", "notes"),
    ("legacy_local_fallback", "*"): ("repo", "notes", "knowledge"),
    ("*", "*"): ("knowledge", "notes"),
}
```

- 4 条规则与 `design_decision.md` 完全一致
- 使用 `tuple` 作为不可变值（design 写的是 list，但 tuple 更安全，最终在 `_select_source_types()` 中转 list 返回——合理改良）
- 全局 fallback 为 `("knowledge", "notes")` 而非 `("repo", "notes", "knowledge")`，符合 kickoff §G3「repo source 显式化，不再作为 HTTP/未知 route 默认」

### [PASS] `_retrieval_policy_family()` capability-based 判定

`orchestrator.py:3168-3183`：
- `executor_family == "cli" + supports_tool_loop + execution_kind == "code_execution"` → `autonomous_cli_coding`
- 额外的 **Specialist guard**：仅当 `taxonomy_role in {"", "general-executor"}` 时才进入 autonomous bucket，避免 Specialist CLI route（如 `librarian`）被误归类
- `executor_family == "api"` → `api`（短路 capability 检查，符合设计）
- `cli + deterministic + not supports_tool_loop` → `legacy_local_fallback`（覆盖 `local-mock` / `local-summary` / `local-note` / `mock-remote`）
- 其余情况返回 `executor_family or "*"`，让查表逻辑 fallback 到 `("*", "*")`

Specialist guard 是 design_decision 没明确列出的实现细节，但完全符合 kickoff §G4 与 risk_assessment R2，是合理的边界收紧。

### [PASS] `_select_source_types()` 查表逻辑

`orchestrator.py:3186-3195`：
- 精确匹配 → 通配 `(family, "*")` → 全局 `("*", "*")` → 硬编码 `["knowledge", "notes"]` 兜底
- `task_family` 在写入 key 前 `strip().lower()` 归一化为 `"*"`（当为空时），与设计一致

### [PASS] `build_task_retrieval_request()` 改写

`orchestrator.py:3198-3209`：
- explicit override 优先：`semantics.get("retrieval_source_types")` → `normalize_retrieval_source_types()` → 若非空直接使用
- 否则查表选择：`_select_source_types(_retrieval_policy_family(state), infer_task_family(state))`
- 改动局部、不污染 `retrieve_context()` / `harness.py:run_retrieval()`，符合 design「policy 在 request 构造层」的核心决策

### [PASS] 测试覆盖：S1 全部分支

| 分支 | 测试 |
|------|------|
| autonomous CLI coding（local-codex） | `test_build_task_retrieval_request_uses_knowledge_only_for_autonomous_cli_coding_routes` |
| legacy local fallback（local-summary） | `test_build_task_retrieval_request_preserves_legacy_sources_for_non_autonomous_cli_fallback_routes` |
| HTTP（http-claude） | `test_build_task_retrieval_request_keeps_http_routes_off_repo_by_default` |
| 未知 / capabilities 缺失 | `test_build_task_retrieval_request_uses_conservative_default_when_route_capabilities_are_missing` |
| Specialist CLI guard | `test_build_task_retrieval_request_does_not_treat_specialist_cli_routes_as_autonomous_coding` |

5 个分支全部覆盖，断言精确。

---

## S2: HTTP path 显式规则 + task_family 覆盖

### [PASS] HTTP `("api", "*")` 默认聚焦 knowledge + notes

policy 表中 HTTP 通配条目为 `("knowledge", "notes")`，无 task_family 细分（design_decision 最终版也明确「不因 task_family 自动启用 repo」）。

### [PASS] task_family 跨样本测试

`test_build_task_retrieval_request_keeps_http_routes_off_repo_across_task_families`：
- 通过 `subTest` 遍历 `planning_session` / `review_feedback` / `operator_entry` / `knowledge_capture` / `retrieval_probe` 五种 source_kind
- 全部断言 `source_types == ["knowledge", "notes"]`，验证 HTTP 在所有 task_family 下都不自动开启 repo

### [PASS] `infer_task_family()` 未被修改

直接 `from .models import infer_task_family` 复用，符合 kickoff 非目标。

---

## S3: Explicit Override + 测试补全

### [PASS] `TaskSemantics.retrieval_source_types` 字段

`models.py:204`：
```python
retrieval_source_types: list[str] | None = None
```

- dataclass 字段，可选默认 `None`，与 design 一致
- `to_dict()` 通过 `asdict(self)` 自动序列化，无需额外处理

### [PASS] `normalize_retrieval_source_types()` 验证函数

`task_semantics.py:5-30`：
- ALLOWED 集合：`("repo", "notes", "knowledge", "artifacts")` ✓
- `None` 直通，非 list/tuple 抛 ValueError
- 非法 source_type 抛带提示信息的 ValueError
- 保序去重（`seen` set + 顺序写入 `normalized_items`）
- 空列表（normalize 后为空）抛 ValueError

边界处理严谨，与 design 一致。

### [PASS] `create_task()` / `update_task_planning_handoff()` 参数透传

- `create_task(retrieval_source_types=...)` 透传到 `build_task_semantics()`
- `update_task_planning_handoff()` 中保留 override：`current_semantics.get("retrieval_source_types") if retrieval_source_types is None else retrieval_source_types`，确保 planning handoff 不丢失之前设置的 override

### [PASS] `build_task_retrieval_request()` 中 explicit 优先

`orchestrator.py:3201-3208`：
```python
explicit_source_types = normalize_retrieval_source_types(semantics.get("retrieval_source_types"))
...
source_types=explicit_source_types or _select_source_types(route_policy_family, task_family),
```

- 利用 `or` 短路：`None` 或空列表都 fall through 到 policy 选择（normalize 永不返回空 list，会抛 ValueError）
- 顺序正确：override → policy fallback

### [PASS] `task_semantics_report` 显示 override

`build_task_semantics_report()`：
```python
f"- retrieval_source_types: {', '.join(retrieval_source_types) if retrieval_source_types else 'policy_default'}",
```

operator 可在 task semantics report 中直接看到当前是 explicit override 还是 policy default。

### [PASS] 测试覆盖：override 完整路径

| 场景 | 测试 |
|------|------|
| `create_task` 持久化（含去重） | `test_create_task_persists_explicit_retrieval_source_override_in_task_semantics` |
| planning handoff 保留 | `test_planning_handoff_preserves_existing_retrieval_source_override` |
| 非法 source_type 拒绝 | `test_create_task_rejects_invalid_explicit_retrieval_source_override` |
| build_task_retrieval_request 优先级 | `test_build_task_retrieval_request_prefers_explicit_retrieval_source_override` |
| build_task_retrieval_request 非法拒绝 | `test_build_task_retrieval_request_rejects_invalid_explicit_retrieval_source_override` |

---

## 全局检查

### [PASS] 与 design_decision 的一致性

| 设计约束 | 状态 |
|----------|------|
| Policy 在 request 构造层，不在管线内部 | ✓ 仅改 `build_task_retrieval_request()` |
| Policy 以常量表形式定义 | ✓ `_RETRIEVAL_SOURCE_POLICY` |
| capability-based route family 判定 | ✓ `_retrieval_policy_family()` |
| autonomous_cli_coding family 收紧为 `["knowledge"]` | ✓ |
| api family 默认 `["knowledge", "notes"]` | ✓ |
| legacy_local_fallback 保留 `["repo", "notes", "knowledge"]` | ✓ |
| 未知 / capability 缺失 fallback `["knowledge", "notes"]` | ✓ |
| Specialist guard（不被误分类为 autonomous） | ✓ taxonomy_role 判定 |
| Explicit override via `TaskSemantics.retrieval_source_types` | ✓ |
| `normalize_retrieval_source_types()` 校验 | ✓ |
| 不修改 `retrieve_context()` / `harness.py` | ✓ |
| 不修改 `infer_task_family()` | ✓ |

### [PASS] 长期设计文档同步

Phase 60 同步刷新了三份长期设计文档，与 kickoff §「设计锚点」对齐：

- `KNOWLEDGE.md §2.3`：新增「Retrieval Source Types 的职责边界」章节，明确 `knowledge / notes / repo / artifacts` 的语义、权威性与默认适用路径
- `AGENT_TAXONOMY.md §7.4`：新增「HTTP / CLI / Specialist 的生态位」表，明确三者不在同一维度竞争
- `ARCHITECTURE.md §4.1`：新增「执行生态位」表与默认上下文原则

这些文档刷新对齐了 Phase 60 的核心理念（HTTP 不是代码库问答默认路径，repo source 显式化），为后续 phase 提供了稳定锚点。

### [BLOCK] `test_failed_task_events_include_failure_payloads` 因 CLI policy 收紧未同步更新

`tests/test_cli.py:9292`：

```
AssertionError: 'warning' != 'passed'
events[15]["payload"]["status"]
```

**原因**：
- 测试在 `tmp_path` 下创建 `notes.md`，使用默认路由（`local-aider`）执行任务
- Phase 60 前：`source_types=["repo", "notes", "knowledge"]` → 召回 `notes.md` → `validation.findings` 包含 `retrieval.present`（pass）→ 总体 `passed`
- Phase 60 后：`local-aider` 是 `autonomous_cli_coding` → `source_types=["knowledge"]` → 工作区无 knowledge object → 召回 0 → `retrieval.empty`（warn）→ 总体 `warning`

`validator.py:60-67` 中：
```python
findings.append(ValidationFinding(
    code="retrieval.empty", level="warn",
    message="Retrieval returned no context for the run.",
    ...
))
```

**影响**：这是 Phase 60 S1 引入的预期行为变更——CLI agent 不预灌 repo/notes chunk，工作区无 knowledge object 时召回为空属于设计预期。

**修复建议（任选其一）**：
1. **更新断言**：将 `events[15]["payload"]["status"]` 期望从 `"passed"` 改为 `"warning"`，反映新 policy 的真实行为
2. **添加 explicit override**：在测试 `task create` 调用中通过 `--retrieval-sources` 或 task_semantics 注入 `["repo", "notes", "knowledge"]`，恢复历史 retrieval 行为
3. **预置 knowledge object**：在 `tmp_path` 下预置一个可被 retrieve 的 knowledge object，让 `["knowledge"]` 也能召回

推荐方案 1：测试是验证「task lifecycle 在失败场景下产出完整事件」，retrieval=0 + validation=warning 是新策略下 CLI 路径的正常状态，断言应反映真实语义而不是绕开它。

### [CONCERN] Pre-existing 失败：`test_meta_optimizer.py` 两条断言仍持有 `local-aider`

`tests/test_meta_optimizer.py:264` 和 `:538`：

- `test_review_and_apply_approved_route_weight_proposals` — `{'local-aider': 1.0}` vs 期望
- `test_review_and_apply_approved_route_capability_boundary_proposals` — `KeyError: 'local-aider'` 在 `rollback_capability_profiles`

**验证**：在 `git stash` 后 main HEAD 上仍然失败，证明这不是 Phase 60 引入的回归。Phase 59 closeout 中提到「`tests/test_meta_optimizer.py` 中同类断言已同步」，但实际只覆盖了部分用例，遗留两条未修复。

**影响**：低。两条测试与 Phase 60 无关，是 Phase 59 alias 移除清理的尾巴。

**建议**：登记为 Phase 59 cleanup 遗留 concern，不阻塞 Phase 60 merge。可由 Codex 在收口阶段顺手修复（与 Phase 59 同样的处理：将 `local-aider` 期望值改为 `local-codex`），或单独起 follow-up commit。

### [PASS] 未越出 phase scope

- 不修改 `retrieve_context()` 内部逻辑 ✓
- 不新增 source_type ✓
- 不修改 `infer_task_family()` ✓
- 不修改 `RouteSpec.executor_family` 赋值逻辑 ✓
- 不修改 `complexity_hint` 消费 ✓
- 不激活 `RetrievalRequest.strategy` 字段 ✓

### [PASS] 调用顺序核实（risk_assessment R2）

- `_retrieval_policy_family()` 在 `route_executor_family` 为空或 capabilities 为 `{}` 时返回 `executor_family or "*"`，避免错误归类
- `test_build_task_retrieval_request_uses_conservative_default_when_route_capabilities_are_missing` 验证空 state 走 `("*", "*")` → `["knowledge", "notes"]`
- 无证据显示有路径在路由前调用 `build_task_retrieval_request()`

---

## 结论

Phase 60 实现质量极高，设计与实现完全对齐，并在原 design_decision 基础上额外加入了 **Specialist guard**（taxonomy_role 检查），合理收紧了 capability-based 判定的边界。长期设计文档（KNOWLEDGE/AGENT_TAXONOMY/ARCHITECTURE）同步刷新，为后续 phase 提供了稳定锚点。

- **1 BLOCK**：`test_failed_task_events_include_failure_payloads` 测试断言未同步 CLI policy 变更（修复建议见上方），属于 Phase 60 行为变更的直接后果，必须在 merge 前修复
- **1 CONCERN**：`test_meta_optimizer.py` 两条测试是 Phase 59 alias 清理遗留，不阻塞 Phase 60，但建议在收口阶段顺手清理
- **0 范围越界**

修复 BLOCK 后建议直接进入收口。
