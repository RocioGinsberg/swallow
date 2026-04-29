---
author: claude
phase: phase64
slice: risk-assessment
status: revised-after-model-review
depends_on: ["docs/plans/phase64/kickoff.md", "docs/plans/phase64/design_decision.md", "docs/plans/phase64/context_brief.md", "docs/plans/phase64/design_audit.md", "docs/plans/phase64/model_review.md", "docs/plans/phase63/m0_audit_report.md"]
---

TL;DR(revised-after-model-review): **10 条风险条目**(model_review 后 R1/R2 重写,新增 R8/R9/R10)。**0 高 / 5 中 / 5 低**。S1 关键风险:chain plan 同步丢漏(R1)+ MPS Path A regression(R7)+ chain plan 与 ROUTE_REGISTRY 静态校验(R10)。S2 关键风险:helper 中性模块抽迁失误(R3)+ invoke_completion 字符级等价(R4)+ chat-completion AST pattern 误报漏报(R5)+ 测试 mock blind spot(R6)+ Provider Router god-module 化(R9)。守卫 AST allow-list 设计(R5)是本 phase 唯一需要 dry-run audit 的项。

## 风险矩阵(revised-after-model-review)

| ID | 风险 | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 等级 | 状态 |
|----|------|---------|--------|-----------|------|------|------|
| R1 | TaskState `fallback_route_chain` 字段在某条触发路径未被预填(orchestrator + MPS) | 2 | 1 | 2 | 5 | 中 | 重写(原 R1 单跳问题) |
| R2 | chain plan tuple 一旦生成不再随运行时动态扩展;若某 fallback 触发再 fallback 时 chain 已耗尽 | 2 | 1 | 2 | 5 | 中 | 重写(原 R2 多跳问题) |
| R3 | `_http_helpers.py` 搬迁失误 — 搬太多/太少/symbol 名变更引发 import 图回归 | 2 | 1 | 2 | 5 | 中 | 沿用 |
| R4 | `invoke_completion` 与原 `call_agent_llm` 字符级等价,实装偏差导致行为漂移 | 2 | 2 | 2 | 6 | 中 | 沿用,提级 |
| R5 | `test_specialist_internal_llm_calls_go_through_router` chat-completion URL AST pattern 误报或漏报 | 2 | 2 | 1 | 5 | 中 | 沿用,具体化 |
| R6 | 测试 mock blind spot — `patch("httpx.*", ...)` / 直接 import `AgentLLMResponse` 等模式未 grep 验证 | 1 | 1 | 2 | 4 | 低 | 提级 |
| R7 | MPS Path A `_resolve_participant_route` 不预填 `fallback_route_chain` 引发 participant fallback regression | 2 | 1 | 2 | 5 | 中 | **新增**(消化 design_audit CONCERN) |
| R8 | `lookup_route_by_name` 是否被未来误用作 selection 路径的隐性升级通道 | 1 | 1 | 1 | 3 | 低 | **新增**(消化 model_review CONCERN Q11) |
| R9 | `router.py` 模块成 god-module(registry + selection + invocation gateway)后续扩展时需要拆 | 1 | 2 | 2 | 5 | 中 | **新增**(消化 model_review CONCERN Q10) |
| R10 | chain plan 静态对齐 ROUTE_REGISTRY,若 ROUTE_REGISTRY 动态扩展(目前是静态)不被发现 | 1 | 1 | 1 | 3 | 低 | **新增** |

(Phase 64 scope 较 Phase 63 显著小,10 条已覆盖现有事实风险面。无高风险条目;最高分 R4=6,因 invoke_completion 与既有 call_agent_llm 字符级等价是 thin seam 的核心契约,需谨慎对齐)

---

## 详细分析

### R1 — TaskState `fallback_route_chain` 字段同步丢漏(中,重写)

**描述**:S1 后 orchestrator 在 `select_route` 路径上预解析 chain plan 并填充 `state.fallback_route_chain: tuple[str, ...]`。如果 orchestrator 中存在其他 route 决策路径未同步预填该字段,executor 读到 `()` 空 tuple 时会触发"无 fallback 可用"的处理,行为与原 router 调用不一致(原代码会去查 `fallback_route_for(current_route_name)`,若 fallback_route_name 为空才返回 None)

