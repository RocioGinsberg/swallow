---
author: claude
phase: phase64
slice: review
status: final
depends_on:
  - docs/plans/phase64/kickoff.md
  - docs/plans/phase64/design_decision.md
  - docs/plans/phase64/risk_assessment.md
  - docs/plans/phase64/design_audit.md
  - docs/plans/phase64/model_review.md
  - docs/plans/phase64/commit_summary.md
  - docs/plans/phase64/consistency_report.md
---

TL;DR:**Verdict: APPROVE**(0 BLOCK / 1 CONCERN / 8 NOTE)。M1/S1 chain plan + M2/S2 router seam + 三层外部化 follow-up 全部按 design 与 commit_summary 落地;§9 17 守卫全 active(0 skip),`docs/design/` 零 diff,pytest 589 passed;consistency-checker 7/7 MATCH。
唯一 [CONCERN-1] = `synthesis.py` 反向 import orchestrator 私有 `_resolve_fallback_chain`,Claude 推荐升级到 `router.resolve_fallback_chain` 公开 API,Human 在 Merge Gate 决定本 PR 内消化或后续 phase 处理。

# Phase 64 PR Review

## 审阅范围

- 分支: `feat/phase64-llm-router-boundary` vs `main`
- diff 体量: 30 文件,3174 insertions / 770 deletions
- commit 序列(7 commits): `cca9983`(design)→ `afec43c`(M1/S1)→ `6ad909e`(M1 fallback override follow-up)→ `d2f03a8`(M2/S2)→ `900c38b`(route registry follow-up)→ `c404f3e`(route policy follow-up)→ `79dc972`(commit_summary docs)
- 设计基线:`docs/plans/phase64/{kickoff,design_decision,risk_assessment}.md`(全部 status=`revised-after-model-review`)+ `commit_summary.md`(Human-approved follow-up scope authoritative)
- 一致性核验:`docs/plans/phase64/consistency_report.md`(consistency-checker subagent 后台并行,verdict=`consistent`,7/7 MATCH)
- 测试基线复跑:`.venv/bin/python -m pytest -q` → **589 passed / 8 deselected / 10 subtests passed**(与 commit_summary 验证记录完全吻合)

## 总体结论

| 维度 | 结果 |
|------|------|
| INVARIANTS.md / DATA_MODEL.md 文字未改 | ✅ `git diff main...HEAD -- docs/design/` 零行 |
| §9 守卫表完整性 | ✅ 17 条全 active(`grep -c "pytest.skip" tests/test_invariant_guards.py` = 0) |
| `test_path_b_does_not_call_provider_router` | ✅ AST 扫 executor.py + 4 selection 函数 + 反 vacuous 锚点 |
| `test_specialist_internal_llm_calls_go_through_router` | ✅ 三段 AST pattern(httpx.post / AsyncClient / Constant URL `/chat/completions` / Call `resolve_new_api_chat_completions_url`)+ 函数级 allow-list |
| `_load_fallback_route` 三参签名 + chain 索引算法 | ✅ executor.py:510-528,multi-hop reentry 安全 |
| `state.fallback_route_chain` immutability | ✅ executor.py:534 显式注释 "do not rewrite it here"(S1-C1 消化) |
| `lookup_route_by_name` read-only forwarder | ✅ router.py:899-902,docstring 显式 |
| MPS Path A 同步预填 chain | ✅ synthesis.py:159 `_resolve_fallback_chain(route.name)` |
| `_http_helpers.py` 中性模块 + 完整 helper 搬迁 | ✅ 92 行,authoritative symbol 全到位 |
| `call_agent_llm` thin caller(测试 mock 透明) | ✅ agent_llm.py:14-23 三行函数体 |
| `invoke_completion` 与原 `call_agent_llm` 字符级等价 | ✅ inline `resolve_swl_chat_model(explicit_model=model)` 消化 S2-C1 |
| route registry 外部化 + governance 路径 | ✅ CLI `swl route registry apply` → `register_route_metadata_proposal(route_registry=...)` → `apply_proposal(..., ROUTE_METADATA)` → `RouteRepo._apply_metadata_change` |
| route policy 外部化(reuse ROUTE_METADATA) | ✅ 不新增 ProposalTarget,governance enum 仍 3 项 |
| Repository 写边界守卫扩展含新 save 函数 | ✅ `save_route_registry` / `save_route_policy` 已加入 `test_only_apply_proposal_calls_private_writers` / `test_no_module_outside_governance_imports_store_writes` / `test_route_metadata_writes_only_via_apply_proposal` |
| 加载顺序在所有入口对齐 | ✅ registry → policy → weights → fallbacks → capability(orchestrator 3 处 + cli 2 处) |
| pytest 全量回归 | ✅ 589 passed / 8 deselected,与 commit_summary 一致 |

