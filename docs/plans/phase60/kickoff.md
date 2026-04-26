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

Phase 60 将 retrieval policy 从"固定三源（repo / notes / knowledge）"升级为"按 execution_family + task_family 分流"。CLI coding path 收紧为 knowledge + explicit refs（CLI agent 自主探索文件，repo chunk 是噪声）；HTTP brainstorm path 聚焦 knowledge + notes；HTTP code-analysis path 保留受控 repo 检索。唯一改动点是 `orchestrator.py:build_task_retrieval_request()`，不触碰 retrieval 管线内部。

# Phase 60 Kickoff: 路径感知的 Retrieval Policy

## Phase 身份

- **Phase**: 60
- **Primary Track**: Knowledge / RAG
- **Secondary Track**: CLI / Routing
- **分支建议**: `feat/phase60-retrieval-policy`

## 背景与动机

Phase 57 落地了神经 embedding + LLM rerank，Phase 58 打通了知识捕获入口，Phase 59 完成了 CLI 三足鼎立（aider / claude-code / codex）。此时 retrieval 的下一个最直接瓶颈不是质量，而是**分流缺失**：

- `build_task_retrieval_request()` 固定传入 `source_types=["repo", "notes", "knowledge"]`，无论 executor 是 CLI agent 还是 HTTP API
- CLI agent（aider / claude-code / codex）具备自主文件探索能力，在执行过程中会主动读取 repo 文件；在 retrieval 阶段额外灌入 repo chunk 是重复噪声
- `state.route_executor_family`（`"cli"` 或 `"api"`）在路由选择后已写入 state，在 `build_task_retrieval_request()` 调用时已确定——信号已在，只是未被消费
- `infer_task_family(state)` 已有 `"planning"` / `"review"` / `"extraction"` / `"retrieval"` / `"execution"` 分类，也未被 retrieval 消费

本 phase 目标：用最小改动把这两个已有信号接入 retrieval request 构造，实现路径分流。

## 目标

1. **G1 — CLI path 收紧**：`executor_family == "cli"` 时，默认 source_types 从 `["repo", "notes", "knowledge"]` 收紧为 `["knowledge"]`，同时保留 explicit document_paths 透传
2. **G2 — HTTP brainstorm path 聚焦**：`executor_family == "api"` + `task_family in ("planning", "review")` 时，source_types 为 `["knowledge", "notes"]`（去掉 repo）
3. **G3 — HTTP code-analysis path 保留 repo**：`executor_family == "api"` + `task_family in ("execution", "extraction")` 时，source_types 保持 `["repo", "notes", "knowledge"]`
4. **G4 — 可覆盖机制**：`RetrievalRequest` 支持显式 `source_types` 覆盖，operator 可通过 task 配置绕过默认 policy

## 非目标

- **修改 `retrieve_context()` 内部逻辑**：分流在 request 构造层完成，管线内部不变
- **新增 source_type**：不引入 `"artifacts"` 以外的新类型
- **修改 `executor_family` 的定义或赋值逻辑**：`RouteSpec.executor_family` 已稳定，不变
- **修改 `infer_task_family()`**：直接复用现有函数，不扩展分类
- **为 brainstorm topology 设计专用 retrieval path**：候选 E 的范围，不在本轮
- **回填历史任务的 retrieval source**：只影响新任务执行
- **修改 `complexity_hint` 消费逻辑**：router 已消费，retrieval 不引入第二个消费点
- **修改 `RetrievalRequest.strategy` 字段语义**：该字段当前是空操作，不在本轮激活

## 设计边界

1. **唯一改动点**：`orchestrator.py:build_task_retrieval_request(state)` — 在此函数内读取 `state.route_executor_family` 和 `infer_task_family(state)`，按 policy 表选择 source_types
2. **policy 以常量表形式定义**：在 `orchestrator.py` 或独立 `retrieval_policy.py` 中定义 `RETRIEVAL_SOURCE_POLICY` dict，便于测试和后续扩展
3. **explicit override 优先**：若 `state.task_semantics` 或 task 配置中有显式 `source_types`，policy 不覆盖
4. **fallback 到现有行为**：`executor_family` 未知或 `task_family` 未知时，保持 `["repo", "notes", "knowledge"]` 原始行为
5. **不修改 harness.py**：`run_retrieval()` 只做透传，不在此层加 policy 逻辑

## Slice 拆分

### S1: Policy 表定义 + CLI path 收紧

**目标**：在 `build_task_retrieval_request()` 中读取 `executor_family`，CLI path 默认只取 `["knowledge"]`

**改动范围**：
- `src/swallow/orchestrator.py`: `build_task_retrieval_request()` 读取 `state.route_executor_family`
- 定义 `_RETRIEVAL_SOURCE_POLICY` 常量（可在 orchestrator.py 顶部或独立模块）
- CLI path: `executor_family == "cli"` → `source_types = ["knowledge"]`
- 非 CLI path: 保持现有 `["repo", "notes", "knowledge"]`（S2 再细分）

