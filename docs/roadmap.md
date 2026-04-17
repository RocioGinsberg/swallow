---
author: gemini
status: living-document
---

# 蓝图差距与演进路线图 (Gap Analysis & Roadmap)

## 一、当前实现与蓝图设计的核心差距 (Gap Analysis)

根据最新修订的 `ARCHITECTURE.md` 与 `docs/design/*.md`，并盘点最新合入的 Phase 35 成果，Swallow 系统已经稳固确立了“本地优先的统一调度系统”底座（包含 Runtime v0、双层知识架构基线、基础网关降级与只读可观测性）。

然而，当前代码实现与最终架构蓝图之间仍存在以下重大差距：

### 1. 物理连接层与成本感知缺失 (Provider Connector & Cost Awareness)
*   **蓝图要求**：网关层应具备真正的物理通道管理能力（Provider Connector），实现成本、延迟的真实隔离，并且 Event Telemetry 必须包含 `token_cost` 才能进行有效的路由优化（见 `GATEWAY_PHILOSOPHY.md` 与 `PROVIDER_ROUTER_AND_NEGOTIATION.md`）。
*   **当前现状**：目前系统主要依赖内部的 Python Dialect Adapters 进行薄封装直连，缺乏如 `new-api` 或 `TensorZero` 这样独立的通道管理与格式互转层；遥测缺失最关键的 Token 成本账单。
*   **核心差距**：Meta-Optimizer 因缺乏成本数据而“盲人摸象”，系统无法实施基于成本的智能路由降级。

### 2. 外部知识孤岛与摄入能力空白 (External Session Ingestion)
*   **蓝图要求**：系统必须能无缝继承用户在外部（如 ChatGPT/Claude Web）的早期探索会话，由 `Ingestion Specialist` 进行提纯降噪并转化为标准 `HandoffContractSchema`，经 Librarian 审查入库。
*   **当前现状**：Phase 32 虽建立了 Librarian 的防线基线，但对外部非结构化对话的导入链路仍然为空。
*   **核心差距**：人类在外部大模型 UI 中探讨沉淀的宝贵上下文无法自然流入 Swallow，导致系统出现“认知断层”。

### 3. 立体操作环境与控制中心缺位 (Workbench Control Center)
*   **蓝图要求**：从线性的 CLI 终端向“立体操作环境”演进，提供可视化呈现任务树（Task Tree）、并发状态监控及双栏的 Artifact Review Area。
*   **当前现状**：Phase 33 的并行 Subtask 跑通后，用户仍然只能在 CLI 终端里逐行滚动查阅和审查状态，效率极低。
*   **核心差距**：缺乏一个基于本地 `.swl/` 目录的 Web/Desktop 只读控制台，导致人类在审批并行任务工件时面临“认知过载”。

### 4. 复杂审查拓扑与动态能力协商不足 (Debate Topology & Dynamic Negotiation)
*   **蓝图要求**：支持 `Debate / Review Topology`（自动双向对抗审查），以及支持运行时的动态能力协商（将抽象 Tool Schema 动态渲染为降级 ReAct 范式），并拥有更丰富的领域解析器（如 `Literature Specialist`）。
*   **当前现状**：当前的 Review Gate 仅具备基础单向打回机制；方言层仅硬编码支持了 Claude XML 与 Codex FIM 静态场景。
*   **核心差距**：系统应对复杂对抗任务的能力仍未解放，底层降级未能做到全自动协商。

---

## 二、架构演进 Roadmap (5 Phases)

为弥补上述差距，推进系统走向高阶治理与立体协同，推荐按以下 5 个 Phase 稳步演进：

### Phase 36: Provider Connector 整合与成本遥测 (Infrastructure & Cost)
*   **Primary Track**: Execution Topology
*   **Secondary Track**: Evaluation / Policy
*   **目标**：正式解耦物理路由管理，补齐 Telemetry 关键拼图。
*   **核心任务**：
    *   引入 Provider Connector 层（推荐集成/部署 `new-api` 作为底层代理）。
    *   扩充 `TelemetryFields` 与 Event Log，全面引入 `token_cost` 核算。
    *   升级 `Meta-Optimizer`：使其能够基于真实成本和延迟交叉分析，提出 Cost-Aware 的路由优化提案。
