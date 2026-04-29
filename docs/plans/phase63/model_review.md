---
author: claude
phase: phase63
slice: design-gate
status: review
depends_on:
  - docs/plans/phase63/kickoff.md
  - docs/plans/phase63/design_decision.md
  - docs/plans/phase63/risk_assessment.md
  - docs/plans/phase63/design_audit.md
reviewer: external-model
verdict: BLOCK
---

TL;DR(2026-04-29 GPT-5 通道,via `mcp__gpt5__chat-with-gpt5_5`): verdict **BLOCK**。3 个 BLOCK(Q1 §5 矩阵-代码漂移 / Q5 SQLite WAL 中间状态可见 / Q6 Repository 是新 bypass surface)+ 3 个 CONCERN(Q2 Repository 公开-私有边界 / Q3 ACTOR_SEMANTIC_KWARGS 不全 / Q4 NO_SKIP_GUARDS 缺 M0 audit)。Phase 63 自称"消化宪法漂移"却引入了新的宪法-代码漂移,自我矛盾。必须 revised-after-model-review 才能进 Human Design Gate。

# Model Review

## Scope

通过 `mcp__gpt5__chat-with-gpt5_5` 通道送审 Phase 63 revised-after-audit 三件套。送审 packet 包含:project context(INVARIANTS 4 条核心规则、Phase 61/62 状态、5 条宪法漂移 Open)、5 slice 完整设计、风险摘要、design_audit 消化清单、6 个具体问题(Q1-Q5 + Q6 open)。GPT-5 (1M context) 单轮回应。

## Verdict

**BLOCK** — 不允许进 Human Design Gate,必须先修订设计。

## Findings

### [BLOCK] Q1 — `librarian_side_effect` token 创建 §5 矩阵-代码漂移

**外部反馈**:Phase 63 自称"消化宪法漂移",但 S2 引入 `librarian_side_effect` token + 不更新 §5 矩阵文字这一组合,事实上让 Orchestrator 获得了 stagedK 写授权,而 §5 矩阵文字仍然写 "-"。这正是本 phase 要消化的那种漂移模式("宪法 vs 代码不对齐"),把它正常化反而进一步侵蚀宪法。

**外部建议**(三选一):
1. **本 phase 内更新 §5 矩阵文字**(显式记录:Orchestrator 可通过 `apply_proposal(..., OperatorToken(source="librarian_side_effect"))` 启动 stagedK promotion)
2. 不引入新 token,把该路径重新走 cli/source 等已授权 actor / source
3. 显式宣告"宪法修订",由 Human Design Gate 审批

**Claude follow-up 决策**:**采用选项 1**。理由:
- Phase 63 本质就是治理收口,§5 矩阵更新是这个收口的合理一部分
- 选项 2 重构成本很高(orchestrator 内的 librarian-side-effect 调用站点要么改成 Specialist 行为、要么改成 Operator 行为,都不准确)
- 选项 3 增加 Human Design Gate 决策负担,且本质上等价于选项 1 + 走流程
- 修订 non-goals:把"不修改 INVARIANTS 文字"收紧为"不修改 INVARIANTS §0 / §1 / §2 / §3 / §4 / §6 / §7 / §8 等核心原则文字;§5 矩阵作为本 phase 实装的一部分允许更新一行"

### [CONCERN] Q2 — Repository 公开-私有边界需要硬守卫

**外部反馈**:Python 的 `_underscore_private` 是约定不是强制。Repository 引入私有写方法 `_promote_canonical` / `_apply_metadata_change` / `_apply_policy_change` 后,如果没有守卫,未来代码(尤其后续 Phase D)可能直接调这些私有方法绕过 `apply_proposal`。

**外部建议**:
- 守卫:`test_only_governance_calls_repository_write_methods`(只有 governance.py 可以调 Repository 私有写方法)
- 守卫:`test_no_module_outside_governance_imports_store_writes`(其他模块不能直接 import canonical / route / policy 的 store 写函数)
- design_decision 中显式声明"Repository 公开方法只允许 read,写权限只通过 governance.apply_proposal"
- 命名考虑:使用更显式的私有方法名(如 `_apply_*_from_governance_only`)

**Claude follow-up 决策**:在 S3 增加上述两条守卫(扩展 `test_only_apply_proposal_calls_private_writers` 的扫描目标到 Repository 私有方法,且禁止其他模块 import store 写函数)。命名保持现有约定(`_apply_*` / `_promote_*`),不引入冗长后缀。

### [CONCERN] Q3 — ACTOR_SEMANTIC_KWARGS 闭集不够完整

