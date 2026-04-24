---
author: claude
phase: 53
slice: kickoff
status: draft
depends_on:
  - docs/plans/phase53/context_brief.md
  - docs/roadmap.md
  - docs/design/AGENT_TAXONOMY.md
---

## TL;DR
Phase 53 将 5 个函数化角色升级为独立 Agent 实体，复用 Phase 51 建立的 `ExecutorProtocol` + `resolve_executor` + taxonomy profile 模式。其中 3 个有现有函数可包装（Ingestion、Consistency Reviewer、Validator），2 个需从零构建最小契约（Literature Specialist、Quality Reviewer）。同时消化 Phase 51 C1（`memory_authority` 命名语义文档收紧）。

# Phase 53 Kickoff: Specialist Agent 生态落地

## 基本信息

| 字段 | 值 |
|------|-----|
| Phase | 53 |
| Primary Track | Agent Taxonomy |
| Secondary Track | Knowledge / Self-Evolution |
| 目标 tag | v0.10.0 (Agent Ecosystem Era) |
| 前置 phase | Phase 52 (v0.9.0) |

## 战略定位

Phase 51 建立了 Specialist Agent 的生命周期模式（MetaOptimizerAgent / LibrarianAgent），Phase 52 完成了执行层异步化。Phase 53 的使命是**把剩余 5 个函数化角色全部升级为独立 Agent 实体**，使 `AGENT_TAXONOMY.md §7.3` 定义的 6 个核心专项角色全部具备显式生命周期、taxonomy profile 与 executor resolver 绑定。

完成后，系统的进化逻辑将完全显式化——每个角色都是可独立测试、可独立部署、可独立审计的实体。

## 角色清单与现状

| 角色 | Taxonomy | memory_authority | 现有实现 | Phase 53 工作 |
|------|----------|-----------------|---------|-------------|
| Ingestion Specialist | `specialist / staged-knowledge` | `staged-knowledge` | `run_ingestion_pipeline()` | 包装为 Agent |
| Literature Specialist | `specialist / task-memory` | `task-memory` | 无 | 从零构建 |
| Quality Reviewer | `validator / stateless` | `stateless` | 无 | 从零构建 |
| Consistency Reviewer | `validator / stateless` | `stateless` | `run_consistency_audit()` | 包装为 Agent |
| Validator | `validator / stateless` | `stateless` | `validate_run_outputs()` | 包装为 Agent |

## 目标 (Goals)

1. **3 个包装型 Agent**：将 Ingestion Specialist、Consistency Reviewer、Validator 的现有函数包装为独立 Agent 类，接入 `resolve_executor` 与 `ExecutorProtocol`。
2. **2 个新建 Agent**：为 Literature Specialist 和 Quality Reviewer 定义最小输入/输出契约并实装。
3. **消化 Phase 51 C1**：在代码注释或 taxonomy 文档中明确区分 `memory_authority`（canonical store 写入权限）与 artifact write side effect（提案/报告等文件写入）。
4. **`resolve_executor` 扩展**：5 个新 Agent 注册到 executor resolver。

## 非目标 (Non-Goals)

- **不改动 Librarian / Meta-Optimizer**：Phase 51 已稳定，不在本 phase 触碰。
- **不做 Planner 自动拆分**：Phase 52 留下的 `parallel_intent` 消费留待后续。
- **不做 Taxonomy 命名重构**：`http-claude` 等品牌名清理留待 Phase 54。
- **不引入新的 LLM 调用**：所有 Agent 的 `execute()` 基于现有函数逻辑或启发式规则，不新增 API 调用。
- **不做多租户或分布式部署**。

## Slice 拆解

### S1: 包装型 Agent（Ingestion + Consistency Reviewer + Validator）

**目标**：将 3 个有现有函数实现的角色升级为独立 Agent。

