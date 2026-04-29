---
author: codex
phase: phase64
slice: route-metadata-externalization-follow-up
status: review
depends_on: ["docs/plans/phase64/kickoff.md", "docs/plans/phase64/design_decision.md", "docs/plans/phase64/design_audit.md", "docs/active_context.md"]
---

TL;DR: Phase 64 原方案只覆盖 S1/S2 两条治理边界守卫收口;本文件记录 Human 在实现过程中追加批准的 route externalization follow-up。新增内容应按 Human follow-up scope review,不是 design_decision 漏写导致的未授权漂移。外部化分三层: fallback override config、route registry metadata、route selection policy metadata。

## Review 前置说明

Phase 64 的原始 `kickoff.md` / `design_decision.md` 聚焦两个目标:

- S1:Path B fallback chain plan 前移到 Orchestrator,Executor 不再做 Provider Router selection
- S2:Specialist internal LLM 调用穿透 `router.invoke_completion`

在 S1/S2 实现过程中,Human 追加了明确 follow-up 要求:

- 不希望把早期 built-in fallback chain 固化为代码契约
- 不希望整张 route registry 继续硬编码在 Python 里
- 询问 route mode mapping / complexity bias 等剩余硬编码是否适合继续外部化

Codex 对第三点的判断是:适合外部化,但它们不属于 route registry 本体。Registry 只回答"有哪些 route";route mode mapping、complexity bias、parallel intent、summary fallback 这类内容回答"selection 如何解释输入并偏向 route",因此落为独立的 route selection policy metadata。

Reviewer 应把以下改动看作 Human-approved follow-up scope,而不是与原 S1/S2 方案冲突的 spontaneous refactor。

## 外部化分层

### 1. Fallback Override Config

目的:消除"真实 `http-claude -> http-qwen -> http-glm -> local-claude-code -> local-summary` 链必须永久固定"的测试/代码契约。

落点:

- 工作区配置:`.swl/route_fallbacks.json`
- 代码入口:`load_route_fallbacks(...)` / `apply_route_fallbacks(...)`
- 加载时机:route selection 前后与 route metadata overlay 同步应用,保证 Orchestrator 预解析 fallback chain 时读到当前配置

边界:

- 这是 operator-local config seam,用于覆盖既有 route 的 fallback 指向
- 它不是整张 registry 替换,也不是 route selection policy
- 它不改变 Phase 64 S1 的核心边界:Executor 仍只消费预解析 chain,不调用 Provider Router selection

### 2. Route Registry Metadata

目的:消除 Python 内硬编码的 `RouteSpec(...)` 全量定义,使"有哪些 route"成为可外部化、可治理的 route metadata。

落点:

- 默认包内 metadata:`src/swallow/routes.default.json`
- 工作区覆盖:`.swl/routes.json`
- 路径 helper:`route_registry_path(base_dir)`
- 代码入口:`load_route_registry(...)` / `save_route_registry(...)` / `apply_route_registry(...)`
- CLI:`swl route registry show` / `swl route registry apply <registry_file>`
- Governance:`register_route_metadata_proposal(..., route_registry=...)` -> `apply_proposal(..., ProposalTarget.ROUTE_METADATA)` -> `RouteRepo._apply_metadata_change(...)`

边界:

- Registry 只描述 route 实体与静态元数据,包括 executor/model/dialect/fallback/capabilities/taxonomy 等
- Registry 不承担 mode mapping、complexity preference、parallel intent 这类 selection policy
- CLI apply 路径通过 `apply_proposal` 写入 `.swl/routes.json`,符合 INVARIANTS §0 第 4 条

### 3. Route Selection Policy Metadata

目的:消除 `ROUTE_MODE_TO_ROUTE_NAME`、`_apply_complexity_bias`、strategy complexity hint、parallel intent hint、summary fallback route name 等 Python 硬编码。

落点:

- 默认包内 metadata:`src/swallow/route_policy.default.json`
- 工作区覆盖:`.swl/route_policy.json`
- 路径 helper:`route_policy_path(base_dir)`
- 代码入口:`load_route_policy(...)` / `save_route_policy(...)` / `apply_route_policy(...)`
- CLI:`swl route policy show` / `swl route policy apply <policy_file>`
- Governance:`register_route_metadata_proposal(..., route_policy=...)` -> `apply_proposal(..., ProposalTarget.ROUTE_METADATA)` -> `RouteRepo._apply_metadata_change(...)`

当前 policy schema:

- `route_mode_routes`:route mode 到 route name 的映射,例如 `http -> local-http`
- `complexity_bias_routes`:complexity hint 到优先 route 的映射,例如 `high -> local-claude-code`
- `strategy_complexity_hints`:哪些 complexity hint 触发 strategy route candidate pass
- `parallel_intent_hints`:哪些 complexity hint 在 `policy_inputs.parallel_intent` 中标记 fan-out 意图
- `summary_fallback_route_name`:route matching 无结果时的最终 summary fallback route

边界:

- 这不是 `ProposalTarget.POLICY`,而是 Provider Router 的 route selection metadata,因此归入 `ProposalTarget.ROUTE_METADATA`
- 这不新增 route,也不改变 `RouteSpec` schema
- 这不改变 S1/S2 的 LLM 路径治理结论,只把 selection preference 从 Python 常量移到 metadata

## Review 判定建议

建议 reviewer 用以下问题判断这组 follow-up 是否合格:

- 是否仍满足 `apply_proposal` 是 route metadata 写入的唯一入口
- `save_route_registry` / `save_route_policy` 是否只在 router helper 或 truth repository 层被调用
- CLI apply 是否通过 `register_route_metadata_proposal` + `apply_proposal(..., ROUTE_METADATA)`,而不是直接写文件
- Orchestrator / CLI 是否在 route selection 前加载 registry + policy + weights + fallbacks + capabilities
- Executor 是否仍不调用 `select_route` / `route_by_name` / `fallback_route_for` 等 selection 函数
- Specialist internal chat-completion 是否仍只通过 `router.invoke_completion`
- `docs/design/INVARIANTS.md` / `docs/design/DATA_MODEL.md` 是否保持无改动

## 验证记录

Route registry externalization follow-up:

- `.venv/bin/python -m pytest tests/test_router.py tests/test_governance.py tests/test_invariant_guards.py -q` -> 63 passed
- `.venv/bin/python -m pytest tests/test_cli.py::CliLifecycleTest::test_route_registry_apply_and_show_cli_flow tests/test_cli.py -k 'route or fallback or capability' -q` -> 49 passed / 191 deselected / 5 subtests passed
- `.venv/bin/python tests/audit_no_skip_drift.py` -> all 8 tracked guards green
- `.venv/bin/python -m pytest` -> 585 passed / 8 deselected

Route policy externalization follow-up:

- `.venv/bin/python -m pytest tests/test_router.py tests/test_governance.py tests/test_invariant_guards.py -q` -> 66 passed
- `.venv/bin/python -m pytest tests/test_cli.py::CliLifecycleTest::test_route_policy_apply_and_show_cli_flow tests/test_cli.py -k 'route or fallback or capability' -q` -> 50 passed / 191 deselected / 5 subtests passed
- `.venv/bin/python tests/audit_no_skip_drift.py` -> all 8 tracked guards green
- `.venv/bin/python -m pytest` -> 589 passed / 8 deselected
- `git diff --check` -> passed
- `git diff -- docs/design/INVARIANTS.md docs/design/DATA_MODEL.md` -> no output