**外部反馈**:`{actor, submitted_by, caller, action, actor_name, performed_by}` 太窄。常见缺漏:
- `created_by` / `updated_by` / `modified_by` / `deleted_by`
- `requested_by` / `approved_by` / `reviewed_by` / `rejected_by` / `applied_by` / `committed_by`
- `authored_by` / `signed_by` / `issued_by` / `initiated_by` / `invoked_by`
- `owner` / `owner_id` / `user` / `user_id` / `username`
- `principal` / `principal_id` / `subject` / `subject_id`
- `identity` / `identity_id` / `agent` / `agent_id`
- `originator` / `origin` / `source_actor` / `operator` / `operator_id`
- `executor` / `executor_id` / `assignee` / `assigned_to`

而且 `action` 不是 actor-semantic — 它通常是动作类型,不是身份。包含它会有噪音。

**Claude follow-up 决策**:扩展闭集 + 移除 `action`。新闭集:
```python
ACTOR_SEMANTIC_KWARGS = frozenset({
    "actor", "actor_name", "actor_id",
    "submitted_by", "performed_by", "caller",
    "created_by", "updated_by", "modified_by", "deleted_by",
    "requested_by", "approved_by", "reviewed_by", "applied_by", "committed_by",
    "authored_by", "signed_by", "initiated_by",
    "owner", "owner_id", "user", "user_id", "username",
    "principal", "principal_id", "operator", "operator_id",
    "originator", "agent", "agent_id",
    "executor_name",  # Swallow-specific
})
```
移除 `action`,因为 `models.py:297 action="local"` 的具体语义是"动作类型"而不是 actor。S1 实装时,`models.py:297` 单独处理(若是 actor 含义,改字段名;若是动作,保留)。

### [CONCERN] Q4 — NO_SKIP_GUARDS 中途红灯没有可执行的 fallback

**外部反馈**:"phase 中途拆分"不是真实可行的 mitigation。NO_SKIP_GUARDS 红灯如果在 M3(S4)实装时大范围爆发,会被迫:(a) 在已经大的 phase 内修宽幅控制面违规、(b) 中途拆 phase 引入诡异 migration 边界、(c) 削弱守卫摧毁 phase 价值。

**外部建议**:**预实装 audit**(M0 阶段或 S1 之前)
- 把 NO_SKIP_GUARDS 的扫描以 read-only/report-only 模式先跑一次
- 记录预期 fail 集合
- 决定:小范围 → Phase 63 内修;大范围 → 预先拆 Phase 63.5(remediation only PR)

**Claude follow-up 决策**:增加 **M0 — Pre-implementation NO_SKIP audit**(在 M1 之前,Codex 实装):
- M0.1 实装 NO_SKIP_GUARDS 8 条扫描逻辑(report-only,使用 `pytest.warns` 或 print 而非 fail)
- M0.2 跑 audit,产出 `docs/plans/phase63/no_skip_audit.md`
- M0.3 Claude 评审 audit:
  - 红灯 ≤ 2 处 → 维持 Phase 63 scope,M1+ 顺序修
  - 红灯 ≥ 3 处或涉及核心模块 → 拆 Phase 63.5,Phase 63 scope 退到不含 NO_SKIP guards 严格执行

### [BLOCK] Q5 — staged 应用 + 失败回滚在 SQLite WAL 下不是 race-free

**外部反馈**:`save_route_weights → apply_route_weights → save_route_capability_profiles → apply_route_capability_profiles` 四步序列即使每步成功后 commit,中间状态(weights 已更新但 profiles 未更新)对其他 reader(CLI / web API / TUI)是**可见的**。这违反 Phase 63 自称的"零行为变化"——`rollback_failed` terminal state 也是新引入的可观测语义。

**外部建议**:三选一
1. **SQLite transaction/savepoint**:四步包在单一 SQLite transaction 内,`BEGIN IMMEDIATE` 获取写锁,全部成功才 commit;失败 rollback transaction(SQLite 原生回滚,无需手工 compensating)
2. **Staged version table**:引入 route metadata 版本暂存表,reader 只看到 latest committed version,中间状态被隐藏
3. **明确放弃零行为变化**:更新 design 文字,承认中间状态可见、`rollback_failed` 是新 terminal state

**Claude follow-up 决策**:**采用选项 1(SQLite transaction)**。理由:
- 选项 2 引入新表 + reader 路径改造,远超 phase scope
- 选项 3 削弱 phase 价值(本 phase 卖点就是零行为变化)
- 选项 1 干净:store 函数若已在内部 `BEGIN; COMMIT;`,需要 refactor 接受外部 `connection` 参数;若每个 store 函数自己开 connection,governance 层引入 `apply_proposal` connection context manager

