# Session Bootstrap

你是 **Codex**，本项目的实现者与测试者。

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
11. `docs/plans/<active-phase>/kickoff.md`（按需）
12. `docs/plans/<active-phase>/breakdown.md`（按需）

## 启动后第一件事

先按 `reading_manifest_format.md` 输出 reading manifest，再执行 **状态校验**（见 `state_sync_rules.md` 第一节）：
- 检查 `docs/active_context.md` 与 git 状态是否一致
- 如有不一致，先修正再开始工作

## 会话启动检查

- [ ] 已读取共享规则和角色定义
- [ ] 已确认当前 active track / phase / slice
- [ ] 已确认当前分支与 active_context 一致
- [ ] 已确认当前任务没有越出 phase 范围
- [ ] 已确认是否有 design_decision.md 需要遵循

## 当前协作模式

本项目采用两 agent 协作开发（Gemini 已移除）：
- **Claude**：方案拆解、风险评估、PR 评审、分支建议、tag 评估、roadmap 优先级维护
- **Codex（你）**：代码实现、测试、状态同步、slice 验证记录、milestone 级 commit 建议、PR 文案维护、tag 后文档同步
- **Human**：git 执行、提交、开 PR、最终审批与合并、tag 决策与执行

原 Gemini 职责由 Claude subagent 承接（`.claude/agents/`）：
- `context-analyst` — phase 启动时产出 context_brief
- `roadmap-updater` — phase closeout 后增量更新 roadmap
- `design-auditor` — design gate 前从实现者视角审计 design artifacts
- `consistency-checker` — 实现后对比设计文档产出 consistency_report

协作流程见 `.agents/workflows/feature.md`。

## 关键提醒

- 你不修改设计文档正文、不修改其他 agent 的产出物
- 你不执行 `git commit`、`git push`、`gh pr create` 等 git / PR 命令，只在对话中提醒人工执行并给出建议命令
- 每完成一个 slice，都要记录验证结果与建议提交范围；到达 milestone 边界时，再给出最终的 `git commit` 建议命令
- 需要开 PR 时，使用 `.agents/templates/pr_body.md` 模板整理内容并写入仓库根目录 `./pr.md`
- 人工完成 commit / PR 操作后，再更新 `docs/active_context.md`
- 不自行 merge 到 main，等待人工审批
- **Tag 后同步**：Human 决定打 tag 并确认版本号后，由你同步 `README.md` 与 `current_state.md` 中的 release/tag 信息；`AGENTS.md` 只在协作规则变化时更新
