---
author: claude
phase: phase64
slice: kickoff
status: revised-after-model-review
depends_on: ["docs/plans/phase64/context_brief.md", "docs/plans/phase64/design_audit.md", "docs/plans/phase64/model_review.md", "docs/plans/phase63/m0_audit_report.md", "docs/plans/phase63/closeout.md", "docs/roadmap.md", "docs/design/INVARIANTS.md"]
---

TL;DR(revised-after-model-review): Phase 64 = roadmap 候选 G.5,**2 slice / 2 milestone**。**Pivot 后**:S1 = orchestrator 一次预解析整条 fallback chain plan(`tuple[str, ...]`)+ 守卫语义重新框定为"executor 不做 Provider Router 的 selection 工作"(允许读静态 RouteSpec 字段);S2 = `swallow.router.invoke_completion(prompt, *, system, model, timeout_seconds)` thin seam(`route_hint` 直接 drop)+ 强制中性模块 `swallow/_http_helpers.py` 抽 helper(打破 router-executor-agent_llm 三向 import 环)+ 守卫细化为 chat-completion endpoint pattern。INVARIANTS / DATA_MODEL 文字不动(§4 已经说 Path C 必经 Provider Router、Path B 不经,与守卫名严格一致)。无 user-facing 行为变化。

## 当前轮次

- track: `Governance`
- phase: `Phase 64`
- 主题: 治理边界 LLM 路径收口(Governance Boundary Phase 2 / 候选 G.5)
- 入口: Direction Gate 已通过(2026-04-29 Human:Phase 63 merge 后承接 G.5);model_review 已闭环(GPT-5 verdict=BLOCK,4 BLOCK + 7 CONCERN 全部消化在本轮 revised 中)

## Phase 64 在 INVARIANTS 框架中的位置(revised-after-model-review)

- **§0 第 1 条(Control)**:控制面决策只在 Orchestrator/Operator 手中。**本 phase 重新框定**:executor 读 RouteSpec 静态字段(`fallback_route_name` 等)= 数据消费,不构成控制面决策;executor 调 `select_route` / `route_by_name` / `fallback_route_for` = 控制面决策(Provider Router 的 selection 工作),**禁止**
- **§0 第 3 条 + §4(LLM 三条路径)**:
  - **§4 表内已声明**:Path A/C 经 Provider Router(✅);Path B agent 内部决定模型(❌ 不经 Provider Router)
  - 守卫名 `test_path_b_does_not_call_provider_router` 的本意 = "Path B 执行入口(executor)不做 Provider Router 的工作",与 §4 表完全对齐
  - 守卫名 `test_specialist_internal_llm_calls_go_through_router` 实际范围扩到 internal non-Path-A LLM(含 retrieval 基础设施层),与 §4 line 85 "Specialist 内部 LLM 调用必须穿透到 Provider Router" 整体语义一致
- **§9 不变量守卫表**:本 phase 启用最后 2 条 NO_SKIP 占位,使 §9 17 条全 active(0 skip)

## 目标(Goals,revised-after-model-review)

- **G1 — Red 1 修复 / Path B 控制面收回(GPT-5 option iii + i 组合)**
  - **Pivot 1**(GPT-5 option iii):Orchestrator 在 `select_route` 完成后,沿 `RouteSpec.fallback_route_name` 链跳跃**完整解析整条 fallback chain**,产出 `tuple[str, ...]` 形式的 chain(从 primary 起,逐跳的 route name),写入 `state.fallback_route_chain: tuple[str, ...]`。环检测:遇到已访问的 route 立即 break,与 executor 现有 `visited_routes` accumulator 语义一致
  - **Pivot 2**(GPT-5 option i):守卫 `test_path_b_does_not_call_provider_router` 重新框定 = "executor.py 不调 selection 函数(`select_route` / `route_by_name` / `fallback_route_for`)",**允许**executor 读 RouteSpec 静态字段(包括读 state.fallback_route_chain)。守卫 docstring 显式注明此语义读法基于 §4 表 + §0 第 1 条
  - 删除 `executor.py:510-513 _load_fallback_route` 内 `from .router import fallback_route_for`;函数体改为读 `state.fallback_route_chain`,按 visited_routes 取下一跳 name(纯字符串查找,不调 router);若需要 `RouteSpec` 对象(`_apply_route_spec_for_executor_fallback` 接受 RouteSpec),用一次 ROUTE_REGISTRY 静态查找(下文 G1.5 决定)
  - 启用 `test_path_b_does_not_call_provider_router` 守卫(non-vacuous AST scan)