**IngestionSpecialistAgent**：
- 包装 `run_ingestion_pipeline()`（`ingestion/pipeline.py:30`）
- `system_role = "specialist"`，`memory_authority = "staged-knowledge"`
- `execute()` 接收 `card.input_context["source_path"]` 和 `card.input_context["format_hint"]`，调用 `run_ingestion_pipeline`，返回 `ExecutorResult` 含 staged candidates 摘要
- 兼容包装器 `IngestionSpecialistExecutor`

**ConsistencyReviewerAgent**：
- 包装 `run_consistency_audit()`（`consistency_audit.py:291`）
- `system_role = "validator"`，`memory_authority = "stateless"`
- `execute()` 接收 `card.input_context["task_id"]` 和 `card.input_context["auditor_route"]`，调用 `run_consistency_audit`，返回 `ExecutorResult` 含 verdict
- 不改动 `_maybe_schedule_consistency_audit` 的 fire-and-forget 路径——Agent 化提供的是显式调用入口，与自动触发路径并存
- 兼容包装器 `ConsistencyReviewerExecutor`

**ValidatorAgent**：
- 包装 `validate_run_outputs()`（`validator.py:8`）
- `system_role = "validator"`，`memory_authority = "stateless"`
- `execute()` 接收 `state` + `retrieval_items` + `card.input_context["artifact_paths"]`，调用 `validate_run_outputs`，返回 `ExecutorResult` 含 findings 摘要
- 兼容包装器 `ValidatorExecutor`

**验收条件**：
- 3 个 Agent 类均实现 `ExecutorProtocol`（`execute` + `execute_async`）
- `resolve_executor` 识别 `"ingestion-specialist"` / `"consistency-reviewer"` / `"validator"` 名称
- 单元测试覆盖 Agent 生命周期（构造、execute、taxonomy profile 验证）
- 现有 `run_ingestion_pipeline` / `run_consistency_audit` / `validate_run_outputs` 的调用方不受影响

### S2: 新建 Agent（Literature Specialist + Quality Reviewer）

**目标**：为 2 个无现有实现的角色定义最小契约并实装。

**LiteratureSpecialistAgent**：
- `system_role = "specialist"`，`memory_authority = "task-memory"`
- 职责（`AGENT_TAXONOMY.md §7.3`）：领域资料深度解析与结构化比较
- 最小输入契约：`card.input_context["document_paths"]`（待解析的文档路径列表）+ `card.goal`（解析目标）
- 最小输出契约：`ExecutorResult.output` 为结构化 markdown（文档摘要 + 关键概念提取 + 跨文档比较矩阵）
- Phase 53 实现范围：**基于文件内容的启发式摘要**（读取文档、提取标题/章节结构、生成结构化摘要），不引入 LLM 调用
- 兼容包装器 `LiteratureSpecialistExecutor`

**QualityReviewerAgent**：
- `system_role = "validator"`，`memory_authority = "stateless"`
- 职责（`AGENT_TAXONOMY.md §7.3`）：关键节点独立校验
- 最小输入契约：`card.input_context["artifact_ref"]`（待校验的 artifact 路径）+ `card.input_context["quality_criteria"]`（校验维度列表）
- 最小输出契约：`ExecutorResult.output` 为结构化 markdown（每个 criterion 的 pass/fail/warn + 总体 verdict）
- Phase 53 实现范围：**基于规则的质量检查**（artifact 存在性、非空、格式合规、关键字段完整性），不引入 LLM 调用
- 与 `validate_run_outputs` 的区别：Validator 检查 task 级 artifact 完整性，Quality Reviewer 检查单个 artifact 的内容质量
- 兼容包装器 `QualityReviewerExecutor`

**验收条件**：
- 2 个 Agent 类均实现 `ExecutorProtocol`
- `resolve_executor` 识别 `"literature-specialist"` / `"quality-reviewer"` 名称
- 单元测试覆盖输入/输出契约（正常路径 + 缺失输入 + 空文档）
- 集成测试验证与 Orchestrator 的协作（`run_task` 可触发 Literature Specialist / Quality Reviewer）

### S3: C1 消化 + `resolve_executor` 统一收口