**Verdict**:**APPROVE**(待 [CONCERN-1] 由 Human 在 Merge Gate 决定本 PR 内消化或登记 backlog)。

---

## M1 / S1 — Path B fallback chain plan(commit `afec43c`)

### [PASS] orchestrator 预解析 chain plan 算法

`orchestrator.py:213-225 _resolve_fallback_chain(primary_route_name)`:
```python
chain: list[str] = []
seen: set[str] = set()
current_name = route.name
while current_name and current_name not in seen:
    chain.append(current_name)
    seen.add(current_name)
    fallback_route = fallback_route_for(current_name)
    current_name = fallback_route.name if fallback_route is not None else ""
return tuple(chain)
```
环检测内置(`current_name not in seen` break),与 design_decision §S1 pseudocode 完全一致。`test_resolve_fallback_chain_covers_builtin_http_chain` (test_router.py) 实测:`http-claude → http-qwen → http-glm → local-claude-code → local-summary`(5 跳完整线性,与实际 ROUTE_REGISTRY 对齐;design 修订时已修正了原 R2 误写的"http-glm ↔ http-qwen 互链")。

### [PASS] executor `_load_fallback_route` 新签名 + chain index 算法

`executor.py:510-528`:
```python
def _load_fallback_route(state: TaskState, current_route_name: str, visited_routes: set[str]) -> RouteSpec | None:
    from .router import lookup_route_by_name
    chain = tuple(...)
    if not chain: return None
    try: current_index = chain.index(current_route_name)
    except ValueError: return None
    next_index = current_index + 1
    if next_index >= len(chain): return None
    next_route_name = chain[next_index]
    if next_route_name in visited_routes: return None
    return lookup_route_by_name(next_route_name)
```
**关键正确性**:multi-hop reentry 时 `state.fallback_route_chain` 不变,executor 第二次进入 `_apply_executor_route_fallback` 时 `current_route_name` 已变为第一跳 fallback,通过 `chain.index(current_route_name)` 在保留的完整 chain 中重新定位 → 取下一跳。这是 design_audit BLOCKER S1-2 + GPT-5 BLOCK Q2 的正确解。

### [PASS] `state.fallback_route_chain` 不可变约束(S1-C1)

`executor.py:534` 在 `_apply_route_spec_for_executor_fallback` 函数体首行加注释:
```python
# The fallback chain is an immutable execution plan from the orchestrator; do not rewrite it here.
```
这是 design_audit revised CONCERN S1-C1 的显式落地。

### [PASS] `lookup_route_by_name` read-only forwarder(GPT-5 option i 落地)

`router.py:899-902`:
```python
def lookup_route_by_name(route_name: str) -> RouteSpec | None:
    """Return static route metadata by name without performing route selection."""
    return route_by_name(route_name)
```
单行 forwarder + docstring 显式声明 read-only,守卫 allow-list 自然识别该函数为合法 executor 调用方(不在 selection set)。

### [PASS] `test_path_b_does_not_call_provider_router` AST 守卫(unskipped + non-vacuous)

`tests/test_invariant_guards.py:457-477`:
- 反 vacuous 锚点:`assert hasattr(router, "fallback_route_for")`(line 461)
- selection 函数 set authoritative:`{"select_route", "route_by_name", "fallback_route_for", "route_for_mode"}`(line 462)
- 扫 `executor.py` 单文件,扫 ImportFrom + Call 节点 — 双路径
- docstring 显式 "Path B executor code may consume route metadata, but must not perform route selection"(与 INVARIANTS §0 第 1 条 + §4 表语义严格对齐)

### [PASS] MPS Path A 同步预填 chain

`synthesis.py:159 _participant_state_for_call`:
```python
fallback_route_chain=_resolve_fallback_chain(route.name)
```
participant 用其自己的 RouteSpec 重算 chain,而非继承 base_state 主链 — 消化 design_audit revised CONCERN MPS regression。

### [NOTE M1-1] synthesis.py 反向 import orchestrator 私有 helper

