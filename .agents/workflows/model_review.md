---
author: codex
phase: meta
slice: workflow
status: review
depends_on:
  - .agents/workflows/feature.md
  - .agents/claude/rules.md
  - .agents/codex/rules.md
  - docs/active_context.md
---

TL;DR:
Model Review 是 design_audit 之后、Human Design Gate 之前的条件 gate。
它只提供第二模型的设计审查意见,不写代码、不改设计正文、不替代 Human 审批。
Codex 只检查该 gate 已完成或已明确跳过,然后按设计实现。

# Workflow: Model Review Gate

> **Document discipline**
> Owner: Human
> Updater: Claude / Codex（workflow 规则变更时）
> Trigger: 需要固定第二模型设计审查流程、调整 design gate 前置条件、或变更 Claude/Codex 分工
> Anti-scope: 不保存具体 phase 的审查正文、不配置真实 provider key、不把 Codex executor 嵌入 Claude Code

---

## 目的

Model Review Gate 用于在高风险 roadmap / kickoff / design_decision 进入 Human Design Gate 前,引入一个只读、 advisory 的第二模型审查面。

本流程解决的是"设计方向是否需要独立模型复核",不是"谁来实现"。实现仍由 Codex 在 design gate 通过后承担。

---

## 权限边界

- **Claude 主线负责**判断是否需要 model review、准备输入包、吸收审查意见并修订 phase 文档。
- **外部模型/GPT/OpenAI reviewer 只负责**输出建议、风险与问题清单。
- **Human 负责**最终 Design Gate 决策。
- **Codex 负责**在实现前检查 model review gate 是否已完成或已明确跳过。

禁止事项:

- 不允许 model review 直接修改 `src/`、`tests/` 或 `docs/design/*.md`。
- 不允许 model review 替代 `design-auditor`。
- 不允许把 Codex executor 作为 Claude Code 内部插件嵌入并执行实现。
- 不允许在未拿到外部审查结果时伪造"第二模型已审查"。

---

## 触发条件

Claude 在 `design-auditor` 完成后、Human Design Gate 之前做一次判断。

默认跳过,仅在以下任一条件满足时设为 required:

- Roadmap 方向、phase 边界或优先级存在明显不确定性。
- 方案触及 `INVARIANTS.md`、`DATA_MODEL.md`、`SELF_EVOLUTION.md` 或其他宪法/设计层核心边界。
- 方案涉及 schema、CLI/API surface、state transition、truth write path、provider routing policy 等高风险改动。
- `design_audit.md` 包含 `[BLOCKER]` 或多个 `[CONCERN]`。
- Human 显式要求第二模型审查。

如果没有触发条件,Claude 在 `docs/active_context.md` 记录:

```markdown
model_review:
- status: skipped
- artifact: none
- reason: no high-risk trigger
```

---

## 输入

Claude 准备 review packet 时只读取必要文件:

- `docs/active_context.md`
- `docs/plans/<phase>/kickoff.md`
- `docs/plans/<phase>/design_decision.md`
- `docs/plans/<phase>/risk_assessment.md`
- `docs/plans/<phase>/design_audit.md`
- `docs/design/INVARIANTS.md`
- 仅当 phase 文档显式引用时,读取相关 `docs/design/*.md`

---

## 输出

Required review 的唯一正式产物:

- `docs/plans/<phase>/model_review.md`

该文件必须包含 YAML frontmatter 与 TL;DR:

```yaml
---
author: claude
phase: <phase-number>
slice: design-gate
status: review
depends_on:
  - docs/plans/<phase>/kickoff.md
  - docs/plans/<phase>/design_decision.md
  - docs/plans/<phase>/risk_assessment.md
  - docs/plans/<phase>/design_audit.md
reviewer: external-model | manual-external | unavailable
verdict: PASS | CONCERN | BLOCK | SKIPPED
---
```

正文至少包含:

- 审查范围
- 关键结论
- `[PASS]` / `[CONCERN]` / `[BLOCK]` findings
- Claude follow-up 是否需要修改 `design_decision.md` / `risk_assessment.md`
- Human Design Gate 前是否仍有阻塞项

完成后 Claude 更新 `docs/active_context.md`:

```markdown
model_review:
- status: completed | skipped | blocked
- artifact: docs/plans/<phase>/model_review.md | none
- reason: <one-line reason>
```

---

## 执行方式

推荐方式:

- 使用项目级 Claude Code skill: `.claude/skills/model-review/SKILL.md`
- 人工或 Claude 在 Step 2.6 调用 `/model-review`
- 如果当前 Claude Code session 看不到 `/model-review`,在该 skill 提交后重启 Claude Code session

允许的外部审查通道:

- Claude Code 环境中已配置的外部 GPT/OpenAI review 工具或 MCP。
- Human 手工把 review packet 发给外部模型,再把结果交回 Claude 归档。
- 后续可增加的企业内部 review adapter。

如果没有可用外部通道:

- 不伪造第二模型审查。
- 若本轮没有 required trigger,记录 skipped。
- 若本轮已有 required trigger,记录 blocked,等待 Human 决定是配置外部 review、手工提供结果,还是显式 skip。

---

## 与 Feature Workflow 的关系

插入点:

```text
Step 2.5 design-auditor
        ↓
Step 2.6 model review gate
        ↓
Step 3 Human Design Gate
```

Human Design Gate 的前置条件:

- `kickoff.md`、`design_decision.md`、`risk_assessment.md`、`design_audit.md` 已产出。
- 若 model review required,`model_review.md` 已产出且无未处理 `[BLOCK]`。
- 若 model review skipped,`docs/active_context.md` 已记录 skipped reason。

Codex Implementation 的前置条件:

- Human Design Gate 已通过。
- `design_audit.md` 无 unresolved `[BLOCKER]`。
- `model_review.status` 不是 `required` / `blocked` 的未解决状态。

---

## 成本控制

- 默认不跑 model review,只在高风险触发条件或 Human 要求时使用。
- 输出只写一个 `model_review.md`,不新增长期状态文档。
- 不让 Codex 参与 roadmap/kickoff 推理,避免实现 agent 被复杂规划上下文污染。
- 不新增 repo-local Codex plugin 或自动加载 skill,避免维护两套 agent 能力系统。