- **G1.5 — Executor 取得 RouteSpec 对象的桥**
  - executor 的 `_apply_route_spec_for_executor_fallback(state, route, reason)`(executor.py:516)接受 `RouteSpec` 对象。Pivot 后 executor 拿到的是 chain 中下一跳的 `name: str`,需要一次"name → RouteSpec" 反查
  - **决议**:**新增 `swallow.router.lookup_route_by_name(name: str) -> RouteSpec | None`** read-only 查询助手,语义 = `route_by_name` 但显式标记为"data lookup, not selection"。守卫 allow-list 把 `lookup_route_by_name` 视为允许,但 `route_by_name` / `select_route` / `fallback_route_for` 不在允许列表
  - **rationale**:语义清晰(name lookup ≠ selection),允许 executor 调一个明确标记为 read-only 的助手,既消化 BLOCKER S1-2 的 state 参数矛盾,又不模糊 §0 第 1 条边界
  - **alternative considered & rejected**:不直接复用 `route_by_name` — 名字暗示 selection;不让 executor 直接 access ROUTE_REGISTRY — 暴露 internal singleton 比暴露 helper 更糟

- **G2 — Red 2 修复 / Specialist 内部 LLM Provider Router seam**
  - 在 `swallow.router` 引入 `invoke_completion(prompt: str, *, system: str = "", model: str | None = None, timeout_seconds: int | None = None) -> AgentLLMResponse` thin seam
  - **`route_hint` 参数 dropped**(YAGNI;非 None 行为本 phase 内 = no-op,GPT-5 警告 silent ignore 是 routing 语义最坏默认值;留给真正需要 routing 的未来 phase 再加)
  - `agent_llm.call_agent_llm` 退化为 `from .router import invoke_completion; return invoke_completion(prompt, system=system, model=model, timeout_seconds=timeout_seconds)`(thin caller,签名 + 返回类型不变,**测试 mock 透明**)
  - `httpx.post` 直连从 `agent_llm.py` 移除,下沉到 `router.invoke_completion` 内部
  - 默认 endpoint / model 决议保留既有 helper(`resolve_swl_chat_model` / `resolve_new_api_chat_completions_url` / `_http_request_headers` / `parse_timeout_seconds` / `resolve_new_api_api_key`),零行为变化基线
  - 启用 `test_specialist_internal_llm_calls_go_through_router` 守卫(non-vacuous AST scan)

- **G3 — Helper 中性模块抽取(强制,GPT-5 BLOCK Q4 消化)**
  - **新增** `src/swallow/_http_helpers.py` — 中性模块,容纳 `agent_llm.py` 与 `router.py` 双向需要的 helper:
    - `AgentLLMResponse`(dataclass)
    - `AgentLLMUnavailable`(exception)
    - `extract_api_usage`(从 executor.py 搬迁)
    - `parse_timeout_seconds`(从 executor.py 搬迁)
    - `resolve_new_api_api_key`(从 executor.py 搬迁)
    - `resolve_new_api_chat_completions_url`(从 executor.py 搬迁)
    - `_http_request_headers`(从 executor.py 搬迁,改名为 `http_request_headers`,公开)
    - `clean_output`(若仅 agent_llm 用,可不搬;若 router/executor 也用,搬)
    - `_normalize_http_response_content`(若仅 agent_llm 用,可不搬)
  - `agent_llm.py` 内部 `from ._http_helpers import ...` 替换原 `from .executor import ...`
  - `router.py` 内部 `from ._http_helpers import ...`
  - `executor.py` 内部相应改成 `from ._http_helpers import ...`(原模块导出完毕)
  - **rationale**:GPT-5 警告 lazy import 会让 Provider Router 反向依赖 Executor,违反 §0 第 3 条"Provider Router 是 LLM gateway"性质;duplicate helper 风险 divergent provider config;中性模块是唯一干净选择
  - **agent_llm.py 现有顶部 import** `from .executor import (_http_request_headers, ...)` (L10-18) 全部消失;tests/ 中如有 `from swallow.agent_llm import AgentLLMResponse` / `AgentLLMUnavailable` 形式 import,在 agent_llm.py 内显式 re-export(`from ._http_helpers import AgentLLMResponse, AgentLLMUnavailable` 顶部 import 即可,Python 名字导出自然支持)

