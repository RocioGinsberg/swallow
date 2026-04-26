---
author: claude
phase: 60
slice: design_decision
status: draft
depends_on:
  - docs/plans/phase60/kickoff.md
  - docs/plans/phase60/context_brief.md
---

## TL;DR

Phase 60 的核心改动是在 `orchestrator.py:build_task_retrieval_request()` 中插入一个 policy 查表步骤，用 `state.route_executor_family` + `infer_task_family(state)` 选择 source_types。三个 slice 依次落地：S1 按 executor_family 二分（CLI vs HTTP），S2 对 HTTP path 按 task_family 细分，S3 补充 explicit override 机制。不触碰 retrieval 管线内部。

# Phase 60 Design Decision: 路径感知的 Retrieval Policy

## 设计决策总览

### 核心决策：Policy 在 request 构造层，不在管线内部

**决策**：retrieval policy 逻辑集中在 `build_task_retrieval_request()` 函数，通过选择不同的 `source_types` 列表传入 `RetrievalRequest`，而不是在 `retrieve_context()` 内部添加分支。

**理由**：
- `retrieve_context()` 已经通过 `classify_source_type(path, allowed_sources)` 实现了 source_types 过滤——只需改变传入的 source_types 列表，管线内部无需感知 executor_family
- `build_task_retrieval_request()` 是唯一的 retrieval request 构造点，改动面最小
- policy 逻辑与 retrieval 算法逻辑解耦，各自可独立演进

**替代方案（已排除）**：
- 在 `retrieve_context()` 内部读取 executor_family：需要把 state 或 executor_family 传入管线，污染 retrieval 层的接口
- 在 `harness.py:run_retrieval()` 中拦截：harness 是透传层，不应承载 policy 逻辑

---

### 决策：Policy 以常量表形式定义

**决策**：在 `orchestrator.py` 顶部定义 `_RETRIEVAL_SOURCE_POLICY` 常量，结构为 `dict[tuple[str, str], list[str]]`，key 为 `(executor_family, task_family)`，value 为 source_types 列表。

```python
_RETRIEVAL_SOURCE_POLICY: dict[tuple[str, str], list[str]] = {
    # CLI path: CLI agent 有自主文件探索能力，repo chunk 是噪声
    ("cli", "*"): ["knowledge"],
    # HTTP brainstorm/planning path: 聚焦知识与文档，不需要 repo chunk
    ("api", "planning"): ["knowledge", "notes"],
    ("api", "review"): ["knowledge", "notes"],
    # HTTP code-analysis path: 保留完整三源
    ("api", "execution"): ["repo", "notes", "knowledge"],
    ("api", "extraction"): ["repo", "notes", "knowledge"],
    ("api", "retrieval"): ["repo", "notes", "knowledge"],
    # fallback: 保持现有行为
    ("*", "*"): ["repo", "notes", "knowledge"],
}
```

**查表逻辑**（伪代码）：
```python
def _select_source_types(executor_family: str, task_family: str) -> list[str]:
    # 精确匹配优先
    if (executor_family, task_family) in _RETRIEVAL_SOURCE_POLICY:
        return _RETRIEVAL_SOURCE_POLICY[(executor_family, task_family)]
    # executor_family 通配
    if (executor_family, "*") in _RETRIEVAL_SOURCE_POLICY:
        return _RETRIEVAL_SOURCE_POLICY[(executor_family, "*")]
    # 全局 fallback
    return _RETRIEVAL_SOURCE_POLICY[("*", "*")]
```

**理由**：
- 常量表比 if-chain 更易读、更易测试、更易扩展
- `("cli", "*")` 通配覆盖所有 CLI task_family，避免为每个 task_family 重复写 CLI 条目
- fallback 保证向后兼容

---

### 决策：Explicit Override 通过 TaskSemantics 字段实现

**决策**：在 `TaskSemantics`（TypedDict）中添加可选 key `retrieval_source_types: list[str]`。`build_task_retrieval_request()` 在查 policy 表之前先检查此字段，若存在则直接使用，跳过 policy。

**理由**：
- `TaskSemantics` 已是 task 配置的扩展点，operator 通过 `--task-semantics` 或 API payload 传入
- 不需要新增 CLI flag 或 API 字段，复用现有机制
- override 语义明确：operator 显式指定时，policy 不干预

**实现位置**：`build_task_retrieval_request()` 开头：
```python
explicit_sources = state.task_semantics.get("retrieval_source_types")
if explicit_sources:
    source_types = explicit_sources
else:
    source_types = _select_source_types(
        state.route_executor_family,
        infer_task_family(state),
    )
```

---

## Slice 实现细节

### S1: Policy 表定义 + CLI path 收紧

**改动文件**：`src/swallow/orchestrator.py`

**具体改动**：

1. 在模块顶部（imports 之后）添加 `_RETRIEVAL_SOURCE_POLICY` 常量和 `_select_source_types()` 辅助函数

2. 修改 `build_task_retrieval_request(state: TaskState)` 函数：
   - 当前：`source_types = ["repo", "notes", "knowledge"]`（硬编码）
   - 改为：调用 `_select_source_types(state.route_executor_family, infer_task_family(state))`
   - S1 阶段只实现 `("cli", "*")` 和 `("*", "*")` 两条规则，HTTP 细分在 S2 补充

