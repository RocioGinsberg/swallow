---
author: claude
phase: 53
slice: context_brief
status: final
---

## TL;DR
Phase 53 completes the Specialist Agent ecosystem by lifting 5 function-based roles (Ingestion, Literature, Quality Reviewer, Consistency Reviewer, Validator) into independent agents with explicit lifecycle, taxonomy profile, and executor resolver bindings. The pattern is established and stable from Phase 51 (`MetaOptimizerAgent` / `LibrarianAgent`). The primary risk is that two of the five roles (`Literature Specialist`, `Quality Reviewer`) have no existing function-level implementation to upgrade — they must be built from scratch.

# Phase 53 Context Brief

## 上游状态 (What Phase 51/52 delivered)

Phase 51 (`v0.8.0`) 稳定了以下基础设施，Phase 53 直接复用：

- `ExecutorProtocol` — `execute(base_dir, state, card, retrieval_items) -> ExecutorResult` + `execute_async` 接口
- `resolve_executor()` in `executor.py` — 按 `executor_name` / `executor_type` 分发到具体 Agent 类
- `SYSTEM_ROLES` / `MEMORY_AUTHORITIES` 枚举 in `models.py` — taxonomy 合法值集合
- `MetaOptimizerAgent` / `LibrarianAgent` — 两个完整的参考实现，含 `agent_name`, `system_role`, `memory_authority` 类属性，`_build_prompt()`, `execute()`, `execute_async()` 方法，以及兼容包装器 (`MetaOptimizerExecutor` / `LibrarianExecutor`)
- `OptimizationProposalApplicationRecord` + rollback 快照 — 提案应用基础设施（Phase 53 的 Reviewer 角色可能产出提案，但不直接应用）

Phase 52 (`v0.9.0`) 补充：

- `AsyncCLIAgentExecutor` 统一 async 入口，`asyncio.create_task` 审计调度路径已收口
- `schedule_consistency_audit` 已改为 async 路径（消化了 Phase 51 C2）

## 当前系统状态

### 已落地为独立 Agent 的角色

| 角色 | 类 | 文件 | system_role | memory_authority |
|---|---|---|---|---|
| Librarian | `LibrarianAgent` | `librarian_executor.py` | `specialist` | `canonical-promotion` |
| Meta-Optimizer | `MetaOptimizerAgent` | `meta_optimizer.py` | `specialist` | `canonical-write-forbidden` |

### 仍为函数化的角色（Phase 53 目标）

| 角色 | 当前实现 | 文件 |
|---|---|---|
| Ingestion Specialist | `run_ingestion_pipeline()` | `ingestion/pipeline.py` |
| Consistency Reviewer | `run_consistency_audit()` / `schedule_consistency_audit()` | `consistency_audit.py` |
| Validator | `validate_run_outputs()` | `validator.py` |
| Literature Specialist | 无现有实现 | — |
| Quality Reviewer | 无现有实现 | — |

### `resolve_executor()` 当前注册情况

`executor.py` 中 `resolve_executor()` 目前只识别 `librarian` 和 `meta-optimizer` 两个 specialist 名称。Phase 53 需要为新增的 5 个角色补充分支。

## 设计蓝图对齐

来自 `AGENT_TAXONOMY.md §7.3`：

| 角色 | Taxonomy | memory_authority |
|---|---|---|
| Ingestion Specialist | `specialist / cloud-backed / staged-knowledge / conversation-ingestion` | `staged-knowledge` |
| Literature Specialist | `specialist / cloud-backed / task-memory / domain-rag-parsing` | `task-memory` |
| Meta-Optimizer | `specialist / cloud-backed / read-only / workflow-optimization` | `canonical-write-forbidden` |
| Quality Reviewer | `validator / cloud-backed / stateless / artifact-validation` | `stateless` |
| Consistency Reviewer | `validator / cloud-backed / stateless / consistency-check` | `stateless` |

注：`AGENT_TAXONOMY.md` 将 Quality Reviewer 和 Consistency Reviewer 的 `system_role` 定义为 `validator`，而非 `specialist`。`MEMORY_AUTHORITIES` 枚举中已有 `stateless`，`SYSTEM_ROLES` 中已有 `validator`，两者均合法。

## Open Concerns 继承

与 Phase 53 直接相关的 backlog 条目：

- **Phase 51 C1**（`concerns_backlog.md`）：`MetaOptimizerAgent.memory_authority = "canonical-write-forbidden"` 语义模糊——禁止的是 canonical store 写入，不是所有文件写入。Phase 53 引入更多 Agent 时，需在 taxonomy 文档或代码注释中明确区分 `canonical write authority` 与 `artifact write side effect`。Phase 52 closeout 明确指出 Phase 53 应同时消化此 concern。
- **Phase 50 C1**（`concerns_backlog.md`）：`extract_route_weight_proposals_from_report()` 依赖文本格式稳定性。若 Phase 53 的 Quality Reviewer 产出结构化报告，应避免复用同一文本解析模式。
- **Phase 50 C2**（`concerns_backlog.md`）：`_FAIL_SIGNAL_PATTERNS` 关键词扫描可能产生 false fail verdict。Consistency Reviewer Agent 化后，应在 prompt 中明确要求输出 `- verdict: pass/fail/inconclusive` 行（`_VERDICT_PATTERN` 已存在于 `consistency_audit.py`，但 fallback 仍依赖关键词）。

## Phase 53 的核心问题

1. **Literature Specialist 和 Quality Reviewer 无现有函数实现**：这两个角色需要从零定义输入/输出边界、prompt 模板和 `execute()` 逻辑，而不是升级现有函数。kickoff 需要明确它们的最小可行输入输出契约。

2. **Consistency Reviewer Agent 化的边界**：`consistency_audit.py` 中的 `run_consistency_audit()` 已被 `schedule_consistency_audit()` 的 `asyncio.create_task` 路径调用，且与 `AuditTriggerPolicy` 耦合。Agent 化时需决定：是将 `ConsistencyReviewerAgent` 作为 `run_consistency_audit()` 的包装器，还是重构调用链。

3. **`resolve_executor()` 扩展策略**：5 个新 Agent 需要在 `executor.py` 中注册。需决定是逐一添加 `if` 分支，还是引入注册表机制（当前模式为前者）。

## 建议 kickoff 焦点

- 明确 Literature Specialist 和 Quality Reviewer 的最小输入/输出契约（`input_context` 字段、`ExecutorResult.output` 格式）
- 确认 Consistency Reviewer Agent 化是包装现有 `run_consistency_audit()` 还是重构调用链
- 确认 Phase 51 C1（`memory_authority` 命名语义）的消化方式（文档注释 vs 代码层面区分）
