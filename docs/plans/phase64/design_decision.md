---
author: claude
phase: phase64
slice: design-decomposition
status: revised-after-model-review
depends_on: ["docs/plans/phase64/kickoff.md", "docs/plans/phase64/context_brief.md", "docs/plans/phase64/design_audit.md", "docs/plans/phase64/model_review.md", "docs/plans/phase63/m0_audit_report.md", "docs/plans/phase63/closeout.md", "docs/design/INVARIANTS.md", "docs/design/ORCHESTRATION.md", "docs/roadmap.md", "src/swallow/router.py", "src/swallow/executor.py", "src/swallow/agent_llm.py", "src/swallow/models.py"]
---

TL;DR(revised-after-model-review): **2 slice / 2 milestone**。**Pivot 1**(GPT-5 option iii):S1 = orchestrator 一次预解析整条 fallback chain plan(`tuple[str, ...]`,环检测内置),写入 `state.fallback_route_chain`;executor 改读 state + 一次性通过新 `swallow.router.lookup_route_by_name(name) -> RouteSpec | None`(read-only 数据查询助手,语义与现有 `route_by_name` 等价但显式标记非 selection)取得 RouteSpec 对象。**Pivot 2**(GPT-5 option i):守卫 `test_path_b_does_not_call_provider_router` 重新框定 = "executor 不调 selection 函数"(允许 lookup_route_by_name)。S2 = 强制中性模块 `swallow/_http_helpers.py` 抽 helper(打破三向 import 环)+ `swallow.router.invoke_completion(prompt, *, system, model, timeout_seconds) -> AgentLLMResponse` thin seam(`route_hint` dropped)+ 守卫细化为 chat-completion URL pattern(允许 embeddings httpx.post)。INVARIANTS / DATA_MODEL 文字不动(§4 表已对齐守卫语义)。

## 方案总述

Phase 64 是治理边界 LLM 路径的收口 phase,**第二段**(承接 Phase 63 治理结构收口)。M0 audit + design_audit + model_review 三轮迭代后 scope 已经清晰:

- **S1(M1)** 通过 GPT-5 推荐的 **option iii(immutable fallback chain plan)+ option i(守卫语义重新框定)** 组合消化全部 BLOCKER:
  - orchestrator 沿 `RouteSpec.fallback_route_name` 链一次跳完,产出 `tuple[str, ...]` chain plan(含环检测),写入 `state.fallback_route_chain`
  - executor 的 `_load_fallback_route` 改签名为 `_load_fallback_route(state: TaskState, current_route_name: str) -> RouteSpec | None`(`state` 参数显式补上 — 16 调用点同步改,但都在 `_apply_executor_route_fallback[_async]` 内部 + 已经持有 `state` 局部变量,改动是机械替换)
  - executor 通过 `swallow.router.lookup_route_by_name(name)`(本 phase 新增的 read-only 助手)把 chain 中的 name 查回 RouteSpec 对象给 `_apply_route_spec_for_executor_fallback` 用
  - 守卫 `test_path_b_does_not_call_provider_router` 扫 `select_route` / `route_by_name` / `fallback_route_for` 调用,**不扫** `lookup_route_by_name`(显式 read-only 数据查询)
- **S2(M2)** 通过 GPT-5 BLOCK Q4 强制方案消化所有 helper / 守卫 / route_hint 争议:
  - 强制新模块 `swallow/_http_helpers.py` 容纳 router/agent_llm/executor 三方共需 helper
  - `router.invoke_completion(...)` 引入 — `route_hint` 参数 drop(YAGNI)
  - `agent_llm.call_agent_llm` 退化为 thin caller(测试 mock 透明)
  - 守卫 `test_specialist_internal_llm_calls_go_through_router` 用 chat-completion URL pattern 而非裸 `httpx.post` 扫描

**等价性保证**:
- S1:fallback chain plan 等价于"对每个 route 调一次 fallback_route_for"——orchestrator 一次性跳完 chain,executor 按 visited_routes 取下一跳与原代码语义完全一致;`lookup_route_by_name` 内部直接复用 `route_by_name` 实装(包括 `-detached` 后缀展开),零行为变化
- S2:`call_agent_llm` 公开签名 + 返回类型 + 异常类型不变;`invoke_completion` 内部实装与原 `call_agent_llm` 字符级等价(URL/model/headers/timeout/payload 解析路径完全一致)