3. `infer_task_family` 已在 `models.py` 中定义，`orchestrator.py` 已 import `models`，直接调用即可

**S1 的 policy 表（简化版，S2 再补充 HTTP 细分）**：
```python
_RETRIEVAL_SOURCE_POLICY = {
    ("cli", "*"): ["knowledge"],
    ("*", "*"): ["repo", "notes", "knowledge"],
}
```

**测试**：
- `test_build_task_retrieval_request_cli_path_uses_knowledge_only`：构造 `route_executor_family="cli"` 的 state，断言返回 source_types == `["knowledge"]`
- `test_build_task_retrieval_request_api_path_uses_full_sources`：构造 `route_executor_family="api"` 的 state，断言返回 source_types == `["repo", "notes", "knowledge"]`
- `test_build_task_retrieval_request_unknown_family_fallback`：构造 `route_executor_family=""` 的 state，断言 fallback 到 `["repo", "notes", "knowledge"]`

---

### S2: HTTP path 按 task_family 细分

**改动文件**：`src/swallow/orchestrator.py`

**具体改动**：

扩充 `_RETRIEVAL_SOURCE_POLICY` 常量，补充 HTTP path 的 task_family 细分条目：

```python
_RETRIEVAL_SOURCE_POLICY = {
    # CLI: 所有 task_family 统一收紧
    ("cli", "*"): ["knowledge"],
    # HTTP brainstorm/planning path
    ("api", "planning"): ["knowledge", "notes"],
    ("api", "review"): ["knowledge", "notes"],
    # HTTP code-analysis path（保留完整三源）
    ("api", "execution"): ["repo", "notes", "knowledge"],
    ("api", "extraction"): ["repo", "notes", "knowledge"],
    ("api", "retrieval"): ["repo", "notes", "knowledge"],
    # fallback
    ("*", "*"): ["repo", "notes", "knowledge"],
}
```

`_select_source_types()` 函数不变（已支持精确匹配 + 通配 + fallback）。

**测试**：
- `test_build_task_retrieval_request_api_planning_uses_knowledge_notes`
- `test_build_task_retrieval_request_api_review_uses_knowledge_notes`
- `test_build_task_retrieval_request_api_execution_uses_full_sources`
- `test_build_task_retrieval_request_api_unknown_task_family_fallback`

---

### S3: Explicit Override + 测试补全

**改动文件**：
- `src/swallow/models.py`（或 `src/swallow/task_semantics.py`，视 TaskSemantics 定义位置）
- `src/swallow/orchestrator.py`

**具体改动**：

1. `TaskSemantics`（TypedDict）添加可选 key：
   ```python
   class TaskSemantics(TypedDict, total=False):
       # ... 现有字段 ...
       retrieval_source_types: list[str]
   ```

2. `build_task_retrieval_request()` 开头添加 override 检查（见上方伪代码）

3. 集成测试：构造完整 state（含 route 信息），验证 policy 在真实调用链中生效

**测试**：
- `test_build_task_retrieval_request_explicit_override_bypasses_policy`：设置 `task_semantics["retrieval_source_types"] = ["repo"]`，断言 policy 不生效
- `test_build_task_retrieval_request_no_override_uses_policy`：不设置 override，断言 policy 正常生效
- `test_retrieval_policy_integration_cli_route`：集成测试，mock `retrieve_context()`，验证 CLI route 下 source_types 正确传入

---

## 关键约束

| 约束 | 来源 | 实现方式 |
|------|------|---------|
| 不修改 `retrieve_context()` 内部 | 设计边界 | policy 只在 request 构造层 |
| 不修改 `infer_task_family()` | 设计边界 | 直接复用，不扩展分类 |
| `executor_family` 未知时 fallback | 风险缓解 | `("*", "*")` fallback 条目 |
| explicit override 优先于 policy | 设计边界 | override 检查在 policy 查表之前 |
| 不引入新 source_type | 非目标 | 只使用现有 `"repo"` / `"notes"` / `"knowledge"` |

---

## 与现有代码的接口

| 现有符号 | 位置 | Phase 60 使用方式 |
|---------|------|-----------------|
| `state.route_executor_family` | `models.py:TaskState` | 读取，不修改 |
| `infer_task_family(state)` | `models.py` | 直接调用 |
| `build_task_retrieval_request(state)` | `orchestrator.py` | 修改此函数 |
| `RetrievalRequest.source_types` | `models.py` | 传入 policy 选择的值 |
| `TaskSemantics` | `models.py` | 添加 `retrieval_source_types` 可选 key（S3） |

---

## 不做的事（明确边界）

- 不修改 `retrieve_context()` 签名或内部逻辑
- 不修改 `harness.py:run_retrieval()`
- 不修改 `RouteSpec.executor_family` 的赋值逻辑
- 不修改 `infer_task_family()` 的分类逻辑
- 不添加 `swl task create --retrieval-sources` CLI flag
- 不激活 `RetrievalRequest.strategy` 字段（仍为空操作）
- 不为 `"notes"` source_type 添加细分（如区分 staged notes vs docs）
