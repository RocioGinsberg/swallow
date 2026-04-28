---
author: codex
phase: 61
slice: closeout
status: review
depends_on:
  - docs/plans/phase61/kickoff.md
  - docs/plans/phase61/design_decision.md
  - docs/plans/phase61/risk_assessment.md
  - docs/plans/phase61/design_audit.md
  - docs/plans/phase61/consistency_report.md
  - docs/plans/phase61/review_comments.md
---

## TL;DR

Phase 61 已完成 `apply_proposal()` governance boundary 落地:canonical knowledge / route metadata / policy 三类主写入均经唯一入口,3 条 INVARIANTS §9 apply_proposal 守卫测试已实装。Claude review 为 0 BLOCK / 6 CONCERN;本 closeout 已消化可本轮处理的文档与 backlog concern,仅保留提交粒度历史问题与后续 phase 债务。

# Phase 61 Closeout

## 结论

Phase 61 `apply_proposal boundary` 已完成实现、review 与 closeout 文档同步,当前状态为 **ready for PR / human merge gate**。

本 phase 的核心目标是把 INVARIANTS §0 第 4 条从设计声明落实为代码边界:

- `src/swallow/governance.py` 新增 `apply_proposal()` / `OperatorToken` / `ProposalTarget` / `ApplyResult`
- canonical knowledge 主写入收敛到 `apply_proposal(target=CANONICAL_KNOWLEDGE)`
- route metadata 主写入收敛到 `apply_proposal(target=ROUTE_METADATA)`
- policy 主写入收敛到 `apply_proposal(target=POLICY)`
- `task knowledge-promote --target canonical` 的 CLI authority 统一为 `operator-gated`
- 3 条 apply_proposal 相关守卫测试落地

## Milestone 回顾

### M1: Governance API + Canonical 收敛

- 新增 governance API 与 in-memory proposal adapter
- `knowledge stage-promote`、Librarian side effect、`task knowledge-promote --target canonical` 的 canonical 主写入经 governance boundary
- 保留 `orchestrator.py` 任务启动派生索引刷新,不纳入 proposal apply 语义
- 新增 `test_canonical_write_only_via_apply_proposal`

对应提交:

- `c2d4abb feat(governance): add apply_proposal canonical boundary`

### M2: Route 收敛 + Meta-Optimizer eval baseline

- `swl proposal apply` 以 review record 作为 route metadata proposal 容器
- `apply_reviewed_optimization_proposals()` 保留公开兼容签名,内部成为 governance wrapper
- `route weights apply` / `route capabilities update` 经 governance boundary
- 保持 `save_route_weights -> apply_route_weights -> save_route_capability_profiles -> apply_route_capability_profiles` 配对顺序
- 新增 `test_route_metadata_writes_only_via_apply_proposal`

对应提交:

- `e54f7a3 feat(governance): route metadata apply_proposal boundary`

### M3: Policy 收敛 + 聚合守卫测试

- `swl audit policy set` 经 `register_policy_proposal()` + `apply_proposal(target=POLICY)`
- `knowledge_review.py` decision 层同时接受 Librarian `canonical-promotion` 与 Operator `operator-gated`
- Phase 49 authority concern 移入 Resolved
- 新增 `test_only_apply_proposal_calls_private_writers`

对应提交:

- `b7f0ecf test(orchestration): relax subtask timeout timing assertion`
- `e48bf9b feat(governance): policy apply_proposal boundary`
- `3dc9d93 docs(governance): policy and concern`

说明:`b7f0ecf` 的 commit message 与 diff 范围不完全一致,Claude review 已记录为提交粒度卫生 concern。本轮不 amend 历史,仅作为后续纪律提醒。

## Review Concern 收口

Claude review 结论:0 `[BLOCK]`,6 `[CONCERN]`。本 closeout 的处理结果:

- Concern 12(commit 粒度卫生):不改历史,记录为后续提交纪律提醒。
- Concern 13(Meta Docs Sync concern 未移入 Resolved):已在 `docs/concerns_backlog.md` 移入 Resolved。
- Concern 14(design_decision §E 行号偏移):已刷新任务启动派生写入行号为 `orchestrator.py:2666/2669`,并保留原审计行号偏移说明。
- Concern 15(SELF_EVOLUTION / DATA_MODEL 文档增量):已补 `librarian_side_effect` source、review record proposal_id 注解、DATA_MODEL §4.1 Phase 61 签名与守卫扫描目标说明。
- Concern 16(后续 backlog 未登记):Claude 已新增 3 条 Open;本 closeout 保留并确认它们仍为后续 phase 债务。
- Concern 17(`_PENDING_PROPOSALS` 生命周期):并入 Repository 抽象层 Open 条目,不在 Phase 61 继续扩张。

## 后续 Open 债务

本 phase 有意不处理以下方向,已登记在 `docs/concerns_backlog.md` Open 表:

- INVARIANTS §9 剩余 14 条非 apply_proposal 守卫测试
- 完整 Repository 抽象层与 durable proposal artifact 层
- `apply_proposal()` 批量 apply 的事务性回滚机制

这些不是 Phase 61 merge blocker,但应在后续 roadmap / phase selection 中纳入评估。

## 验证结果

实现阶段已完成:

- `.venv/bin/python -m pytest tests/test_governance.py tests/test_invariant_guards.py` — 8 passed
- `.venv/bin/python -m pytest tests/test_cli.py tests/test_consistency_audit.py tests/test_governance.py tests/test_invariant_guards.py` — 256 passed
- `.venv/bin/python -m pytest tests/eval/test_eval_meta_optimizer_proposals.py -m eval` — 1 passed
- `.venv/bin/python -m pytest` — 543 passed, 8 deselected
- `git diff --check` — pass

Closeout 文档同步后执行:

- `git diff --check` — pass

## Stop / Go 判断

### Stop

Phase 61 应停止继续扩张:

- kickoff / design_decision 定义的 M1 / M2 / M3 全部完成
- review 无 BLOCK
- closeout concern 已尽量本轮消化
- 继续处理 `_PENDING_PROPOSALS` 生命周期、Repository 类、事务回滚会自然进入新 phase 范围

### Go

建议进入 PR / merge gate:

- 当前分支可作为单 PR 合入 `main`
- merge 后由 Codex 同步 `current_state.md` / `docs/active_context.md`
- merge 后由 Claude / roadmap-updater 更新 `docs/roadmap.md`
- tag 是否发布由 Claude tag evaluation 与 Human 决策
