---
author: claude/context-analyst
phase: phase64
slice: context-brief
status: draft
depends_on:
  - docs/roadmap.md
  - docs/plans/phase63/m0_audit_report.md
  - docs/plans/phase63/closeout.md
  - docs/design/INVARIANTS.md
  - docs/design/ORCHESTRATION.md
  - docs/concerns_backlog.md
  - src/swallow/executor.py
  - src/swallow/router.py
  - src/swallow/agent_llm.py
  - src/swallow/literature_specialist.py
  - src/swallow/quality_reviewer.py
  - src/swallow/retrieval.py
  - src/swallow/synthesis.py
  - tests/test_invariant_guards.py
---

TL;DR: Phase 64 scope = enable 2 NO_SKIP guards (`test_path_b_does_not_call_provider_router` + `test_specialist_internal_llm_calls_go_through_router`) + fix their underlying violations. Red 1: `executor.py:510-513` independently resolves a fallback route by importing and calling `router.fallback_route_for`, bypassing the orchestrator control plane. Red 2: `agent_llm.py:57` issues `httpx.post` directly to the chat completions endpoint, circumventing the Provider Router for all Specialist internal LLM calls. Neither fix is mechanical — both touch real governance boundaries identified by the Phase 63 M0 audit.

---

## 目标摘要

启用 INVARIANTS §9 中以 `pytest.skip(reason="G.5 will enable, see roadmap candidate G.5")` 占位的 2 条 NO_SKIP 守卫测试，并修复对应代码，使 §9 全 17 条守卫严格执行。

---

## 变更范围

### 直接影响模块

| 文件 | 函数 / Symbol | 问题 |
|------|--------------|------|
| `src/swallow/executor.py:510-513` | `_load_fallback_route` | 内联 import + 调用 `router.fallback_route_for`，executor 层自主进行 fallback route 选路 |
| `src/swallow/executor.py:696-734` | `_apply_executor_route_fallback` | 调用 `_load_fallback_route`，是 fallback 决策的实际执行链 |
| `src/swallow/executor.py:737-774` | `_apply_executor_route_fallback_async` | 同上，异步版本 |
| `src/swallow/executor.py:1185+` | `run_http_executor` / async 变体 | 多处调用 `_apply_executor_route_fallback[_async]`（L1212, L1239, L1256, L1281, L1333, L1360, L1377, L1402, L1468, L1509, L1526, L1552, L1594, L1627, L1659, L1685）|
| `src/swallow/agent_llm.py:56-63` | `call_agent_llm` L57 `httpx.post` | 直连 chat completions URL，完全绕过 Provider Router |
| `tests/test_invariant_guards.py:456-461` | 两条 `pytest.skip` 占位 | 需替换为实际 AST 扫描守卫逻辑 |

### 间接影响模块

| 文件 | 关联方式 |
|------|---------|
| `src/swallow/router.py:781-785` | `fallback_route_for` 定义（Red 1 fix 可能重新分配职责）|
| `src/swallow/orchestrator.py:764,848` | 已有合规的 `fallback_route_for` 调用（在 orchestrator 层）— 构成合规参考基线 |
| `src/swallow/literature_specialist.py:391` | 调用 `call_agent_llm`（Red 2 调用方之一）|
| `src/swallow/quality_reviewer.py:234` | 调用 `call_agent_llm`（Red 2 调用方之一）|
| `src/swallow/retrieval.py:559` | 调用 `call_agent_llm`（见意外发现节）|
| `src/swallow/synthesis.py:120-138` | Path A route resolution seam 参考实现（`route_by_name` + `_MPS_DEFAULT_HTTP_ROUTE`）|

---

## 近期相关变更 (git history)

| Commit | 描述 | 相关模块 |
|--------|------|---------|
| `a1d2418` | merge: Governance Closure | Phase 63 全量落地 |
| `5116b62` | test(phase63): add invariant guard batch | 补齐 §9 全 17 条守卫名，含 2 条 G.5 skip 占位 |
| `1df5992` | feat(phase63): add truth repository write boundary | truth/ Repository 骨架 + bypass 守卫 |
| `088836f` | refactor(phase63): remove orchestrator staged knowledge dead code | 删 `_route_knowledge_to_staged` |
| `e905eee` | feat(phase63): centralize actor and path resolution guards | identity.py + workspace.py 集中化 |
| `c3637b1` | docs(phase63): add M0 governance audit report | 精确定位 2 条红灯：executor.py:510 + agent_llm.py:57 |

