---
author: claude
phase: 60
slice: kickoff
status: draft
depends_on:
  - docs/plans/phase60/context_brief.md
  - docs/roadmap.md
  - docs/plans/phase59/closeout.md
---

## TL;DR

Phase 60 将 retrieval policy 从"固定三源（repo / notes / knowledge）"升级为"按 route capability + execution_family + task_family 分流"。自主 CLI coding path（aider / claude-code / codex）收紧为 knowledge-only；HTTP API path 默认聚焦 knowledge + notes，不再把 execution / extraction / retrieval 自动视为 repo chunk 主路径；非自主 local fallback / deterministic route 可为兼容暂保留旧三源。repo source 只作为显式 override 或 legacy fallback 辅助源，不作为代码库问答的默认核心路径。核心改动点仍是 `orchestrator.py:build_task_retrieval_request()`，不触碰 retrieval 管线内部。

# Phase 60 Kickoff: 路径感知的 Retrieval Policy

## Phase 身份

- **Phase**: 60
- **Primary Track**: Knowledge / RAG
- **Secondary Track**: CLI / Routing
- **分支建议**: `feat/phase60-retrieval-policy`

## 背景与动机

Phase 57 落地了神经 embedding + LLM rerank，Phase 58 打通了知识捕获入口，Phase 59 完成了 CLI 三足鼎立（aider / claude-code / codex）。此时 retrieval 的下一个最直接瓶颈不是质量，而是**分流缺失**：

- `build_task_retrieval_request()` 固定传入 `source_types=["repo", "notes", "knowledge"]`，无论 executor 是 CLI agent 还是 HTTP API
- CLI agent（aider / claude-code / codex）具备自主文件探索能力，在执行过程中会主动读取 repo 文件；代码库问答 / 代码修改任务默认应走这类 CLI route，而不是通过 HTTP executor + repo chunk 间接补上下文
- HTTP executor 的价值更偏向规划、审查、总结、知识复用与模型分发；若把它作为代码库 Q&A 默认路径，需要 repo chunk 兜底，反而会重新引入过时的本地 RAG 噪声
- 但 `executor_family="cli"` 还覆盖 `local-mock` / `local-note` / `local-summary` / `mock-remote` 等非自主 fallback / test route；这些 route 不应被一刀切收紧为 knowledge-only
- `state.route_executor_family`（`"cli"` 或 `"api"`）在路由选择后已写入 state，在 `build_task_retrieval_request()` 调用时已确定——信号已在，只是未被消费
- `infer_task_family(state)` 已有 `"planning"` / `"review"` / `"extraction"` / `"retrieval"` / `"execution"` 分类，也未被 retrieval 消费

本 phase 目标：用最小改动把 route capability、executor family 与 task_family 接入 retrieval request 构造，实现路径分流。

## 设计锚点

Phase 60 的实现必须对齐三份长期设计文档：

- `KNOWLEDGE.md §2.3`：`knowledge` 是治理后的长期知识，`notes` 是 Markdown 文档现场，`repo` 是局部源码 chunk，不代表完整代码库理解
- `ARCHITECTURE.md §4.1`：HTTP executor 是模型认知层，autonomous CLI agent 是 workspace 行动层，Specialist Agent 是固定专精流程封装
- `AGENT_TAXONOMY.md §7.4`：Specialist 不是第三种通用 executor family；它可以复用 HTTP 或本地逻辑，但 system role、input_context 与 memory authority 必须保持窄边界

## 目标