S5 实装方式调整为:
- M0(audit slice 一并产出)中 audit 现有 store 函数的 connection 模式
- 若 store 函数已接受 `cursor` / `connection` 参数:S5 内 governance.apply_proposal 包 `BEGIN IMMEDIATE` + 失败 ROLLBACK
- 若 store 函数硬编码 connection:S5 增加 store-side refactor(每个 store 写函数增加 `*, conn: Connection | None = None` 可选参数,默认 None 时打开自己的,governance 调用时显式传入共享 conn)。这是 S5 内部的范围扩张,但可控
- 若 store-side refactor 触发回归风险过高:fallback 到选项 2(staged version table),但需 phase scope 重评估

### [BLOCK] Q6 — Repository 是新的 bypass surface

**外部反馈**:与 Q2 同源但更严重——S3 引入 Repository 后,如果没有"只有 governance 可以调 Repository 私有写方法"的硬守卫,Phase 63 把一个 bypass(orchestrator 直写 stagedK)换成了好几个潜在 bypass(任何模块都可以 import Repository 私有方法)。

**Claude follow-up 决策**:见 Q2 的 follow-up — 在 S3 增加两条守卫,这是 Q6 的具体落实。

## Claude Follow-Up

修订 design_decision.md / risk_assessment.md / kickoff.md → `revised-after-model-review`,具体:

**Phase scope 调整**:
1. 增加 **M0(Pre-implementation audit slice,无代码改动)**:NO_SKIP_GUARDS report-only audit + store connection 模式 audit。M0 产出 `docs/plans/phase63/m0_audit_report.md`,Claude 据此评估是否需要拆 Phase 63.5
2. 修订 non-goals:**允许更新 INVARIANTS §5 矩阵 Orchestrator 行 stagedK 列**(本 phase 实装的一部分)。其他 INVARIANTS 文字仍然不动
3. S5 改为 **SQLite transaction/savepoint 实装**(`BEGIN IMMEDIATE` + 单一 transaction);staged compensating rollback 退回 fallback
4. ACTOR_SEMANTIC_KWARGS 闭集扩展 + 移除 `action`

**新增守卫**(S3 内,§9 表外):
- `test_only_governance_calls_repository_write_methods`(扩展既有 `test_only_apply_proposal_calls_private_writers` 的扫描目标到 Repository 私有方法)
- `test_no_module_outside_governance_imports_store_writes`(verify `from .router import save_*` / `from .knowledge_store import *_canonical_*` 等只在 truth/*.py 内出现)

**修订风险条目**:
- R3 升级为 BLOCKER 已消化(model_review)→ 重 evaluate
- 新增 R12 — §5 矩阵更新可能与既有 INVARIANTS 文字不变假设冲突(低)
- 新增 R13 — store 函数 connection 参数 refactor 触发回归(中)
- R10 调整为更细致(连同 §3.3 know_change_log 既有字段)

## Human Gate Note

人工 Design Gate 应重点检查:
1. **§5 矩阵更新**:design_decision §S2 应包含一段更新后的 §5 矩阵 Orchestrator 行 stagedK 列内容(从 "-" 改为说明性文字),且本次修订是否合理纳入 phase scope(原 non-goals 是否需要明示删除)
2. **M0 audit slice 触发条件**:M0 报告中 NO_SKIP 红灯数量决定是否拆 Phase 63.5。Human 在 Design Gate 时应明确"若 M0 报告显示 ≥3 处红灯,Claude/Human 后续如何决策"的预案
3. **SQLite transaction 实装**:S5 中 `BEGIN IMMEDIATE` 路径 vs. fallback(staged version table)的判断标准
4. **新增 Repository bypass 守卫**:S3 守卫 `test_no_module_outside_governance_imports_store_writes` 是否过严(可能触发既有合规调用,如 ingestion/pipeline.py 4 处 `submit_staged_candidate` 是 Specialist path,§5 中是合规的)
5. **本 phase 是否仍然只 1 个 PR**:M0 加入后 phase 变重(6 slice,4-5 milestone),是否应分两 PR(M0 + Phase 63 主体 / 或 Phase 63 + Phase 63.5 后置)

如果 M0 报告显示 NO_SKIP 红灯过多,本 phase 应**先合并 M0 + 一些低风险 slice**,再拆出 Phase 63.5 处理 NO_SKIP 修复,以避免单次 PR 过大失控。
