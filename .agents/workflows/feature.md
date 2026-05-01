# Workflow: Feature Delivery

标准的多角色 feature delivery 流程。每个新 phase / slice 的实现默认使用此流程。

> **当前分工原则**：Codex 主导方案定义与实现；Claude 主线不再默认承担重型方案规划，只负责 context / audit 类 subagent 协调、PR review、tag evaluation 与 concern 同步。

---

## 产出物原则

新 phase 的默认计划产物压缩为：

1. `docs/plans/<phase>/context_brief.md` — `context-analyst` subagent 产出，只写事实上下文。
2. `docs/plans/<phase>/plan.md` — Codex 产出，作为 kickoff / design / risk / milestone 的唯一计划入口。
3. `docs/plans/<phase>/plan_audit.md` — `design-auditor` subagent 产出，审计 `plan.md` 是否可实施、可验证、未越界。
4. `docs/plans/<phase>/review_comments.md` — Claude 主线在实现后产出 PR review。
5. `docs/plans/<phase>/closeout.md` — phase 收口时产出。

条件产物：

- `docs/plans/<phase>/model_review.md` — 仅高风险或 Human 要求第二模型审查时产出。
- `docs/plans/<phase>/consistency_report.md` — 高风险跨模块实现后，可由 `consistency-checker` subagent 先行产出。
- `docs/plans/<phase>/commit_summary.md` — 仅当人工提交、release note 或 PR 梳理明显受益时产出。

Legacy 兼容：

- 旧 phase 已存在的 `kickoff.md` / `design_decision.md` / `risk_assessment.md` / `breakdown.md` 仍可读取。
- 新 phase 默认不再拆这些文件；只有 Human 明确要求或 `plan.md` 已长到不可审查时，才拆出增量文档。
- 增量文档不得复制 `plan.md` 的目标、非目标、背景或风险段落。

---

## 流程总览

```text
[subagent: roadmap-updater]: Roadmap Factual Update (phase transition / post-merge)
        ↓
Codex: Direction / Candidate Planning Pass (when needed)
        ↓
Human: Direction Gate
        ↓
[subagent: context-analyst]: Context Brief
        ↓
Codex: Plan Authoring (`plan.md`)
        ↓
[subagent: design-auditor]: Plan Audit (`plan_audit.md`)
        ↓
Codex: Optimize `plan.md`
        ↓
Human: Plan Gate
        ↓
Codex: Implementation with milestone commit gates
        ↓
Claude: PR Review + Concern Sync
        ↓
Human: Merge Gate
        ↓
Codex: Post-Merge State Sync
        ↓
[subagent: roadmap-updater]: Post-Merge Roadmap Factual Update
        ↓
Claude: Tag Evaluation → Human: Tag Gate → Codex: Tag Sync (if tag)
```

Human gates are mandatory. Codex and Claude may propose, audit, or review, but Human executes commits, PR creation, merge, and tags.

---

## Step 0: Phase Transition & Direction Gate

**Trigger**: previous phase has been closed and merged, or Human asks to start a new direction.

### `roadmap-updater` subagent

When there is a completed phase to reconcile:

1. Read `docs/plans/<prev-phase>/closeout.md` and `docs/roadmap.md`.
2. Update factual completion state and consumed gaps.
3. Do not reorder future candidate priority unless explicitly scoped.

### Codex

When direction is not already clear, or Human asks for planning:

1. Read `docs/roadmap.md`, `docs/active_context.md`, and the relevant design / engineering anchors.
2. Propose the next candidate / phase ordering directly in `docs/roadmap.md` when the conversation surfaces a durable direction.
3. Keep this pass concise: candidate goal, dependency, risk, recommended order.
4. Update `docs/active_context.md` and ask Human for the Direction Gate.

### Claude

Claude main may add review or tag-related risk notes, but does not own the heavy direction plan by default.

### Human Direction Gate

Human chooses the next phase / candidate and confirms whether Codex should start plan authoring.

---

## Step 1: `context-analyst` — Context Brief

**Trigger**: Human selected the next direction.

**Input**:

- Human direction decision.
- `docs/roadmap.md`.
- `docs/active_context.md`.
- Roadmap-referenced `docs/design/*.md` and `docs/engineering/*.md`.
- Recent relevant git history and touched modules.

