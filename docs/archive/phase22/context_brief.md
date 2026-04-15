---
author: gemini
phase: 22
slice: taxonomy-aware-routing-baseline
status: draft
depends_on: ["docs/design/AGENT_TAXONOMY_DESIGN.md"]
---

**TL;DR**
Phase 22 将理论设计落地到代码层面，在注册中心与调度器中引入智能体分类学（Agent Taxonomy）元数据，确保基于系统角色和记忆权限进行安全合规的任务路由分发，防止隐式提权和隐藏编排器。

### 任务概述 (Task Overview)
将上一轮写入核心文档的智能体分类学（Agent Taxonomy：System Role, Execution Site, Memory Authority）转化为代码层面的可用实体与调度约束。系统能力注册中心（Capabilities/Registry）需要能够识别这些显式标签，并且智能调度器（Dispatcher/Router）需要基于分类学进行任务派发与合规校验，彻底告别“基于模型品牌”的粗粒度路由。

### 变更范围 (Scope)
- **Primary Track**: `Capabilities`（系统能力的显式声明与组装）
- **Secondary Track**: `Execution Topology`（基于分类学的路由决策边界）
- **核心文件**: 
  - `src/swallow/capabilities.py` (定义与注入 taxonomy 属性)
  - `src/swallow/dispatch_policy.py` 或 `router.py` (增加基于分类学的路由守卫与分配策略)
  - `src/swallow/models.py` (相关的基础数据 Schema 更新)

### 相关设计文档 (Related Design Docs)
- `docs/design/AGENT_TAXONOMY_DESIGN.md`
  - **核心约束**：Agent 必须明确其 System Role (如 General Executor, Specialist Agent, Validator)。
  - **核心约束**：必须声明 Memory Authority (如 Stateless, Task-State, Canonical-Write-Forbidden)。
- `docs/design/ORCHESTRATION_AND_HANDOFF_DESIGN.md`
  - **核心约束**：智能调度器 (Dispatcher) 垄断任务流转语义，依分类学画像而非模型品牌进行任务绑定与分发。

### 近期变更摘要 (Recent Commits & State)
- 完成了 `Agent Taxonomy Integration` 文档轮次。
- 移除了临时的 `refine.md`，正式生成了 `docs/design/AGENT_TAXONOMY_DESIGN.md`。
- `ARCHITECTURE.md` 与 `README.md` 的概念描述已对齐。
- 系统已具备 Phase 21 遗留的强硬 Dispatch Policy Gate 和 Context Pointers 校验基础，为安全路由铺平了道路。

### 关键上下文 (Key Context)
当前的 Dispatch/Router 机制虽然能够拦截非法的 Handoff 交接单，但调度器可能仍然缺乏对接收端“身份”的深度认知。通过引入 Taxonomy 元数据：
1. **防止越权**：例如，阻止一个被标注为 `Validator` 或 `Canonical-Write-Forbidden` 的智能体接收到明确要求进行大范围代码重构的 `Task-State` 写请求。
2. **高闭环价值**：结合 Phase 21 的 Mock Topology 视图，我们可以在 CLI 界面和日志中直接看到任务被 Dispatch 给了哪个分类的实体，实现高度的可观测性。

### 风险信号 (Risk Signals)
- **过度工程**：本轮只需实现基于 Taxonomy 标签的**本地运行时校验与路由拦截 (Runtime Validation & Routing Gate)**，切勿在当前阶段将其扩大为分布式的、鉴权系统级别的 RBAC (Role-Based Access Control) 实现。
- **影响向下兼容**：需确保现有的通用能力（如 Codex / API Executors）能被顺滑地赋予对应的默认分类学标签（例如 `general-executor`），避免破坏已稳定运行的基础代码。