---
author: gemini
status: living-document
---

# 蓝图差距与演进路线图 (Gap Analysis & Roadmap)

## 一、当前实现与蓝图设计的核心差距 (Gap Analysis)

根据最新收口的 Phase 49 (v0.7.0) 成果，系统已完成全异步化改造、SQLite 任务真值层与知识层 SQLite SSOT 落地。通过对全量设计蓝图（Track 1-7）的深度审计，当前系统正从”真值归一”转入**策略闭环与 Specialist Agent 体系落地**阶段。

### 1. [已消化] 知识真值的”双重真相”风险 (SSOT Consistency)
*   **蓝图要求**：`STATE_AND_TRUTH_DESIGN` 要求单一事实源 (SSOT)，拒绝线性历史依赖。
*   **当前现状**：Phase 49 已将 Evidence / Wiki 知识读取切换为 SQLite primary，文件系统仅保留 mirror / export / fallback 视图。
*   **消化结果**：知识层事务性真值闭环已在 `v0.7.0` 落地，后续不应再回退为文件系统主读。

### 2. [已消化] Specialist Agent 的缺位与提案应用流程不完整 (Specialist Agent Lifecycle & Proposal Consumption)
*   **蓝图要求**：`AGENT_TAXONOMY_DESIGN` 定义了 6 个专项角色（Librarian、Meta-Optimizer、Ingestion Specialist、Literature Specialist、Quality Reviewer、Consistency Reviewer），应具备边界清晰的职责与独立生命周期。`SELF_EVOLUTION_AND_MEMORY` 要求系统能够通过”自我观察 → 提案生成 → operator 审批 → 自动应用”的完整闭环实现自我进化。
*   **当前现状**：Librarian 已落地为独立 Agent；Meta-Optimizer 已落地为只读分析入口，可产出提案；但其他 5 个专项角色仍为函数化，且提案应用流程（operator review → apply）尚未完整。
*   **核心差距**：知识沉淀和策略自省仍属于”函数的副作用”，而非”显式的工作流”；遥测数据处于”已捕获但未消费”状态，浪费了宝贵的反馈信号。
*   **消化计划**：Phase 50 应完成 Meta-Optimizer 提案应用流程与独立 Agent 生命周期；Phase 52 应完成其他 5 个专项角色的落地。

### 3. [已消化] 执行能力的不完整性 (Execution Capability Gaps)
*   **蓝图要求**：`ORCHESTRATION.md` 定义了高并发多路子任务编排与复杂拓扑的能力。
*   **当前现状**：CLIAgentExecutor 等残留同步桥接层，并发控制不完整。
*   **消化结果**：Phase 52 已落地 `AsyncCLIAgentExecutor` 统一 async 入口、`complexity_hint` 路由偏置、fan-out timeout 守卫与 `subtask_summary.md` 收口。Runtime v0 仍通过 harness bridge 接入同步执行链（原生 async subprocess 留待 Runtime v1）。

### 4. [低优先级] Taxonomy 命名的品牌残留 (Taxonomy Naming)
*   **蓝图要求**：推荐命名格式 `[role]/[site]/[authority]/[domain]`，品牌名仅作 implementation binding。
*   **当前现状**：内部模型清晰，但 CLI/API 仍有品牌名残留（如 `http-claude`）。
*   **消化计划**：Phase 53 应完成命名重构与品牌清理。

---

## 二、已消化差距 (Digested Gaps)

### [Phase 49] 知识真值归一与向量 RAG (v0.7.0)
*   **解决方式**：落地知识层 SQLite SSOT、`swl knowledge migrate`、`LibrarianAgent` 与 `sqlite-vec` 可退级检索。
*   **成果**：系统进入 **Knowledge Era**，消除了知识层”双重真相”风险，并形成本地语义检索基线。

### [Phase 48] 存储引擎升级与全异步改造 (v0.6.0)
*   **解决方式**：落地 `SqliteTaskStore` 与全链路 `async/await`，实装 `swl migrate` 过渡入口。
*   **成果**：系统进入 **Async Era**，消除了高并发子任务的 IO 阻塞瓶颈。

### [Phase 47] 多模型共识与策略护栏 (v0.5.0)
*   **解决方式**：实装 N-Reviewer 共识门禁与 TaskCard 级成本护栏。
*   **成果**：系统进入 **Consensus Era**，具备了自我纠偏与财务自律能力。