## Slice 拆解

### S1 — Path B fallback chain plan + lookup_route_by_name(M1 单独 review)

**目标**:消化 GPT-5 BLOCK Q1 + Q2 + design_audit BLOCKER S1-1 + S1-2:
- Pivot:orchestrator 预解析整条 chain plan,executor 改读 state(GPT-5 option iii)
- Pivot:守卫语义重新框定 = executor 不调 selection 函数(GPT-5 option i)
- 引入 `lookup_route_by_name` read-only 数据查询助手桥接 chain name 到 RouteSpec 对象

**影响范围**:
- 改动:`src/swallow/models.py` —— TaskState 新增字段 `fallback_route_chain: tuple[str, ...] = ()`(默认空 tuple = 无 fallback 链;`@dataclass(slots=True)` 兼容)。**位置建议**:在现有 `route_*` 字段集合附近(line 380-394 附近)
- 改动:`src/swallow/orchestrator.py` —— `select_route` 调用路径上,在 RouteSelection 拿到 primary RouteSpec 后,调用新 helper `_resolve_fallback_chain(route_name) -> tuple[str, ...]`(orchestrator 内部私有函数;**或**直接调 `router.fallback_route_for` 多次)预填 `state.fallback_route_chain`。具体填充点:`select_route` 之后第一处对 state route 字段的赋值附近(orchestrator 内部 grep 验证)。**Phase 62 MPS path 同步**:`synthesis.py:_resolve_participant_route` 在调 `select_route(base_state)` 后也要同款预填(消化 design_audit CONCERN MPS regression)
- 新增:`src/swallow/router.py:lookup_route_by_name(name: str) -> RouteSpec | None` — read-only 数据查询助手,内部实装 = `return route_by_name(name)`(直接复用),docstring 显式声明 "data lookup, not selection. Allowed for executor consumption per Phase 64 dependency rule"
- 改动:`src/swallow/executor.py:510-513` `_load_fallback_route`:
  - **新签名**:`def _load_fallback_route(state: TaskState, current_route_name: str, visited_routes: set[str]) -> RouteSpec | None`
  - **新函数体**:从 `state.fallback_route_chain` 中找到 `current_route_name` 的位置,取下一跳 name(若不存在或在 visited_routes 中,返回 None);用 `lookup_route_by_name(next_name)` 取 RouteSpec
  - 删除内联 `from .router import fallback_route_for`
- 改动:`src/swallow/executor.py:714` 与 `src/swallow/executor.py:755` —— `_apply_executor_route_fallback[_async]` 内部对 `_load_fallback_route(...)` 的调用,补全 `state` + `seen_routes` 参数。**调用点数量**:仅 2 处(executor.py:714 / executor.py:755),不是 16 处 — 16 处是 `_apply_executor_route_fallback[_async]` 自身的调用方,签名不变
- 改动:`tests/test_invariant_guards.py:456-457` 删除 `pytest.skip`,实装 AST 守卫
- 不动:`router.py:781 fallback_route_for` 函数本身(orchestrator 仍合法调用)
- 不动:executor.py 16 处 `_apply_executor_route_fallback[_async]` 调用点(签名不变,这些调用点零修改)
- 不动:`_executor_route_fallback_enabled` / `_apply_route_spec_for_executor_fallback` 触发逻辑
- 不动:`RouteSpec` schema、`fallback_route_name` 字段、ROUTE_REGISTRY

**关键设计决策**:

- **chain plan 形式 = `tuple[str, ...]`,不是 RouteSpec 列表 / dict**:GPT-5 BLOCK Q2 + design_audit BLOCKER S1-1 共同教训 — 不要序列化 RouteSpec(嵌套 dataclass 反序列化复杂、`from_dict` 不存在)。tuple of str 简单、不可变、`@dataclass(slots=True)` 友好、orchestrator 与 executor 之间 contract 极轻。chain 第一项 = primary route name;chain 后续项 = fallback chain 上的 route names