1. **G1 — 自主 CLI coding path 收紧**：仅当 route 同时满足 `executor_family == "cli"`、`supports_tool_loop == True`、`execution_kind == "code_execution"` 时，默认 source_types 从 `["repo", "notes", "knowledge"]` 收紧为 `["knowledge"]`；不影响 `input_context.document_paths` 等显式输入透传
2. **G2 — HTTP path 聚焦**：`executor_family == "api"` 时，默认 source_types 为 `["knowledge", "notes"]`；`task_family` 可用于测试与未来扩展，但本 phase 不因 `"execution"` / `"extraction"` / `"retrieval"` 自动启用 repo
3. **G3 — Repo source 显式化**：`"repo"` 仅通过 `task_semantics["retrieval_source_types"]` 显式 override，或在非自主 local fallback / deterministic route 的兼容分支中保留；不再作为 HTTP 默认策略
4. **G4 — Specialist / explicit input_context 不被误伤**：Literature / Ingestion / Librarian / Validator 等专精路径继续以 explicit input_context、artifact refs 或专属 staged/canonical flow 为准，不因通用 HTTP/CLI policy 被泛化成 repo/notes 检索路径
5. **G5 — 可覆盖机制**：`TaskSemantics.retrieval_source_types` 支持显式 source_types 覆盖，operator 可通过 task 配置绕过默认 policy

## 非目标

- **修改 `retrieve_context()` 内部逻辑**：分流在 request 构造层完成，管线内部不变
- **新增 source_type**：不引入 `"artifacts"` 以外的新类型
- **修改 `executor_family` 的定义或赋值逻辑**：`RouteSpec.executor_family` 已稳定，不变
- **修改 `infer_task_family()`**：直接复用现有函数，不扩展分类
- **为 brainstorm topology 设计专用 retrieval path**：候选 E 的范围，不在本轮
- **回填历史任务的 retrieval source**：只影响新任务执行
- **修改 `complexity_hint` 消费逻辑**：router 已消费，retrieval 不引入第二个消费点
- **修改 `RetrievalRequest.strategy` 字段语义**：该字段当前是空操作，不在本轮激活
- **为 Specialist 设计新 retrieval 协议**：本轮只要求不误伤现有 explicit input_context / artifact_ref / document_paths 语义，不新增 Specialist 专属 source policy

## 设计边界

1. **唯一主改动点**：`orchestrator.py:build_task_retrieval_request(state)` — 在此函数内读取 `state.route_executor_family`、`state.route_capabilities` 和 `infer_task_family(state)`，按 policy 表选择 source_types
2. **policy 以常量表形式定义**：在 `orchestrator.py` 或独立 `retrieval_policy.py` 中定义 `RETRIEVAL_SOURCE_POLICY` dict，便于测试和后续扩展
3. **explicit override 优先**：若 `state.task_semantics["retrieval_source_types"]` 有合法显式 source_types，policy 不覆盖
4. **fallback 分层处理**：明确识别的非自主 local fallback / deterministic route 可保持 `["repo", "notes", "knowledge"]` 兼容；未知 route 或 capability 不完整时使用 `["knowledge", "notes"]`，避免静默把 repo chunk 重新放回默认主链
5. **Specialist 以 taxonomy / capability 守边界**：不得用裸 `executor_family` 推断 Specialist 语义；若 route taxonomy、executor_name 或 explicit input_context 指向专精流程，policy 必须保持现有显式输入优先
6. **不修改 harness.py**：`run_retrieval()` 只做透传，不在此层加 policy 逻辑

## Concerns Backlog Triage

Phase 60 启动前已复核 `docs/concerns_backlog.md`：

- Phase 49 sqlite-vec WARN 竞态、Phase 57 embedding dimensions import 固化都属于 retrieval-adjacent concern，但 Phase 60 不触碰 retrieval adapter / embedding 配置层，不并入本轮
- Phase 59 release-doc sync debt（`AGENTS.md` / `README.md` 仍停留在 v1.2.0 描述）保留为 tag-level 文档任务，不阻塞本轮 implementation
- Phase 60 只消费与 retrieval request source policy 直接相关的风险：不要把非自主 CLI fallback route 一并收紧

## Slice 拆分

### S1: Policy 表定义 + 自主 CLI coding path 收紧

**目标**：在 `build_task_retrieval_request()` 中读取 route capability + `executor_family`，建立 route policy family，并让自主 CLI coding path 默认只取 `["knowledge"]`