**触发场景**:
- Phase 62 MPS Path A 的 participant / arbiter 路径(R7 单独跟踪)
- Operator CLI 用 `--executor-override` / `--route-override` 强制路由,绕过 select_route 主流程
- Multi-card 子任务、orchestrator subtask delegation 等次级路径
- 初始 TaskState 创建路径(`create_task` 等)未路过 `select_route`

**缓解**:
- design_decision §S1 推荐把"select_route 后预填 chain"抽成 orchestrator 内部 helper `_apply_route_selection_with_fallback_chain(state, ...)`,主 orchestrator 与 synthesis(MPS)共用
- Codex 实装时 grep 所有 `select_route(` 调用方 + 所有产生/mutate `TaskState.route_*` 字段的位置,逐个确认是否预填 fallback_route_chain
- TaskState 默认值 `()` 空 tuple 是合规的——表示当前路由无 fallback 链;executor 读到空 tuple 时按"无 fallback 可用"处理(与 `fallback_route_for` 返回 None 等价)
- S1 PR body 必须包含"fallback_route_chain 填充点完整清单"作为审查项

**回滚成本**:低。state 字段引入隔离,revert orchestrator + executor 改动可还原

---

### R2 — chain plan 一次生成,运行时动态变化场景下耗尽(中,重写)

**描述**:GPT-5 BLOCK Q2 提议 chain plan 一次跳完,这等价于"orchestrator 锁定 fallback chain,executor 按 visited_routes 取下一跳"。原代码每次 `_load_fallback_route(current_route_name)` 都查最新 ROUTE_REGISTRY;新代码使用预解析的 chain。两者等价仅当 chain plan 在 task 生命周期内对应的 ROUTE_REGISTRY 不变(实际现状成立 — ROUTE_REGISTRY 是 module-level 静态)

**触发场景**:
- ROUTE_REGISTRY 在 task 执行中被动态修改(实际不会,model load 后 immutable)
- chain plan 解析时漏掉了某个 fallback path(如环检测过严过早 break)
- 多次 fallback 后 visited_routes 累积,chain 已耗尽但 executor 仍要再 fallback(此时 chain plan 长度已 exhaust,行为 = "无更多 fallback,走 apply_fallback_if_enabled" — 与原代码 `fallback_route_for` 返回 None 等价)

**ROUTE_REGISTRY 当前 fallback chain 形态(grep router.py L282-L474 验证)**:
- `local-aider` → `local-summary`(2 跳,terminal)
- `local-codex` → `local-summary`(2 跳,terminal)
- `local-http` → `local-claude-code` → `local-summary`(3 跳,terminal)
- `http-claude` → `http-qwen` → `http-glm` → `local-claude-code` → `local-summary`(5 跳,terminal,最长链)
- `http-qwen` → `http-glm` → `local-claude-code` → `local-summary`(同入主干)
- `http-glm` → `local-claude-code` → `local-summary`
- `http-gemini` → `http-qwen` → ...(汇入主干)
- `http-deepseek` → `http-qwen` → ...(汇入主干)
- `local-claude-code` → `local-summary`(2 跳,terminal)

**结论**:**线性多入口汇合,无环,最长链 5 跳**。chain plan 算法只需处理:(a) 线性追踪;(b) 终点检测(fallback_route_name 为空);(c) 防御性环检测(虽然当前无环,但若未来 ROUTE_REGISTRY 引入环,环检测仍要正确 break)

**缓解**:
- chain plan 静态等价 — design_decision §S1 已说明 chain plan 内置环检测,与 executor `visited_routes` 累积语义一致
- ROUTE_REGISTRY 当前 fallback 静态:**线性 + 多入口汇合 + 无环**,chain plan 算法对最长 5 跳链都应正确产出 5 元 tuple,executor `visited_routes` 累积时按 chain 索引取下一跳与原 `fallback_route_for(current)` 单跳查询语义等价
- **回归测试必须覆盖**:(a) 线性主干 `http-claude → http-qwen → http-glm → local-claude-code → local-summary` 完整 chain;(b) 终止条件(`local-summary` 自身无 fallback,chain 不再延伸);(c) 防御性环检测的合成 fixture(在 test 中临时构造一个含环 ROUTE_REGISTRY,验证算法 break 而非死循环)
- Codex 实装时 grep ROUTE_REGISTRY 所有 fallback chain,确认 chain plan 算法正确处理:线性 / 无环(当前现实)+ 防御性环(未来防御)

