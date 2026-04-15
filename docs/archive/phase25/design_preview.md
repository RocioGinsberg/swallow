---
author: gemini
phase: 25
slice: strategy-selection
status: draft
depends_on: 
  - "docs/plans/phase24/closeout.md"
  - "docs/system_tracks.md"
---

**TL;DR**
Phase 24 成功建立了暂存知识库（Staged Knowledge Registry）与终端审查命令。至此，我们在知识防污染层面建立起了“缓冲地带”。本文档总结了当前的系统全貌，并针对 Phase 25 提出了三个极具高闭环价值的候选演进方向（A: 暂存知识的检索集成；B: 基于分类学的运行时能力沙盒；C: 核心主循环的断点恢复上下文），供操作员（Human Operator）评估与决策。

# Phase 25: 演进方向决策书 (Design Preview / Decision Proposal)

## 一、 当前系统基建现状盘点

经历前 24 个 Phase 的演进，Swallow 系统的架构体系已经初具规模，核心防线逐步确立：

1. **Orchestration & Handoff**: 具备了严格的交接契约（Handoff Contract Schema）与语义校验，并打通了本地/远端的执行流转拓扑。
2. **Taxonomy & Routing**: 通过 Phase 22/23，系统不再依赖模型品牌进行路由，而是通过明确的分类学（System Role & Memory Authority）在底层进行安全派发拦截，并在终端透明可视。
3. **Knowledge Governance**: 在刚刚闭环的 Phase 24 中，系统落地了 `Staged-Knowledge` 权限底座。受限实体只能向全局的 `.swl/staged_knowledge/registry.jsonl` 提交候选（Candidate），并将晋升（Promote）的决策权交还给操作员。

**现状总结**：系统的“骨架（结构定义）”和“皮肤（可视化与拦截网关）”已经建立，目前的焦点应转移到“血液循环（数据流动与运行时安全）”上。

---

## 二、 Phase 25 候选方向评估

以下是为您梳理的三个具备高边际收益（High ROI）的候选方向：

### 候选方向 A：暂存知识的检索集成 (Staged Knowledge Retrieval Integration)
* **关联 Track**: `Retrieval / Memory`
* **当前痛点**: 
  Phase 24 建立了暂存队列，但目前这些宝贵的经验只对操作员（CLI命令）可见。这意味着，如果 Agent A 今天晚上暂存了一个关于特定 Bug 的解决思路，明天早上的 Agent B 在使用 Retrieval 检索时，将**无法**搜到这条经验（因为它还在排队等待人工 Promote）。系统的短期学习能力被人工审查的滞后性卡死了。
* **设计目标**: 
  将 Staged Knowledge 接入到系统的标准检索体系中。检索结果不仅包含 Canonical，还按需融合 Staged 数据，但在输出中打上明确的 `[STAGED / UNVERIFIED]` 信任度标记，让执行智能体在吸收这些经验时保持谨慎。
* **优势 (Pros)**: 彻底打通短期记忆向长期记忆过滤的“活水流”，让多智能体系统在无需人工频繁干预的情况下也能具备准实时的上下文共享能力。
* **劣势 (Cons)**: 可能会增加 Retrieval 索引的查询复杂度，并考验后续大模型对 `UNVERIFIED` 标记的遵循程度。

### 候选方向 B：基于分类学的运行时能力沙盒 (Taxonomy-Driven Capability Enforcement)
* **关联 Track**: `Capabilities` (Primary) + `Evaluation / Policy` (Secondary)
* **当前痛点**: 
  这是 Phase 24 遗留的另一个高优候选项。我们有了 Taxonomy 的路由网关，但当任务派发给一个 `Specialist / Stateless` 的 Agent 时，底层 Harness 运行时可能依然把所有的 Tool（比如 `run_shell_command` 或大范围的文件写工具）全部暴露给它，这存在潜在的“大模型幻觉越权”风险。
* **设计目标**: 
  在 Harness 层实现硬性拦截（Defensive Execution Sandbox）。根据继承的 `TaxonomyProfile`，动态裁剪并过滤当前实体无权使用的能力（Capabilities）。
* **优势 (Pros)**: 从“路由级防御”下沉到“执行引擎级防御”，闭环 Taxonomy 权限体系的最后一公里。
* **劣势 (Cons)**: 属于底层系统加固，短期在业务能力上无明显感知。

### 候选方向 C：任务断点恢复上下文增强 (Task Resume & Recovery Context Semantics)
* **关联 Track**: `Core Loop`
* **当前痛点**: 
  当前系统大量使用了 `dispatch_blocked` 等待人类放行以及 `waiting_human` 等中间挂起状态。当任务 Failed 重新拉起或者人工提供意见后 Resume 时，目前的恢复依赖于底层的原始记录栈。系统缺乏一种机制在 Agent 再次拉起时，专门喂给它一个提纯过的“断点恢复上下文（Recovery Briefing）”。
* **设计目标**: 
  强化主循环。在发生 `Resume` 时，由 Orchestrator 或专门的 Specialist Agent 自动生成一段高密度的状态恢复提示：“你上次因为 XX 失败，人工给予了 YY 建议，当前请从 ZZ 继续”。
* **优势 (Pros)**: 大幅降低长周期任务重启后的 Token 浪费与“迷失感”，增强容错性。
* **劣势 (Cons)**: 优化类工作，逻辑相对细碎。

---

## 三、 推荐结论 (Recommendation)

作为系统的架构看门人，我的倾向性评估如下：

* **业务价值与智能度提升最高：【方向 A】**。它将“静态的知识审核队列”变成了“活的参考库”。只有接入了 Retrieval，暂存知识才真正产生了价值，否则它只是一个孤立的待办列表。
* **安全性与一致性最强：【方向 B】**。如果系统即将引入更多高风险的外部开源模型来处理专项任务，那完成运行时能力裁剪是当务之急。

**决策请求**：
请 Human Operator 权衡上述利弊，给出您的判断。
1. 如果希望系统马上变得更聪明，能跨任务共享未验证经验，请回复：**“选择方向 A”**。
2. 如果希望把执行引擎的防线彻底封死，请回复：**“选择方向 B”**。
3. 如果希望改善重试体验，请回复：**“选择方向 C”**。

在您做出决定后，我将立即产出对应的 `context_brief.md` 以启动 Phase 25 规划。