**改动范围**：
- `src/swallow/orchestrator.py`: `build_task_retrieval_request()` 读取 `state.route_executor_family`
- 定义 `_RETRIEVAL_SOURCE_POLICY` 常量（可在 orchestrator.py 顶部或独立模块）
- 自主 CLI coding path: `executor_family == "cli"` + `route_capabilities.supports_tool_loop == True` + `route_capabilities.execution_kind == "code_execution"` → `source_types = ["knowledge"]`
- 非自主 CLI fallback / test path（如 `local-mock` / `local-note` / `local-summary` / `mock-remote`）进入 `legacy_local_fallback` family，可暂保留现有 `["repo", "notes", "knowledge"]`
- HTTP path 在 S1 可先落入不含 repo 的全局保守 fallback；S2 再补充显式 `("api", "*")` 规则与 task_family 测试覆盖
- Specialist / validator route 不因兼容解析（如 `resolve_executor("cli", "librarian")`）被归入 autonomous CLI coding path

**验收条件**：
- `build_task_retrieval_request()` 对 `local-aider` / `local-claude-code` / `local-codex` 这类自主 CLI coding route 返回 `source_types=["knowledge"]`
- 对 `local-summary` 或 `local-mock` 这类非自主 CLI route 返回 `source_types=["repo", "notes", "knowledge"]`
- 对 HTTP route 返回不含 repo 的保守默认值 `["knowledge", "notes"]`
- 对 Specialist / validator 风格 state，若存在 explicit input_context / artifact_ref / document_paths，不被通用 policy 覆盖或丢弃
- pytest 覆盖：自主 CLI route / 非自主 CLI route / HTTP route 各一个 unit test

**不做**：
- task_family 细分（S2 的范围）
- explicit override 机制（S3 的范围）

### S2: HTTP path 显式规则 + task_family 覆盖

**目标**：把 S1 的 HTTP 保守 fallback 固化为显式 `("api", "*")` policy，补齐 planning / review / execution / extraction / retrieval 的 task_family 测试覆盖；不在本 phase 自动打开 repo。

**改动范围**：
- `src/swallow/orchestrator.py`: `build_task_retrieval_request()` 对 `executor_family == "api"` 分支调用 `infer_task_family(state)`
- planning / review / execution / extraction / retrieval 等 HTTP task_family 默认均为 `source_types = ["knowledge", "notes"]`
- 未知 HTTP task_family fallback 到 `["knowledge", "notes"]`
- 代码库问答或源码分析若确实需要 repo chunk，应通过 S3 explicit override 请求 `["repo", "notes", "knowledge"]`，或优先路由到 autonomous CLI coding route

**验收条件**：
- `build_task_retrieval_request()` 对 HTTP + planning route 返回 `["knowledge", "notes"]`
- 对 HTTP + execution / extraction / retrieval route 返回 `["knowledge", "notes"]`
- pytest 覆盖：各 task_family 分支均有 unit test

**不做**：
- 修改 `infer_task_family()` 本身
- 引入新的 task_family 值

### S3: Explicit Override + 测试补全

**目标**：允许 operator 通过 task 配置显式指定 source_types，覆盖 policy 默认值；补全集成测试

**改动范围**：
- `src/swallow/orchestrator.py`: `build_task_retrieval_request()` 检查 `state.task_semantics.get("retrieval_source_types")` 或等价字段，若存在合法 source_types 则跳过 policy 选择
- `src/swallow/models.py`: 在 dataclass `TaskSemantics` 中添加可选 `retrieval_source_types: list[str] | None = None` 字段
- `src/swallow/task_semantics.py`: `build_task_semantics()` 保持该字段可选；后续 attach / merge semantics 路径不得意外丢弃已有 override
- override normalization：只允许 `repo` / `notes` / `knowledge` / `artifacts`，保序去重；出现非法 source_type 时显式抛错，不静默降级为空检索
- 集成测试：mock orchestrator 调用链，验证 policy 在真实 state 构造下生效

**验收条件**：
- 显式 `retrieval_source_types` 覆盖 policy 默认值，并拒绝非法 source_type
- 未设置时 policy 正常生效
- pytest 覆盖：override 路径 + 无 override 路径