- **G4 — `retrieval.py` 与 `retrieval_adapters.py` 守卫范围**
  - **`retrieval.py:559 rerank_retrieval_items`**:scope-in。它通过 `call_agent_llm` 间接调 LLM,本 phase 后自动经新 seam,无需修改 retrieval.py 代码本身
  - **`retrieval_adapters.py:206`**:scope-out。它直接 `httpx.post` 调 `/v1/embeddings`(embeddings,非 chat completions),与 §4 LLM 调用契约不冲突
  - 守卫 `test_specialist_internal_llm_calls_go_through_router` 实装策略**不再扫所有 `httpx.post`**(GPT-5 BLOCK Q9 消化):改为扫描 chat-completion 语义节点 — 实装层面 = 扫描 `httpx.post` 调用且 URL 字符串包含 `/chat/completions` 字符串字面量(或调用方解析的 URL helper 命中 `resolve_new_api_chat_completions_url`)。具体 AST pattern 在 design_decision §S2 关键设计决策段 authoritative 定义
  - 守卫 docstring 显式注明:"扫描范围 = chat-completion endpoint;embeddings / non-LLM HTTP 不在管辖"

- **G5 — 启用 §9 2 条 G.5 占位守卫**
  - `test_path_b_does_not_call_provider_router`:替换 `pytest.skip` 为 G1 + G1.5 提到的 selection-禁止守卫
  - `test_specialist_internal_llm_calls_go_through_router`:替换 `pytest.skip` 为 G2 + G4 提到的 chat-completion endpoint 守卫
  - 完结后 §9 17 条全 active(0 skip)

## 非目标(Non-Goals,revised-after-model-review)

- **不修改 INVARIANTS / DATA_MODEL 任何文字**(§4 表已经声明 Path B 不经 Provider Router、Path C 必经,守卫名严格对齐表语义,无需改宪法文字)
- **不修改 RouteSpec / AgentLLMResponse / call_agent_llm 公开签名**(call_agent_llm 函数体退化但签名/返回类型/异常类型不变)
- **不引入 `route_hint` 参数到 invoke_completion**(YAGNI,model_review BLOCK 后 dropped)
- **不引入新 `RouteSpec.from_dict()` classmethod**(pivot 后无需序列化 RouteSpec)
- **不引入新 ROUTE_REGISTRY 内建路由**
- **不修改 fallback 触发条件**(`_executor_route_fallback_enabled` 不动)
- **不改 `RouteSpec.fallback_route_name` 字段语义或链结构**
- **不引入 SQLite transaction wrapping**(候选 H 范围)
- **不动 Phase 63 已落地的 truth/governance/identity/workspace/§9 守卫 batch**
- **不拆 Phase 64.5**(GPT-5 提议 split,Claude 不采纳:候选 G.5 = NO_SKIP 红灯消除是承诺,拆掉等于 scope failure)
- **不引入 metrics / audit log / cost_estimation 集中**(后续方向)

## 设计边界

- 严格遵循 INVARIANTS §0 第 1 / 第 3 条、§4 LLM 调用契约
- Provider Router 概念边界(本 phase 后):registry + selection + invocation gateway 三合一(`router.py` 模块承担)。**新增 `lookup_route_by_name`(read-only 数据查询)是显式分离 selection 与 lookup 的标记**
- Dependency rule(GPT-5 CONCERN Q11 消化):
  - Orchestrator/Operator → 可调 selection(`select_route` / `route_by_name` / `fallback_route_for`)
  - Executor → 可调 `lookup_route_by_name`(数据查询);**禁止**调 selection
  - Internal LLM clients(`agent_llm.call_agent_llm` / `retrieval.rerank_retrieval_items`)→ 必经 `router.invoke_completion`