*   **产出价值**：彻底打通网关层盲区，系统具备真实的成本感知与审计治理能力。

### Phase 37: 外部会话摄入与知识边界跨越 (Ingestion Specialist)
*   **Primary Track**: Retrieval / Memory
*   **Secondary Track**: Workbench / UX
*   **目标**：打通人类外部探索与 Swallow 内部规范记忆的桥梁。
*   **核心任务**：
    *   实现 **Ingestion Specialist Agent**：支持解析导入的 ChatGPT/Claude Web 聊天记录（JSON/MD 格式）。
    *   开发降噪提纯工作流：将聊天中的闲聊剥离，提取有效结论、架构约束与被否方案，转化为标准的 `HandoffContractSchema`。
    *   对齐防线：提纯后的记录自动进入 Staged-Knowledge 暂存区，无缝对接 Librarian 的审查晋升防线。
*   **产出价值**：消灭知识孤岛，极大降低人工整理早期需求和脑暴记录的成本。

### Phase 38: 可视化工作台基线 (Control Center Baseline)
*   **Primary Track**: Workbench / UX
*   **Secondary Track**: Core Loop
*   **目标**：落地“立体操作环境”，解救 CLI 时代的认知过载。
*   **核心任务**：
    *   构建只读的本地 Web 控制中心（Control Center），直接挂载并消费 `.swl/` 目录的状态数据。
    *   实现 Task Tree 的图形化追踪，展示父子任务的并行进度。
    *   实现 Artifact Review Area：双栏显示 Draft 与对比 Diff，提供清晰的 Approve / Reject 视图。
*   **产出价值**：为多智能体的高并发运行提供“仪表盘”，确保人类在 Loop 中能轻松、高效地行使监督权。

### Phase 39: 对抗与审查拓扑增强 (Debate Topology & Quality)
*   **Primary Track**: Core Loop
*   **Secondary Track**: Execution Topology
*   **目标**：完成 Review Feedback Loop，让系统学会真正的“左右互搏”。
*   **核心任务**：
    *   升级 Review Gate，实现真正的 **Debate Topology**：Reviewer 不仅拦截，还能生成结构化的 `Review_Feedback` Artifact 持续打回，直到与 Executor 达成共识或触发防线熔断。
    *   开发特定的 Validator：如 **Consistency Review Agent**，专门用于校验设计文档与最终代码实现的一致性。
*   **产出价值**：系统产出质量的下限得到架构级担保，摆脱对“一次生成即正确”的脆弱假设。

### Phase 40: 动态能力协商与领域专长扩展 (Dynamic Negotiation & Specialists)
*   **Primary Track**: Execution Topology
*   **Secondary Track**: Capabilities
*   **目标**：使方言适配器具备动态自适应能力，并扩充高级领域解析器。
*   **核心任务**：
    *   实现高级 **Capability Negotiator**：不仅做静态格式转换，还能在目标模型无原生 Tool Calling 能力时，动态、实时地将其渲染为鲁棒的 ReAct Prompt 降级文本流。
    *   实现 **Literature Specialist**：引入领域 RAG 包，专用于复杂长文档/多源文件的交叉对比和结构化表格提取。
*   **产出价值**：系统的适配能力达到泛化顶点，即便在最极端、模型最廉价的降级环境下也能坚韧运作。

---

## 三、推荐 Phase 队列：优先级排序与风险批注 (Claude 维护)

> 本节由 Claude 维护，基于差距分析和依赖关系进行优先级排序与风险评估。
> 最近更新：2026-04-17 (Phase 35 完成后全量刷新，Claude 审计 + 优先级调整)

### 队列总览