---

## 红灯 1 — Path B fallback route 选路

### 当前实装（`executor.py:510-513`）

```python
def _load_fallback_route(route_name: str) -> RouteSpec | None:
    from .router import fallback_route_for
    return fallback_route_for(route_name)
```

`_load_fallback_route` 是在 executor 层直接 import 并调用 `router.fallback_route_for`。这个调用出现在 `_apply_executor_route_fallback` / `_apply_executor_route_fallback_async` 两条路径的 L714 / L755。

### `fallback_route_for` 签名与实装（`router.py:781-785`）

```python
def fallback_route_for(route_name: str) -> RouteSpec | None:
    route = route_by_name(route_name)
    if route is None or not route.fallback_route_name:
        return None
    return route_by_name(route.fallback_route_name)
```

纯查询函数：根据 `RouteSpec.fallback_route_name` 字段返回下一跳 `RouteSpec`，无副作用。

### orchestrator 层的合规调用现状

`orchestrator.py:125` 导入 `fallback_route_for`，`orchestrator.py:764` 和 `orchestrator.py:848`（`_run_binary_fallback` 和其异步变体）在 Orchestrator 层合规地调用。这两条合规路径是 "fallback 决策属于 Orchestrator" 的现有实证。

### 守卫期望

`test_path_b_does_not_call_provider_router` 启用后需要扫描 executor 层代码（排除 orchestrator.py / router.py / cli.py 等白名单），断言不存在对 `fallback_route_for` 或等价 router 内 route selection 函数的直接 import / 调用。

### _executor_route_fallback_enabled 的触发条件（`executor.py:505-507`）

```python
def _executor_route_fallback_enabled(state: TaskState) -> bool:
    route_name = str(state.route_name or "").strip().lower()
    return route_name.startswith("http-") or route_name in {"local-http", "local-aider", "local-claude-code"}
```

即：http 系和三个 CLI route 启用 executor-level fallback；这是一个 executor 层的 fallback gate，不经 Orchestrator 决策。

---

## 红灯 2 — Specialist 内部 LLM 调用绕过 Provider Router

### 当前实装（`agent_llm.py:38-83`）

`call_agent_llm(prompt, *, system, model, timeout_seconds)` 完整调用链：

1. `resolve_new_api_api_key()` — 读 `SWL_API_KEY` env；如为空则抛 `AgentLLMUnavailable`
2. `resolve_agent_llm_model(model)` — 调 `resolve_swl_chat_model()`，读 `SWL_CHAT_MODEL` 或系统默认
3. 构造 messages（可含 system 消息）
4. L57: `httpx.post(resolve_new_api_chat_completions_url(), json=..., headers=_http_request_headers(), timeout=...)`
5. 解析 `choices[0].message.content`，调用 `extract_api_usage` 解析 token 计数
6. 返回 `AgentLLMResponse(content, input_tokens, output_tokens, model)`

`resolve_new_api_chat_completions_url()` (`executor.py:487-491`): 读 `SWL_API_BASE_URL` env，拼 `/v1/chat/completions`，默认值为 `DEFAULT_NEW_API_CHAT_COMPLETIONS_URL`。

`_http_request_headers()` (`executor.py:1160-1165`): 固定 `Content-Type: application/json`，如有 `SWL_API_KEY` 则加 `Authorization: Bearer`。

错误处理：`httpx.HTTPError` → `AgentLLMUnavailable`；payload 解析失败 → `AgentLLMUnavailable`；空 content → `AgentLLMUnavailable`。

`AgentLLMResponse` 是 frozen dataclass，字段：`content: str`, `input_tokens: int`, `output_tokens: int`, `model: str`。

### 调用方完整清单（grep 验证）

| 调用方 | 位置 | 调用上下文 |
|--------|------|-----------|
| `literature_specialist.py` | L391 | 主执行路径：分析文档 + 提取 key_concepts / relation_suggestions |
| `quality_reviewer.py` | L234 | 主执行路径：LLM 语义 verdict（失败时 fallback 到纯启发式，不抛出）|
| `retrieval.py` | L559 | `rerank_retrieval_items` — **非 Specialist 路径**（见意外发现节）|

### 调用方对 AgentLLMResponse 的依赖面