- **chain plan 一旦预填即视为 read-only**(S1-C1 消化):`_apply_route_spec_for_executor_fallback`(executor.py:516)在 fallback 应用时就地 mutate ~15 个 `state.route_*` 字段(`state.route_name = route.name` 等)。**`fallback_route_chain` 字段不在被 mutate 列表中** — Codex 在 PR body 中显式声明此约束:fallback chain 由 orchestrator 一次预填,fallback 应用时不更新该字段。这保证 multi-hop reentry(executor.py:724 `_run_executor_for_fallback_route`)在第二次 fallback 时仍能从原 chain 中按 visited_routes 找到下一跳。`_apply_route_spec_for_executor_fallback` 自身**不需要修改** — 该函数现有不动 `fallback_route_chain` 字段(因为字段不存在,本 phase 新增的字段),只需 Codex 在 PR body 中显式不加该字段到 mutate 路径

- **chain plan 环检测**:orchestrator 预解析时遇到已访问的 name 立即 break(与 executor 现有 `visited_routes` accumulator 等价)。pseudocode:
  ```python
  def _resolve_fallback_chain(primary_route_name: str) -> tuple[str, ...]:
      chain: list[str] = []
      seen: set[str] = set()
      current = primary_route_name
      while current and current not in seen:
          chain.append(current)
          seen.add(current)
          fallback = fallback_route_for(current)
          current = fallback.name if fallback else ""
      return tuple(chain)
  ```
  实现位置:**orchestrator.py 私有 helper**(orchestrator 是合法 selection 调用方,可直接调 `fallback_route_for`)。不放 router.py(避免 router.py 职责扩张);不放新模块(YAGNI,本 phase 不抽)

- **executor 取 RouteSpec 桥**:`lookup_route_by_name` 是本 phase **唯一新增的 router 公开符号(除 `invoke_completion` 外)**。语义 = `route_by_name` 但显式标记 read-only 数据查询。internal 实装 = `return route_by_name(name)`(单行 forwarder)。这是 GPT-5 推荐的"Provider Router 显式分离 selection 与 metadata consumption"在代码层的具体落地

- **`_load_fallback_route` 新签名 vs "16 调用点零修改" 承诺**:design_audit BLOCKER S1-2 的承诺已取消 — 改 16 调用点确实是必要工作。但实际上调 `_load_fallback_route` 的不是 16 个 site,是 `_apply_executor_route_fallback`(L714)与 `_apply_executor_route_fallback_async`(L755)**两个函数内部 + 16 个调用 `_apply_executor_route_fallback[_async]` 的 site**。S1 改的是前者(2 处),后者(16 处)签名不变,自然零修改。**这是 design_audit 错把"`_apply_executor_route_fallback` 调用方"等同于"`_load_fallback_route` 调用方"导致的误读**;实际工作量是 2 行改动 + 1 个新参数

- **`_load_fallback_route` 三参签名**(state / current_route_name / visited_routes):pivot 前是 `(route_name)`;pivot 后是 `(state, current_route_name, visited_routes)`。三参反映了 chain 在 visited 状态下的下一跳查询语义。`current_route_name` 仍接收 — executor 在 fallback 重入时 current name 已经变成上一跳的 fallback,需要在 chain 中定位 current 的位置以取下一跳

- **MPS Path A 同步**:`synthesis.py:_resolve_participant_route` 在 `select_route(base_state)` 后预填 `participant_state.fallback_route_chain`,与主 orchestrator 路径对齐。**实装层面**:把"select_route 后预填 chain" 抽成 orchestrator 内部 helper `_apply_route_selection_with_fallback_chain(state, ...)`,主 orchestrator 与 synthesis 共用

- **守卫策略(`test_path_b_does_not_call_provider_router`)**:
  - **扫描范围**:`src/swallow/executor.py`(单文件)
  - **扫描内容**:AST 节点 ImportFrom + Call,搜寻对 **selection 函数**的 import 或调用
  - **selection 函数名集合**(authoritative):`{select_route, route_by_name, fallback_route_for, route_for_mode}`
  - **不扫**:`lookup_route_by_name`(显式 read-only 数据查询);`RouteSpec` 类构造(executor 内部已有 RouteSpec 操作,合规)
  - **守卫 docstring** 显式注明:"executor 不应做 Provider Router 的 selection 工作。允许调 `lookup_route_by_name`(read-only 数据查询)消费 RouteSpec 静态字段。语义读法基于 INVARIANTS §4 表(Path B = agent 自己组装 prompt,不经 Provider Router)+ §0 第 1 条(控制面在 Orchestrator/Operator)"
  - **反 vacuous 锚点**:`assert hasattr(swallow.executor, "_load_fallback_route") and any(... router import in selection_calls in <historical baseline>)` 风格 — 简单做法:在守卫中 `assert hasattr(swallow.router, "fallback_route_for")` 确认 selection 函数仍存在(否则守卫扫描目标空了变 vacuous)

