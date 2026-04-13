---
author: gemini
phase: 27
slice: kickoff
status: draft
depends_on: [docs/plans/phase27/design_preview.md, ARCHITECTURE.md, docs/design/KNOWLEDGE_AND_RAG_DESIGN.md]
---

## TL;DR
Phase 27 旨在打通长期记忆的复用闭环。通过在检索阶段自动召回 Canonical 知识并实体化为 Grounding Artifact，使系统具备基于历史沉淀进行自我对齐的能力。

---

## 一、任务概述
1. **记忆感知召回**：在任务 `retrieval` 阶段注入对 `CanonicalRegistry` 的自动查询逻辑。
2. **证据链实体化**：将召回的知识写入 `grounding_report` Artifact，并将其引用登记到任务状态的 `context_refs` 中。
3. **闭环验证**：确保召回的知识能被后续 Agent 显式识别为“权威证据”而非临时推测。

## 二、变更范围
- `src/swallow/retrieval.py`: 核心变更点。需增加对 `CanonicalRegistry` 的召回逻辑。
- `src/swallow/orchestrator.py`: 需在 `retrieval` 步骤后处理 `Grounding Artifact` 的挂载与状态更新。
- `src/swallow/models.py`: 可能需要定义 `GroundingArtifactSchema` 或更新 `TaskState`。
- `src/swallow/canonical_registry.py`: 需提供高效的 Key-based 召回接口。

## 三、相关设计文档
- **`ARCHITECTURE.md`**: 约束召回结果必须作为“单一事实源”持久化，严禁隐式注入 Prompt。
- **`docs/design/KNOWLEDGE_AND_RAG_DESIGN.md`**: 规定了 Grounding 必须附带 Citation（来源标识）。
- **`docs/design/STATE_AND_TRUTH_DESIGN.md`**: 要求所有影响决策的外部知识必须进入 `context_refs`。

## 四、近期变更摘要
- `d8ce78f`: 修正了 staged promote 的 canonical key 生成逻辑，实现与 supersede 语义对齐。
- `6923976`: 建立了 staged knowledge registry 基础。
- `058d9a0`: 引入了 canonical reuse policy 概念，为本阶段提供了策略预留。
- `eafea29`: 实现了 Canonical Registry 的持久化存储层。

## 五、关键上下文
- **避免“盲目注入”**：召回的知识可能过载。实现时应优先考虑“高信噪比”策略，只召回与当前 Task ID 或核心元数据强相关的条目。
- **Resume 稳定性**：由于模型调用存在随机性，必须在第一次召回后锁定结果并存入 Artifact，确保任务在 `swl run --resume` 时不会因为召回内容变化而导致逻辑漂移。

## 六、风险信号
- **[一致性风险]**：如果 `CanonicalRegistry` 尚未收口（例如仍有重复 Key），召回可能返回冲突信息。需依赖 Phase 26 的 `canonical-audit` 命令进行前置健康检查。
- **[边界风险]**：不要在本阶段引入向量检索（Vector Search），应严格遵守设计预览中的 Non-goals，保持 Key-based 匹配。
