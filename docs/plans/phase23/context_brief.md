---
author: gemini
phase: 23
slice: taxonomy-visibility-in-cli
status: draft
depends_on: ["docs/design/AGENT_TAXONOMY_DESIGN.md", "docs/plans/phase22/closeout.md"]
---

**TL;DR**
Phase 23 将 Phase 22 建立的智能体分类学（Agent Taxonomy）元数据暴露给操作员终端界面。通过更新 CLI 的 `inspect`、`review` 等命令，让人类可以直接观测到任务当前分配的系统角色和记忆权限，进一步提升系统的可观测性和交接安全性。

### 任务概述 (Task Overview)
在 Phase 22 中，系统已经在底层数据模型和调度器网关中引入了 Taxonomy (如 `system_role` 和 `memory_authority`)，并持久化到了 `TaskState` 中。为了闭环这一设计，我们需要在 `Workbench / UX` 层面将这些关键的边界信息展示出来。操作员在执行放行、审查或监控任务时，必须能直观地看到当前处理实体的安全画像。

### 变更范围 (Scope)
- **Primary Track**: `Workbench / UX`（终端人体工程学与观测路径）
- **Secondary Track**: `Execution Topology`（呈现交接和执行实体的分类）
- **核心关注点**: 
  - CLI `task inspect` 视图：增加 Taxonomy Profile 渲染。
  - CLI `task review` 或其他交接放行视图：在需要人类介入时，提示接收方的系统角色与内存写权限。
  - 不修改底层路由逻辑（Phase 22 已完成该部分）。

### 相关设计文档 (Related Design Docs)
- `docs/design/AGENT_TAXONOMY_DESIGN.md`
  - **核心精神**：让 Agent 的分类学比品牌名称更显式。CLI 输出应该优先显示 "Specialist / Staged-Knowledge" 等标签，强化角色认知。
- `docs/design/INTERACTION_AND_WORKBENCH.md`
  - **核心约束**：操作员必须清楚系统当前的状态边界。关键的安全边界（如是否具备规范写入权限）应该一目了然。

### 近期变更摘要 (Recent Commits & State)
- Phase 22 已经成功落地 `TaxonomyProfile` 路由级挂载。
- `TaskState` 目前能够保存选定路由的 taxonomy 信息。
- 基于分类学的异常调度已经被后端 Dispatch Guard 拦截保护。
- Phase 22 已经完成代码合并并闭环收口。

### 关键上下文 (Key Context)
- 当前系统的可观测性高度依赖于 CLI 命令。如果分类学信息只停留在数据结构和内存中，操作员在拦截审批和状态观测阶段仍然缺乏足够的上下文感知。
- “所见即所审”：操作员在面对 `waiting_human` 状态的任务时，明确看到 `canonical-write-forbidden` 标签，会极大增强系统的可控感和确定性。

### 风险信号 (Risk Signals)
- **信息过载**：CLI 面板空间有限，Taxonomy 信息需要在不破坏现有精简视图的前提下，采用醒目但紧凑的格式呈现（例如短语标签如 `[Role: specialist | Mem: task-state]`）。
- **范围蔓延**：不要在本阶段修改更复杂的 TUI 框架，仅专注于现有的标准命令行控制台输出体系，保持极简快速的基线闭环。