**验收条件**：
- `build_task_retrieval_request()` 对 CLI route 返回 `source_types=["knowledge"]`
- 对 HTTP route 返回 `source_types=["repo", "notes", "knowledge"]`（S2 前的过渡态）
- pytest 覆盖：CLI route / HTTP route 各一个 unit test

**不做**：
- task_family 细分（S2 的范围）
- explicit override 机制（S3 的范围）

### S2: HTTP path 按 task_family 细分

**目标**：HTTP path 内部按 `infer_task_family(state)` 进一步分流

**改动范围**：
- `src/swallow/orchestrator.py`: `build_task_retrieval_request()` 对 `executor_family == "api"` 分支调用 `infer_task_family(state)`
- brainstorm/planning/review path: `source_types = ["knowledge", "notes"]`
- code-analysis/execution/extraction path: `source_types = ["repo", "notes", "knowledge"]`
- `"retrieval"` task_family: `source_types = ["knowledge", "notes", "repo"]`（保持完整，retrieval 任务本身需要全量）
- 未知 task_family: fallback 到 `["repo", "notes", "knowledge"]`

**验收条件**：
- `build_task_retrieval_request()` 对 HTTP + planning route 返回 `["knowledge", "notes"]`
- 对 HTTP + execution route 返回 `["repo", "notes", "knowledge"]`
- pytest 覆盖：各 task_family 分支均有 unit test

**不做**：
- 修改 `infer_task_family()` 本身
- 引入新的 task_family 值

### S3: Explicit Override + 测试补全

**目标**：允许 operator 通过 task 配置显式指定 source_types，覆盖 policy 默认值；补全集成测试

**改动范围**：
- `src/swallow/orchestrator.py`: `build_task_retrieval_request()` 检查 `state.task_semantics.get("retrieval_source_types")` 或等价字段，若存在则跳过 policy 选择
- `src/swallow/models.py`: 在 `TaskSemantics` 中添加可选 `retrieval_source_types: list[str] | None = None` 字段（如果 TaskSemantics 是 TypedDict，添加对应 key）
- 集成测试：mock orchestrator 调用链，验证 policy 在真实 state 构造下生效

**验收条件**：
- 显式 `retrieval_source_types` 覆盖 policy 默认值
- 未设置时 policy 正常生效
- pytest 覆盖：override 路径 + 无 override 路径

**不做**：
- CLI 暴露 `--retrieval-sources` 参数（后续 phase 按需添加）
- 修改 `swl task create` 命令

## 完成条件

1. **CLI path 收紧**：`executor_family == "cli"` 任务的 retrieval request 默认不包含 `"repo"` source
2. **HTTP brainstorm path 聚焦**：planning / review task_family 的 HTTP 任务不包含 `"repo"` source
3. **HTTP code-analysis path 保留**：execution / extraction task_family 的 HTTP 任务保留完整三源
4. **Explicit override 生效**：`task_semantics["retrieval_source_types"]` 可覆盖 policy
5. **Fallback 稳定**：未知 executor_family 或 task_family 时行为与 Phase 59 一致
6. **测试覆盖**：S1/S2/S3 各分支均有 pytest 覆盖，无 regression

## Eval 验收条件

本 phase 改动的是 retrieval 的**输入过滤**，不改变 retrieval 管线内部质量逻辑。主要风险是 CLI path 收紧后 recall 下降（本来有用的 repo chunk 被过滤）。

| Slice | Eval 需要 | 说明 |
|-------|----------|------|
| S1 (CLI path 收紧) | 否 | 行为变更明确（去掉 repo），pytest 覆盖边界即可；CLI agent 自主探索能力是 recall 的替代来源 |
| S2 (HTTP task_family 细分) | 否 | task_family 分类已有 `infer_task_family()` 覆盖，pytest 验证分支路由即可 |
| S3 (Override) | 否 | 纯机制，pytest 覆盖即可 |

如果后续真实使用中 CLI path 出现 recall 问题（operator 反馈），再考虑单独起 eval 基线。

## Branch Advice

- 当前分支: `main`（Phase 59 已 merge，v1.3.0 已打）
- 建议操作: 新建分支
- 建议分支名: `feat/phase60-retrieval-policy`
- 建议 PR 范围: S1-S3 全部 slice 合入单个 PR

## 风险预告

详见 `risk_assessment.md`，关键风险：

1. **CLI path recall 下降**：去掉 `"repo"` 后，若某些 CLI 任务依赖 repo chunk 作为上下文补充，可能出现 recall 下降。缓解：S3 的 explicit override 机制允许 operator 按需恢复
2. **`executor_family` 默认值干扰**：`TaskState` 默认 `route_executor_family = "cli"`，若某个路径在路由完成前调用 retrieval，会错误走 CLI policy。缓解：S1 需验证调用顺序，确认路由先于 retrieval
3. **`infer_task_family()` 返回 `"execution"` 的覆盖面**：大多数普通任务可能都被归为 `"execution"`，导致 HTTP path 细分效果有限。缓解：S2 的 fallback 保持现有行为，不引入 regression