**回滚成本**:低

---

### R3 — `_http_helpers.py` 搬迁失误(中,沿用)

**描述**:S2 引入 `_http_helpers.py` 中性模块,需要从 `executor.py` 与 `agent_llm.py` 搬迁多个 symbol。design_decision §S2 已给出 authoritative 清单,但搬迁过程仍有失误风险:
- 搬太多(如把 Specialist 不需要的 helper 也搬,引入不必要的 import 图变动)
- 搬太少(invoke_completion 内部需要某 helper 但未搬,导致 lazy import 仍需要)
- symbol 名变更(如 `_http_request_headers` 改名 `http_request_headers` 且未在原位置 deprecation alias)

**触发场景**:
- 现有测试代码 `tests/test_specialist_agents.py:13` 等直接 `from swallow.agent_llm import AgentLLMResponse, AgentLLMUnavailable`,搬迁后 `agent_llm.py` 必须 re-export 这些 symbol 才能保持兼容
- `executor.py` 自身使用 `_http_request_headers` 等,搬走后改 import 路径

**缓解**:
- design_decision §S2 已列 authoritative 搬迁清单,Codex 严格对齐
- 推荐策略:**搬迁后立即跑** `python -c "from swallow.agent_llm import AgentLLMResponse, AgentLLMUnavailable; from swallow._http_helpers import *"` 等 import smoke 检查
- `_http_request_headers` → `http_request_headers` 改名:`agent_llm.py` 内可 `from ._http_helpers import http_request_headers as _http_request_headers` 维持兼容 alias(若有调用方依赖私有名);否则直接公开
- 测试 import path:Codex 实装后 grep `tests/` 目录所有 `from swallow.agent_llm import` / `from swallow.executor import`,确认搬迁后还能正常 import

**回滚成本**:中。涉及多文件 import 改动;但 Phase 64 在新 branch 上,git revert 整个 commit 是清晰边界

---

### R4 — `invoke_completion` 字符级等价偏差(中,沿用 + 提级)

**描述**:`invoke_completion` 是 thin seam,内部实装必须与原 `call_agent_llm` 字符级等价(URL/model/headers/timeout/payload 解析路径完全一致)。设计偏差会导致 LLM 调用语义改变(如 timeout 解析不一致、payload 字段处理顺序变化、错误消息文字变化)

**触发场景**:
- timeout 解析:`timeout_seconds or parse_timeout_seconds(os.environ.get(...))` 顺序错置
- model 解析:`resolved_model = model or resolve_swl_chat_model()` vs `resolve_agent_llm_model(model)` 实装差异(原 `call_agent_llm` 用 `resolve_agent_llm_model(model)`,该函数内部走 `resolve_swl_chat_model`;`invoke_completion` 应保持同样调用链)
- 异常类型:原代码捕获 `httpx.HTTPError` / `(KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError)` 两类异常,seam 必须完全对齐
- 错误消息文字:原代码消息文本是 testing fixture 可能依赖的字符串

**缓解**:
- design_decision §S2 已给出 step-by-step rebuild 模板(包括捕获异常类型)
- Codex 实装后,**diff 对比** `agent_llm.call_agent_llm` 旧实装 vs `router.invoke_completion` 新实装,确保函数体完全等价(只差 `model` 解析的 helper 名字 — 如果 `invoke_completion` 内调用 `resolve_swl_chat_model` 而非 `resolve_agent_llm_model`,需在 PR body 说明 rationale)
- integration smoke test(R6 缓解的一部分)mock `httpx.post` 后断言 URL/headers/json payload 与历史基线一致

**回滚成本**:低。函数体等价问题,单点 fix 即可

---

### R5 — chat-completion URL AST pattern 误报 / 漏报(中,具体化)

**描述**:`test_specialist_internal_llm_calls_go_through_router` 守卫扫 `httpx.post(url, ...)` 调用且 URL 字面量含 `/chat/completions`,而非裸 `httpx.post`。AST pattern 设计错配会导致:
- **误报**:embeddings 调用(`retrieval_adapters.py:206` 用 `f"{base_url}/v1/embeddings"`)被误识别(若 pattern 仅扫 url 是 Constant 含 `/chat`,embeddings 不命中,合规;但若 pattern 扫所有动态 url,embeddings 误报)
- **漏报**:chat-completion 用动态变量(如 `endpoint = config.get('chat_url'); httpx.post(endpoint, ...)`)绕过守卫
- **AST pattern 兼容**:`httpx.post(...)` Direct 调用 + `httpx.AsyncClient(...).post(...)` 都需要识别

