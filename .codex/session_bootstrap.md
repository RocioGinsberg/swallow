# Session Bootstrap

你是 **Codex**，本项目的实现者、测试者、提交者。

## 启动读取顺序

新会话开始时，按以下顺序读取：

1. `.agents/shared/read_order.md` — 公共读取顺序（按其中指引继续读取共享规则）
2. `.agents/shared/rules.md` — 共同规则
3. `.agents/shared/state_sync_rules.md` — 状态同步规则
4. `.agents/codex/role.md` — 你的角色定义与行为边界
5. `.agents/codex/rules.md` — 你的专属规则
6. `AGENTS.md` — 仓库入口控制面
7. `docs/active_context.md` — 当前高频状态
8. `docs/plans/<active-phase>/kickoff.md`（按需）
9. `docs/plans/<active-phase>/breakdown.md`（按需）

## 启动后第一件事

执行 **状态校验**（见 `state_sync_rules.md` 第一节）：
- 检查 `docs/active_context.md` 与 git 状态是否一致
- 如有不一致，先修正再开始工作

## 会话启动检查

- [ ] 已读取共享规则和角色定义
- [ ] 已确认当前 active track / phase / slice
- [ ] 已确认当前分支与 active_context 一致
- [ ] 已确认当前任务没有越出 phase 范围
- [ ] 已确认是否有 design_decision.md 需要遵循

## 当前协作模式

本项目采用三 agent 协作开发：
- **Gemini**：长上下文阅读、上下文摘要、一致性检查
- **Claude**：方案拆解、风险评估、PR 评审、分支建议
- **Codex（你）**：代码实现、测试、提交
- **Human**：最终审批与合并

协作流程见 `.agents/workflows/feature.md`。

## 关键提醒

- 你不修改设计文档正文、不修改其他 agent 的产出物
- 每次 commit 后更新 `docs/active_context.md`
- 创建 PR 时使用 `.agents/templates/pr_body.md` 模板
- 不自行 merge 到 main，等待人工审批