**验收条件**:
- `grep -n 'select_route\|route_by_name\|fallback_route_for\|route_for_mode' src/swallow/executor.py` 命中 0
- `grep -n 'lookup_route_by_name' src/swallow/executor.py` 命中 ≥ 1(executor 通过新助手取 RouteSpec)
- `swallow.router.lookup_route_by_name(...)` 存在
- `state.fallback_route_chain` 字段存在于 TaskState
- `swallow.orchestrator` 内部 helper `_resolve_fallback_chain` 或等价路径将 chain 预填至 state(具体函数名由 Codex 实装,在 PR body 中说明)
- `synthesis.py` MPS participant 路径同步预填 chain
- `test_path_b_does_not_call_provider_router` 启用且通过(非 `pytest.skip`)
- 全量 pytest 通过;executor 现有 fallback 测试套件零破坏

**风险评级**:影响范围 2 / 可逆性 1 / 依赖 2 = 5(中)。chain plan 字段 + lookup_route_by_name 引入 + 2 处调用签名变化。回滚成本低(revert 单 commit)

---

### S2 — Helper 中性模块 + Provider Router invoke_completion seam(M2 单独 review)

**目标**:消化 GPT-5 BLOCK Q4 + Q9 + design_audit S2 全部 CONCERN:
- 新增 `swallow/_http_helpers.py` 中性模块(强制,打破 router-executor-agent_llm 三向 import 环)
- 新增 `swallow.router.invoke_completion(...)` thin seam(无 `route_hint` 参数)
- `agent_llm.call_agent_llm` 退化为 thin caller
- 守卫细化为 chat-completion URL pattern

**影响范围**:
- 新增:`src/swallow/_http_helpers.py` — 中性模块,从 `executor.py` + `agent_llm.py` 搬迁的 symbol(authoritative 清单见下文 §S2 关键设计决策)
- 改动:`src/swallow/executor.py` — 顶部相应 helper 函数定义改为 `from ._http_helpers import ...`(原定义搬走)
- 改动:`src/swallow/agent_llm.py` — 顶部 `from .executor import (...)` 改为 `from ._http_helpers import (...)`;`call_agent_llm` 函数体退化为单行 `from .router import invoke_completion; return invoke_completion(prompt, system=system, model=model, timeout_seconds=timeout_seconds)`;`AgentLLMResponse` / `AgentLLMUnavailable` re-export 自 `_http_helpers`(`from ._http_helpers import AgentLLMResponse, AgentLLMUnavailable` 顶部 import 即可,Python 名字导出自然支持)
- 新增:`src/swallow/router.py:invoke_completion(prompt: str, *, system: str = "", model: str | None = None, timeout_seconds: int | None = None) -> AgentLLMResponse` — 内部从 `_http_helpers` import 所需 helper,实装与原 `call_agent_llm` 字符级等价
- 不动:`src/swallow/literature_specialist.py:391` / `quality_reviewer.py:234` / `retrieval.py:559` 三处 `call_agent_llm` 调用代码
- 不动:`src/swallow/retrieval_adapters.py:206` `httpx.post` 调 `/v1/embeddings`(embeddings,非 chat-completion,守卫不管辖)
- 不动:`router.py` 现有 `route_by_name` / `select_route` / `fallback_route_for` / `ROUTE_REGISTRY` / `lookup_route_by_name` 任何符号
- 改动:`tests/test_invariant_guards.py:460-461` 删除 `pytest.skip`,实装 AST 守卫

**关键设计决策**:

