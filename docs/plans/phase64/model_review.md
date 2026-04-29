---
author: claude
phase: phase64
slice: design-gate
status: review
depends_on:
  - docs/plans/phase64/kickoff.md
  - docs/plans/phase64/design_decision.md
  - docs/plans/phase64/risk_assessment.md
  - docs/plans/phase64/design_audit.md
reviewer: external-model
verdict: BLOCK
---

TL;DR: External GPT-5 review (via `mcp__gpt5__chat-with-gpt5_5`) verdict = **BLOCK**。Phase 64 不能按当前 draft 进入 Human Design Gate。核心争议:S1 把"executor 调 `fallback_route_for` 纯查表"当作 §0 第 1 条违规、再以 RouteSpec 序列化下传作解,既需要不存在的 `RouteSpec.from_dict()` 又破坏 executor 重入 fallback chain 语义,治错了病。建议 pivot = "分离 route selection 与 route metadata consumption":orchestrator 预解析**完整** fallback chain plan(不止一跳),executor 消费 immutable plan 不再 import router。S2 方向正确但 helper 破环 / route_hint 契约 / 守卫范围 / 测试覆盖均需 design 层锁定。共 4 BLOCK + 7 CONCERN。

# Model Review

## Scope

- **Reviewer**: external GPT-5 via `mcp__gpt5__chat-with-gpt5_5`(项目 `.claude/skills/model-review/SKILL.md` workflow,Phase 63 model_review 同款 channel)
- **Review packet**: 完整 Phase 64 design proposal(S1/S2 + non-goals)+ INVARIANTS §0 第 1/3/4 条 / §4 / §9 守卫表 anchors + design_audit findings + 11 个团队预设的核验角度
- **Mode**: Adversarial / independent challenge(显式要求 reviewer 不要 validation,要 pivot 建议)
- **Output**: 11 个 findings(verdict per finding)+ overall BLOCK + 1 个具体 design pivot

## Verdict

**BLOCK** — Phase 64 design draft 不通过 model review,需进入 `revised-after-model-review` 阶段处理 4 个 BLOCK + 7 个 CONCERN。

## Findings

### Critical findings — must fix before Human Design Gate

- **[BLOCK Q1]** `test_path_b_does_not_call_provider_router` 守卫语义未在 design 中锁定。`fallback_route_for` 是纯查表(读 module-level 静态 `ROUTE_REGISTRY`),GPT-5 指出至少有 3 种合理读法:(a) 严格 — executor 不许 import router 任何符号;(b) 控制面 — executor 不许调 `select_route`,但允许读静态 route metadata;(c) Provider Router — executor 不许调 provider 选择 / provider HTTP,但纯查表合规。design 默认走 (a) 没给出宪法层依据。**这是 S1 BLOCKER S1-1/S1-2 的根因**:design 选最严守卫语义,所以陷入 RouteSpec 序列化困境。

- **[BLOCK Q2]** Reentrant fallback chain 单跳预解析隐藏 architectural invariant。executor `_apply_executor_route_fallback` 通过 `_run_executor_for_fallback_route` + `visited_routes` accumulator 已实装多跳能力。design 改为 orchestrator 单跳预解析,**等价仅在 ROUTE_REGISTRY 链长 ≤ 1 时成立**(当前事实,但未来若任何 phase 加 depth-2 route,代码会静默失效)。这不是简化是隐性 regression。design 必须显式选:(i) 锁定 max-depth=1 invariant + 加 enforcement 守卫;(ii) 预解析整条 chain 而非单跳;(iii) 重新评估守卫语义是否真的禁纯查表(回到 Q1)。

- **[BLOCK Q4]** S2 helper 破环 design 留 "Codex decides" 不可接受。GPT-5 警告:lazy import executor helper 会让 Provider Router 反向依赖 Executor — 这是 §0 第 3 条 "Provider Router 是 LLM gateway" 性质的反向 dependency,architectural failure。必须在 design 层强制 = 中性 helper 模块(选项 a),禁止 lazy import(选项 b)与 duplicate(选项 c)。

- **[BLOCK Q9]** S2 `httpx.post` 守卫过宽,与 invariant 语义不挂钩。守卫扫描所有 `httpx.post`,但 invariant 关心的是 LLM provider chat completions,不是任何 POST。`retrieval_adapters.py:206` 是 embeddings(合规)— 但守卫不能仅靠 allow-list 兜底,这会让 allow-list 随未来新 HTTP 调用持续膨胀,且把"网络策略"伪装成"LLM 路径策略"。守卫策略需细化到 chat-completion endpoint pattern(URL 含 `/chat/completions`)或已知 LLM helper 调用,而非裸 `httpx.post`。