`synthesis.py:9 from .orchestrator import _resolve_fallback_chain`(私有 `_` 前缀函数被跨模块 import)。Python 约定上私有性 informational,但 governance.py / 既有项目内有类似模式;不破坏行为。

- 影响:低。如果将来 orchestrator 重构改名 `_resolve_fallback_chain`,synthesis.py 会跟着断。
- 建议(可选):升级到 router 公开 API 例如 `router.resolve_fallback_chain(...)`(基于现有 `fallback_route_for`),让 orchestrator 与 synthesis 都从 router 调。**留作 [CONCERN-1] 由 Human 决定本 PR 内消化或后续 phase 处理**。

---

## M1 fallback override config seam(commit `6ad909e`,Human follow-up)

### [PASS] operator-local config seam,正确不走 governance

`router.py:790-828` `load_route_fallbacks` / `apply_route_fallbacks`:
- 读 `.swl/route_fallbacks.json`(config seam,operator 本地 override)
- mutate ROUTE_REGISTRY 实例的 `route.fallback_route_name` 字段
- **未实装 `save_route_fallbacks` 函数** — 正确,因为这不是 truth metadata 写入(operator-local config),不在 §0 第 4 条 governance 范围
- `_BUILTIN_ROUTE_FALLBACKS` baseline snapshot(line 587)在缺失配置时 reset 回内置默认,防止 idempotent 误差
- 未知 fallback 名拒绝(`if not configured_fallback or configured_fallback in known_routes`)— input 校验合规

### [PASS] 加载顺序在所有入口对齐(consistency-checker 已核)

orchestrator.py(`acknowledge_task` / `create_task` / `run_task_async`)+ cli.py(`main` 顶部 + `route select` 子命令)五处入口全部按 `apply_route_weights → apply_route_fallbacks → apply_route_capability_profiles` 顺序加载;Phase 64 后续 follow-up 把 registry / policy 也加进来,顺序变成:`apply_route_registry → apply_route_policy → apply_route_weights → apply_route_fallbacks → apply_route_capability_profiles`。

### [NOTE M1-2] route_fallbacks.json 不走 governance,与 registry/policy 不一致

design 决策 = config seam,与 commit_summary §Layer 1 一致;但相比 Layer 2/3 走 `apply_proposal` 路径,Layer 1 不留 `know_change_log` audit 痕迹。如果未来需要审计 fallback override 谁改的、何时改的,需要把 fallbacks 也接入 governance。

- 影响:低。当前是 operator local config seam,审计需求未现。
- 建议:closeout 留痕。

---

## M2 / S2 — Specialist 内部 LLM Provider Router seam(commit `d2f03a8`)

### [PASS] `_http_helpers.py` 中性模块强制方案落地(GPT-5 BLOCK Q4 消化)

92 行,authoritative symbols 完整搬迁:`AgentLLMResponse` / `AgentLLMUnavailable` / `DEFAULT_NEW_API_CHAT_COMPLETIONS_URL` / `resolve_new_api_chat_completions_url` / `resolve_new_api_api_key` / `http_request_headers` / `normalize_http_response_content` / `extract_api_usage` / `parse_timeout_seconds` / `clean_output`。`router.py` 与 `executor.py` 均从 `_http_helpers` 顶部 import,**循环依赖断**(原 router → executor / agent_llm → executor / agent_llm → router 三向 import 全部清理)。

### [PASS] `call_agent_llm` thin caller(测试 mock 透明)

`agent_llm.py:14-23`:
```python
def call_agent_llm(prompt, *, system="", model=None, timeout_seconds=None) -> AgentLLMResponse:
    from .router import invoke_completion
    return invoke_completion(prompt, system=system, model=model, timeout_seconds=timeout_seconds)
```
3 行函数体,签名 + 返回类型 + 异常类型与原版完全一致;`AgentLLMResponse` / `AgentLLMUnavailable` 在 `agent_llm.py:6` re-export 自 `_http_helpers`,Specialist 与测试 `from swallow.agent_llm import ...` 零迁移。

### [PASS] `invoke_completion` 与原 `call_agent_llm` 字符级等价