- §9 守卫启用后严格执行,不允许 `pytest.skip` 退路
- 测试 mock 模式保持(`patch("swallow.X.call_agent_llm", ...)`),不要求测试代码迁移

## 完成条件

- 全量 pytest 通过(包含启用后的 §9 17 条守卫,2 条 G.5 守卫从 `pytest.skip` 转 active 全 pass)
- `tests/test_invariant_guards.py:test_path_b_does_not_call_provider_router` 函数体不再含 `pytest.skip`,改为非 vacuous AST scan(扫 executor.py 内 selection-语义函数调用)
- `tests/test_invariant_guards.py:test_specialist_internal_llm_calls_go_through_router` 同上(扫 chat-completion endpoint pattern)
- `grep -n 'fallback_route_for\|select_route\|route_by_name' src/swallow/executor.py` 命中 0
- `grep -rn 'httpx\.post' src/swallow/` 命中:`router.py:invoke_completion`(seam)+ `executor.py:run_http_executor` (Path A 合法)+ `retrieval_adapters.py`(embeddings,非 chat-completion);**不命中** `agent_llm.py`
- `swallow.router.invoke_completion(...)` / `swallow.router.lookup_route_by_name(...)` 存在并被相应调用方使用
- `swallow._http_helpers` 模块存在,且 `agent_llm.py` 顶部 import 不再来自 `executor.py`
- `state.fallback_route_chain: tuple[str, ...]` 字段存在于 `TaskState`,并被 orchestrator 在 `select_route` 路径上预填
- `git diff docs/design/INVARIANTS.md docs/design/DATA_MODEL.md` 无任何改动
- `docs/plans/phase64/closeout.md` 完成 + `docs/concerns_backlog.md`:Phase 63 closeout 中 NO_SKIP 占位部分 Resolved 标志改为 Resolved
- `git diff --check` 通过

## Slice 拆解(详细见 `design_decision.md`,revised-after-model-review)

| Slice | 主题 | Milestone | 风险评级 |
|-------|------|-----------|---------|
| S1 | Path B fallback chain plan + `lookup_route_by_name` + `test_path_b_does_not_call_provider_router` | M1 | 中(5)|
| S2 | Helper 中性模块 + Provider Router invoke_completion seam + `test_specialist_internal_llm_calls_go_through_router` | M2 | 中(6)|

Milestone 分组:
- **M1**(单独 review):S1 — orchestrator 预解析 chain plan + executor 改读 state + lookup_route_by_name 引入 + 守卫 unskip + 全测试。**先于 S2**:S1 完成后 executor 已无 selection 调用,S2 在干净基线上引入新 seam
- **M2**(单独 review):S2 — `_http_helpers.py` 抽取 + `router.invoke_completion` + `call_agent_llm` 退化 + 守卫 unskip + 全测试

**slice 数量 2 个**,符合"≤5 slice"指引。

## Eval 验收

不适用。Phase 64 全部为治理 / 守卫 / 控制面收口,无降噪 / 提案有效性 / 端到端体验质量梯度;pytest(含 §9 全 17 条守卫 active)即足以验收。

## 风险概述(详细见 `risk_assessment.md`,revised-after-model-review)

