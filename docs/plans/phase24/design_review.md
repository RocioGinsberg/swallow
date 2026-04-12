---
author: gemini
phase: 24
slice: strategy-selection
status: draft
depends_on: 
  - "docs/plans/phase23/closeout.md"
  - "docs/system_tracks.md"
---

**TL;DR**
Phase 23 收口标志着“智能体分类学（Agent Taxonomy）”在路由分发与可观测性层面的阶段性闭环。本文档梳理了当前系统的基建现状，并提出了三个高价值的 Phase 24 候选方向（A: 运行时能力裁剪；B: 暂存知识审查流；C: 核心断点恢复），以供操作员（Human Operator）评估与决策下一阶段的系统演进路线。

# Phase 24: 演进方向决策书 (Design Decision Proposal)

## 一、 当前系统基建现状盘点

在决定下一步去哪之前，我们需要明确我们“已经拥有了什么”。

经过前 23 个 Phase 的迭代，Swallow 系统已经稳固了以下核心底座：
1. **Core Loop**: 稳定的任务状态机 (`TaskState`, `EventLog`) 与工件管理。
2. **Execution Topology**: 明确的本地/远端执行语义、强校验的交接契约（Handoff Contract Schema）。
3. **Dispatch & Routing**: 基于智能体分类学（Taxonomy）的安全派发拦截（Phase 22）。
4. **Workbench & UX**: 终端视角的强可观测性，Taxonomy 可视化（Phase 23）及人类介入审批流 (`dispatch_blocked` -> `acknowledge`)。
5. **Knowledge**: 基于检索树的溯源体系（Phase 15）与规范知识库（Canonical Registry）的雏形。

**现状结论**：在**任务编排（Orchestration）**与**交接路由（Handoff & Routing）**这两层上，系统已经具备了极强的防御性和可追溯性。继续在此方向上堆砌复杂度的边际收益正在急剧递减。我们需要将视角转向“运行时安全”、“知识演进”或“容错恢复”。

---

## 二、 Phase 24 候选方向评估

以下是为您梳理的三个具备高闭环价值（High ROI）的候选方向：

### 候选方向 A：基于分类学的运行时能力拦截 (Taxonomy-Driven Capability Enforcement)
* **关联 Track**: `Capabilities` (Primary) + `Evaluation / Policy` (Secondary)
* **当前痛点**: 
  Phase 22/23 我们通过 Taxonomy（如 `Canonical-Write-Forbidden`）做到了“不把修核心代码的任务派发给验证者”。但如果在 Harness 运行时层，底层还是把 `write_canonical_knowledge` 这样的超级工具暴露给它，就有可能因为大模型幻觉导致“越权调用”。
* **设计目标**: 
  在 Harness 层实现防御性执行（Defensive Execution）。基于 `TaskState` 中继承的 `TaxonomyProfile`，动态裁剪、过滤该实体无权使用的 Tools / Capabilities。
* **优势 (Pros)**: 顺滑承接 Phase 22/23 的势能，彻底闭环 Taxonomy 的安全防护链条（从“派发拦截”深入到“沙盒拦截”），改动范围可控。
* **劣势 (Cons)**: 属于安全加固类工作，业务侧体感不明显。

### 候选方向 B：暂存知识管道与人工审查流 (Staged Knowledge Pipeline Baseline)
* **关联 Track**: `Retrieval / Memory`
* **当前痛点**: 
  我们在架构设计（`AGENT_TAXONOMY_DESIGN.md`）中定义了 `Staged-Knowledge` 权限。但目前代码中缺乏从 `Candidate (候选)` -> `Review Queue (审核队列)` -> `Canonical (规范)` 的清晰生命周期实现。知识要么直接生效，要么散落在临时文件中，极易污染全局规范（Implicit Global Memory 污染风险）。
* **设计目标**: 
  构建“暂存知识库”。让具备 `Staged-Knowledge` 权限的 Agent 只能写“候选草稿”，然后开发配套的 `swl knowledge review` CLI 界面，让 Validator Agent 或 Human 决定是否晋升 (Promote) 为规范知识。
* **优势 (Pros)**: 解决长周期复杂任务中的知识沉淀痛点，是对系统“记忆能力”的重大突破。落实“知识晋升必须显式且有门控”的架构底线。
* **劣势 (Cons)**: 涉及新的存储结构和多级状态流转，工程量相对较大。

### 候选方向 C：任务恢复与异常重试边界强化 (Task Resume & Recovery Boundaries)
* **关联 Track**: `Core Loop`
* **当前痛点**: 
  我们在引入人类介入（`waiting_human`）和各类 Mock 执行后，任务状态经常需要挂起和重新拉起。当任务异常（Failed）或被中途打断时，恢复（Resume）逻辑主要依赖底层粗粒度记录，缺乏专门向 Agent 注入的“断点恢复上下文（Recovery Context）”。
* **设计目标**: 
  强化主循环中的 Checkpointing 机制。当任务 Failed 重新拉起时，Harness 能自动提取上一轮失败事件、最后一次成功状态，拼接成专属的“恢复说明”，让 Agent 精准知道“从何处跌倒，该从何处继续”。
* **优势 (Pros)**: 显著提升系统健壮性，减少 Agent 失败后从头开始的 Token 浪费。
* **劣势 (Cons)**: 属于 Core Loop 底层优化，不如“知识体系”的演进在直观功能上具有吸引力。

---

## 三、 推荐结论 (Recommendation)

作为系统的长上下文架构守护者，我的评估如下：

* **短期延续性最优：【方向 A】**。它能够在较小的代码变更下，将过去两轮的设计彻底在底层沙盒封死，做到滴水不漏。
* **长期架构价值最大：【方向 B】**。随着系统能力的增强，我们接下来一定会面临海量的“外部输入吸收”和“自我反思经验”沉淀。如果没有一个强大的、有门控的 Staged Knowledge 管道，系统会被自身的冗余记忆压垮。

**决策请求**：
请 Human Operator 权衡上述利弊，给出您的判断。
1. 如果倾向于彻底打穿 Taxonomy 安全线，请回复：**“选择方向 A”**。
2. 如果倾向于开启记忆进化之路，请回复：**“选择方向 B”**。
3. 或者指出您自己的切入点，我将据此重新规划 `Phase 24: context_brief.md`。