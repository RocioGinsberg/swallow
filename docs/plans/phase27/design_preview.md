---
author: gemini
phase: 27
slice: fresh_kickoff_required
status: draft
depends_on: [docs/plans/phase26/closeout.md, docs/system_tracks.md, ARCHITECTURE.md]
---

## TL;DR
Phase 27 建议聚焦于 **Knowledge-Driven Task Grounding**。在 Phase 26 解决了记忆“存得干净”的问题后，本阶段旨在解决“用得精准”的问题，建立长期记忆对新任务的引导闭环。

---

## 一、基建现状盘点
- **Registry 健康化**：Phase 26 引入了 `canonical-audit` 和 `supersede` 语义，解决了重复键和孤立记录问题。
- **Pipeline 完整性**：Staged Knowledge Pipeline 已覆盖了从输入到晋升的路径，但缺乏自动化的“召回与复用”触发机制。
- **CLI 表层**：具备基础管理命令，但缺乏面向任务执行过程中的“知识复用审查”入口。

## 二、 现状与蓝图差距分析 (Reality vs. Blueprint)

按照“多层锚点分析”模式，对比当前实现与系统各级蓝图的差距：

| 维度 | 参考源 | 蓝图愿景 | 当前现状 | 核心差距 | 局部最优风险预警 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **系统级 (Bedrock)** | `ARCHITECTURE.md` | **Orchestrator 保持愚蠢**：调度层只决定时机，执行层负责认知。 | Retrieval 逻辑目前高度耦合在特定执行路径中，未形成标准 Service。 | 缺乏统一的“认知交接”协议，知识注入路径散乱。 | **[高风险]** 若直接将知识硬编码进 Prompt，会破坏 Orchestrator 与 Harness 的边界。 |
| **状态级 (Truth)** | `STATE_AND_TRUTH_DESIGN.md` | **单一事实源**：任务依赖外部可验证存储，而非模型对话历史。 | 召回的知识目前以“隐式上下文”存在，未进入 `context_refs` 或 `Artifacts`。 | 召回的证据链不具备持久化地位，一旦任务重启，召回结果可能由于随机性而漂移。 | **[高风险]** 导致任务恢复（Resume）后的 Grounding 基础不一致，产生不可预测的行为。 |
| **领域级 (Domain)** | `KNOWLEDGE_AND_RAG_DESIGN.md` | **Agentic RAG**：Agent 根据意图自主选择检索工具及多跳推理。 | **Manual / Key-based**：仅支持基于任务 ID 或 Key 的平面匹配。 | 缺乏“意图驱动”的召回决策，无法处理跨领域的复杂知识关联。 | **[低风险]** 本阶段可先做 Key-based 闭环，但需预留 Agentic 决策位。 |

**Phase 27 的架构修正重点**：必须将“召回的知识”实体化为 **Grounding Artifact**，并将其引用登记到任务状态的 `context_refs` 中，以满足 `ARCHITECTURE.md` 的可溯源与可恢复要求。

## 三、候选方向评估

### 方向 1：Knowledge-Driven Task Grounding Baseline (推荐)
- **设计目标**：在任务的 Retrieval 阶段，自动识别并加载关联的 Canonical 知识，作为 Task Grounding 的核心上下文。
- **核心逻辑**：`Identify Intent -> Recall from Registry -> Generate Grounding Artifact -> Inject with Citations`.
- **Track**：Primary: Track 2 (Retrieval / Memory), Secondary: Track 5 (Workbench)
- **优势 (Pros)**：
    - 直接兑现 Phase 26 价值；建立“证据链”闭环。
- **劣势 (Cons)**：
    - 需要处理召回噪声。

### 方向 2：Enhanced Recovery & State Resumption (可选)
- **设计目标**：强化 Orchestrator 对异常中断后的状态恢复语义。
- **Track**：Track 1 (Core Loop)
- **优势 (Pros)**：提升鲁棒性。
- **劣势 (Cons)**：边际收益略低于方向 1。

## 三、推荐结论
**建议启动 Phase 27: Knowledge-Driven Task Grounding Baseline**。

### 核心目标 (Primary Track 2)
1. **实现 Retrieval-Memory 对齐**：在 `retrieval` 逻辑中注入对 Canonical Registry 的自动查询。
2. **实体化 Grounding Evidence**：将召回的长期知识写为 `grounding_report` Artifact，并进入任务 `context_refs`。
3. **Operator 复用审查 (Secondary Track 5)**：在任务执行前，展示“已召回的背景知识”，允许 Operator 剔除错误项。

### 非目标 (Non-goals)
- 不涉及语义向量搜索。
- 不涉及跨机器知识同步。

---

## 四、Human Operator 决策请求

请问是否选择 **方向 1 (Knowledge-Driven Task Grounding)** 作为 Phase 27 的启动方向？

- **Yes**：我将起草 `docs/plans/phase27/context_brief.md`。
- **Other**：请指出您希望优先推进的其他 Track 或特定需求。
