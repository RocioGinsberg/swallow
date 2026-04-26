---
author: claude
phase: 60
slice: context-analysis
status: draft
depends_on: ["docs/roadmap.md"]
---

TL;DR: Phase 57 landed neural embedding + LLM rerank; Phase 59 added `local-codex` as a first-class CLI route.
`retrieve_context()` is called through a single choke point (`build_task_retrieval_request` in orchestrator.py)
and always requests `["repo", "notes", "knowledge"]` regardless of executor family. `state.route_executor_family`
is already populated at call time, so the signal needed for path-aware policy is available — it just isn't wired
into retrieval request construction.

## 变更范围

- **直接影响模块**:
  - `src/swallow/retrieval.py` — `build_retrieval_request()` (default source_types), `retrieve_context()` (top-level
    pipeline entry; no execution-path awareness today)
  - `src/swallow/orchestrator.py` — `build_task_retrieval_request(state: TaskState)` at line ~3152 (sole call site
    that constructs the retrieval request for task execution); `_run_retrieval_async()` at line ~3399 which invokes it
  - `src/swallow/models.py` — `RetrievalRequest` dataclass (fields: `source_types`, `context_layers`, `strategy`);
    `TaskState` fields `route_executor_family` and `route_backend`; `TaskSemantics` field `complexity_hint`;
    `infer_task_family()` function

- **间接影响模块**:
  - `src/swallow/harness.py` — `run_retrieval()` passes `request` through to `retrieve_context()` unchanged; no
    source-type logic here
  - `src/swallow/retrieval_adapters.py` — `MARKDOWN_ADAPTER` (source_type `"notes"`) and `REPO_TEXT_ADAPTER`
    (source_type `"repo"`); `select_retrieval_adapter()` maps file suffix to adapter; no routing logic
  - `src/swallow/router.py` — `RouteSpec.executor_family` populated at route registration time; `select_route()`
    writes `route_executor_family` onto state before retrieval phase runs

## 近期相关变更 (git history)

| Commit | 描述 | 相关模块 |
|--------|------|---------|
| 014f30c | docs(roadmap): update tag and phase | docs |
| 6eda794 | feat(route): register real local codex route | router.py |
| 4da921d | feat(executor): wire codex cli agent config | executor.py |
| 4026e57 | feat(doctor): add cli agent binary probes | doctor.py |
| 3f1c38a | feat(knowledge): add clipboard ingest and generic chat json | knowledge, cli |
| e234060 | feat(knowledge): add swl note staged capture | knowledge, cli |
| b399aa3 | docs(phase58): tighten knowledge capture ingestion scope | docs |

## 关键上下文

- **`retrieve_context()` 的唯一任务执行调用路径**: `orchestrator.py:build_task_retrieval_request()` →
  `_run_retrieval_async()` → `harness.run_retrieval()` → `retrieve_context()`. 这一路径在路由完成（route
  已写入 state）之后执行，因此 `state.route_executor_family`（值为 `"cli"` 或 `"api"`）在调用时已确定。

- **`build_task_retrieval_request` 硬编码了 source_types**: 当前实现固定传入
  `source_types=["repo", "notes", "knowledge"]`，没有参数接收 executor_family 或 task_family。这是需要修改的唯一
  构造点。

- **source_type 枚举**: retrieval 管道支持三种 source type — `"repo"`（非 .md 文件，REPO_TEXT_ADAPTER）、
  `"notes"`（.md 文件，MARKDOWN_ADAPTER）、`"knowledge"`（verified knowledge objects + canonical records）、
  以及 `"artifacts"`（.swl task artifacts，仅当显式请求时启用）。

- **executor_family 的取值**: `RouteSpec.executor_family` 字段有两个实际值 — `"cli"`（local-aider,
  local-claude-code, local-codex, local-mock, local-note, local-summary）和 `"api"`（local-http,
  http-claude, http-qwen, http-glm, http-gemini, http-deepseek）。`state.route_executor_family` 在路由选择后
  被写入。

- **task_family 已有推断函数**: `infer_task_family(state)` 从 `state.task_semantics["source_kind"]` 推断，
  返回值为 `"planning"`, `"review"`, `"extraction"`, `"retrieval"`, `"execution"` 之一。该函数已被 router.py
  用于路由选择，但未被 retrieval 使用。

- **task_intent 字段不存在**: `TaskState` 和 `TaskSemantics` 中均无 `task_intent` 字段。roadmap 中提到的
  task_intent 概念需要映射到现有的 `task_family`（`infer_task_family()`）或 `complexity_hint`
  (`task_semantics.complexity_hint`)。两者都已存在但均未接入 retrieval。

- **`complexity_hint` 已在 router 中消费**: `_resolve_complexity_hint(state)` 读取
  `state.task_semantics["complexity_hint"]`，在路由选择中用于 complexity bias（`"low"/"routine"` → aider,
  `"high"` → claude-code）。retrieval 完全不读取此字段。

- **`RetrievalRequest.strategy` 字段已存在但未生效**: dataclass 有 `strategy: str = "system_baseline"` 字段，
  但 `retrieve_context()` 内部未按 strategy 分支任何逻辑。该字段可以作为路径分流的载体，但目前是空操作。

- **`context_layers` 字段控制 knowledge 范围**: `"task"` 允许当前任务 knowledge，`"history"` 允许跨任务
  knowledge，`"workspace"` 用于 file 扫描。该字段已有分流语义，但未按 executor_family 调整。

- **`retrieve_context()` 的文件扫描是全量的**: 函数对 `workspace_root.rglob("*")` 做全量遍历，靠
  `classify_source_type(path, allowed_sources)` 过滤。删除 `"repo"` 或 `"notes"` from source_types 即可跳过
  对应文件类型的扫描，无需修改扫描逻辑本身。

## 风险信号

- **默认行为变更影响已有测试**: `build_task_retrieval_request` 返回的 source_types 变化会影响所有依赖其输出
  的测试。tests/test_cli.py 有 220 个测试；需确认哪些 mock retrieval，哪些走真实路径。

- **`executor_family` 在 route 选择前不可用**: 若某个代码路径在路由完成之前调用 retrieval（如 fan-out 子任务
  的某些早期路径），`state.route_executor_family` 可能仍是默认值 `"cli"`（TaskState 默认值）。需核实子任务路径
  的调用顺序。

- **brainstorm/knowledge capture path 的归属**: Phase 58 引入的 `swl note` 和 clipboard ingest 走的是
  knowledge 写入路径而非 task 执行路径，不触发 `build_task_retrieval_request`。这些路径当前不在 retrieval
  policy 范围内。

- **`"notes"` source_type 的双重含义**: `"notes"` 由 MARKDOWN_ADAPTER 处理，覆盖所有 .md 文件（包括 docs/,
  results/ 等），而非仅 staged notes。CLI agent 自主探索时可能仍需要部分 .md 文件（如 task prompt
  文件）。直接删除 `"notes"` 需要评估 CLI path 是否真的不需要任何 .md chunk。