**目标**：消化 Phase 51 C1（`memory_authority` 命名语义），统一 executor resolver 注册。

**C1 消化**：
- 在 `models.py` 的 `MEMORY_AUTHORITIES` 定义处添加文档注释，明确每个权限等级的语义边界
- 特别说明 `canonical-write-forbidden`：禁止的是 canonical knowledge store 写入，不禁止 proposal/report/artifact 等文件写入
- 在 `AGENT_TAXONOMY.md` 的 §5 Memory Authority 表格中补充"允许的 side effect"列

**`resolve_executor` 统一收口**：
- 当前 `resolve_executor` 使用 if-chain 分发，5 个新 Agent 会增加 5 个分支
- 评估是否引入注册表机制（`EXECUTOR_REGISTRY: dict[str, Callable[[], ExecutorProtocol]]`）替代 if-chain
- 如果引入注册表：每个 Agent 模块在 import 时自注册，`resolve_executor` 变为 `EXECUTOR_REGISTRY.get(name, LocalCLIExecutor)()`
- 如果保持 if-chain：按字母序排列，保持可读性

**验收条件**：
- `MEMORY_AUTHORITIES` 定义处有清晰的语义注释
- `AGENT_TAXONOMY.md §5` 补充"允许的 side effect"列
- `resolve_executor` 可解析全部 7 个 specialist/validator 名称（librarian + meta-optimizer + 5 个新增）
- 全量 pytest 通过

## 设计边界

- **Agent 是函数的包装器，不是替代品**：现有函数（`run_ingestion_pipeline` 等）继续存在，Agent 的 `execute()` 调用它们。CLI 直接调用函数的路径不变。
- **`execute_async` 统一用 `asyncio.to_thread` 包装**：与 MetaOptimizerAgent / LibrarianAgent 模式一致，不引入新的 async 原语。
- **不引入 LLM 调用**：Literature Specialist 和 Quality Reviewer 的 Phase 53 实现基于启发式规则，后续 phase 可接入 LLM 增强。
- **Validator 与 Quality Reviewer 职责正交**：Validator 检查 task 级 artifact 完整性（"文件都在吗"），Quality Reviewer 检查单个 artifact 内容质量（"内容合格吗"）。
- **Consistency Reviewer Agent 与 fire-and-forget 路径并存**：`_maybe_schedule_consistency_audit` 继续使用 `asyncio.create_task` 自动触发，Agent 提供显式的 operator 调用入口。

## 风险评估

| 风险 | 等级 | 缓解 |
|------|------|------|
| Literature Specialist 无现有实现，输入/输出契约可能不稳定 | 中 | 最小契约 + 启发式实现，后续 phase 迭代 |
| Quality Reviewer 与 Validator 职责边界模糊 | 中 | 明确正交定义 + 单元测试覆盖边界 |
| `resolve_executor` if-chain 膨胀（7+ 分支） | 低 | 评估注册表机制，或保持 if-chain + 字母序 |
| 5 个新 Agent 的 import 增加启动时间 | 低 | 延迟 import（与现有 librarian/meta-optimizer 模式一致） |
| C1 消化不彻底（文档注释不够清晰） | 低 | Review 时重点检查 |

## 验收条件（Phase 级别）

- 7 个 specialist/validator Agent 全部可通过 `resolve_executor` 解析
- 每个 Agent 有独立的单元测试文件
- `AGENT_TAXONOMY.md §7.3` 的 6 个角色全部有对应的 Agent 类
- `memory_authority` 语义在代码和文档中均有清晰说明
- 全量 pytest 通过

## 依赖与前置条件

- Phase 51 (v0.8.0)：`ExecutorProtocol`、`resolve_executor`、`TaxonomyProfile`、`MetaOptimizerAgent` / `LibrarianAgent` 参考模式
- Phase 52 (v0.9.0)：`AsyncCLIAgentExecutor`、`schedule_consistency_audit` asyncio 路径
- `AGENT_TAXONOMY.md`：6 个核心专项角色的 taxonomy 定义
