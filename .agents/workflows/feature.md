# Workflow: Feature Delivery

标准的多角色 feature delivery 流程。每个新 phase/slice 的实现默认使用此流程。

---

## 流程总览

```
Gemini: Roadmap Check (Phase Transition)
        ↓
Claude: Roadmap Priority Review
        ↓
 Human: Direction Gate ⛔
        ↓
Gemini: Context Analysis
        ↓
Claude: Design Decomposition
        ↓
 Human: Design Gate ⛔
        ↓
 Codex: Implementation
        ↓
Claude: PR Review
        ↓
 Human: Merge Gate ⛔
```

⛔ = 人工 gate，必须由人工审批后才能继续。

---

## Step 0: Gemini, Claude & Human — Phase Transition & Direction Gate ⛔

**触发条件**：上一个 phase 已经完成 closeout 收口并合入主线。

### 常规流程（roadmap 已存在且无需刷新）

**Gemini 输入**：
- `docs/roadmap.md`（跨 phase 蓝图对齐活文档）
- `docs/plans/<prev-phase>/closeout.md`

**Gemini 动作**：
1. 增量更新 `docs/roadmap.md` 的差距总表（消化已完成差距、补充新差距）
2. 更新 `docs/active_context.md`，通知 Claude 进行优先级评审

**Claude 动作**：
1. 读取更新后的 `docs/roadmap.md`
2. 评审并更新推荐 phase 队列的优先级排序与风险批注
3. 更新 `docs/active_context.md`，通知 Human 进行方向选择

**人工动作 (Direction Gate ⛔)**：
- 阅读 `docs/roadmap.md` 的推荐 phase 队列（含 Claude 的优先级判断与风险批注）
- 选择下一个方向（如：”启动 Phase 28, R2-1”）

### 全量刷新流程（roadmap 不存在或蓝图发生重大变更）

**Gemini 输入**：
- `docs/system_tracks.md`
- `ARCHITECTURE.md` + `docs/design/*.md`
- `current_state.md`

**Gemini 产出**：
- `docs/plans/<new-phase>/design_preview.md`（演进方向决策书）
- 据此全量更新 `docs/roadmap.md` 的差距总表

**Claude 动作**：
1. 读取更新后的 roadmap + design_preview
2. 评审并更新推荐 phase 队列的优先级排序与风险批注

**人工动作 (Direction Gate ⛔)**：
- 阅读 design_preview + roadmap（含 Claude 批注），选定方向

**完成后**：
- Gemini 在接收到明确选择后更新 `docs/active_context.md`，继续执行 Step 1。

---

## Step 1: Gemini — Context Analysis

**触发条件**：人工已在 Direction Gate 中明确选定下一阶段的方向。

**输入**：
- 人工在 Step 0 指定的阶段目标决策
- `docs/roadmap.md`（差距 ID 和上下文）
- `docs/plans/<new-phase>/design_preview.md`（仅在全量刷新流程中存在）
- `docs/design/*.md`（仅阅读 roadmap 指向的相关设计文档）
- 相关 git history

**产出**：
- `docs/plans/<phase>/context_brief.md`

**完成后**：
- 更新 `docs/active_context.md`：登记产出物，下一步设为"Claude 进行方案拆解"

---

## Step 2: Claude — Design Decomposition

**触发条件**：context_brief.md 已产出。

**输入**：
- `docs/plans/<phase>/context_brief.md`
- `docs/architecture_principles.md`
- `docs/plans/<phase>/kickoff.md`

**产出**：
- `docs/plans/<phase>/design_decision.md`
- `docs/plans/<phase>/risk_assessment.md`

**附加动作**：
- 执行 `branch-advise`：建议分支名和 PR 策略
- 执行 `phase-guard`：检查是否越出 scope

**完成后**：
- 更新 `docs/active_context.md`：登记产出物，下一步设为"等待人工审批 design_decision"

---

## Step 3: Human — Design Gate ⛔

**触发条件**：design_decision.md 和 risk_assessment.md 已产出。

**人工动作**：
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
- Gemini 的 consistency_report.md（如果在 Step 4 后执行了一致性检查）

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

## 可选步骤：Gemini — Post-Implementation Consistency Check

在 Step 4 和 Step 5 之间可插入：

- Gemini 阅读 diff + 设计文档，产出 `consistency_report.md`
- Claude 在 Step 5 的 review 中参考此报告

此步骤不是必须的，建议在高风险 slice 或跨模块改动时使用。

---

## 异常处理

### Claude review 发现 [BLOCK] 项
→ 回到 Step 4，Codex 修改后重新提交，Claude 重新 review

### 人工在 Design Gate 打回
→ 回到 Step 2，Claude 修改 design_decision，可能需要 Gemini 更新 context_brief

### 人工在 Merge Gate 打回
→ 根据打回原因决定回到 Step 4（实现问题）或 Step 2（设计问题）

### Agent 忘记更新状态
→ 下一个 agent 在 session 开头校验时发现不一致，先修正再继续（见 state_sync_rules.md）