`router.py:831-876`:URL / model / messages / headers / timeout / payload 解析 / token 抽取 / `AgentLLMResponse` 构造 — 字段 1:1 对应原 `call_agent_llm`。
- **S2-C1 消化路径**:`router.py:843` `resolved_model = resolve_swl_chat_model(explicit_model=model)`,inline 跳过 `resolve_agent_llm_model` wrapper(`agent_llm.py:10` 仍保留该 wrapper 给测试 fixture);避免 router → agent_llm 反向 import。
- 异常路径完全等价:`httpx.HTTPError` → `AgentLLMUnavailable` / `(KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError)` → `AgentLLMUnavailable`。

### [PASS] `test_specialist_internal_llm_calls_go_through_router` AST 守卫(unskipped + non-vacuous + 比 design 更严)

`tests/test_invariant_guards.py:480-567`:
- 反 vacuous 锚点:`assert hasattr(router, "invoke_completion")`(line 487)
- 三种 httpx.post 形态全识别:
  - 直接 `httpx.post(...)`
  - `httpx.AsyncClient(...) as client: client.post(...)` — 通过 `_collect_httpx_client_names` 收集 receiver names(消化 design_audit revised CONCERN S2-C2)
  - 同款 Client/AsyncClient 多种声明形态(`Assign` / `AnnAssign` / `With` / `AsyncWith`)
- URL pattern 三段(`Constant` 含 `/chat/completions` OR `Call(resolve_new_api_chat_completions_url)`)
- **Allow-list 比 design 更严**:用 `function_stack[-1] == "invoke_completion"` 精确到函数级 allow,而非整个 router.py 模块级(line 564)— 这是设计层之上的 tightening
- `_http_helpers.py` 整文件排除(继承 helper)

### [PASS] integration smoke test mock httpx.post(R6 缓解 hard requirement)

`tests/test_router.py:137-163 test_call_agent_llm_invokes_router_completion_gateway`:
- mock `swallow.router.httpx.post` 而非 `call_agent_llm`(确保 `call_agent_llm → invoke_completion → httpx.post` 整条链路被实际执行)
- 断言 URL / model / messages / timeout / Authorization header 全 pipeline 正确
- 这是原 design_decision §S2 line 208 + risk_assessment R6 强制要求的 integration-level smoke test,完整到位 ✓

### [NOTE M2-1] retrieval_adapters.py:206 embeddings httpx.post 守卫不命中(预期合规)

`retrieval_adapters.py:206` 用 `f"{resolved_base_url}/v1/embeddings"`(动态 f-string URL,非 Constant 字面量);AST URL pattern step 2 不命中(动态变量 → 不命中规则),embeddings 调用合规漏出守卫管辖范围 — 与 GPT-5 BLOCK Q9 修正后的设计意图一致。closeout 可登记说明守卫不管辖 embeddings,与 §0 第 3 条聚焦 chat-completion 一致。

### [NOTE M2-2] `executor.py:1171, 1291` Path A httpx.post 通过 allow-list 排除

`run_http_executor` / async 变体的 `httpx.post`(L1171)与 `httpx.AsyncClient(...).post`(L1291)是合法 Path A 调用;它们的 URL 来源 = `resolve_new_api_chat_completions_url()` 调用结果,理论上 step 2 rule 2 会命中 — 但 allow-list step 3 的"function-level allow"只放 `router.py:invoke_completion`,**executor.py 中的命中应该被识别为违规** — 看实际代码:

实际守卫实装(line 564):`if rel_path != "src/swallow/router.py" or current_function != "invoke_completion": violations.append(...)`。executor.py 必然进入 violations 分支。**但守卫 PASS**,说明 executor.py 的 httpx.post URL 表达式不被 step 2 的 `_chat_completion_url_expression` 命中(实际是 `endpoint = resolve_new_api_chat_completions_url(); httpx.post(endpoint, ...)` —— `endpoint` 是变量名 `Name`,不是 `Call` 也不是 `Constant`,所以 URL pattern 不命中)。

**这是合理的实装结果**:守卫只命中"直接传 chat-completion endpoint 字面量或 helper 调用",不命中"先赋值给变量再用"。但这意味着如果未来某 Specialist 写 `endpoint = some_chat_url(); httpx.post(endpoint, ...)`,守卫会漏报。当前代码安全,但守卫强度依赖实装风格。

- 影响:低。closeout 登记一条 backlog Open:"守卫只识别字面量 / 直接 helper 调用,变量绑定路径漏报;后续若 Specialist / 基础设施层引入 indirect URL 路径,需评估守卫精化"。

---

## M2 follow-up — Route Registry Externalization(commit `900c38b`,Human follow-up)

### [PASS] governance 入口扩展严格对称