### [Phase 51] 策略闭环与 Specialist Agent 落地 (v0.8.0)
*   **解决方式**：实装 S1 提案 review/apply 工作流（operator gate、持久化、rollback 快照）、S2 `MetaOptimizerAgent` 独立生命周期（`execute` / `execute_async`、`MetaOptimizerSnapshot`）、S3 route 能力画像与 task-family guard、S4 遥测驱动的 capability 提案生成与应用闭环。
*   **成果**：系统进入 **Policy Era**，实现”自我观察 → 提案生成 → operator 审批 → 自动应用”的完整闭环。Specialist Agent 体系初步成型，为后续 Ingestion/Literature/Quality Reviewer 等角色落地奠定基础。已合并到 main（commit `4b0de67`），review 结论 `approved_with_concerns`，2 个 CONCERN 已登记到 `docs/concerns_backlog.md`，tag `v0.8.0`。

### [Phase 52] 平台级多路并行与复杂拓扑 (v0.9.0)
*   **解决方式**：S1 `AsyncCLIAgentExecutor` 统一 async 入口（Aider / Claude Code 复用同一执行路径，Runtime v0 通过 harness bridge 接入）、codex/cline 主命名收口（默认路径切到 `aider` / `local-aider`）、`schedule_consistency_audit` 改为 `asyncio.create_task` 路径；S2 `TaskSemantics.complexity_hint` 贯通路由偏置，`parallel_intent` 进入 `RouteSelection.policy_inputs`；S3 `AsyncSubtaskOrchestrator` 补齐 subtask timeout、局部失败隔离、`AIWF_MAX_SUBTASK_WORKERS` 与 `subtask_summary.md`；post-implementation validation 吸收 `meta_optimizer` cost trend 顺序修正与 legacy route alias 兼容（`local-codex → local-aider`、`local-cline → local-claude-code`）。
*   **成果**：系统进入 **Parallel Era**，高并发多路编排能力落地。437 tests passed，review 结论 `approved_with_concerns`，2 个 CONCERN（harness 桥接为 Runtime v0 架构约束、codex 品牌残留留待 Phase 53/54 清理）已登记到 `docs/concerns_backlog.md`，tag `v0.9.0`。

---

## 三、架构演进 Roadmap (Phases 49-51)

### Phase 49: 知识真值归一与向量 RAG (Knowledge SSOT & Vector RAG) ✅ [Done]
*   **Primary Track**: Knowledge / RAG
*   **Secondary Track**: State / Truth
*   **目标**：彻底消除知识层的“双重真相”，实装本地向量检索。
*   **核心任务**：
    - **知识层 SSOT 归一**：将 `Evidence Store` / `Wiki Store` 全量迁移至 SQLite。废除文件系统作为真值的逻辑，仅将其保留为可导出的“视图”。
    - **图书管理员 (Librarian Agent) 实装**：落地首个专项智能体实体。由其接管知识的冲突检测、去重与 SQLite 写入边界。
    - **向量化 RAG 与平滑退级**：集成 `sqlite-vec` 提供本地向量能力。强制要求具备“向量 -> 文本模糊匹配”的自动降级机制，确保环境鲁棒性。
*   **产出价值**：终结碎片化存储，实现具备语义维度的高质量知识闭环。

### [Phase 50 已完成] 路由策略闭环与专项审计 (Policy Closure & Specialist Audit) ✅ [Done]
*   **Primary Track**: Evaluation / Policy
*   **Secondary Track**: Provider Routing
*   **目标**：将现有的孤立审计与遥测能力连接成可感知的策略闭环。
*   **核心任务**：
    - **S1: Meta-Optimizer 结构化提案**：将 `build_optimization_proposals()` 的输出从纯文本升级为结构化 `OptimizationProposal` dataclass，并补充 workflow 类提案。
    - **S2: 一致性审计自动触发策略**：在 harness 执行完成后，根据可配置 `AuditTriggerPolicy` 决定是否自动触发一致性审计（fire-and-forget）。
    - **S3: 路由质量权重**：RouteRegistry 支持 per-route 质量权重，Meta-Optimizer 提案可建议权重调整，operator 通过 CLI 应用。
*   **产出价值**：系统从”孤立的遥测记录”进化到”可感知的策略行为”，实现审计、提案、权重调整的单向数据流闭环。
*   **成果**：406 tests passed，0 BLOCK / 2 CONCERN（可接受），已合并到 main（commit `434a56c`）。

### Phase 51: 策略闭环与 Specialist Agent 落地 (Policy Closure & Specialist Agent Lifecycle) ✅ [Done] — tag v0.8.0
*   **Primary Track**: Evaluation / Policy + Agent Taxonomy
*   **Secondary Track**: Provider Routing
*   **目标**：完成”自我观察 → 提案生成 → operator 审批 → 自动应用”的完整闭环，落地 Meta-Optimizer 作为独立 Specialist Agent。
*   **核心任务**：
    - **S1: Meta-Optimizer 提案应用流程**（Primary）：设计与实装 operator review → apply 的完整工作流。包括提案持久化、operator gate、应用审计、回滚机制。
    - **S2: Meta-Optimizer 独立 Agent 生命周期**（Primary）：落地 Meta-Optimizer 作为独立 Specialist Agent（类似 Librarian）。定义其输入/输出边界、权限模型、与 Orchestrator 的协作接口。
    - **S3: 一致性审计自动化触发**（Primary）：将只读的一致性抽检升级为可配置的自动化触发策略。支持基于 task 特征、route 质量、成本等维度的触发规则。
    - **S4: Route 能力画像扩展**（Secondary）：实装能力画像评分机制与 unsupported_task_types 字段。支持路由决策时的能力边界守卫。
