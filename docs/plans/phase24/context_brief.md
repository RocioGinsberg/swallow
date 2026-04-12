---
author: gemini
phase: 24
slice: staged-knowledge-pipeline-baseline
status: draft
depends_on: 
  - "docs/plans/phase24/design_decision.md"
  - "docs/design/AGENT_TAXONOMY_DESIGN.md"
  - "docs/design/KNOWLEDGE_AND_RAG_DESIGN.md"
---

**TL;DR**
Phase 24 将启动候选方向 B (暂存知识管道与审核流基线)。本轮致力于在系统架构中引入 `Staged Knowledge` (暂存知识) 的概念与底层结构，防止执行实体越权直接将临时发现或未经验证的经验写入全局规范知识库 (Canonical Registry)。

### 任务概述 (Task Overview)
在 `AGENT_TAXONOMY_DESIGN.md` 中，我们明确规定了多数 Agent 的权限被限制为 `Staged-Knowledge` 或 `Canonical-Write-Forbidden`。然而，当前代码中缺乏配套的“中间态/暂存态知识容器”。Phase 24 的核心任务是建立一条显式的知识管道：使受限实体只能生成 `Staged Knowledge Candidate` (候选草稿)，而不是直接污染 Canonical Registry，为后续的人类或高级 Validator 提供一个明确的审查队列。

### 变更范围 (Scope)
- **Primary Track**: `Retrieval / Memory`（知识的生命周期与复用隔离）
- **Secondary Track**: `Workbench / UX`（操作员面对暂存知识的可见性与审批介入点基线）
- **核心关注点**:
  - 数据模型：新增 `StagedKnowledge` 或 `KnowledgeCandidate` Schema。
  - 存储层：在隔离的目录或存储区域存放 Staged Knowledge（如 `.swallow/knowledge/staged/`）。
  - 执行约束：确保 Harness 或 Capability 在执行知识写入时，对被标记为 `Canonical-Write-Forbidden` 的实体强制路由至 Staged 存储，而非 Canonical。
  - 审查基线：搭建极简的 `swl knowledge stage-list`（列出待审列表）和基础的晋升/拒绝语义占位。

### 相关设计文档 (Related Design Docs)
- `docs/design/AGENT_TAXONOMY_DESIGN.md`
  - **约束**：强制区分 `Staged-Knowledge` 与 `Canonical Promotion Authority`。
- `docs/design/KNOWLEDGE_AND_RAG_DESIGN.md`
  - **约束**：知识不能是隐式的，必须是显式的 Artifact。并且进入 Canonical 前必须经过显式的 Review Gate。

### 近期变更摘要 (Recent Commits & State)
- Phase 22 & 23 已在路由和控制台完成 Taxonomy 的流转和可见性。系统现在已经明确知道谁具有 `Canonical Promotion Authority`，谁只具有 `Staged-Knowledge` 权限。
- Human Operator 已确认选择方向 B 作为 Phase 24 的切入点。

### 关键上下文 (Key Context)
- **为什么重要**：如果缺乏这一层，大模型产生的具有幻觉的长期记忆（如错误的架构理解、过时的修复步骤）将会悄无声息地污染整个系统的基准事实，导致后续所有 Retrieval 严重偏航。
- **与 Canonical Registry 的关系**：Staged Knowledge 就像是 PR (Pull Request)，而 Canonical Registry 是 `main` 分支。本阶段重点是建立 PR 的提交机制和列表。

### 风险信号 (Risk Signals)
- **过度设计 UI 流**：本轮不要去实现带有复杂 Diff 对比或高阶语意冲突检测的审核流界面。保持 CLI CLI 操作（如列出、查看原始内容、简单 Promote/Reject 命令）的清爽基线。
- **过早自动晋升**：在当前基线中，不要实现基于 LLM Validator 的“自动晋升”。保持手动 Operator Gate 为核心防线。