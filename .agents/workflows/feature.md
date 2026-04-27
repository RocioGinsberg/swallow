# Workflow: Feature Delivery

标准的多角色 feature delivery 流程。每个新 phase/slice 的实现默认使用此流程。

> **注意**：Gemini 已从协作流程中移除（2026-04-23）。原 Gemini 步骤由 Claude subagent 承接。

---

## 流程总览

```
[subagent: roadmap-updater]: Roadmap Incremental Update (Phase Transition)
        ↓
Claude: Roadmap Priority Review
        ↓
 Human: Direction Gate ⛔
        ↓
[subagent: context-analyst]: Context Analysis
        ↓
Claude: Design Decomposition
        ↓
[subagent: design-auditor]: Pre-Implementation Design Audit
        ↓
 Human: Design Gate ⛔  (审阅 design_decision + design_audit)
        ↓
 Codex: Implementation
        ↓
Claude: PR Review  (可选: [subagent: consistency-checker] 先行)
        ↓
 Human: Merge Gate ⛔
        ↓
Claude: Tag Evaluation  →  Human: Tag Gate  →  Codex: Tag Sync (如打 tag)
        ↓
[subagent: roadmap-updater]: Post-Phase Roadmap Update
```

⛔ = 人工 gate，必须由人工审批后才能继续。

---

## Step 0: Claude (subagent + main) & Human — Phase Transition & Direction Gate ⛔

**触发条件**：上一个 phase 已经完成 closeout 收口并合入主线。

### 常规流程（roadmap 已存在且无需刷新）

**subagent `roadmap-updater` 动作**：
1. 读取 `docs/plans/<prev-phase>/closeout.md` 和当前 `docs/roadmap.md`
2. 增量更新差距总表（消化已完成差距、补充新差距）
3. 更新 roadmap 中已完成 phase 的状态标记

**Claude 动作**：
1. 读取更新后的 `docs/roadmap.md`
2. 评审并更新推荐 phase 队列的优先级排序与风险批注
3. 更新 `docs/active_context.md`，通知 Human 进行方向选择

**人工动作 (Direction Gate ⛔)**：
- 阅读 `docs/roadmap.md` 的推荐 phase 队列（含 Claude 的优先级判断与风险批注）
- 选择下一个方向（如：”启动 Phase 50”）

### 全量刷新流程（roadmap 不存在或蓝图发生重大变更）

**Claude 动作**（直接由 Claude 主线处理，不用 subagent）：
1. 读取 `docs/system_tracks.md` + `docs/design/*.md` + `current_state.md`
2. 产出 `docs/plans/<new-phase>/design_preview.md`（演进方向决策书）
3. 全量更新 `docs/roadmap.md` 的差距总表
4. 评审并更新推荐 phase 队列的优先级排序与风险批注

**人工动作 (Direction Gate ⛔)**：
- 阅读 design_preview + roadmap（含 Claude 批注），选定方向

---

## Step 1: subagent `context-analyst` — Context Analysis

**触发条件**：人工已在 Direction Gate 中明确选定下一阶段的方向。

**输入**：
- 人工在 Step 0 指定的阶段目标决策
- `docs/roadmap.md`（差距 ID 和上下文）
- `docs/design/*.md`（仅阅读 roadmap 指向的相关设计文档）
- 相关 git history

**产出**：
- `docs/plans/<phase>/context_brief.md`

**完成后**：
- 更新 `docs/active_context.md`：登记产出物，下一步设为”Claude 进行方案拆解”

---

## Step 2: Claude — Design Decomposition

**触发条件**：context_brief.md 已产出。

**输入**：
- `docs/plans/<phase>/context_brief.md`
- `docs/design/INVARIANTS.md`
- 相关 `docs/design/*.md`（按 kickoff / context_brief 指向按需读取）
- `docs/plans/<phase>/kickoff.md`

**产出**：
- `docs/plans/<phase>/design_decision.md`
- `docs/plans/<phase>/risk_assessment.md`

**附加动作**：
- 执行 `branch-advise`：建议分支名和 PR 策略
- 执行 `phase-guard`：检查是否越出 scope

**完成后**：
- 更新 `docs/active_context.md`：登记产出物，下一步设为"运行 design-auditor subagent"

---

## Step 2.5: subagent `design-auditor` — Pre-Implementation Design Audit

**触发条件**：design_decision.md 和 risk_assessment.md 已产出。

**输入**：
- `docs/plans/<phase>/kickoff.md`
- `docs/plans/<phase>/design_decision.md`
- `docs/plans/<phase>/risk_assessment.md`

**产出**：
- `docs/plans/<phase>/design_audit.md`

**审计视角**：从实现者（Codex）角度检查：
- 每个 slice 的目标是否足够清晰可以直接开始编码
- 验收条件是否具体可测
- 是否有跨 slice 的依赖顺序缺失
- 是否有 risk_assessment 未覆盖的实现层风险

**发现 [BLOCKER] 时**：
- 在 `docs/active_context.md` 标注"design-audit BLOCKED: <原因>"
- 回到 Step 2，Claude 修正 design_decision 后重新运行 design-auditor

**完成后**：
- 更新 `docs/active_context.md`：登记产出物，下一步设为"Human: Design Gate"

---

## Step 3: Human — Design Gate ⛔

**触发条件**：design_decision.md、risk_assessment.md、design_audit.md 均已产出。

**人工动作**：
- 阅读 design_audit.md（重点看 Overall verdict 和 [BLOCKER] 项）
- 阅读 design_decision.md（重点看 TL;DR + slice 拆解 + 风险评级）
- 阅读 risk_assessment.md（重点看高风险项）
- 审阅 branch-advise 建议