- **S1 chain plan tuple 同步丢漏**(R1):TaskState 新字段在某条触发路径未被 orchestrator 预填(如 MPS participant 路径);缓解 = orchestrator pre-resolve 时机锁定 + MPS `_resolve_participant_route` 同步预填
- **S1 reentrant 多跳被 chain 覆盖**(R2):pivot 后是 chain plan 而非单跳,multi-hop 重入安全;但 chain plan tuple 一旦生成不再随 fallback 失败动态扩展;缓解 = chain 长度由 ROUTE_REGISTRY 静态决定,与现有 `fallback_route_for` 单跳重入语义实际一致
- **S2 _http_helpers.py 抽取破环**(R3):helper 搬迁后 executor.py 自身 import 也要改;搬太多/太少都引入隐性 regression;缓解 = design_decision §S2 列出 authoritative symbol 清单
- **S2 invoke_completion 字符级等价**(R4):seam 内部实装与 call_agent_llm 必须字符级等价;缓解 = design_decision §S2 给出 step-by-step rebuild
- **S2 守卫 chat-completion AST pattern**(R5):AST 扫描需精确识别 URL 字符串包含 `/chat/completions` 而非裸 `httpx.post`;缓解 = design_decision §S2 给出 AST pattern + dry-run audit
- **S1+S2 测试 mock blind spot**(R6):context_brief 已确认 mock 是 `patch("swallow.X.call_agent_llm", ...)`,但 GPT-5 警告未 grep `patch("httpx.*", ...)` / 直接 import `AgentLLMResponse` 等;缓解 = S2 PR body 必须包含 grep 命中清单 + 一条 integration-level smoke test
- **R7-R10**(详见 risk_assessment.md):MPS fallback 路径 scope / Provider Router god-module 化 / dependency rule 文档化 / chain plan 与 ROUTE_REGISTRY 静态校验

## Model Review Gate

**已完成**(2026-04-29,reviewer = external GPT-5 via `mcp__gpt5__chat-with-gpt5_5`):**verdict = BLOCK**。4 BLOCK + 7 CONCERN 全部消化在本 revised-after-model-review:
- BLOCK Q1(守卫语义未锁定)→ G1 Pivot 2 重新框定 + 守卫 docstring 注明 §4/§0 依据
- BLOCK Q2(单跳预解析隐藏 max-depth invariant)→ G1 Pivot 1 改为完整 chain plan
- BLOCK Q4(helper 破环 Codex decides)→ G3 强制中性模块 `_http_helpers.py` + authoritative symbol 清单
- BLOCK Q9(`httpx.post` 守卫过宽)→ G4 守卫细化为 chat-completion endpoint pattern
- CONCERN Q3(`route_hint` 契约)→ 直接 drop
- CONCERN Q5(retrieval scope-in 守卫名)→ G4 守卫 docstring 注明范围
- CONCERN Q6(`RouteSpec.from_dict` 工程化困境)→ Pivot 后无需序列化,问题消失
- CONCERN Q7(拆 Phase 64.5)→ 不拆,scope 守得住
- CONCERN Q8(测试 mock blind spot)→ S2 PR body 强制 grep 命中清单 + integration smoke test
- CONCERN Q10(router god-module)→ Provider Router 概念边界声明 = registry+selection+gateway 三合一,显式
- CONCERN Q11(dependency rule)→ §设计边界 节加 dependency rule

**修订后是否再触发一次 model_review**:**不触发**。GPT-5 一轮已覆盖核心结构性风险,本轮 revised 是按其 pivot 方向 + 直接接受其 BLOCK 修复,scope 收敛而非扩张;design-auditor 二次校验即可。

## Branch Advice

- 当前分支:`main`(Phase 63 已 merge)
- 建议 branch 名:`feat/phase64-llm-router-boundary`
- 建议操作:Human Design Gate 通过后,Human 切出该 branch,Codex 在该分支上实装 S1 → S2

## 完成后的下一步

- Phase 64 closeout 后,触发 `roadmap-updater` subagent 同步 §三差距表(NO_SKIP 红灯修复行标 [已消化]):候选 G.5 完整闭环
- 进入候选 H(Truth Plane SQLite 一致性)启动准备:候选 H 的新 phase 编号在 Direction Gate 时分配

## 不做的事(详见 non-goals)

- 不修改 INVARIANTS / DATA_MODEL 任何文字
- 不引入 RouteSpec.from_dict / 不扩展 RouteSpec / AgentLLMResponse / call_agent_llm 公开签名
- 不引入 invoke_completion 的 route_hint 参数
- 不动 fallback 触发条件 / Path A/B 分支逻辑
- 不动 Phase 63 已落地内容
- 不引入 SQLite 事务 / metrics / audit log / cost 集中
- 不拆 Phase 64.5

## 验收条件(全 phase)

详见上方 §完成条件。本 kickoff 与 design_decision 一致,无补充。
