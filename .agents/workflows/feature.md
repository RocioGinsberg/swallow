# Workflow: Feature Delivery

标准的多角色 feature delivery 流程。每个新 phase/slice 的实现默认使用此流程。

---

## 流程总览

```
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

## Step 1: Gemini — Context Analysis

**触发条件**：新 phase kickoff 已写好，或新 slice 任务已明确。

**输入**：
- `docs/plans/<phase>/kickoff.md`
- `docs/plans/<phase>/breakdown.md`（如已有）
- `docs/design/*.md`
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
- ✅ 通过：在 `docs/active_context.md` 标注"design approved"，通知 Codex 开始实现
- ❌ 打回：标注具体修改要求，回到 Step 2
- 🔄 部分通过：标注哪些 slice 可以先做，其余暂缓

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
- 每个 slice：功能实现/测试 → Codex 给出 commit 建议 → 人工执行 commit → 状态同步

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

---

## Step 6: Human — Merge Gate ⛔

**触发条件**：PR 已创建，review_comments.md 已产出。

**人工动作**：
- 阅读 PR body（包含三方产出物摘要）
- 阅读 review_comments.md
- 在 PR 上留下最终意见

**决策**：
- ✅ 合并：merge PR，在 `docs/active_context.md` 标注"merged"
- ❌ 打回：在 PR 上说明原因，回到 Step 4 或 Step 2
- 🔄 部分合并：cherry-pick 部分 commit（特殊情况）

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