**触发场景**:
- design 给的 AST pattern 写错(如只扫 Direct `httpx.post`,漏 AsyncClient.post)
- 未来若 Specialist 引入 dynamic url 调 chat completions,守卫漏报
- Phase 64 后某 phase 引入 streaming endpoint(如 `/v1/chat/completions/stream`),守卫 substring match 仍命中(合规)

**缓解**:
- design_decision §S2 已给出三段 AST 扫描规则:URL 字面量含 `/chat/completions` → 命中;URL 是 `Call(Name("resolve_new_api_chat_completions_url"))` → 命中;动态变量 / f-string → **不命中**(避免 embeddings 误报)
- Codex 实装守卫前**先 dry-run 扫描**列出当前命中,确认 allow-list 完备;若发现 design 未列出的合法命中,提交 PR 前与 Claude 确认 allow-list 扩展
- 守卫 docstring 明确扫描范围 + allow-list 来源指向 design_decision §S2

**回滚成本**:低。守卫规则可独立修订

---

### R6 — 测试 mock blind spot(低,提级)

**描述**:context_brief 已确认现有测试 mock 是 `patch("swallow.X.call_agent_llm", ...)`,但 GPT-5 CONCERN Q8 警告未 grep 验证以下 blind spot:
- `patch("httpx.post")` / `patch("swallow.agent_llm.httpx.post")` 直接 mock 提供方层
- `patch("swallow.agent_llm.resolve_*")` 等 helper 函数 mock
- `from swallow.agent_llm import AgentLLMResponse / AgentLLMUnavailable` 直接 import(R3 已覆盖,re-export)
- 直接断言异常类型 / 响应结构

**触发场景**:
- 现有 test 在某处 mock `httpx.post`(而非 `call_agent_llm`)— S2 后 `httpx.post` 调用位置从 `agent_llm.py` 移到 `router.py`,mock target 失效
- 现有 test mock `agent_llm` 内的 helper 函数 — S2 helper 搬到 `_http_helpers`,mock target 失效

**缓解**:
- **design_decision §S2 已强制要求 Codex 在 PR body 提供 grep 命中清单**:`grep -rn 'patch.*httpx\|patch.*agent_llm\|from swallow.agent_llm import\|from swallow._http_helpers import' tests/`
- 全量 pytest 通过即视为 mock 透明性整体验证
- 加一条 integration-level smoke test mock `httpx.post` 而非 `call_agent_llm`,确保 invoke_completion 实际被执行

**回滚成本**:低。测试单点 fix

---

### R7 — MPS Path A `_resolve_participant_route` 不预填 chain regression(中,新增)

**描述**:design_audit CONCERN 已点出 — `synthesis._participant_state_for_call` 通过 `dataclasses.replace(base_state, ...)` 复制 state 时,`fallback_route_chain` 字段会复制 base_state 的值;但 base_state 的 chain 是按 primary route 解析的,与 participant 的 HTTP route 不同。如果 MPS HTTP participant 失败触发 executor-level fallback,executor 读到错误的 chain(指向 primary 而非 participant)

**触发场景**:
- MPS participant 路由是 `http-*` 系列,触发 `_executor_route_fallback_enabled`(executor.py:505 返回 True)
- participant 第一次执行失败,触发 fallback;executor 读 `state.fallback_route_chain`(继承自 base_state,指向 primary 链)
- fallback 查到的 RouteSpec 是 primary 的 fallback,而非 participant 的 fallback(两者可能完全不同)

**缓解**:
- design_decision §S1 已说明:`synthesis.py:_resolve_participant_route` 在 `select_route(base_state)` 后,**用 orchestrator 共享 helper `_apply_route_selection_with_fallback_chain(participant_state, ...)`** 重新预填 chain(基于 participant 的 RouteSpec.fallback_route_name)
- 该 helper 实装位置:orchestrator.py 内部,签名 = `_apply_route_selection_with_fallback_chain(state, primary_route_name) -> None`(就地 mutate state)
- 单测覆盖:Phase 62 MPS 测试套件中找到一个 HTTP participant 用例,加 fallback 触发场景的回归测试