**Output**:

- `docs/plans/<phase>/context_brief.md`

**Rules**:

- Facts only: touched modules, recent changes, hidden coupling, risk signals.
- No goals, non-goals, implementation suggestions, or priority ranking.
- The invoking mainline agent updates `docs/active_context.md`; subagent does not.

---

## Step 2: Codex — Plan Authoring

**Trigger**: `context_brief.md` exists, or Human explicitly asks Codex to plan from roadmap/design context.

**Input**:

- `docs/plans/<phase>/context_brief.md`.
- `docs/roadmap.md`.
- `docs/design/INVARIANTS.md`.
- Roadmap / context referenced design and engineering docs.
- Relevant `src/` and `tests/` files when needed to avoid abstract planning.

**Output**:

- `docs/plans/<phase>/plan.md`

`plan.md` must contain:

- Goal and non-goals.
- Design / engineering anchors by file path.
- Slice / milestone table with scope, risk, validation, and commit gate.
- Material risks only, with mitigation or stop/go signal.
- Validation plan.
- Branch / PR recommendation.
- Completion conditions.

**Compression rules**:

- Target a concise plan that can be reviewed quickly.
- Avoid long background. Put historical detail in `context_brief.md`, not `plan.md`.
- Avoid separate `risk_assessment.md`; risk belongs next to the affected slice / milestone.
- Avoid separate `breakdown.md` unless the phase is too large for one readable plan.

**Completion**:

- Codex updates `docs/active_context.md`: register `plan.md`, set next step to `design-auditor` plan audit.

---

## Step 2.5: `design-auditor` — Plan Audit

**Trigger**: `plan.md` exists.

**Input**:

- `docs/plans/<phase>/context_brief.md`
- `docs/plans/<phase>/plan.md`
- `docs/design/INVARIANTS.md`
- Plan-referenced design / engineering docs

**Output**:

- `docs/plans/<phase>/plan_audit.md`

**Audit perspective**:

- Is each slice implementable without asking for a new planning pass?
- Are acceptance criteria testable?
- Are milestone / commit gates adequate for risk?
- Are invariant, truth write, schema, CLI/API, provider routing, or state transition risks surfaced?
- Does the plan duplicate unnecessary phase docs?

**Findings**:

- `[READY]` — no issue.
- `[CONCERN]` — implementable with explicit assumption or Human awareness.
- `[BLOCKER]` — do not enter Plan Gate until Codex revises `plan.md` or Human explicitly overrides.

**Completion**:

- Claude main or the invoking workflow owner updates `docs/active_context.md`: register `plan_audit.md`, set next step to model review gate or Human Plan Gate.

---

## Step 2.6: Claude — Model Review Gate (Conditional)

**Trigger**: `plan_audit.md` exists and Human Plan Gate has not started.

Rules live in `.agents/workflows/model_review.md`.

Default is skipped. Set required only when:

- Roadmap direction or plan boundary is uncertain.
- The plan touches invariants, schema, state transitions, truth write path, provider routing, public CLI/API, or self-evolution policy.
- `plan_audit.md` has `[BLOCKER]` or multiple `[CONCERN]`.
- Human explicitly asks for a second-model review.

If required, Claude produces `docs/plans/<phase>/model_review.md`. If skipped, Claude records skipped status and reason in `docs/active_context.md`.

---

## Step 3: Human — Plan Gate

**Trigger**:

- `plan.md` exists.
- `plan_audit.md` exists and has no unresolved `[BLOCKER]`, or Human explicitly accepts the blocker.
- Required model review is completed, or explicitly skipped by Human / Claude.

**Human reviews**:

- `context_brief.md` TL;DR for factual context.
- `plan.md` goals, non-goals, slices, risks, milestone gates, validation.
- `plan_audit.md` verdict and findings.
- `model_review.md` if present.

**Decision**:

- Pass: Human creates / switches to the feature branch, then asks Codex to implement.
- Revise: Codex updates `plan.md`, rerun audit if material.
- Partial pass: Human names the approved milestones; blocked milestones remain out of scope.

---

## Step 4: Codex — Implementation

**Trigger**: Human Plan Gate passed and feature branch is active.