- **`_http_helpers.py` 搬迁清单(authoritative,Codex 实装时严格对齐)**:
  | Symbol | 来源 | Phase 64 后位置 | 注 |
  |--------|------|----------------|----|
  | `AgentLLMResponse` | `agent_llm.py:22-30` 附近 | `_http_helpers.py` | dataclass,搬迁后 `agent_llm.py` re-export |
  | `AgentLLMUnavailable` | `agent_llm.py`(exception 定义)| `_http_helpers.py` | exception,re-export |
  | `extract_api_usage` | `executor.py` | `_http_helpers.py` | 搬走 |
  | `parse_timeout_seconds` | `executor.py` | `_http_helpers.py` | 搬走 |
  | `resolve_new_api_api_key` | `executor.py` | `_http_helpers.py` | 搬走 |
  | `resolve_new_api_chat_completions_url` | `executor.py` | `_http_helpers.py` | 搬走 |
  | `_http_request_headers` | `executor.py:1160-1165` | `_http_helpers.py` 改名 `http_request_headers` | 搬走且改公开 |
  | `extract_json_object` | `agent_llm.py` | **不搬**(留在 agent_llm.py,Specialist import 不变)| Specialist 现 `from .agent_llm import call_agent_llm, AgentLLMUnavailable, extract_json_object` 三件 — call_agent_llm 留 agent_llm.py(thin caller)、AgentLLMUnavailable re-export、extract_json_object 留 agent_llm.py |
  | `clean_output` | `executor.py` | **不搬,除非 router.invoke_completion 需要** | 由 Codex spike 时确认 router seam 是否调用;若调,搬;若否,留 executor.py |
  | `_normalize_http_response_content` | `executor.py` | 同上 | 由 Codex spike 时确认 |
  | `resolve_swl_chat_model` | `runtime_config.py` | 不动(Phase 64 scope 外)| `runtime_config.py` 已是中性模块,直接 import |

- **`invoke_completion` 内部实装(authoritative,Codex 严格对齐)**:
  ```python
  def invoke_completion(
      prompt: str,
      *,
      system: str = "",
      model: str | None = None,
      timeout_seconds: int | None = None,
  ) -> AgentLLMResponse:
      from ._http_helpers import (
          AgentLLMResponse,
          AgentLLMUnavailable,
          extract_api_usage,
          http_request_headers,
          parse_timeout_seconds,
          resolve_new_api_api_key,
          resolve_new_api_chat_completions_url,
      )
      from .runtime_config import resolve_swl_chat_model
      import httpx, json, os
      api_key = resolve_new_api_api_key()
      if not api_key:
          raise AgentLLMUnavailable("LLM enhancement unavailable: API key not configured.")
      resolved_timeout = timeout_seconds or parse_timeout_seconds(
          os.environ.get("AIWF_EXECUTOR_TIMEOUT_SECONDS", "30")
      )
      resolved_model = model or resolve_swl_chat_model()  # equivalent to legacy resolve_agent_llm_model(model)
      url = resolve_new_api_chat_completions_url()
      messages: list[dict[str, str]] = []
      if system.strip():
          messages.append({"role": "system", "content": system.strip()})
      messages.append({"role": "user", "content": prompt})
      try:
          response = httpx.post(
              url,
              json={"model": resolved_model, "messages": messages},
              headers=http_request_headers(),
              timeout=resolved_timeout,
          )
          response.raise_for_status()
          payload = response.json()
          choices = payload["choices"]
          message = choices[0]["message"]
          # … 余下与原 call_agent_llm 解析路径完全一致 …
      except httpx.HTTPError as exc:
          raise AgentLLMUnavailable(f"LLM enhancement unavailable: {exc}") from exc
      except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
          raise AgentLLMUnavailable(f"LLM enhancement returned an unreadable payload: {exc}") from exc
      if not content:
          raise AgentLLMUnavailable("LLM enhancement returned an empty response.")
      input_tokens, output_tokens = extract_api_usage(payload)
      returned_model = clean_output(str(payload.get("model", "") or resolved_model)) or resolved_model
      return AgentLLMResponse(content=content, input_tokens=input_tokens, output_tokens=output_tokens, model=returned_model)
  ```
  **注**:`resolved_model = model or resolve_swl_chat_model()` 是把现 `agent_llm.py:34 resolve_agent_llm_model(model)`(单行 wrapper,实装就是 `model or resolve_swl_chat_model()`)inline 展开,避免在 router.py 反向 import agent_llm.py 形成新循环。`resolve_agent_llm_model` 函数本身不搬到 `_http_helpers`(YAGNI,inline 即可);`agent_llm.py` 内 `resolve_agent_llm_model` 保留(被 tests/test_specialist_agents.py:13 直接 import)

- **`call_agent_llm` 退化形式**:
  ```python
  def call_agent_llm(
      prompt: str,
      *,
      system: str = "",
      model: str | None = None,
      timeout_seconds: int | None = None,
  ) -> AgentLLMResponse:
      from .router import invoke_completion
      return invoke_completion(prompt, system=system, model=model, timeout_seconds=timeout_seconds)
  ```