**决策**：
- ✅ 通过：在 `docs/active_context.md` 标注"design approved"，由 Human 先切换到建议的 feature branch，再通知 Codex 开始实现
- ❌ 打回：标注具体修改要求，回到 Step 2
- 🔄 部分通过：标注哪些 slice 可以先做，其余暂缓

**人工 git 节奏点**：
- design gate 一旦通过，先完成 branch 创建/切换；未切换前不进入实现
- 此处仍不提交实现代码；提交从各 slice 完成后开始

---

## Step 4: Codex — Implementation

**触发条件**：design_decision.md 已通过人工审批。

**输入**：
- `docs/plans/<phase>/design_decision.md`
- Claude 的 branch-advise（分支名、PR 策略）
- 相关 `src/` 和 `tests/` 文件

**动作**：
- 按 Claude 建议提醒人工创建/切换分支
- 按 design_decision 中的 slice 顺序逐个实现
- 每个 slice：功能实现/测试 → Codex 给出 commit 建议 → Human 审查该 slice diff 并执行 commit → 状态同步

**每个 slice 的人工节奏点**：
1. Human 确认当前已位于本轮 feature branch
2. Codex 完成当前 slice 的最小闭环实现与测试
3. Codex 在对话中给出该 slice 的单独 commit 建议命令
4. Human 审查并执行该 slice commit
5. commit 完成后，再进入下一个 slice 或更新状态

**强约束**：
- 一个 slice 对应一个独立 commit 节奏点；不要把多个 slices 合并成一次“大包提交”
- 进入下一个 slice 前，前一个 slice 应已经完成人工审查和独立 commit
- PR 创建前保持 slice 级 commit 历史，不再额外整理成单一汇总提交

**产出**：
- 代码改动（在 feature branch 上）
- 测试结果
- 每个 slice 的建议 commit 命令

**完成后**：
- 更新 `docs/active_context.md`：登记完成的 slice、当前分支、下一步设为"Claude 进行 PR review"

---

## Step 5: Claude — PR Review

**触发条件**：Codex 实现完成，所有 slice 的代码和测试已由人工按 slice 完成提交。

**输入**：
- Git diff（feature branch vs main）
- `docs/plans/<phase>/design_decision.md`
- `docs/plans/<phase>/context_brief.md`（按需）

**附加输入**（可选）：
- `consistency_report.md`（如果在 Step 4 后执行了一致性检查）

**产出**：
- `docs/plans/<phase>/review_comments.md`

**附加动作**：
- 执行 `branch-advise`：确认是否可以开 PR
- 如有 `[BLOCK]` 项，回到 Step 4 让 Codex 修改

**完成后**：
- 更新 `docs/active_context.md`：登记评审状态，下一步设为"等待人工合并决策"
- Codex 按 `.agents/templates/pr_body.md` 模板整理 PR 内容并写入 `./pr.md`，提醒人工创建 PR

**人工 git 节奏点**：
- `./pr.md` 准备完成后，由 Human push 当前 feature branch 并创建 PR
- Claude review 完成后，如有实现修订或 review 结论变化，Codex 更新 `./pr.md`，Human 视需要更新 PR 描述
- PR 创建前不再补做“把所有 slice 压成一个大提交”的整理

---

## Step 6: Human — Merge Gate ⛔

**触发条件**：PR 已创建，review_comments.md 已产出。

**人工动作**：
- 阅读 PR body（包含三方产出物摘要）
- 阅读 review_comments.md
- 确认 PR 上的描述与仓库中的 `./pr.md`、`review_comments.md` 一致
- 在 PR 上留下最终意见

**决策**：
- ✅ 合并：merge PR，在 `docs/active_context.md` 标注"merged"
- ❌ 打回：在 PR 上说明原因，回到 Step 4 或 Step 2
- 🔄 部分合并：cherry-pick 部分 commit（特殊情况）

**合并前检查**：
- review_comments.md 中的 `[BLOCK]` 项必须为零，或已被明确处理
- 若 review 后发生新的代码提交，先确认 `./pr.md` 已更新到最新状态
- merge 决策发生在 review 处理完成之后，而不是创建 PR 之后立即执行

---

## Step 7: Claude & Human — Tag Evaluation Gate

**触发条件**：phase 已 merge 到 main，`current_state.md` 和 `docs/active_context.md` 已由 Codex 完成 post-merge 同步。

**详细流程见**：`.agents/workflows/tag_release.md`

**本步骤摘要**：

1. Claude 运行 `tag-evaluate` skill，在 `docs/active_context.md` 记录建议（打 / 不打 / 等待）
2. Human 决策（Tag Gate ⛔）
3. 如打 tag：Codex 同步 release docs → Human commit + 执行 tag → roadmap-updater 更新 tag 记录
4. 如不打/延迟：在 `docs/active_context.md` 标注原因，流程结束

---

## 可选步骤：subagent `consistency-checker` — Post-Implementation Consistency Check

在 Step 4 和 Step 5 之间可插入：

- `consistency-checker` 阅读 diff + 设计文档，产出 `consistency_report.md`
- Claude 在 Step 5 的 review 中参考此报告

此步骤不是必须的，建议在高风险 slice 或跨模块改动时使用。

---

## 异常处理

### Claude review 发现 [BLOCK] 项
→ 回到 Step 4，Codex 修改后重新提交，Claude 重新 review

### 人工在 Design Gate 打回
→ 回到 Step 2，Claude 修改 design_decision，必要时重新运行 `context-analyst` subagent 更新 context_brief

### 人工在 Merge Gate 打回
→ 根据打回原因决定回到 Step 4（实现问题）或 Step 2（设计问题）

### Agent 忘记更新状态
→ 下一个 agent 在 session 开头校验时发现不一致，先修正再继续（见 state_sync_rules.md）