**回滚成本**:低。synthesis.py 单点修改

---

### R8 — `lookup_route_by_name` 隐性升级通道(低,新增)

**描述**:GPT-5 CONCERN Q11 — 本 phase 引入 `lookup_route_by_name(name) -> RouteSpec | None` 作为"data lookup, not selection"显式标记。未来 phase 若误把 selection 决策塞进 lookup_route_by_name(如"按 name 查 + 加 fallback 决策"),守卫扫不到(因为它在 allow-list 内),会重新创造 selection bypass 通道

**触发场景**:
- 后续 phase 想在 executor 内做轻量 fallback 决策,扩展 lookup_route_by_name 实装(违反本 phase 约定)
- code review 时未发现新加逻辑超出 read-only data lookup 范围

**缓解**:
- design_decision §S1 已说明:`lookup_route_by_name` internal 实装 = 单行 `return route_by_name(name)`,docstring 显式声明"data lookup, not selection"
- 后续 phase 若需要扩展该函数,触发 design 层评估 — 而非 silent 扩
- 加一条额外架构守卫(可选,本 phase 内不做):`test_lookup_route_by_name_is_thin_forwarder` 扫描该函数体只允许 `route_by_name(name)` 单行调用;**本 phase scope 内不引入此守卫**(YAGNI),登记 backlog

**回滚成本**:零(架构约定层面)

---

### R9 — `router.py` god-module 化(中,新增)

**描述**:GPT-5 CONCERN Q10 — Phase 64 后 router.py 同时承担:registry / selection (`select_route`/`route_by_name`/`fallback_route_for`/`route_for_mode`) / data lookup (`lookup_route_by_name`) / invocation gateway (`invoke_completion`)。模块职责扩张,后续若加 audit log / metrics / cost_estimation 等会进一步膨胀

**触发场景**:
- Phase 65+ 引入 Provider Router metrics 集中,放 router.py
- 引入 cost_estimation 时,放 router.py(因为它已是 invocation gateway)
- 模块行数膨胀至难以单 review 单元

**缓解**:
- design_decision 中已明确 Provider Router 概念边界 = 三合一(本 phase 边界声明)
- 本 phase 内**不拆**(YAGNI,scope 守得住);登记 backlog Open:"router.py 在 Phase 64 后行数有增长趋势,后续若引入 metrics / audit log / cost_estimation,评估拆出 `provider_gateway.py` 独立模块"
- closeout 时 grep `wc -l src/swallow/router.py`,与 Phase 63 后的行数对比(前后 delta < 200 = OK,> 200 = 触发 review)

**回滚成本**:零(架构约定层面)

---

### R10 — chain plan 与 ROUTE_REGISTRY 静态对齐(低,新增)

**描述**:chain plan 在 orchestrator `select_route` 路径上预解析,基于当前 ROUTE_REGISTRY 状态。若未来 ROUTE_REGISTRY 引入动态扩展机制(目前是静态 module-level singleton),chain plan 锁定的快照会与运行时 registry 不一致

**触发场景**:
- 未来 phase 引入"运行时加载新 RouteSpec"(如 hot reload)
- ROUTE_REGISTRY 从 module-level 改为 mutable container

**缓解**:
- 当前 ROUTE_REGISTRY 是模块级静态(`router.py:588 ROUTE_REGISTRY: RouteRegistry`),module load 后不变
- 本 phase 内不引入相关变化;若未来 phase 真要做 hot reload,触发 design 层 race condition / chain plan refresh 评估
- 登记 backlog:"chain plan 锁定快照与 ROUTE_REGISTRY 静态前提强相关;若引入 dynamic registry,evaluate chain plan 刷新策略"

**回滚成本**:零(架构约定层面)

---

## 总体策略(revised-after-model-review)