- **测试 mock 透明性强制要求**(消化 design_audit CONCERN + GPT-5 CONCERN Q8):**Codex 在 S2 PR body 中必须提供**:
  - grep 命中清单:`grep -rn 'patch.*httpx\|patch.*agent_llm\|from swallow.agent_llm import\|from swallow._http_helpers import' tests/`
  - 一条 integration-level smoke test(在 `tests/test_invariant_guards.py` 或 `tests/test_router.py` 新建): mock `httpx.post`(而非 `call_agent_llm`),验证 `call_agent_llm(...)` → `invoke_completion(...)` → `httpx.post(...)` 整条链路被实际执行。这一条 test 是 design_decision §S2 的 hard requirement,Claude review 时必查

- **守卫策略(`test_specialist_internal_llm_calls_go_through_router`)**:
  - **扫描范围**:`src/swallow/` 全 .py 文件(排除 `router.py:invoke_completion`、`tests/` 目录、`_http_helpers.py`)
  - **AST pattern**(细化,GPT-5 BLOCK Q9 消化):
    1. 查所有 chat-completion `httpx.post` 调用节点,**两种形态都识别**(S2-C2 消化):
       - **直接调用**:`Call(func=Attribute(value=Name("httpx"), attr="post"))` — 即 `httpx.post(...)`
       - **AsyncClient 实例调用**:`Call(func=Attribute(attr="post"))` 且接收方是 `httpx.AsyncClient(...)` 或 `httpx.Client(...)` 实例 — 即 `async with httpx.AsyncClient(...) as client: await client.post(...)`(executor.py 中 Path A 异步实装)。**实装层面**:在 AST scan 中先收集所有 `Attribute(attr="post")` 调用,再 cross-reference 同模块中是否存在 `httpx.AsyncClient(...)` / `httpx.Client(...)` 构造的赋值或 `with` 语句,识别 receiver
    2. 对每个命中,提取 `url` 参数(positional[0] 或 keyword `url`):
       - 若是 `Constant("..../chat/completions")` 字符串字面量 → 命中(违规,除非在 allow-list)
       - 若是 `Call(Name("resolve_new_api_chat_completions_url"))` → 命中
       - 若是 f-string / 变量 / 其他动态 url 表达式 → **不命中**(避免误报 embeddings / 其他 API)
    3. 命中后,检查所在文件:仅 `router.py:invoke_completion` 是 allow-list(整个 `agent_llm.py` 不在 allow-list,因为 S2 后该文件已无 httpx.post)
  - **守卫 docstring** 显式注明:"扫描范围 = chat-completion endpoint;embeddings(`/v1/embeddings`)/ non-LLM HTTP 不在管辖。Provider Router 是 chat-completion 的唯一 gateway"
  - **反 vacuous 锚点**:`assert hasattr(swallow.router, "invoke_completion")`(确认 seam 存在);可选加 `assert callable(swallow.router.invoke_completion)`

**验收条件**:
- `swallow._http_helpers` 模块存在且导出上述 authoritative 清单
- `swallow.router.invoke_completion(...)` 存在,签名为 `(prompt, *, system="", model=None, timeout_seconds=None) -> AgentLLMResponse`(**无 `route_hint`**)
- `swallow.agent_llm.call_agent_llm` 实现退化为单行 invoke_completion 调用
- `grep -n 'httpx\.post' src/swallow/agent_llm.py` 命中 0
- `grep -n 'httpx\.post' src/swallow/router.py` 命中 1(invoke_completion 内)
- `grep -rn 'from .executor import' src/swallow/agent_llm.py` 命中 0(改走 _http_helpers)
- `test_specialist_internal_llm_calls_go_through_router` 启用且通过(非 `pytest.skip`),AST pattern 按 chat-completion URL 字面量扫
- `tests/test_invariant_guards.py` 或 `tests/test_router.py` 新增 integration smoke test,mock `httpx.post` 并断言 `call_agent_llm → invoke_completion → httpx.post` 整链被执行
- 现有 `tests/test_specialist_agents.py` / `tests/test_retrieval_adapters.py` 中 `patch("swallow.X.call_agent_llm", ...)` mock 模式仍有效(测试零迁移)
- 全量 pytest 通过