`governance.py`:
- `_RouteMetadataProposal` dataclass 加 `route_registry: dict[str, dict[str, object]] | None = None` 字段,与 weights/profiles 模式对称(line 68)
- `register_route_metadata_proposal(..., route_registry=...)` 新增 kwarg,review_path 互斥校验同步扩展(line 134-152)
- `_apply_route_metadata` 透传 `route_registry` 到 `RouteRepo._apply_metadata_change`
- **不新增 ProposalTarget enum value**,registry 写复用 `ProposalTarget.ROUTE_METADATA`(consistency-checker CP3 已核 MATCH)

### [PASS] CLI `swl route registry show/apply` 严格走 governance

`cli.py:2625-2648`:
- `apply` 子命令读 JSON → `register_route_metadata_proposal(base_dir, proposal_id, route_registry=...)` → `apply_proposal(proposal_id, OperatorToken(source="cli"), ProposalTarget.ROUTE_METADATA)` — 完全合规 §0 第 4 条
- `show` 子命令读 + render,无写

### [PASS] Repository 写边界守卫扩展

`tests/test_invariant_guards.py` 三处守卫的 `protected_names` set 已加入 `save_route_registry`(line 211 / 275 / 326)。守卫继续保护 Repository 抽象层不被绕过。

### [PASS] routes.default.json schema 与 RouteSpec 字段集合一致

353 行 JSON 数据,字段集合(`name` / `executor_name` / `backend_kind` / `model_hint` / `dialect_hint` / `executor_family` / `execution_site` / `remote_capable` / `transport_kind` / `capabilities` / `taxonomy` / `fallback_route_name`)与 `models.py` `RouteSpec` dataclass 字段严格对应,**不修改 RouteSpec schema**(consistency-checker CP7 已核)。

---

## M2 follow-up — Route Selection Policy Externalization(commit `c404f3e`,Human follow-up)

### [PASS] route policy 严格归入 ROUTE_METADATA(不新建 ProposalTarget.POLICY)

`commit_summary.md:88` 强调:"这不是 `ProposalTarget.POLICY`,而是 Provider Router 的 route selection metadata,因此归入 `ProposalTarget.ROUTE_METADATA`"。实装严格执行:
- `governance.py` 仍 3 个 ProposalTarget enum value(consistency-checker CP3)
- `_RouteMetadataProposal` 加 `route_policy` 字段(line 70),与 registry / weights / profiles 平级
- `_apply_route_metadata` 透传 `route_policy` 到 `RouteRepo._apply_metadata_change`(line 311)

### [PASS] route_policy schema 与 commit_summary §Layer 3 完全一致

`route_policy.default.json`:
```json
{
  "complexity_bias_routes": {...},
  "parallel_intent_hints": [...],
  "route_mode_routes": {...},
  "strategy_complexity_hints": [...],
  "summary_fallback_route_name": "..."
}
```
5 个 schema key 与 commit_summary line 80-84 列出的一致。

### [PASS] CLI `swl route policy show/apply` 与 registry 镜像

cli.py 实装 `apply` 通过 `register_route_metadata_proposal(..., route_policy=...)` + `apply_proposal(..., ROUTE_METADATA)`,与 registry CLI 完全镜像(consistency-checker CP1 已核)。

### [PASS] Repository 写边界守卫扩展

`save_route_policy` 已加入三处守卫的 protected_names(line 212 / 276 / 327),与 registry 同步。

---

## 全局一致性

### [PASS] INVARIANTS / DATA_MODEL 文字未改

```bash
$ git diff main...HEAD -- docs/design/ | wc -l
0
```
本 phase 全部 non-goals 中"不修改 INVARIANTS / DATA_MODEL 任何文字"严格守住。

### [PASS] §9 标准表 17 条全 active(0 skip)

```bash
$ grep -c "pytest.skip" tests/test_invariant_guards.py
0
```
Phase 64 = 候选 G.5 的核心承诺(消除 NO_SKIP 红灯 2 条占位)完整兑现。

### [PASS] 测试基线复跑

```
$ .venv/bin/python -m pytest -q
589 passed, 8 deselected, 10 subtests passed in 87.45s
```
与 commit_summary.md `c404f3e` 验证记录(line 117-118)完全一致。

### [PASS] commit message 风格规范

7 commits 全部 conventional commit:`feat/refactor/test/docs(phase64): ...`;commit_summary 详细记录 follow-up scope authoritative description,避免 reviewer 误判 follow-up 为 spontaneous refactor。