1. **S1 → S2 顺序实装**(无并行):S1 完成后 executor 已无 selection 调用,S2 在干净基线上引入 _http_helpers + invoke_completion seam
2. **每个 milestone 独立 review**:M1 单 commit,M2 单 commit;每个 milestone 完成后 Codex 跑全量 pytest 并提交 commit gate state(沿用 Phase 63 commit_gate 范式)
3. **S1 PR body 强制项**:fallback_route_chain 填充点完整清单(R1 缓解);chain plan 算法对 ROUTE_REGISTRY 现有 fallback chain(线性 / 环 / 自环)的覆盖证明(R2 缓解);MPS `_resolve_participant_route` 同步预填测试用例(R7 缓解)
4. **S2 PR body 强制项**:`_http_helpers.py` 搬迁清单 + import smoke check(R3 缓解);`invoke_completion` vs `call_agent_llm` diff 对照(R4 缓解);测试套件 mock pattern grep 命中清单(R6 缓解);chat-completion AST pattern dry-run 扫描结果 + allow-list audit(R5 缓解);integration smoke test mock httpx.post 验证 invoke_completion 被实际执行
5. **守卫 dry-run audit**:Codex 在每条守卫 unskip 前先 dry-run 列出当前命中,确认 allow-list 完备
6. **Model Review Gate 已完成**(GPT-5 verdict=BLOCK,4 BLOCK + 7 CONCERN 全部消化);**revised 后不再触发**(scope 收敛,design-auditor 二次校验即可)
7. **Phase 64 完成后**:进入候选 H(Truth Plane SQLite)启动准备,phase 编号在 Direction Gate 时分配

## 与既有 risk 模式的对照

- **类似 Phase 63 R3(Repository 抽象层)**:本 phase R4(invoke_completion 字符级等价)同样是 governance/control 层引入新公开接口;但 scope 小很多(单函数 vs 4 类),风险等级 6 vs 7
- **类似 Phase 62 R12(Path A 绕过 Provider Router)**:本 phase 是其镜像问题(Path C 绕过 Provider Router),解法同源(走 Provider Router seam),风险面已被 Phase 62 处理过类似场景
- **类似 Phase 62 R13(`_validate_target` 漏改)**:本 phase R7(MPS path 漏预填)同源(Phase 62 BLOCKER 类似);Phase 62 落地经验 = 在 design 层共用 helper 而非两条路径分别实装
- **新模式**:Phase 64 是首次"helper 抽取破循环"动作(R3),属于纯架构整理;无 user-facing 变化,纯 import 图重构

## 与 INVARIANTS 的对照(本 phase 强约束)

| INVARIANTS 条目 | Phase 64 落地方式 |
|----------------|----------------|
| §0 第 1 条(Control 在 Orchestrator/Operator) | S1 把 fallback selection 决策从 executor 移到 orchestrator(预解析 chain plan);allow executor 调 lookup_route_by_name(read-only data consumption);**守卫语义重新框定**有 §4 表 + §0 第 1 条共同背书 |
| §0 第 3 条 + §4(LLM 三条路径,Path C = N × Path A) | S2 让所有 internal LLM 调用穿透 router.invoke_completion seam;chat-completion 唯一 gateway = router.py |
| §4 表(Path A/B/C × Provider Router) | 守卫名 `test_path_b_does_not_call_provider_router` / `test_specialist_internal_llm_calls_go_through_router` 与 §4 表语义严格对齐;**INVARIANTS 文字不动** |
| §9 不变量守卫 | 启用最后 2 条 NO_SKIP 占位,使 §9 17 条全 active(0 skip)|
| §0 第 4 条(Truth 写入唯一入口)| 不动(Phase 63 已落地)|
| §5 Truth 写入矩阵 | 不动 |
| §7 集中化函数 | 不动(Phase 63 已落地 identity / workspace)|

## Provider Router 概念边界声明(本 phase 后)

| 角色 | 允许调用方 | 禁止调用方 |
|------|----------|----------|
| Selection (`select_route` / `route_by_name` / `fallback_route_for` / `route_for_mode`)| Orchestrator / Operator(CLI)/ synthesis.py(MPS Path A,合规)| Executor / Specialist / retrieval / agent_llm |
| Data Lookup (`lookup_route_by_name`)| Executor + 上述 selection 调用方都允许 | (无禁止)|
| Invocation Gateway (`invoke_completion`)| `agent_llm.call_agent_llm`(thin caller)→ 间接被 Specialist + retrieval 调 | 任何模块直接调 chat-completion endpoint(`httpx.post(url=/chat/completions, ...)`)— 仅 router.invoke_completion 内部一处合法 |
| Registry (`ROUTE_REGISTRY`,`RouteRegistry` 类) | router.py 内部,其他模块通过上述函数访问 | 任何模块直接访问 ROUTE_REGISTRY |
