---
author: gemini
status: living-document
---

# 蓝图差距与演进路线图 (Gap Analysis & Roadmap)

## 一、当前实现与蓝图设计的核心差距 (Gap Analysis)

根据最新修订的 `ARCHITECTURE.md` 与 `docs/deploy.md`，Swallow 系统已进入 **V0.2.0** 阶段，确立了本地优先的任务编排与对抗审查基线（Phase 40 已完成）。然而，随着部署拓扑向“本地工作站全栈化”调整，系统仍存在以下关键差距：

### 1. 本地栈集成与真实成本感知 (Local Stack & Real Cost)
*   **蓝图要求**：系统应深度整合本地 Docker 运行的 `new-api` 与 `TensorZero`，利用真实的物理遥测数据进行路由优化，而非依赖静态估算。
*   **当前现状**：`swl doctor` 尚未覆盖本地容器栈健康检查；`Meta-Optimizer` 的 `token_cost` 仍基于硬编码单价估算。
*   **核心差距**：系统无法在本地多模型竞争环境下，根据真实的账单反馈自动选择最高性价比的路径。

### 2. 知识晋升的事务性与副作用控制 (Librarian Side-Effects)
*   **蓝图要求**：Librarian 执行路径应严格遵循“无副作用执行”，所有状态变更由 Orchestrator 统一事务化持久化，确保索引与数据不脱节（见 `docs/concerns_backlog.md`）。
*   **当前现状**：`LibrarianExecutor` 内部仍存在零散的 `save_state` 操作；知识索引更新缺乏 Checkpoint 保护。
*   **核心差距**：在并发或中断场景下，系统面临知识库索引崩溃或状态不一致的风险。

### 3. 高并发下的立体操作体验 (Workbench UX)
*   **蓝图要求**：随着并行子任务（Phase 33）与对抗循环（Phase 40）的引入，系统需要可视化手段展示复杂的任务树与 Artifact 对比审阅区。
*   **当前现状**：用户仍受限于线性 CLI 终端，在审阅多个并行子任务的生成物时面临严重的认知过载。
*   **核心差距**：缺乏一个基于本地 `.swl/` 数据源的只读 Web 控制台，导致人类在 Loop 中的监督效率低下。

### 4. 从单体审查向多机/多 Agent 共识演进 (Consensus Topology)
*   **蓝图要求**：支持多 Reviewer 对话拓扑，通过多模型共识（Majority Pass）确保输出质量。
*   **当前现状**：目前的 `ReviewGate` 仅支持单 Reviewer 模式；方言层对不支持 Tool Calling 的模型缺乏鲁棒的 ReAct 降级支持。
*   **核心差距**：系统对核心设计文档或代码的质量担保仍依赖单一模型的判断，缺乏冗余校验。

---

## 二、架构演进 Roadmap (Phases 41-46)

为弥补上述差距，推荐按以下 6 个 Phase 稳步演进：

### Phase 41: Librarian 收口与结构化清理 (Librarian Consolidation)
*   **Primary Track**: Core Loop
*   **Secondary Track**: Retrieval / Memory
*   **目标**：消化积压技术债（C36/C40），确保内核路径的原子性。
*   **核心任务**：
    - **Librarian Side-Effect 收口**：重构 `LibrarianExecutor` 使其仅返回结构化 Payload，由 `Orchestrator` 接管全部持久化逻辑。
    - **辩论逻辑去重**：提取共享的 `_debate_loop_core()`，消除单任务与子任务路径约 170 行的逻辑冗余。
*   **产出价值**：内核稳定性达到准生产级，为后续的大规模知识摄入扫清架构障碍。

### Phase 42: 本地栈健康检查与真实成本遥测 (Local Stack & Cost Mastery)
*   **Primary Track**: Execution Topology
*   **Secondary Track**: Evaluation / Policy
*   **目标**：深度适配课题组本地全栈拓扑，将估算成本升级为真实遥测。
*   **核心任务**：
    - **增强 `swl doctor`**：实现对本地 Docker 容器（new-api/TensorZero/Postgres）、pgvector 扩展及 WireGuard 出口隧道的自动化健康检查。
    - **真实成本遥测**：`Meta-Optimizer` 接入本地 TensorZero API 抓取真实 Token 账单；在遥测中显式标记 Debate 轮次成本。
*   **产出价值**：彻底消除路由优化的”数据盲区”，使系统具备基于真实开销的自动选路能力。

