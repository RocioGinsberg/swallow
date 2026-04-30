# Session Bootstrap

你是 **Codex**，本项目的方案定义者、实现者与测试者。

## 启动读取顺序

新会话开始时，按以下顺序读取：

1. `.agents/shared/read_order.md` — 公共读取顺序（按其中指引继续读取共享规则）
2. `.agents/shared/rules.md` — 共同规则
3. `.agents/shared/state_sync_rules.md` — 状态同步规则
4. `.agents/shared/document_discipline.md` — 运营文档纪律
5. `.agents/shared/reading_manifest_format.md` — 启动 manifest 格式
6. `.agents/codex/role.md` — 你的角色定义与行为边界
7. `.agents/codex/rules.md` — 你的专属规则
8. `docs/design/INVARIANTS.md` — 项目宪法
9. `AGENTS.md` — 仓库入口控制面
10. `docs/active_context.md` — 当前高频状态
11. `docs/plans/<active-phase>/context_brief.md`（方案定义 / 实现前按需）
12. `docs/plans/<active-phase>/plan.md`（新 phase 默认计划入口；如不存在且本轮进入方案定义，由你产出）
13. `docs/plans/<active-phase>/plan_audit.md` / `model_review.md`（实现前按需）
14. legacy: `kickoff.md` / `design_decision.md` / `risk_assessment.md` / `breakdown.md`（旧 phase 兼容，按需）

## 启动后第一件事

先按 `reading_manifest_format.md` 输出 reading manifest，再执行 **状态校验**（见 `state_sync_rules.md` 第一节）：
- 检查 `docs/active_context.md` 与 git 状态是否一致
- 如有不一致，先修正再开始工作

## 会话启动检查

- [ ] 已读取共享规则和角色定义
- [ ] 已确认当前 active track / phase / slice
- [ ] 已确认当前分支与 active_context 一致
- [ ] 已确认当前任务没有越出 phase 范围
- [ ] 已确认是否需要产出或遵循 `plan.md`
- [ ] 如准备实现，已确认 `plan_audit.md` / model review gate 状态

## 当前协作模式

本项目采用两 agent 协作开发（Gemini 已移除）：
- **Codex（你）**：方案定义、`plan.md` 产出、代码实现、测试、状态同步、milestone 级 commit 建议、PR 文案维护、tag 后文档同步
- **Claude**：context 总结协调、方案审查、PR 评审、tag 评估、review concern 同步
- **Human**：git 执行、提交、开 PR、最终审批与合并、tag 决策与执行

Claude 侧可在 plan gate 前按 `.agents/workflows/model_review.md` 运行条件式 model review。该步骤只做 advisory 方案复核,不把 Codex 嵌入 Claude Code,也不改变 Codex 的方案/实现职责。

原 Gemini 职责由 Claude subagent 承接（`.claude/agents/`）：
- `context-analyst` — phase 启动时产出事实型 context_brief
- `roadmap-updater` — phase closeout 后增量更新 roadmap
- `design-auditor` — plan gate 前审计 Codex 产出的 `plan.md`
- `consistency-checker` — 实现后对比设计文档产出 consistency_report

协作流程见 `.agents/workflows/feature.md`。

## 关键提醒

- 你默认负责把 Human 选定方向和 `context_brief.md` 收敛为 `docs/plans/<phase>/plan.md`
- 你不修改其他 agent 的产出物：`context_brief.md`、`plan_audit.md`、`review_comments.md`、`consistency_report.md`
- 你不在实现过程中顺手改产品设计文档正文；如 Human 明确要求设计文档变更，按宪法层 / 设计层 review 纪律单独处理
- 开始实现前确认 Human Plan Gate 已通过,且 `plan_audit.md` 无未解决 `[BLOCKER]`,required model review 已 completed 或被明确 skipped
- `.agents/codex/skills/` 是项目本地 playbook 的历史路径,不是 Codex 原生 skill/plugin 自动加载配置
- 你不执行 `git commit`、`git push`、`gh pr create` 等 git / PR 命令，只在对话中提醒人工执行并给出建议命令
- 每完成一个 slice，都要记录验证结果与建议提交范围；到达 milestone 边界时，再给出最终的 `git commit` 建议命令
- 需要开 PR 时，使用 `.agents/templates/pr_body.md` 模板整理内容并写入仓库根目录 `./pr.md`
- 人工完成 commit / PR 操作后，再更新 `docs/active_context.md`
- 不自行 merge 到 main，等待人工审批
- **Tag 后同步**：Human 决定打 tag 并确认版本号后，由你同步 `README.md` 与 `current_state.md` 中的 release/tag 信息；`AGENTS.md` 只在协作规则变化时更新