*   **产出价值**：系统从”有感遥测”进化到”主动优化”，实现架构级的自我迭代闭环。Specialist Agent 体系初步成型，为后续 Ingestion/Literature/Quality Reviewer 等角色落地奠定基础。
*   **风险等级**：中（涉及新的 operator gate 流程与 Agent 生命周期管理，需要充分测试）
*   **依赖**：Phase 50 的结构化提案与自动触发基础设施

### Phase 52: 平台级多路并行与复杂拓扑 (Advanced Parallel Topologies) ✅ [Done] — tag v0.9.0
*   **Primary Track**: Core Loop
*   **Secondary Track**: Execution Topology
*   **目标**：利用 Async & SQLite 底座，解锁蓝图中的高并发多路子任务编排。
*   **核心任务**：
    - **S1: 全异步执行器升级**：将 `CLIAgentExecutor` 等残留的同步桥接层彻底改为原生 async subprocess。
    - **S2: 多路 Subtask 并行压测**：实装跨任务/跨模型的并行提取与对比拓扑，处理资源争抢与死锁保护。
*   **产出价值**：实现蓝图定义的”长周期、高并发”任务树处理能力。
*   **风险等级**：中高（涉及执行器架构改造与并发控制）
*   **依赖**：Phase 51 的 Specialist Agent 体系稳定

### Phase 53: 其他 Specialist Agent 落地 (Specialist Agent Ecosystem) 🚀 [Next]
*   **Primary Track**: Agent Taxonomy
*   **Secondary Track**: Knowledge / Self-Evolution
*   **目标**：完成 AGENT_TAXONOMY 中定义的 5 个专项角色的落地（Ingestion Specialist、Literature Specialist、Quality Reviewer、Consistency Reviewer、Validator）。
*   **核心任务**：
    - **S1: Ingestion Specialist 独立生命周期**：将外部会话摄入逻辑从函数化升级为独立 Agent。支持规则式过滤、质量评分、自动分类。
    - **S2: Literature Specialist 独立生命周期**：将知识文献管理逻辑升级为独立 Agent。支持文献去重、版本管理、引用追踪。
    - **S3: Quality Reviewer 与 Consistency Reviewer 独立生命周期**：将质量评审与一致性检查升级为独立 Agent。支持多维度评分、自动化审查、反馈生成。
*   **产出价值**：完成 Specialist Agent 体系的全面落地，系统进化逻辑完全显式化、工作流化。
*   **风险等级**：中（基于 Phase 51 的 Agent 生命周期模式，复用度高）
*   **依赖**：Phase 51 的 Specialist Agent 基础设施

### Phase 54: Taxonomy 命名与品牌残留清理 (Taxonomy Naming & Brand Cleanup)
*   **Primary Track**: Agent Taxonomy
*   **Secondary Track**: Provider Routing
*   **目标**：完成 `[role]/[site]/[authority]/[domain]` 命名格式的全面推行，清理 CLI/API 中的品牌名残留。
*   **核心任务**：
    - **S1: CLI 命名重构**：将 `http-claude`、`local-cline` 等品牌名改为 `http-executor/cloud-backed/...` 的完整形式。保持向后兼容性。
    - **S2: API 命名重构**：更新 Route Registry、Executor Registry 等内部 API 的命名。
    - **S3: 文档与示例更新**：更新所有文档、示例、测试中的命名引用。
*   **产出价值**：系统命名体系完全对齐蓝图，提升长期可维护性与扩展性。
*   **风险等级**：低（纯重构，无功能变化）
*   **依赖**：Phase 51-53 的 Specialist Agent 体系稳定

---

## 四、推荐 Phase 队列与风险批注 (Claude 维护)

> 最近更新：2026-04-23 (Phase 52 已完成，tag v0.9.0，Phase 53 为下一阶段)

### 队列总览