### Phase 43: ReAct 降级方言 (Dynamic Capability Negotiation) — 暂缓
*   **Primary Track**: Execution Topology
*   **Secondary Track**: Capabilities
*   **状态**：暂缓。2026 年主流开源模型（Qwen2.5+/Llama3.1+/DeepSeek V2+）及推理框架（Ollama 0.4+/vLLM）已原生支持 Tool Calling，ReAct 降级的适用场景收窄至极小模型或旧版量化权重等边缘情况。当前 Swallow 通过 new-api 代理云端/本地 API，暂无真实需求。如未来遇到具体模型 tool calling 不可用的场景，再按需实现。
*   **原设计**：将 Tool Schema 渲染为 ReAct 纯文本引导语（`Action: / Action Input:`），回包阶段通过正则还原为标准工具调用意图。

### Phase 44: 可视化工作台增强 (Web Control Center Enhancement)
*   **Primary Track**: Workbench / UX
*   **Secondary Track**: Core Loop
*   **目标**：落地”立体操作环境”，解救 CLI 时代的认知过载。
*   **核心任务**：
    - **任务树仪表盘**：图形化展示任务层级（Task Tree）、并行子任务进度及实时成本/延迟曲线。
    - **Artifact 对比审阅区**：提供双栏视图（Draft vs History/Ref），支持高效的 Approve / Reject 操作。
*   **产出价值**：极大提升人机协同效率，使 Swallow 成为一个可观测、可管控的真实工作环境。

### Phase 45: 领域专家 Agent 与深度摄入 (Specialist Agents & Deep Ingestion)
*   **Primary Track**: Retrieval / Memory
*   **Secondary Track**: Workbench / UX
*   **目标**：深化 Ingestion 链路，建立领域知识的专家化处理能力。
*   **核心任务**：
    - **深度摄入 Specialist**：支持还原 Open WebUI 等外部工具的完整对话树上下文，而非仅提取碎片消息。
    - **文献专家 (Literature Specialist)**：引入针对多源长文档的交叉对比 RAG 模块，生成高可靠性的结构化综述。
    - **自动化晋升流**：打通 Ingested 知识 → Staged Candidate → Librarian 自动触发审查的闭环链路。
*   **产出价值**：系统记忆不再局限于内部执行产出，能够无缝吸纳人类在外部探索积累的宝贵经验。

### Phase 46: 多模型共识与策略护栏 (Consensus & Policy Guardrails)
*   **Primary Track**: Evaluation / Policy
*   **Secondary Track**: Core Loop
*   **目标**：引入冗余审查机制，通过策略自动管控系统风险。
*   **核心任务**：
    - **N-Reviewer 共识拓扑**：支持 TaskCard 配置多个审查模型，实现”多数票通过”或”首席模型否决”等共识算法。
    - **智能预算策略**：`Meta-Optimizer` 基于历史统计自动生成 `ExecutionBudgetPolicy` 建议，实现成本超标的自动熔断。
    - **跨模型质量抽检**：由高阶模型对海量低阶模型生成的中间产物进行随机一致性审计。
*   **产出价值**：系统具备自我纠偏与财务自律能力，适应更高强度的全自动运行场景。

---

## 三、推荐 Phase 队列与风险批注 (Claude 维护)

> 最近更新：2026-04-18 (Phase 40 完结 + 部署拓扑调整后全量审计)

### 队列总览

| 优先级 | Phase | 名称 | Primary Track | Secondary Track | 风险等级 |
|--------|-------|------|---------------|-----------------|----------|
| ~~1~~ | ~~41~~ | ~~Librarian 收口与结构化清理~~ | ~~Core Loop~~ | ~~Retrieval / Memory~~ | ~~低-中~~ |
| ~~2~~ | ~~42~~ | ~~本地栈健康检查 + 真实成本遥测~~ | ~~Execution Topology~~ | ~~Evaluation / Policy~~ | ~~低~~ |
| — | 43 | ReAct 降级方言（暂缓） | Execution Topology | Capabilities | 中 |
| **3** | **44** | **可视化工作台 Control Center 增强** | Workbench / UX | Core Loop | 中 |
| 4 | 45 | 领域专家 Agent 与深度摄入 | Retrieval / Memory | Workbench / UX | 中 |
| 5 | 46 | 多模型共识与策略护栏 | Evaluation / Policy | Core Loop | 中-高 |