### Concerns — accept with explicit mitigation

- **[CONCERN Q3]** `route_hint` 参数 design 留 "warn+ignore vs NotImplementedError 由 Codex 决"。GPT-5 强调:silent ignore 是 routing 语义最坏的默认值(调用方误以为 routing 生效)。锁定要求:**非 None 时 fail-closed 抛 specific unsupported 异常**,或 Phase 64 内**直接 drop 该参数**(YAGNI)。Claude 推荐 drop(本 phase 内 0 调用方使用,接口扩展属于未来 phase 的 design 范围)。

- **[CONCERN Q5]** `retrieval.py` scope-in 决策方向正确但守卫名误导。`test_specialist_internal_llm_calls_go_through_router` 字面只覆盖 Specialist,但 design 让 retrieval 也走新 seam。需在 design 中:(a) 锁定 invariant 重述为 "internal non-Path-A LLM calls" 或 "Path C + 基础设施 LLM calls" 全部经 Provider Router;(b) 守卫 docstring 注明 retrieval 包含理由,与未来基础设施层 LLM 调用一致。**不要只在守卫 allow-list 上偷偷扩范围**。

- **[CONCERN Q7]** Phase 64 同时做两个 architectural migration(S1 = executor/router boundary;S2 = LLM gateway centralization),都触动宪法层守卫。GPT-5 建议如果两个 design 不能同时锁定,**拆 Phase 64.5**:Phase 64 解决 S1 守卫语义 + fallback 架构;Phase 64.5 做 LLM seam。但**不允许"代码清理本 phase / 守卫启用下次"** — roadmap 候选 G.5 的核心承诺就是消除 NO_SKIP 红灯,把守卫启用推迟会构成 scope failure。

- **[CONCERN Q8]** 测试 mock 透明性靠 "现有测试 patch `call_agent_llm` 符号级" 假设,design 没有 grep 验证。GPT-5 列出 4 类未验证的 blind spot:`patch("httpx.post")` / `patch("swallow.agent_llm.httpx.post")` / patch helper 函数 / 直接 import `AgentLLMResponse`。required mitigation = design 在 S2 实装前显式跑 test grep,并新增至少一条 integration-level smoke test 让 `call_agent_llm → router.invoke_completion → httpx.post(mocked)` 整条链路被覆盖(否则 invoke_completion 内部布线 bug 现有测试套件抓不到)。

- **[CONCERN Q10]** `router.invoke_completion` 让 router 模块同时承担:registry/selection 权威 + Provider HTTP 执行 gateway。GPT-5 指出这可能是 §0 第 3 条 "Provider Router = gateway" 的合规读法,但 design 没给出明示。如果 Provider Router 是 selector + gateway 一体,design 必须显式声明;否则 router.py 会成 god module(registry / selection / fallback metadata / provider invocation / model+env resolution / auth/headers 全在一个文件)。**mitigation**:design 中明确 "Provider Router" 的概念边界 = registry+selection+gateway 三合一(本 phase 选项),或拆出独立 `provider_gateway` 模块。

- **[CONCERN Q11]** S1 与 S2 让 router 走相反方向:S1 说 executor 不许碰 router(收紧),S2 说 router 是 LLM HTTP gateway(扩张)。GPT-5 指出这种不对称需要 design 显式 dependency rule(谁可以依赖 router、谁不能)。**mitigation**:design 中加一条 dependency policy:Orchestrator/Operator → 可调 selection;Executor → 只消费 immutable route execution data,不调 selection;internal LLM clients → 必经 provider gateway。否则未来守卫会变得 arbitrary。

- **[CONCERN Q6]** S1 的两个 BLOCKER 可能本质上是 **"S1 治错病"** 的征兆 — design audit 已报 BLOCKER,但 root cause 不是 RouteSpec 序列化机制选错,而是 design 假设 executor 必须拥有 RouteSpec 对象。GPT-5 建议三个真正的 architectural option:(i) 允许 executor 静态查 fallback metadata(回退到 Q1 (b)/(c) 守卫语义);(ii) orchestrator 完全预 apply fallback 副作用,executor 消费 already-adjusted state(无 RouteSpec 概念);(iii) orchestrator 把完整 fallback chain plan 作为 immutable execution metadata 传入 executor。当前 design 的 "TaskState 单字段 dict payload" 是**最差中间路线**(既要序列化又要重建对象,既要单跳又要重入)。