| 优先级 | Phase | 名称 | Primary Track | Secondary Track | 风险等级 |
|--------|-------|------|---------------|-----------------|----------|
| **1** | **36** | **Concern Cleanup + LibrarianExecutor 收口** | Core Loop | Retrieval / Memory | 低 |
| 2 | 37 | 可视化工作台 Control Center 基线 | Workbench / UX | Core Loop | 高 |
| 3 | 38 | Provider Connector 整合与成本遥测 | Execution Topology | Evaluation / Policy | 中高 |
| 4 | 39 | Ingestion Specialist 外部会话摄入 | Retrieval / Memory | Workbench / UX | 中 |
| 5 | 40 | Debate Topology 与对抗审查 | Core Loop | Execution Topology | 中 |
| 6 | 41a | 动态能力协商 (ReAct Degradation) | Execution Topology | Capabilities | 中高 |
| 7 | 41b | Literature Specialist 领域 RAG | Retrieval / Memory | Capabilities | 中 |

### 依赖关系

```
Phase 35 (Meta-Optimizer Baseline)
  │
  ├──→ Phase 36 (Concern Cleanup)
  │       └──→ Phase 39 (Ingestion Specialist) [依赖 36 清理 LibrarianExecutor]
  │
  ├──→ Phase 37 (Control Center) [独立，CLI 痛点优先]
  │
  ├──→ Phase 38 (Provider Connector & Cost) [独立，需外部依赖]
  │
  └──→ Phase 40 (Debate Topology) [依赖 Phase 33 ReviewGate 稳定]
          └──→ Phase 41a (Dynamic Negotiation)
                Phase 41b (Literature Specialist) [独立于 41a]
```

### Phase 36 — Concern Cleanup + LibrarianExecutor 收口（新增）

**Primary Track**: Core Loop
**Secondary Track**: Retrieval / Memory
**风险等级**: 低

本轮优先消化 `docs/concerns_backlog.md` 中积压的 5 条 Open concern，其中 Phase 32 LibrarianExecutor 的 state mutation 问题最为关键——Phase 39 Ingestion Specialist 将进一步依赖 Librarian 路径，如果 side effect 仍散落在 executor 内部，并发场景会产生不可预测的状态覆盖。

**核心任务**：

| Concern | 来源 | 消化方式 | Slice |
|---------|------|---------|-------|
| LibrarianExecutor 直接操作 state + 多层持久化 | Phase 32 | 收回 side effect 到 orchestrator：LibrarianExecutor 只返回 ExecutorResult + 待写入 payload，由 orchestrator 执行 save_state / save_knowledge_objects / append_canonical_record | S1 |
| `acknowledge_task()` route_mode 硬编码 | Phase 21 | 增加 `route_mode` 参数，默认 `”summary”` 保持兼容 | S2 |
| `canonical_write_guard` 无运行时执行 | Phase 25 | 在 executor dispatch 前增加 guard check：if route 标记 canonical_write_guard 且 executor 非 Librarian → block | S2 |
| `build_stage_promote_preflight_notices()` 返回类型变更 | Phase 28 | 补充类型标注 + 添加 migration docstring；若确认无外部调用者则标记 Won't Fix | S2 |
| CodexFIMDialect 未转义 FIM 标记 | Phase 34 | 添加 `<fim_prefix>` / `<fim_suffix>` 文本替换（escape 为 `[fim_prefix]` / `[fim_suffix]`） | S2 |

**Slice 拆分**：
- **S1**: LibrarianExecutor state mutation 收口（orchestrator.py + librarian_executor.py 重构）
- **S2**: 4 条 API cleanup concern 批量消化

**风险**: 4/9（impact 2, reversibility 1, dependency 1）—— S1 影响 Librarian 执行路径，需回归验证；S2 为低风险 API 调整。

**为什么优先**：
1. 按 `concerns_backlog.md` 规则，每 3-5 个 phase 需回顾清理，当前已跨 5 个 phase（Phase 31-35）
2. Phase 32 concern 阻塞后续 Ingestion Specialist 安全接入 Librarian
3. 积压 concern 不清理会导致技术债复利增长

---

### Phase 37 — 可视化工作台 Control Center 基线（原 Phase 38，提前）

**优先级调整理由**：当前 CLI 审查体验是日常开发最直接的痛点，Phase 33 并行子任务跑通后在 CLI 逐条审查 artifact 效率极低。比 Ingestion Specialist 和 Provider Connector 更紧迫。

（Phase 描述与核心任务保持不变，见上方第二节。）