**风险评级**:影响范围 2 / 可逆性 1 / 依赖 3 = 6(中)。helper 抽迁 + 新公开接口引入 + 三方 import 图重构。回滚成本中等(revert 涉及 router + agent_llm + executor + _http_helpers)

---

## 依赖与顺序

```
S1 (M1, executor → state read + lookup_route_by_name) ──> S2 (M2, _http_helpers + invoke_completion)
   (S2 守卫扫描需要 S1 完成后 executor 已无 selection 调用作干净基线)
```

**Codex 推荐实装顺序**:**S1 → S2**(无并行)。S1 完成后整个 executor 已无 selection 调用,S2 在干净基线上引入 `_http_helpers` + 新 seam

## Milestone 与 review checkpoint

| Milestone | 包含 slice | review 重点 | 提交节奏 |
|-----------|-----------|------------|---------|
| **M1** | S1 | TaskState 字段引入是否最小 / orchestrator + MPS pre-resolve 时序对称 / `_load_fallback_route` 新签名 + 2 调用点更新 / `lookup_route_by_name` 引入合规 / 守卫 AST pattern + 反 vacuous 锚点 | 单独 milestone commit |
| **M2** | S2 | `_http_helpers.py` 搬迁清单完整 / `invoke_completion` 与原 call_agent_llm 字符级等价 / `call_agent_llm` thin caller 退化 / 守卫 chat-completion URL pattern + integration smoke test / 测试 mock 透明性 grep 证明 | 单独 milestone commit |

## 守卫与测试映射

| Slice | 启用 / 新增守卫 | §9 表内 | §9 表外 |
|-------|---------------|---------|---------|
| S1 | `test_path_b_does_not_call_provider_router`(unskip,扫 selection 调用)| 1 | 0 |
| S2 | `test_specialist_internal_llm_calls_go_through_router`(unskip,扫 chat-completion URL)+ integration smoke test | 1 | 0(smoke test 是 PR body 强制要求,不计 §9)|
| **合计** | **2 条 unskip + 1 条 smoke test** | **2** | **0** |

完结后:INVARIANTS §9 标准表 17 条全部 active(0 skip)

## phase-guard 检查

- ✅ 当前方案不越出 kickoff goals(G1-G5 + S1-S2 一一对应)
- ✅ kickoff non-goals 严守:**不修改 INVARIANTS / DATA_MODEL 任何文字**;不扩展 RouteSpec / AgentLLMResponse / call_agent_llm 公开签名;不引入 RouteSpec.from_dict;不引入 route_hint;不动 Phase 63 内容
- ✅ slice 数量 2 个,符合"≤5 slice"指引
- ✅ 0 高风险 slice(S1 中 5 / S2 中 6;全 phase 无 7+)
- ✅ Provider Router 概念边界已声明 = registry + selection + invocation gateway 三合一;dependency rule 已在 kickoff §设计边界 节列出

## Branch Advice

- 当前分支:`main`(Phase 63 已 merge)
- 建议 branch 名:`feat/phase64-llm-router-boundary`
- 建议操作:Human Design Gate 通过后 Human 切出该 branch,Codex 在该分支上实装 S1 → S2

## Model Review Gate

**已完成**(2026-04-29,reviewer = external GPT-5 via `mcp__gpt5__chat-with-gpt5_5`):**verdict = BLOCK**。本 design_decision 转 `revised-after-model-review` 已落实所有 BLOCK + CONCERN 消化 — 详见 `docs/plans/phase64/model_review.md` §Findings 与 `kickoff.md §Model Review Gate`

**修订后是否再触发一次**:**否**(GPT-5 一轮已覆盖核心结构性风险,本轮 revised 是按 pivot 方向 + 接受其 BLOCK 修复,scope 收敛而非扩张;design-auditor 二次校验即可)

## 不做的事(详见 kickoff non-goals)

- 不修改 INVARIANTS / DATA_MODEL 任何文字
- 不引入 RouteSpec.from_dict / 不扩展 RouteSpec / AgentLLMResponse / call_agent_llm 公开签名
- 不引入 invoke_completion 的 route_hint 参数
- 不动 fallback 触发条件 / Path A/B 分支逻辑
- 不动 Phase 63 已落地内容
- 不引入 SQLite 事务 / metrics / audit log / cost 集中
- 不拆 Phase 64.5

## 验收条件(全 phase)

详见 `kickoff.md §完成条件`。本 design_decision 与 kickoff 一致,无补充。
