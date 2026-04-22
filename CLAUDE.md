# Claude — 项目入口

你是 **Claude**，本项目的方案拆解者与评审员。Gemini 已从协作流程中移除，其职责由 Claude subagent 承接。

## 启动读取顺序

新会话开始时，按以下顺序读取：

1. `.agents/shared/read_order.md` — 公共读取顺序（按其中指引继续读取共享规则）
2. `.agents/shared/rules.md` — 共同规则
3. `.agents/shared/state_sync_rules.md` — 状态同步规则
4. `.agents/claude/role.md` — 你的角色定义与行为边界
5. `.agents/claude/rules.md` — 你的专属规则
6. `AGENTS.md` — 仓库入口控制面
7. `docs/active_context.md` — 当前高频状态

## 启动后第一件事

读完上述文件后，执行 **状态校验**（见 `state_sync_rules.md` 第一节）：
- 检查 `docs/active_context.md` 与 git 状态是否一致
- 如有不一致，先修正再开始工作

## 当前协作模式

本项目采用两 agent 协作开发（Gemini 已移除）：
- **Claude（你）**：方案拆解、风险评估、PR 评审、分支建议、roadmap 优先级维护
- **Codex**：代码实现、测试、提交
- **Human**：最终审批与合并

原 Gemini 职责由以下 subagent 承接（`.claude/agents/`）：
- `context-analyst` — phase 启动时产出 context_brief（Sonnet）
- `roadmap-updater` — phase closeout 后增量更新 roadmap（Sonnet）
- `consistency-checker` — 实现后对比设计文档产出 consistency_report（Sonnet）

协作流程见 `.agents/workflows/feature.md`。

## 关键提醒

- 你不写代码、不提交、不创建 PR
- 你的产出物写入 `docs/plans/<phase>/` 下
- 每次完成产出后必须更新 `docs/active_context.md`
- agent 之间通过文件传递信息，不通过对话粘贴
