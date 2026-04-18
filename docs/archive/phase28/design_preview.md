---
author: gemini
phase: 28
slice: fresh_kickoff_required
status: draft
depends_on: [docs/plans/phase27/closeout.md, docs/system_tracks.md, ARCHITECTURE.md]
---

## TL;DR
Phase 28 建议聚焦于 **Knowledge Promotion & Refinement Baseline**。在 Phase 27 实现了知识的“召回与锁定”后，本阶段旨在打通知识从“暂存 (Staged)”到“权威 (Canonical)”的晋升路径，实现系统认知的持续增长与闭环。

---

## 一、基建现状盘点
- **Grounding 闭环**：Phase 27 实现了从 Canonical Registry 召回知识并锁定到 Task State 的流程。
- **Staged 积累**：Phase 24 建立了 Staged Knowledge Pipeline，但目前暂存的知识处于“只进不出”的状态。
- **Registry 审计**：Phase 26 提供了元数据去重和 Supersede 语义，为知识晋升提供了格式保障。
- **缺失环节**：缺乏从 `staged_knowledge` 到 `canonical_registry` 的显式晋升触发机制和 Operator 审查界面。

## 二、 现状与蓝图差距分析 (Reality vs. Blueprint)

按照“多层锚点分析”模式，对比当前实现与系统各级蓝图的差距：

| 维度 | 参考源 | 蓝图愿景 | 当前现状 | 核心差距 | 局部最优风险预警 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **系统级 (Bedrock)** | `ARCHITECTURE.md` | **自我进化 (Self-Evolution)**：执行轨迹转化为结构化图谱资产。 | 知识沉淀停留在 Staged 阶段，未进入全局 Canonical 记忆。 | 缺乏“记忆沉淀 (Consolidation)”阶段的系统化实现。 | **[高风险]** 若长期依赖人工手动编辑 JSON 晋升，会导致 Canonical 记忆枯竭，系统失去进化动力。 |
| **领域级 (Domain)** | `KNOWLEDGE_AND_RAG_DESIGN.md` | **Graph RAG & 混合图谱**：知识需具备明确的实体关系和引用链。 | 知识对象缺乏跨任务的关联审计。 | 晋升过程尚未包含“知识精炼 (Refinement)”和“去重合并”的高级策略。 | **[中风险]** 直接晋升原始 Staged 数据可能引入噪声，破坏 Canonical 记忆的信噪比。 |
| **状态级 (Truth)** | `STATE_AND_TRUTH_DESIGN.md` | **单一事实源**：Canonical 记录必须具备完整的溯源 (Traceability) 和决策依据。 | Staged 记录虽然有 `source_task_id`，但晋升后的决策证据链尚不稳固。 | 需要在 Registry 中显式链接晋升时的 `decision_note`。 | **[低风险]** 现有的 `canonical_registry.py` 已有初步字段，需在实现层对齐。 |

**Phase 28 的架构修正重点**：建立 **"Review-to-Promote"** 机制，确保只有经过验证和精炼的知识才能进入系统长期记忆，维持记忆的权威性。

## 三、候选方向评估

### 方向 1：Knowledge Promotion & Refinement Baseline (推荐)
- **设计目标**：实现 `task staged` 和 `task promote` 命令，提供知识从暂存到晋升的完整 Operator 工作流。
- **核心逻辑**：`List Staged -> Review & Edit -> Approve/Reject -> Append to Canonical -> Mark Staged as Promoted`.
- **Track**：Primary: Track 2 (Retrieval / Memory), Secondary: Track 5 (Workbench)
*   **优势 (Pros)**：
    - 直接解决知识流转瓶颈，实现“学习闭环”。
    - 低实现复杂度，高架构价值。
- **劣势 (Cons)**：
    - 依然依赖人工审查，尚未进入全自动模式。

### 方向 2：Provider Dialect & Negotiation (Layer 6)
- **设计目标**：在路由层引入 Dialect 翻译（如 Claude XML），实现 Layer 6 的蓝图愿景。
- **Track**：Primary: Track 3 (Execution Topology), Secondary: Track 6 (Eval/Policy)
- **优势 (Pros)**：提升模型原生性能，减少 Orchestrator 耦合。
- **劣势 (Cons)**：与当前“知识闭环”的业务优先级相比，紧迫性稍低。

### 方向 3：Initial Agentic RAG Exploration
- **设计目标**：实验性引入执行中（Mid-flight）检索工具。
- **Track**：Primary: Track 2 (Retrieval / Memory), Secondary: Track 1 (Core Loop)
- **优势 (Pros)**：迈向动态认知。
- **劣势 (Cons)**：风险较高，需要更稳固的 Grounding 基础（已由 Phase 27 提供，但 Promotion 不足会限制其效果）。

## 三、推荐结论
**建议启动 Phase 28: Knowledge Promotion & Refinement Baseline**。

### 核心目标 (Primary Track 2)
1. **实现晋升工作流**：建立 `task promote <id>` 逻辑，将 `StagedCandidate` 转化为 `CanonicalRecord` 并持久化。
2. **知识精炼 (Refinement)**：允许在晋升时对 `text` 进行微调或摘要提取。
3. **Operator 控制面 (Secondary Track 5)**：提供 `task staged` 命令用于浏览、过滤和审查暂存知识。
4. **去重与 Supersede 增强**：利用 Phase 26 的审计能力，在晋升时自动检查冲突并提示 Supersede。

### 非目标 (Non-goals)
- 不涉及全自动 AI 晋升决策。
- 不涉及语义向量去重。

---

## 四、Human Operator 决策请求

请问是否选择 **方向 1 (Knowledge Promotion & Refinement)** 作为 Phase 28 的启动方向？

- **Yes**：我将起草 `docs/plans/phase28/context_brief.md`。
- **Other**：请指出您希望优先推进的其他 Track 或特定需求。