### Gemini 原版 Phase 41 拆分说明

Gemini 原版 Phase 41 混合了三个差异较大的方向：(a) swl doctor 容器健康检查、(b) 真实成本遥测、(c) ReAct 降级方言。ReAct 降级属于 Capabilities track，风险特征（正则解析脆弱性、需要高测试覆盖）与前两者不同。拆为 Phase 42（doctor + 成本遥测）和 Phase 43（ReAct 降级），降低单 phase 复杂度。原版 Phase 42-45 顺延为 Phase 41/44-46。

### 依赖关系

```
Phase 41 (Librarian 收口) ✅
  └──→ Phase 45 (深度摄入，依赖 Librarian 稳定)

Phase 42 (Doctor + 成本遥测) ✅
  └──→ Phase 46 (智能预算，依赖真实成本数据)

Phase 43 (ReAct 降级) — 暂缓，按需实现

Phase 44 (Web Control Center 增强) — 独立，当前优先
```

### Phase 41 — Librarian 收口与结构化清理（优先级 #1）

**优先级理由**：4 条 Open concern 中最老的（Phase 36 C1）已跨 4 个 phase，Librarian save_state → index 一致性问题在并发场景下有数据损坏风险。Phase 40 新增的 debate 代码重复（C1）也自然归入此 phase。先稳固内核再加新能力更安全。

**Concern 消化计划**：

| Concern | 来源 | 消化 Slice |
|---------|------|-----------|
| `_apply_librarian_side_effects()` save_state → index 一致性 | Phase 36 C1 | S1: Librarian 持久化原子化 |
| 单任务与子任务 debate loop 代码重复 ~170 行 | Phase 40 C1 | S2: 提取 `_debate_loop_core()` |

**风险**: 低-中。S1 涉及 orchestrator 调用路径变更，需全量知识晋升回归；S2 为纯重构。

### Phase 42 — 本地栈健康检查 + 真实成本遥测

**Concern 消化计划**：

| Concern | 来源 | 消化 Slice |
|---------|------|-----------|
| fallback `token_cost` 未计入 Meta-Optimizer route stats | Phase 38 C1 | S2: 成本遥测升级时一并修正 |
| debate retry 事件与正常执行事件无法区分 | Phase 40 C2 | S2: Meta-Optimizer 事件扫描排除/标记 debate 轮次 |

**风险**: 低。swl doctor 扩展为新增代码；成本遥测升级局限在 meta_optimizer 模块内。

### Phase 43 — ReAct 降级方言（暂缓）

**暂缓理由**：2026 年主流开源模型及推理框架已原生支持 Tool Calling，当前无真实需求。如未来遇到具体模型不可用场景再按需实现。kickoff 草稿保留在 `docs/plans/phase43/kickoff.md` 供参考。

**风险**: 中（如恢复实施）。正则解析脆弱性需极高测试覆盖。

### Phase 44 — 可视化工作台 Control Center 增强

**注意**：Phase 37 已建立只读 Web 基线（`swl serve`），本 phase 是增量扩展（Task Tree 图形化 + Artifact 对比审阅区），非从零构建。

**约束重申**：严格只读，零写入 `.swl/`，极简栈（JSON API + 单页 HTML）。

**风险**: 中。Scope 膨胀风险仍为最高关注点。

### Phase 45 — 领域专家 Agent 与深度摄入

**依赖前置**：Phase 41 Librarian 收口必须先完成。深度摄入产出走 Librarian 防线，如果 Librarian 的 side-effect 问题未修复，并发摄入会产生不可预测的状态覆盖。

**风险**: 中。幻觉防控 + 引用标注是核心挑战。

### Phase 46 — 多模型共识与策略护栏

**依赖前置**：Phase 42（真实成本数据，用于预算策略）。Phase 43（ReAct 降级）已暂缓，如需弱模型参与共识可届时恢复。

**风险**: 中-高。成本爆炸风险，多 Reviewer 线性增加 Token 消耗，必须与智能预算策略同步上线。

### Tag 建议

自 `v0.2.0` 以来已完成 Phase 38/39/40，新增外部知识摄入、对抗审查拓扑、成本遥测基线三项用户可感知的能力增量。main 处于稳定状态（302 tests passed），无进行中的重构，4 条 Open concern 均为内部优化不影响公共 API。

**建议打 `v0.3.0`**：外部知识摄入 + 对抗审查拓扑 + 成本遥测基线。