### [PASS] consistency-checker 7/7 MATCH

`docs/plans/phase64/consistency_report.md`(verdict = `consistent`):
- CP1 (write boundary): MATCH
- CP2 (Phase 63 invariant guards still active): MATCH
- CP3 (no new ProposalTarget): MATCH
- CP4 (INVARIANTS/DATA_MODEL untouched): MATCH
- CP5 (S1/S2 main-line boundaries intact): MATCH
- CP6 (load order in 5 entry points): MATCH
- CP7 (no schema change): MATCH

---

## 处理建议

### 进入 PR(Human Merge Gate 决定本 PR 内是否消化)

- **[CONCERN-1] synthesis.py 反向 import 私有 `_resolve_fallback_chain`** — 单条 [CONCERN]:`synthesis.py:9 from .orchestrator import _resolve_fallback_chain` 跨模块 import 私有 helper。两选项:
  - **选项 A(推荐,本 PR 内消化)**:把 `_resolve_fallback_chain` 升级到 router 公开 API 例如 `router.resolve_fallback_chain(primary_route_name)`,内部实装就是现有 algorithm,orchestrator 与 synthesis 都从 router 调用。3 行改动 + 1 行 docstring。
  - **选项 B**:接受现状,closeout 登记 backlog Open,留给后续重构。
  - Claude 推荐选项 A:既消化 [CONCERN]、又把 chain 解析能力升级为 router 模块的 public 数据查询 API,与 `lookup_route_by_name` 对称。

### 进入 closeout 留痕(不入 PR body / 不入 backlog)

- M1-1 `synthesis.py` private import(若选 [CONCERN-1] 选项 A,本条消化;若选项 B,留 backlog)
- M1-2 `route_fallbacks.json` 不走 governance(operator-local config seam,与 commit_summary §Layer 1 边界声明一致)
- M2-1 retrieval_adapters.py embeddings 守卫不管辖(预期合规,与 §0 第 3 条聚焦 chat-completion 一致)

### 进入 concerns_backlog(后续 phase 消化)

- **M2-2 守卫漏报 indirect URL 绑定路径**:`endpoint = resolve_new_api_chat_completions_url(); httpx.post(endpoint, ...)` 形态守卫 step 2 URL pattern 不命中。当前代码安全,但守卫强度依赖实装风格;后续若引入间接路径需评估守卫精化(如:扫 helper 函数返回值流向 + 跨函数 def-use 链分析)。

### 进入 PR body 测试节

```
.venv/bin/python -m pytest
589 passed, 8 deselected, 10 subtests passed in 87.45s

.venv/bin/python -m pytest tests/test_invariant_guards.py
(no skipped guards; §9 17 active)

git diff main...HEAD -- docs/design/  # 0 lines (INVARIANTS / DATA_MODEL untouched)
git diff --check  # passed (per commit_summary)
```

skipped 0 条:Phase 63 留下的 2 条 G.5 占位守卫(`test_path_b_does_not_call_provider_router` + `test_specialist_internal_llm_calls_go_through_router`)已 unskip + active + 通过。

---

## Tag 建议

候选 G.5 = Phase 64 是 governance 三段(候选 G + G.5 + H)中的第二段。Claude 建议 **本 PR merge 后不立即打 tag**,待候选 H(Truth Plane SQLite)完成后,以 governance closure 整体收口为主题打 `v1.4.0` minor bump。Phase 64 阶段性产物在 commit_summary + closeout 中记录即可。

## 决议

**APPROVE**(待 [CONCERN-1] 由 Human 在 Merge Gate 决定本 PR 内消化或登记 backlog)。

下游动作:
1. **[Human]** Merge Gate:决定 [CONCERN-1] 是否本 PR 内消化(选项 A 升级 router 公开 API 是 Claude 推荐),或 (B) 进入 backlog
2. **[Codex]**(若选 A)实装 `router.resolve_fallback_chain` 公开 API + 同步 synthesis.py + 跑回归;整理 `pr.md`
3. **[Codex]**(若选 B)直接整理 `pr.md`,在 PR body 留 [CONCERN-1] 状态说明
4. **[Codex]** Phase 64 closeout 文件 `docs/plans/phase64/closeout.md` 待 merge 后产出,内含本 review 的 NOTE 条目与 backlog 登记
5. **[Human]** push branch + 创建 PR
