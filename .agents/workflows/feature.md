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
Claude: Kickoff + Design Decomposition
        ↓
[subagent: design-auditor]: Pre-Implementation Design Audit
        ↓
 Human: Design Gate ⛔  (审阅 kickoff + design_decision + design_audit)
        ↓
 Codex: Implementation
        ↓
Claude: PR Review + Concern Sync  (可选: [subagent: consistency-checker] 先行)
        ↓
 Human: Merge Gate ⛔
        ↓
Codex: Post-Merge State Sync
        ↓
 [subagent: roadmap-updater]: Post-Merge Roadmap Update
        ↓
Claude: Tag Evaluation  →  Human: Tag Gate  →  Codex: Tag Sync (如打 tag)
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
- 由 Claude 主线更新 `docs/active_context.md`：登记产出物，下一步设为”Claude 进行 kickoff + 方案拆解”

---

## Step 2: Claude — Kickoff + Design Decomposition

**触发条件**：context_brief.md 已产出。

**输入**：
- `docs/plans/<phase>/context_brief.md`
- `docs/design/INVARIANTS.md`
- 相关 `docs/design/*.md`（按 roadmap / context_brief 指向按需读取）

**产出**：
- `docs/plans/<phase>/kickoff.md`
- `docs/plans/<phase>/design_decision.md`
- `docs/plans/<phase>/risk_assessment.md`
- `docs/plans/<phase>/breakdown.md`（仅当 phase 有多个 review milestones、slice > 3、或需要独立执行推进表时）

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
- 由 Claude 主线更新 `docs/active_context.md`：登记产出物，下一步设为"Human: Design Gate"

---

## Step 3: Human — Design Gate ⛔

**触发条件**：kickoff.md、design_decision.md、risk_assessment.md、design_audit.md 均已产出。

**人工动作**：
- 阅读 kickoff.md（重点看 goals / non-goals / completion conditions）
- 阅读 design_audit.md（重点看 Overall verdict 和 [BLOCKER] 项）
- 阅读 design_decision.md（重点看 TL;DR + slice 拆解 + 风险评级）
- 阅读 risk_assessment.md（重点看高风险项）
- 如有 `breakdown.md`，阅读其中的 milestone / review checkpoint 拆分
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

**触发条件**：kickoff.md 与 design_decision.md 已通过人工审批。

**输入**：
- `docs/plans/<phase>/kickoff.md`
- `docs/plans/<phase>/design_decision.md`
- `docs/plans/<phase>/breakdown.md`（如存在）
- Claude 的 branch-advise（分支名、PR 策略）
- 相关 `src/` 和 `tests/` 文件

**动作**：
- 按 Claude 建议提醒人工创建/切换分支
- 按 design_decision 中的 slice 顺序逐个实现
- 每个 slice：功能实现/测试 → Codex 记录验证结果与建议提交范围 → 状态同步
- 默认的人类审查节奏以 **milestone** 为单位，而不是强制每个低风险 slice 都先停下来等待 commit

**milestone 默认规则**：
- 如果 `design_decision.md` / `breakdown.md` 没有显式分组，则默认 `1 milestone = 1 slice`
- 高风险 slice、schema 变更、公共 CLI/API surface 变化、跨模块重构必须单独成为一个 milestone
- 低风险且边界清晰的相邻 slices 可以预先分组到同一个 milestone，在同一轮 human review 中一起审查

**每个 milestone 的人工节奏点**：
1. Human 确认当前已位于本轮 feature branch
2. Codex 完成当前 milestone 内各 slice 的最小闭环实现与测试
3. Codex 提供 milestone review/commit 方案：说明每个 slice 的验证结果，以及建议“逐 slice commit”还是“单一 milestone commit”
4. Human 审查并执行当前 milestone 的 commit
5. 当前 milestone 提交完成后，再进入下一个 milestone 或交给 Claude review

**强约束**：
- milestone 是默认 review gate；不要把整个 phase 压成一次“大包审查”
- 进入下一个 milestone 前，前一个 milestone 应已经完成人工审查和 commit
- 如 milestone 内 slices 共享文件或逻辑耦合很强，可合并为一个 milestone commit；如需要独立 rollback 边界，则仍应拆成逐 slice commit
- PR 创建前保持 milestone 级清晰历史，不再额外整理成单一汇总提交

**产出**：
- 代码改动（在 feature branch 上）
- 测试结果
- milestone 级建议 commit 命令（并附 slice → 验证结果映射）

**完成后**：
- 更新 `docs/active_context.md`：登记完成的 slice、当前分支、下一步设为"Claude 进行 PR review"

---

## Step 5: Claude — PR Review

**触发条件**：Codex 实现完成，所有 milestones 的代码和测试已由人工完成提交。

**输入**：
- Git diff（feature branch vs main）
- `docs/plans/<phase>/design_decision.md`
- `docs/plans/<phase>/context_brief.md`（按需）

**附加输入**（可选）：
- `consistency_report.md`（如果在 Step 4 后执行了一致性检查）

**产出**：
- `docs/plans/<phase>/review_comments.md`
- `docs/concerns_backlog.md`（条件更新：仅当存在 `[CONCERN]` 项时）

**附加动作**：
- 执行 `branch-advise`：确认是否可以开 PR
- 如存在 `[CONCERN]` 项，在同一轮中同步更新 `docs/concerns_backlog.md`（必要时可调用 `concern-logger` subagent，默认优先由 Claude 直接完成）
- 如有 `[BLOCK]` 项，回到 Step 4 让 Codex 修改

**完成后**：
- 更新 `docs/active_context.md`：登记评审状态，下一步设为"等待人工合并决策"
- Codex 按 `.agents/templates/pr_body.md` 模板整理 PR 内容并写入 `./pr.md`，提醒人工创建 PR

**人工 git 节奏点**：
- `./pr.md` 准备完成后，由 Human push 当前 feature branch 并创建 PR
- Claude review 完成后，如有实现修订、review 结论变化或 concern backlog 状态变化，Codex 更新 `./pr.md`，Human 视需要更新 PR 描述
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

## Step 6.5: Codex — Post-Merge State Sync

**触发条件**：PR 已 merge 到 `main`。

**动作**：
- 更新 `current_state.md`：同步最新 main checkpoint、默认恢复入口和公开 tag 之前的主线状态
- 更新 `docs/active_context.md`：标注已 merge、下一步设为"roadmap post-merge update"

**完成后**：
- 进入 Step 6.6 进行 roadmap factual update

---

## Step 6.6: Claude (main) + subagent `roadmap-updater` — Post-Merge Roadmap Update

**触发条件**：Codex 已完成 post-merge state sync。

**动作**：
- 运行 `roadmap-updater` subagent：将已 merge phase 的事实状态写回 `docs/roadmap.md`
- Claude 主线在 subagent 完成后更新 `docs/active_context.md`，下一步设为"Claude: Tag Evaluation"

---

## Step 7: Claude & Human — Tag Evaluation Gate

**触发条件**：phase 已 merge 到 main，`current_state.md`、`docs/active_context.md` 和 `docs/roadmap.md` 都已完成 post-merge 同步。

**详细流程见**：`.agents/workflows/tag_release.md`

**本步骤摘要**：

1. Claude 运行 `tag-evaluate` skill，在 `docs/active_context.md` 记录建议（打 / 不打 / 等待）
2. Human 决策（Tag Gate ⛔）
3. 如打 tag：Codex 同步 release docs → Human commit + 执行 tag → Codex 同步 tag 结果
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
