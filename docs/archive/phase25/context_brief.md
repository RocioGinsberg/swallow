---
author: gemini
phase: 25
slice: taxonomy-driven-capability-enforcement
status: draft
depends_on: 
  - "docs/plans/phase25/design_preview.md"
  - "docs/design/AGENT_TAXONOMY_DESIGN.md"
  - "docs/design/HARNESS_AND_CAPABILITIES.md"
---

**TL;DR**
Phase 25 将启动候选方向 B (基于分类学的运行时能力沙盒)。本轮目标是打穿分类学 (Taxonomy) 权限的最后一层防线：在底层的 Harness 执行沙盒中，根据任务绑定的 `TaxonomyProfile` 动态剥离当前实体无权使用的 `Capabilities` / `Tools`。

### 任务概述 (Task Overview)
经过 Phase 22/23 的建设，我们的路由层已经会拒绝非法委派。但“分配安全”不代表“执行安全”。如果任务合法派发给了只具备 `Stateless` / `Validator` 权限的 Agent，但执行该任务的 Harness 实例依然将破坏力极强的系统工具（如 `run_shell_command`, `write_canonical_knowledge`）注入大模型的 Prompt 中，就存在被大模型幻觉利用从而越权的致命漏洞。
Phase 25 的任务就是在能力注入（Capability Assembly）阶段引入“白名单/黑名单”拦截机制，确保底层沙盒环境完全匹配智能体的权限边界。

### 变更范围 (Scope)
- **Primary Track**: `Capabilities`（能力的装配、显式声明与组装边界）
- **Secondary Track**: `Evaluation / Policy`（运行时防御性执行的策略层落地）
- **核心关注点**:
  - `src/swallow/capabilities.py` 或相关装配模块：新增对 `TaxonomyProfile` 属性的支持映射，定义各个工具被允许使用的角色层级。
  - `src/swallow/harness.py`：在执行环境初始化、大模型 Context 组装期间，依据当前 Task 的 `Taxonomy` 执行硬裁剪 (Hard Filtering)，剔除越权工具。
  - 事件流与可观测性：在发生工具裁剪时，于日志中提供必要的防守降级记录。

### 相关设计文档 (Related Design Docs)
- `docs/design/AGENT_TAXONOMY_DESIGN.md`
  - **核心约束**：General Executor 与 Specialist Agent 在内存权限与可执行动作上存在绝对鸿沟。
- `docs/design/HARNESS_AND_CAPABILITIES.md`
  - **核心约束**：Harness 是最严密的护城河。能力（Capabilities）不能只是提示词，它们必须是被托管和被审查的沙盒组件。

### 近期变更摘要 (Recent Commits & State)
- Phase 24 落地了“暂存知识库（Staged Knowledge）”缓解了知识污染。
- `TaxonomyProfile` 已作为实体全面浸透至路由、控制台与任务状态记录。
- 操作员已选定 Phase 25 候选方向 B：致力于消除大模型工具越权的安全隐患。

### 关键上下文 (Key Context)
- 本次改动可以视为 **"Least Privilege Principle (最小权限原则)"** 在 AI 系统底层（Tool Calling Context）的彻底落地。
- 以往的防护侧重于“堵外来任务的委派”，这次的防护侧重于“收缴执行者手上的违禁工具”。

### 风险信号 (Risk Signals)
- **过度复杂的策略模型**：不要在本阶段引入诸如 OPA (Open Policy Agent) 这样的重量级权限配置引擎。建议在代码中先建立静态映射表或硬编码基线守卫（例如：如果 `memory_authority` != `canonical-promotion`, 剔除 `promote_knowledge_tool`）。
- **向后兼容失败**：注意不要误伤现存的默认通用路由（`general-executor`）。必须确保正常的代码编写和执行流程在通用权限下不受影响。