**不做**：
- CLI 暴露 `--retrieval-sources` 参数（后续 phase 按需添加）
- 修改 `swl task create` 命令

## 完成条件

1. **自主 CLI coding path 收紧**：aider / claude-code / codex 这类 route 的 retrieval request 默认不包含 `"repo"` source
2. **非自主 CLI fallback 稳定**：local-summary / local-note / local-mock 等 legacy route 若缺少自主 tool loop，可暂保持 `["repo", "notes", "knowledge"]` 兼容
3. **HTTP path 聚焦**：planning / review / execution / extraction / retrieval task_family 的 HTTP 任务默认不包含 `"repo"` source
4. **Repo source 显式可恢复**：需要源码 chunk 的任务必须通过 explicit override 或路由到 autonomous CLI coding route，而不是依赖 HTTP 默认携带 repo
5. **Specialist 显式输入稳定**：Specialist / validator 路径的 `document_paths`、`artifact_ref`、`source_path` 等显式输入不被 source policy 改写
6. **Explicit override 生效**：`task_semantics["retrieval_source_types"]` 可覆盖 policy
7. **Fallback 稳定**：明确识别的 legacy local fallback 可保持 Phase 59 三源兼容；未知 executor_family、缺失 route capability 或未知 HTTP task_family 不默认启用 repo
8. **测试覆盖**：S1/S2/S3 各分支均有 pytest 覆盖，无 regression

## Eval 验收条件

本 phase 改动的是 retrieval 的**输入过滤**，不改变 retrieval 管线内部质量逻辑。主要风险不是自主 CLI agent "降智"，而是代码库问答任务被误路由到 HTTP 后缺少 repo 上下文；该类任务应优先走 CLI tool-loop，或显式 override retrieval source。

| Slice | Eval 需要 | 说明 |
|-------|----------|------|
| S1 (自主 CLI coding path 收紧) | 否 | 行为变更明确（去掉 repo），pytest 覆盖边界即可；CLI agent 自主探索能力是代码库上下文的主路径。非自主 CLI fallback route 可保留 legacy 三源 |
| S2 (HTTP path 聚焦) | 否 | pytest 验证 HTTP 各 task_family 默认不含 repo；代码库上下文由 CLI route 或 explicit override 承担 |
| S3 (Override) | 否 | 纯机制，pytest 覆盖即可 |

如果后续真实使用中出现 HTTP 误路由导致的代码库上下文不足，再单独评估 router policy 或 explicit override 的 operator 入口，而不是回退到 HTTP 默认 repo chunk。

## Branch Advice

- 当前分支: `feat/phase60-retrieval-policy`
- 建议操作: 先提交文档 gate，再开始 S1 实现
- 建议分支名: `feat/phase60-retrieval-policy`
- 建议 PR 范围: S1-S3 全部 slice 合入单个 PR

## 风险预告

详见 `risk_assessment.md`，关键风险：

1. **代码库任务误路由到 HTTP**：HTTP 默认不再携带 `"repo"`，若代码库问答 / 代码分析任务没有走 autonomous CLI route，可能上下文不足。缓解：路由策略优先选择 CLI tool-loop；S3 的 explicit override 机制允许 operator 按需恢复 repo source
2. **`executor_family` 默认值干扰**：`TaskState` 默认 `route_executor_family = "cli"`，若某个路径在路由完成前调用 retrieval，可能误走 CLI policy。缓解：S1 使用 route capability guard；缺失 capability 时不进入 autonomous CLI policy，未知 route fallback 到不含 repo 的保守默认
3. **Specialist 被通用 policy 误分类**：兼容入口可能让 Specialist 看起来像 `executor_family="cli"`，但它不是 autonomous CLI coding route。缓解：以 route capability / taxonomy / explicit input_context 做 guard，不用裸 executor_family 判断
4. **legacy fallback 噪声保留**：非自主 local fallback 为兼容暂保留 repo source，可能继续带入旧噪声。缓解：明确标注为 legacy 兼容分支，后续可基于真实反馈继续收紧