**Input**:

- `plan.md`.
- `plan_audit.md` and `model_review.md` if present.
- Relevant `src/` and `tests/`.

**Actions**:

- Implement in plan order.
- Prefer the smallest operator-visible closed loop before tightening.
- For each slice: implement, test, record verification, update state when appropriate.
- Stop at each milestone gate and give Human a clear review / commit recommendation.

**Milestone rules**:

- If `plan.md` does not group milestones, default `1 milestone = 1 slice`.
- High-risk slices, schema changes, public CLI/API changes, cross-module refactors, and truth-write-path changes must stand alone as a milestone.
- Low-risk adjacent slices may share a milestone only when rollback and review remain clear.

**Human commit gate per milestone**:

1. Codex finishes the milestone and runs relevant verification.
2. Codex summarizes changed files, slice coverage, test result, and suggested commit command.
3. Human reviews and commits.
4. Only then continue to the next milestone.

**Completion**:

- Codex updates `docs/active_context.md`: implementation complete, next step Claude PR review.

---

## Optional: `consistency-checker`

Use between Step 4 and Step 5 when the implementation is high risk or cross-module.

**Output**:

- `docs/plans/<phase>/consistency_report.md`

Claude references it during PR review. It does not replace review.

---

## Step 5: Claude — PR Review

**Trigger**: Codex implementation is complete and all planned milestone commits are made by Human.

**Input**:

- Git diff of feature branch vs `main`.
- `plan.md`.
- `plan_audit.md`.
- `context_brief.md` as needed.
- `consistency_report.md` if present.

**Output**:

- `docs/plans/<phase>/review_comments.md`
- `docs/concerns_backlog.md` only when `[CONCERN]` items exist.

**Review must cover**:

- Implementation matches `plan.md`.
- Invariants and design anchors are respected.
- Tests / guard / eval coverage are sufficient for touched risk.
- No unapproved scope expansion.

**Findings**:

- `[PASS]` — acceptable.
- `[CONCERN]` — acceptable with tracked follow-up.
- `[BLOCK]` — must return to Codex implementation before merge.

After review, Codex updates `./pr.md` from `.agents/templates/pr_body.md` and tells Human the PR is ready to create / update.

---

## Step 6: Human — Merge Gate

**Trigger**:

- PR exists or Human is ready to merge locally.
- `review_comments.md` exists.
- `./pr.md` reflects the current implementation and review state.

**Merge prerequisites**:

- No unresolved `[BLOCK]`.
- Tests required by `plan.md` have been run or skipped with reason.
- Review concerns are either addressed or tracked.
- PR description matches the current repository state.

Human decides merge / revise / partial merge.

---

## Step 6.5: Codex — Post-Merge State Sync

**Trigger**: feature branch has been merged into `main`.

**Actions**:

- Update `current_state.md`.
- Update `docs/active_context.md`.
- Set next step to roadmap post-merge factual update.

---

## Step 6.6: `roadmap-updater` — Post-Merge Roadmap Factual Update

**Trigger**: Codex completed post-merge state sync.

**Actions**:

- `roadmap-updater` records completed candidate / consumed gaps.
- Claude or Codex may perform a light consistency pass depending on who is active in the session.
- `docs/active_context.md` is updated to tag evaluation or next-phase entry state.

---

## Step 7: Tag Evaluation

Detailed workflow: `.agents/workflows/tag_release.md`.

Summary:

1. Claude evaluates whether current `main` merits a tag.
2. Human decides.
3. If tagging: Codex syncs release docs, Human commits and tags, Codex syncs tag result.
4. If not tagging: record reason in `docs/active_context.md`.

---

## Exception Handling

### Plan audit has `[BLOCKER]`

Return to Step 2. Codex revises `plan.md`; rerun Step 2.5 if the change is material.

### Human rejects Plan Gate

Return to Step 2. If rejection is context-related, rerun `context-analyst`; otherwise Codex revises `plan.md`.

### Claude review has `[BLOCK]`

Return to Step 4. Codex fixes, Human commits the fix, Claude re-reviews the affected scope.

### Agent forgets state sync

The next agent must correct `docs/active_context.md` before continuing, following `.agents/shared/state_sync_rules.md`.