| 优先级 | Phase | 名称 | Primary Track | Secondary Track | 风险等级 | 备注 |
|--------|-------|------|---------------|-----------------|----------|------|
| ~~1~~ | ~~48~~ | ~~存储引擎升级与全异步改造~~ | ~~Core Loop~~ | ~~State / Truth~~ | ~~已完成~~ | tag `v0.6.0` |
| ~~2~~ | ~~49~~ | ~~知识真值归一与向量 RAG~~ | ~~Knowledge / RAG~~ | ~~State / Truth~~ | ~~已完成~~ | tag `v0.7.0` |
| ~~3~~ | ~~50~~ | ~~路由策略闭环与专项审计~~ | ~~Evaluation / Policy~~ | ~~Provider Routing~~ | ~~已完成~~ | tag `v0.7.0+`，406 tests passed |
| ~~4~~ | ~~51~~ | ~~策略闭环与 Specialist Agent 落地~~ | ~~Evaluation / Policy + Agent Taxonomy~~ | ~~Provider Routing~~ | ~~已完成~~ | tag `v0.8.0`，commit `4b0de67`，approved_with_concerns |
| ~~5~~ | ~~52~~ | ~~平台级多路并行与复杂拓扑~~ | ~~Core Loop~~ | ~~Execution Topology~~ | ~~已完成~~ | tag `v0.9.0`，437 tests passed，approved_with_concerns |
| **6** | **53** | **其他 Specialist Agent 落地** | **Agent Taxonomy** | **Knowledge / Self-Evolution** | **中** | 完成 5 个专项角色的独立生命周期 |
| **7** | **54** | **Taxonomy 命名与品牌残留清理** | **Agent Taxonomy** | **Provider Routing** | **低** | 纯重构，无功能变化 |

### 全局锚点分析 (Claude 维护)

| 维度 | 参考源 | 蓝图愿景 | 当前差距 | Phase 消化计划 | 风险预警 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **系统级锚点** | `ARCHITECTURE.md` | 基于状态的异步协同，SSOT 事实层，自我优化闭环 | 遥测与审计结果已进入可感知策略行为（Phase 50），但缺少”提案应用”与”独立 Agent”的完整闭环 | **Phase 51**: 完成提案应用流程与 operator gate，落地 Meta-Optimizer 独立 Agent | **[中高]** 若不完成 Phase 51，系统仍停留在”有感遥测”阶段，无法进入”主动优化” |
| **领域级卫星** | `AGENT_TAXONOMY` | 显式的角色认知分工，6 个专项角色独立生命周期 | Librarian 已落地，Meta-Optimizer 仍为函数化，其他 4 个仍缺失 | **Phase 51**: 落地 Meta-Optimizer 独立 Agent；**Phase 53**: 落地其他 5 个专项角色 | 通用 Agent 上下文压力降低有限，策略建议仍缺少明确 agent 边界 |
| **跨界嗅探** | `SELF_EVOLUTION` | 记忆沉淀作为显式工作流，Proposal over Mutation 原则 | 遥测数据已被消费为提案（Phase 50），但提案应用流程缺失 | **Phase 51**: 实装提案应用流程与 operator gate | 浪费了宝贵的反馈信号，导致路由和策略演进滞后于业务实际 |
| **执行能力** | `ORCHESTRATION.md` | 高并发多路子任务编排与复杂拓扑 | CLIAgentExecutor 等残留同步桥接层，并发控制不完整 | **Phase 52**: 全异步执行器升级与多路并行压测 | 高并发场景下可能出现资源争抢与死锁 |
| **命名体系** | `AGENT_TAXONOMY` | `[role]/[site]/[authority]/[domain]` 格式，品牌名仅作 implementation binding | CLI/API 仍有品牌名残留（如 `http-claude`） | **Phase 54**: 完成命名重构与品牌清理 | 低优先级，不影响功能，但影响长期可维护性 |

### 核心差距消化路线

**战略级差距（Phase 51 必须完成）**：
1. Meta-Optimizer 提案应用流程（operator review → apply）
2. Meta-Optimizer 独立 Agent 生命周期
3. 一致性审计自动化触发策略的完整工作流

**中期差距（Phase 52-53 推进）**：
1. 全异步执行器升级与多路并行编排（Phase 52）
2. 其他 5 个 Specialist Agent 落地（Phase 53）

**低优先级差距（Phase 54 推进）**：
1. Taxonomy 命名与品牌残留清理（Phase 54）

### Tag 评估

- **Phase 49** → `v0.7.0` (Knowledge Era)：知识真值归一与向量检索能力的正式闭环
- **Phase 50** → `v0.7.0+` (Policy Closure)：策略闭环初步成型，孤立能力连接成可感知行为
- **Phase 51** → `v0.8.0` (Policy Era)：策略闭环与 Specialist Agent 体系初步成型（commit `4b0de67`，approved_with_concerns，2 CONCERN 登记至 concerns_backlog.md）
- **Phase 52** → `v0.9.0` (Parallel Era)：高并发多路编排能力落地（approved_with_concerns，2 CONCERN 登记至 concerns_backlog.md）
- **Phase 53** → `v1.0.0` (Specialist Era)：Specialist Agent 体系完全落地，系统进化逻辑完全显式化（待 closeout 后确认）