- `literature_specialist.py` / `quality_reviewer.py`: 消费 `.content`（传入 `extract_json_object`）、`.input_tokens` / `.output_tokens` / `.model`（写入 usage metrics）
- `retrieval.py`: 消费 `.content`（传入 `extract_json_object`），不消费 token 字段
- 三处均捕获 `AgentLLMUnavailable` 作为可降级信号（LLM 不可用时走启发式路径，不阻塞主流程）

### Provider Router 现状是否能承载

Provider Router 当前的 selection 接口(`select_route`, `route_by_name`)产出 `RouteSpec`，`RouteSpec` 携带 `executor_name`, `model_hint`, `backend_kind`, `transport_kind`, `capabilities` 等字段，但**没有直接的 "invoke completion" 方法**。

`executor.py` 中 `run_http_executor` 是把 `RouteSpec` 对应的 HTTP 端点做 `httpx.post` 的实际实现，入参是 `TaskState + retrieval_items`，不是裸 `prompt + system`。

Specialist 内部调用需要的 seam：裸 `(prompt, system, model)` → Provider Router 管辖的 HTTP 端点 → `AgentLLMResponse`。

**现有 Path A 最近的参考**：`synthesis.py:119-138` 用 `route_by_name(_MPS_DEFAULT_HTTP_ROUTE)` 获取 `RouteSpec`，随后在 `_run_participant` 中通过 `run_http_executor` 执行。但 `run_http_executor` 入参依赖 `TaskState`，不适合 Specialist 内部调用（Specialist 内部调用无 task state）。

设计需要解决：Provider Router 是否要暴露一个轻量的 `invoke_completion(prompt, system, model_hint, *, route_hint=None) -> AgentLLMResponse` seam，或者 `agent_llm.call_agent_llm` 内部改为先经 Provider Router 查询 `RouteSpec`（获取 endpoint / api_key / model），再发起 `httpx.post`。

---

## §9 守卫占位现状

`tests/test_invariant_guards.py:456-461`:

```python
def test_path_b_does_not_call_provider_router() -> None:
    pytest.skip(reason="G.5 will enable, see roadmap candidate G.5")


def test_specialist_internal_llm_calls_go_through_router() -> None:
    pytest.skip(reason="G.5 will enable, see roadmap candidate G.5")
```

两条守卫均为函数体仅含 `pytest.skip` 的占位，未包含任何 AST 扫描逻辑。Phase 64 需将两条守卫替换为实际断言逻辑。

**合理的 AST 断言策略（基于现有守卫模式）：**

- **`test_path_b_does_not_call_provider_router`**: 扫描 `src/swallow/executor.py`（或更宽 executor 层文件集），断言不存在对 `fallback_route_for` / `route_by_name` / `select_route` 的 import 或调用。白名单需排除 `orchestrator.py` / `router.py` / `cli.py` / `synthesis.py`（这些合法调用 router）。
- **`test_specialist_internal_llm_calls_go_through_router`**: 扫描调用 `call_agent_llm` 的文件（`literature_specialist.py`, `quality_reviewer.py`, `retrieval.py`），断言这些模块不直接 import `httpx` 且 `agent_llm.py` 内部 `httpx.post` 直连路径不存在（或改走 Provider Router seam）。

---

## Provider Router 现状契约

| Symbol | 定义位置 | 签名 / 语义 |
|--------|---------|------------|
| `route_by_name(route_name)` | `router.py:769` | 返回 `RouteSpec | None`，支持 `-detached` 后缀自动展开 |
| `select_route(state, executor_override, route_mode_override)` | `router.py:822` | 读 `TaskState`，返回 `RouteSelection(route, reason, policy_inputs)` |
| `fallback_route_for(route_name)` | `router.py:781` | 查 `RouteSpec.fallback_route_name`，返回下一跳 `RouteSpec | None` |
| `ROUTE_REGISTRY` | `router.py:588` | `RouteRegistry` 全局单例，包含 13 条内建路由 |
| `RouteSpec` | `models.py` | 含 `fallback_route_name`, `executor_name`, `backend_kind`, `transport_kind`, `model_hint` 等字段 |

**现有冲突检测**：`fallback_route_for` 当前被 `orchestrator.py`（合规）和 `executor.py`（违规）两处调用。`orchestrator.py` 的调用（L764, L848）都在 `_run_binary_fallback` 函数内，属于 orchestrator 主控流，合规。如果 Phase 64 修复把 executor 的 `_load_fallback_route` 删除或改写，`orchestrator.py` 的调用路径不受影响。

