# Phase 26 Design Preview & Strategy Analysis

## 1. 当前系统里程碑快照 (Current System Snapshot)

随着 Phase 24 和 Phase 25 的相继完成，Swallow 系统的防御与治理基线已初步成型：

1. **记忆与知识治理 (Phase 24 - Staged Knowledge Pipeline)**：系统不再盲目让 Agent 直接写入全局记忆，而是建立了一个需要人工审查的 Staged (暂存) 缓冲区（对应 `KNOWLEDGE_AND_RAG_DESIGN.md` 和 `SELF_EVOLUTION_AND_MEMORY.md`）。
2. **执行最小权限 (Phase 25 - Taxonomy-Driven Capability Enforcement)**：基于 Agent 分类学，系统现在会在实际组装 Prompt 前，静态且强制地降级无关的 Capabilities（对应 `STATE_AND_TRUTH_DESIGN.md` 中“状态驱动的优雅降级”）。

**当前架构结论**：系统的“拦水坝”已建好（知道如何拦截不受信任的写入和越权的执行），保障了后续扩展的安全性，但**核心流程闭环**尚未完全打通。

---

## 2. 核心设计文档对齐与差距分析 (Gap Analysis)

根据 `ARCHITECTURE.md` 和 `docs/system_tracks.md`，我们可以看到以下几个方向存在明显的能力断层：

### 2.1 记忆闭环的最后一公里 (Retrieval / Memory Track)
*   **设计期望**：`SELF_EVOLUTION_AND_MEMORY.md` 强调显式的记忆沉淀是系统的核心，知识被审查后应能反哺新的任务。
*   **当前差距**：Phase 24 实现了审批晋升 (`stage-promote`)，但当前存在一个已记录的架构隐患（见 `docs/concerns_backlog.md`）：**`stage-promote` 仅仅是直接 append 到 Canonical Registry，完全没有去重（Deduplication）和语义冲突检查机制**。如果不加控制，长期运行会导致 Canonical 层堆积大量脏数据和重复事实，最终毁掉 Retrieval 的精准度。同时，晋升后的知识是否已顺畅融入新任务的默认 Retrieval 链路，闭环尚未完全跑通。

### 2.2 中断与恢复语义的边界 (Core Loop Track)
*   **设计期望**：`STATE_AND_TRUTH_DESIGN.md` 的“四件套（State, Event, Artifact, Git）”是为了应对长周期任务的失败与重启。
*   **当前差距**：`cli.py` 中虽然已经布设了 `retry_allowed`、`resume_allowed` 的检测逻辑，但 Orchestrator 主循环在面对异常崩溃、超时、或者人工拒绝 (Reject) 后的 Checkpoint 恢复语义尚未收敛成一个完整的标准流。

### 2.3 真实远程拓扑的落实 (Execution Topology Track)
*   **设计期望**：`ORCHESTRATION_AND_HANDOFF_DESIGN.md` 提到了 Local vs Remote 边界。
*   **当前差距**：Phase 19-23 做足了 Remote Handoff 的前置戏码（Contract、Mock Dispatch、拦截器），但目前全部都是 `[MOCK-REMOTE]`，尚未引入真实的 Transport 传输层。

---

## 3. 第一梯队推荐方向 (The Recommended Path)

结合 `docs/concerns_backlog.md` 以及架构演进的紧迫性，强烈推荐优先推进以下方向：

### 🏆 推荐方案：规范化记忆层的去重与合并
*   **Track**: `Retrieval / Memory`
*   **Slice**: `Canonical Knowledge Deduplication & Merge Gate`

#### 为什么这是最高优先级？
1. **解决明确的技术债务**：直接消化 `concerns_backlog.md` 中 Phase 24 遗留的明确 `[CONCERN]`（即 `stage-promote` 直接 append canonical record，缺少 canonical 层去重检查）。
2. **保护数据真相层 (Truth Layer)**：随着 Capability 被规范化执行，系统安全处理的任务量会增加。如果不加控制，操作员（或未来 Validator）审批产生的大量相似知识将迅速污染 Canonical 事实库，直接导致未来 RAG 的精准度崩溃。
3. **闭环 RAG 飞轮**：知识治理只有具备了去重（Deduplication）和合并（Merge/Supersede）机制，才算真正具备了“沉淀与进化”属性，而非单纯的日志堆叠。

#### 目标边界建议：
*   **要做什么**：在 Canonical Registry 写入前插入 Dedupe 拦截点；设计并实现明确的覆盖（Supersede）或版本控制语义机制。
*   **不做什么**：本阶段不引入极其复杂的自动向量聚合（Vector-based semantic merge）引擎，优先通过元数据（Metadata / Source Hash / Task ID）和精确哈希建立硬性阻断。

---

## 4. 其他候选方向 (Alternative Candidates)

为了提供充分的审计与决策上下文，以下是依据 `docs/system_tracks.md` 梳理的备选推进方向。如果在当前业务收口上人类操作员有不同的痛点，可以选择以下任一方向作为 Phase 26。

### 备选 A：中断与恢复语义的固化
*   **Track**: `Core Loop`
*   **Slice**: `Checkpoint & Recovery Semantics Stabilization`
*   **分析**：
    *   *现状*：`cli.py` 和状态模型中已经布设了 `retry_allowed`、`resume_allowed` 的检测标记，并存在 `stop_policy` 和 `execution_budget_policy`，但 Orchestrator 主循环在面对异常崩溃、超时或人工介入阻断后的恢复路径（Recovery Path）尚未整合成一个严密的标准流。
    *   *价值*：增强复杂长流任务在系统宕机或被干预后的鲁棒性。
    *   *为什么不作为首选*：目前通过重新派发和手工接管尚可维持基本操作，不像“脏数据污染 Canonical 库”具有不可逆的破坏性。

### 备选 B：真实的远程执行拓扑
*   **Track**: `Execution Topology`
*   **Slice**: `Mock-to-Real Remote Execution Transport`
*   **分析**：
    *   *现状*：Phase 19-23 做足了 Remote Handoff 的前置契约（Contract、Mock Dispatch、拦截器），但目前状态全部为 `[MOCK-REMOTE]`，尚未引入真实的 Transport 传输层或跨进程/跨机器的数据序列化流转。
    *   *价值*：彻底实现 Local 与 Remote 分离执行的架构愿景。
    *   *为什么不作为首选*：引入真实 Remote 会带来巨大的网络、认证、并发状态同步复杂度。在本地核心闭环（知识与状态闭环）尚未完全稳固前，过早过桥可能引入巨大联调成本。

### 备选 C：工作台审查体验升级
*   **Track**: `Workbench / UX`
*   **Slice**: `Operator Review TUI / Interactive Dashboard`
*   **分析**：
    *   *现状*：Phase 24 / 25 增加了基于 CLI 的列表审查（如 `swl knowledge stage-list`、`swl knowledge stage-inspect`）。
    *   *价值*：随着 Staged Knowledge 队列和拦截事件的增加，纯 CLI 命令行在审查大段文本差异（Diff）时体验较差。引入轻量级的 TUI（如基于 Textual / Rich）或本地极简 Web 界面，能大幅提升 Review 效率。
    *   *为什么不作为首选*：当前数据量和人工频率尚可通过 CLI + IDE 配合解决。这是一个优化项而非底层机制的空缺。

---

## 5. 下一步行动建议 (Next Steps for Operator)

1. 请操作员（Human）审阅上述选项，并确认一个最终方案。
2. 确认完毕后，系统将正式切换至 Plan Mode，针对选定 Track 产出 Phase 26 的 `context_brief.md` 与 `kickoff.md`。