**约束重申**：
- 严格只读：零写入 `.swl/`，所有状态流转仍走 CLI
- 极简栈：JSON API + 单页 HTML，不引入 React/Vue 构建工具链
- AGENTS.md 非目标对照：不得演化为全功能 Web 系统

---

### Phase 38 — Provider Connector 整合与成本遥测（原 Phase 36，推后）

**优先级调整理由**：Provider Connector 引入外部依赖（Docker/Go），运维复杂度高。应在内部 concern 清理和 UX 痛点缓解后再引入。

（Phase 描述与核心任务保持不变，见上方第二节。）

**分期建议不变**：
- Phase 38a: `token_cost` 遥测扩展（纯 Python，不引入外部依赖）
- Phase 38b: Provider Connector 实际部署（new-api 本地 sidecar）

---

### Phase 39 — Ingestion Specialist 外部会话摄入（原 Phase 37，推后）

**优先级调整理由**：依赖 Phase 36 对 LibrarianExecutor 的 state mutation 收口。Ingestion 产出必须走 Librarian 防线，如果 Librarian 自身仍有 side effect 隐患，Ingestion 链路的可靠性无法保证。

（Phase 描述与核心任务保持不变，见上方第二节。）

---

### Phase 40 — Debate Topology 与对抗审查（原 Phase 39）

（Phase 描述、核心任务与风险批注保持不变。）

---

### Phase 41a — 动态能力协商 (ReAct Degradation)（原 Phase 40 拆分）

**Primary Track**: Execution Topology
**Secondary Track**: Capabilities

仅包含 Dynamic Capability Negotiator：在目标模型无原生 Tool Calling 时，动态渲染为 ReAct Prompt 降级文本流。

---

### Phase 41b — Literature Specialist 领域 RAG（原 Phase 40 拆分）

**Primary Track**: Retrieval / Memory
**Secondary Track**: Capabilities

仅包含 Literature Specialist：领域 RAG 包，专用于长文档/多源文件交叉对比。独立于 41a，可按需排序。

---

### 各 Phase 风险批注

**Phase 36 — Concern Cleanup**
- 🔍 S1 风险点：LibrarianExecutor 重构涉及 orchestrator 调用路径变更，需确保知识晋升/回写全路径回归。建议增加 Librarian 专项集成测试。
- 🔍 S2 风险点：极低。4 条 concern 均为 API 清理，不影响核心执行路径。

**Phase 37 — Control Center Baseline**
- ⚠️ Scope 膨胀风险（最高）：必须坚守只读 + 极简栈。
- 🔍 AGENTS.md 非目标：不得演化为全功能 Web 系统。

**Phase 38 — Provider Connector & Cost**
- ⚠️ 运维复杂度风险：首次引入 Python CLI 之外的系统依赖。
- 🔍 非目标对照：严格限制为本地 sidecar，不得演化为多租户网关。

**Phase 39 — Ingestion Specialist**
- ⚠️ 幻觉与质量风险：限制输入为 JSON + Markdown，产出必须走 Staged-Knowledge → Librarian 防线。

**Phase 40 — Debate Topology**
- ⚠️ 死循环陷阱：max rounds = 3 + 结构化 feedback artifact + 熔断升级到 human。

**Phase 41a — Dynamic Negotiation**
- ⚠️ 正则解析脆弱性：需极高测试覆盖率。

**Phase 41b — Literature Specialist**
- 风险低。领域 RAG 包为独立模块，不影响核心调度路径。

### Claude 审计总结

**调整要点**：

1. **新增 Phase 36 Concern Cleanup**：优先消化 5 条积压 concern，重点是 LibrarianExecutor state mutation 收口，为后续 Ingestion Specialist 扫清障碍
2. **Phase 38 (Control Center) 提前至 #2**：CLI 审查痛点是当前最直接的日常效率瓶颈
3. **Phase 36 (Provider Connector) 推后至 #3**：外部依赖引入应在内部清理和 UX 缓解之后
4. **Phase 37 (Ingestion Specialist) 推后至 #4**：依赖 LibrarianExecutor 收口
5. **原 Phase 40 拆分为 41a + 41b**：Dynamic Negotiation 和 Literature Specialist 分属不同 track