---

## 意外发现

### retrieval.py 调用 call_agent_llm（非 Specialist 路径）

`src/swallow/retrieval.py:547-566`：`rerank_retrieval_items` 函数内 lazy import 并调用 `call_agent_llm`。`retrieval.py` 是检索基础设施层（非 Specialist），被 orchestrator 和多个 Specialist 共同调用。

含义：`test_specialist_internal_llm_calls_go_through_router` 守卫的 AST 策略不能简单扫描"Specialist 模块 import agent_llm"，需要精确区分"哪些 `call_agent_llm` 调用违反 Path C 契约"：
- `retrieval.py` 的调用是 retrieval 基础设施调用，属于 orchestrator 触发的 retrieval 环节，不完全等同于 Specialist 内部 LLM。
- 守卫设计需明确：是否把 `retrieval.py` 也纳入"必须走 Provider Router"的约束。

### executor.py `httpx.post` 测试 mock 风险

现有测试大概率 mock 了 `httpx.post` 来测试 `call_agent_llm`（`literature_specialist`, `quality_reviewer` 相关测试）。如果 Red 2 修复把 `httpx.post` 换成 Provider Router seam，这些测试的 mock 点将从 `httpx.post` 移动到新 seam 函数，需要批量调整 mock 目标。

### executor.py 本身也调用 httpx.post（Path A）

`executor.py:1200` 在 `run_http_executor` 中同样有 `httpx.post`。这条是合法的 Path A 调用（已经是 Provider Router 管辖的路由结果的执行）。`test_path_b_does_not_call_provider_router` 守卫如果扫描 `httpx.post` 调用，需要排除 `run_http_executor` 这条合法路径，或改为扫描 `fallback_route_for` import 模式而非 `httpx.post`。

### synthesis.py Path A seam 可复用性

`synthesis.py:126-138` 的 `_resolve_participant_route` 用 `route_by_name` + `select_route` 解析 `RouteSpec`，随后传给 `_run_participant` 调用 `run_http_executor`。这是"从 Provider Router 获取 RouteSpec，再调用 HTTP executor"的最近落地参考。但 `run_http_executor` 接受 `TaskState + retrieval_items`，不能直接用于 Specialist 裸 prompt 场景。两者之间仍存在 seam gap：Specialist 调用需要更轻量的接口，或者 `call_agent_llm` 内部改为读取 Provider Router 的 `RouteSpec.model_hint` 来决定模型，而不是用 `resolve_swl_chat_model()` 独立读 env。

---

## 依赖关系 / 相邻 Open

### 与 Phase 63 closeout 3 条 backlog 的关系

| backlog 条目 | 与 Phase 64 关系 |
|------------|----------------|
| `staged_candidate_count` 字段残留（review M2-1）| 无关 |
| `_apply_route_review_metadata` 过长（review M2-5）| 无关（属于 governance.py 内部重构）|
| `events` / `event_log` 双写 backfill（review M3-1）| 无关（候选 H Truth Plane SQLite 范围）|

### 与候选 H（Truth Plane SQLite）的顺序依赖

无强依赖。Phase 64（G.5）修复 LLM 路径边界，Phase H 修复 Truth 物理存储。两者可以顺序但不相互阻塞。候选 H 中 `apply_proposal` 事务化依赖 route metadata / policy 先迁入 SQLite，与 Phase 64 无直接代码接触点。

### INVARIANTS §0 第 3 条（LLM 三条路径）

两条红灯修复的根本依据：§0 第 3 条规定"Path C = N × Path A，Specialist 内部 LLM 调用必须穿透到 Provider Router，不允许绕路直连 provider"。`agent_llm.py:57` 直连违反此条。`executor.py:510-513` 的 fallback 自主选路违反 §0 第 1 条（Control 只在 Orchestrator 和 Operator 手里）。

---

## Branch 建议

候选 branch 名（供 Human 切出参考）：
- `feat/phase64-llm-router-boundary`（聚焦 LLM path 治理边界）
- `feat/phase64-no-skip-fixes`（聚焦 NO_SKIP 守卫启用）

推荐：`feat/phase64-llm-router-boundary`（更能表达本 phase 的核心修复语义）