## Claude Follow-Up

**design_decision.md / risk_assessment.md / kickoff.md 必须修订到 `revised-after-model-review`**,落实以下结构性变化:

1. **S1 pivot 决策**(必选):由 Human 在恢复时(2026-04-30)对比 GPT-5 提的 (i)/(ii)/(iii) 三个 option 选定 — Claude 推荐 **option (iii) immutable fallback chain plan** + (i) "守卫语义重新框定为 executor 不调 selection 函数" 双管齐下。option (i) 单独走能用最少改动消化 BLOCKER;option (iii) 单独走能保持 fallback chain 多跳能力但实装量更大。组合方案兼顾两者。
2. **S2 helper 破环锁定** = 中性模块 `swallow/_http_helpers.py`(non-negotiable)+ 完整搬迁 symbol 清单写入 design_decision §S2。
3. **S2 `route_hint` 决策**:推荐本 phase 直接 **drop 该参数**(YAGNI)。如保留,锁定 fail-closed = 非 None 抛 `RouteHintNotSupported(NotImplementedError 子类)`。
4. **S2 守卫策略细化**:不再扫所有 `httpx.post`,改为扫"调用 chat-completion endpoint" — 实装层面用 AST 寻找含 `/chat/completions` URL 字符串的 `httpx.post` 节点;allow-list 仅 router.py(seam)与 executor.py(Path A)。
5. **§0 第 3 条措辞重读**:design 中加一节 "invariant 语义注脚":守卫名 `test_specialist_internal_llm_calls_go_through_router` 实际范围 = "internal non-Path-A LLM calls"(含 retrieval 基础设施层),与 §0 第 3 条 "Path C = N × Path A" 整体语义一致。**不修改 INVARIANTS.md 文字**,只在 phase design 中给出守卫 docstring 注明。
6. **Provider Router 概念边界**:design 中显式声明 "Provider Router 在本 phase 后 = registry + selection + gateway 三合一";新加 dependency rule 节(Orchestrator/Operator/Executor/internal LLM clients 各自允许的 router 依赖路径)。
7. **新增 risk 条目**:R8(单跳预解析隐藏 max-depth invariant) + R9(Provider Router god-module 化)+ R10(test mock blind spots)。
8. **新增 design 验收**:S2 PR body 必须包含 grep 测试套件中所有 `patch("httpx.*", ...)` / `patch("swallow.agent_llm.*", ...)` 的命中清单 + 整条链路 integration-level smoke test 文件名;否则 Claude review 不通过。
9. **拆 Phase 64.5 决策**:GPT-5 建议拆,但 Claude 不推荐 — 守卫启用是 G.5 的 raison d'être,拆掉 S2 等于让候选 G.5 变成"代码改动 phase + 守卫启用 phase"两段,价值密度太低。建议保持 Phase 64 = S1 + S2 单 phase,但 design pivot 后再评估是否仍 ≤ 5 slice。

## Human Gate Note

Human 在 Design Gate 前必须确认:

1. **S1 pivot 选 (i) / (ii) / (iii) / 组合**:这是本次 model_review 暴露的最大决策点;选项之间影响 phase scope、risk 等级、INVARIANTS 守卫语义读法。Claude 推荐 = **(iii) immutable fallback chain plan + (i) 守卫语义重新框定**(同时消化 BLOCKER S1-1/S1-2 + 保持 chain 多跳能力 + 简化守卫实装)。
2. **`route_hint` drop vs fail-closed**:Claude 推荐 drop。
3. **是否拆 Phase 64.5**:Claude 推荐不拆。
4. **Provider Router gateway 化措辞** 是否需要触发 INVARIANTS 文字修订(Phase 63 non-goal 是 "不修改 INVARIANTS 文字" — Phase 64 应延续此 non-goal,只在 design 给守卫 docstring 注明)。
5. 是否再触发一次 model review(after-pivot)— Claude 不推荐,GPT-5 这一轮覆盖面已足,revised-after-model-review 修订幅度可控,format-validator + design-auditor 即可二次校验。

如果 Human 认可上述方向,Claude 在恢复后(2026-04-30)按选定 pivot 修订三件套到 `revised-after-model-review`,然后再走 design-auditor 二次校验,通过后进入 Human Design Gate。
