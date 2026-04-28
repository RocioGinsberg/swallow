# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Collaboration / Workflow`
- latest_completed_phase: `Meta Docs Sync`
- latest_completed_slice: `Roadmap Audit & Closeout`
- active_track: `Architecture / Governance`
- active_phase: `Phase 61`
- active_slice: `M3: Policy 收敛 + 聚合守卫测试`
- active_branch: `feat/phase61-apply-proposal`
- status: `pre_m3_meta_cleanup_review_ready`

---

## 当前状态说明

Phase 61 目标是把 INVARIANTS §0 第 4 条要求的 `apply_proposal()` 唯一入口在代码中落地,收敛 canonical knowledge / route metadata / policy 三类 truth 的主写入路径,并补齐 3 条 apply_proposal 相关守卫测试。

Phase 61 设计产物已提交到当前 feature branch(`be401dd docs(phase61): design file generate`)。Codex 启动实施前审阅了 kickoff / context_brief / design_decision / risk_assessment / design_audit,确认 design audit 的 2 个 BLOCKER 已在 `design_decision.md` 修订稿中处理:

1. `orchestrator.py:2664-2667` 的任务启动派生刷新不纳入 `apply_proposal()` 收敛,也不进入主写入守卫扫描。
2. Meta-Optimizer 批量 apply 以 review record 作为 governance 层 `proposal_id` 适配对象,不拆成 N 次 per-entry apply。

当前 M1 已完成并由 Human 提交:`c2d4abb feat(governance): add apply_proposal canonical boundary`。

M1 实现说明:

1. 新增 `src/swallow/governance.py`,提供 `OperatorToken` / `ProposalTarget` / `ApplyResult` / `apply_proposal()`。
2. `knowledge stage-promote`、Librarian side effect、`task knowledge-promote --target canonical` 的 canonical 主写入均改为通过 `apply_proposal(target=CANONICAL_KNOWLEDGE)`。
3. `orchestrator.py:2664-2667` 的任务启动派生刷新按 design_decision §E 保留原状,不纳入主写入守卫。
4. 新增 `test_canonical_write_only_via_apply_proposal` AST 守卫测试,禁止 production caller 绕过 governance 直接调用 canonical 主写入函数。

M1 验证结果:

- `.venv/bin/python -m pytest tests/test_governance.py tests/test_invariant_guards.py` — 4 passed
- `.venv/bin/python -m pytest tests/test_cli.py -k "stage_promote or knowledge_promote_canonical or retrieve_context_includes_canonical_reuse_visible_records or create_task_preserves_existing_canonical_reuse_policy"` — 14 passed
- `.venv/bin/python -m pytest tests/test_librarian_executor.py` — 5 passed
- `.venv/bin/python -m pytest tests/test_cli.py tests/test_librarian_executor.py tests/test_governance.py tests/test_invariant_guards.py` — 246 passed
- `.venv/bin/python -m pytest` — 539 passed, 8 deselected
- `git diff --check` — pass

当前 M2 已完成:S3 Route metadata 写路径收敛 + Meta-Optimizer eval baseline。M2 的关键风险是保持 `apply_reviewed_optimization_proposals()` 的批量 apply 语义和 route registry 内存刷新配对不变。

M2 已由 Human 提交:`e54f7a3 feat(governance): route metadata apply_proposal boundary`。

M2 baseline:

- `.venv/bin/python -m pytest tests/eval/test_eval_meta_optimizer_proposals.py -m eval` — 1 passed

M2 实现说明:

1. `swl proposal apply` 现在注册 review record proposal 后直接调用 `apply_proposal(target=ROUTE_METADATA)`。
2. `apply_reviewed_optimization_proposals()` 保持公开签名不变,内部改为 governance wrapper,兼容现有调用方。
3. `swl route weights apply` 与 `swl route capabilities update` 不再直接调用 `save_route_weights` / `save_route_capability_profiles`,改为注册 route metadata payload 后调用 governance。
4. `_apply_route_metadata()` 在 governance 层保持 `save_route_weights -> apply_route_weights -> save_route_capability_profiles -> apply_route_capability_profiles` 配对顺序。
5. 新增 `test_route_metadata_writes_only_via_apply_proposal` AST 守卫测试。

M2 验证结果:

- `.venv/bin/python -m pytest tests/eval/test_eval_meta_optimizer_proposals.py -m eval` — 1 passed(实施前 baseline 与实施后均通过)
- `.venv/bin/python -m pytest tests/test_governance.py tests/test_invariant_guards.py` — 6 passed
- `.venv/bin/python -m pytest tests/test_meta_optimizer.py` — 19 passed
- `.venv/bin/python -m pytest tests/test_cli.py -k "proposal_apply or route_capabilities_update"` — 2 passed
- `.venv/bin/python -m pytest tests/test_cli.py tests/test_meta_optimizer.py tests/test_governance.py tests/test_invariant_guards.py` — 262 passed
- `.venv/bin/python -m pytest` — 541 passed, 8 deselected
- `git diff --check` — pass
- `grep -R --include='*.py' "save_route_weights\|save_route_capability_profiles" -n src/swallow --exclude=governance.py --exclude=router.py` — no matches

当前在进入 M3 前按 Human 确认执行协作流程 cleanup:

1. 删除 stale `change.md`,避免继续维护误导性的工具/agent 配置草稿。
2. 新增 `.agents/workflows/model_review.md`,固定 design_audit 后、Human Design Gate 前的条件式第二模型审查 gate。
3. 新增 Claude Code 项目 skill `.claude/skills/model-review/SKILL.md`,作为 `/model-review` 的执行入口。
4. 更新 feature workflow、Claude 规则、Codex 规则与 Codex bootstrap,明确 Claude 负责 model review 判断与消化,Codex 只在 gate resolved 后实现。

---

## 当前关键文档

1. `docs/plans/phase61/kickoff.md`
2. `docs/plans/phase61/context_brief.md`
3. `docs/plans/phase61/design_decision.md`
4. `docs/plans/phase61/risk_assessment.md`
5. `docs/plans/phase61/design_audit.md`
6. `docs/design/INVARIANTS.md`
7. `docs/design/SELF_EVOLUTION.md`
8. `docs/design/DATA_MODEL.md`
9. `docs/design/INTERACTION.md`
10. `docs/concerns_backlog.md`

---

## 当前推进

已完成:

- **[Human/Claude]** Phase 61 design docs 已产出并提交到 `feat/phase61-apply-proposal`
- **[Codex]** 已完成启动读取与状态校验
- **[Codex]** 已审阅 Phase 61 设计产物,未发现阻塞实施缺口
- **[Codex]** 已同步 active branch / active slice 状态
- **[Codex]** 已完成 M1 实现与验证
- **[Human]** 已提交 M1:`c2d4abb feat(governance): add apply_proposal canonical boundary`
- **[Codex]** 已完成 M2 eval baseline
- **[Codex]** 已完成 M2 实现与验证
- **[Human]** 已提交 M2:`e54f7a3 feat(governance): route metadata apply_proposal boundary`
- **[Codex]** 已按 Human 确认删除 stale `change.md`
- **[Codex]** 已新增 Claude 侧 model review workflow / skill,并同步 Claude/Codex gate 规则

进行中:

- 无。

待执行:

- **[Human]** 审阅本次 docs/meta cleanup diff 并决定是否提交
- **[Codex]** docs/meta cleanup 提交后进入 M3:`Policy 收敛 + 聚合守卫测试`

当前阻塞项:

- 无。

---

## 当前下一步

1. **[Human]** 审阅 docs/meta cleanup diff
2. **[Human]** 如认可,提交:`docs(meta): add model review workflow gate`
3. **[Codex]** Human 完成 docs/meta commit 后继续 M3

---

## 当前产出物

- `docs/plans/phase61/context_brief.md`(claude, 2026-04-28, Phase 61 code/design context)
- `docs/plans/phase61/kickoff.md`(claude, 2026-04-28, apply_proposal phase kickoff)
- `docs/plans/phase61/design_audit.md`(claude, 2026-04-28, design audit with original blockers)
- `docs/plans/phase61/design_decision.md`(claude, 2026-04-28, revised-after-audit implementation decision)
- `docs/plans/phase61/risk_assessment.md`(claude, 2026-04-28, revised-after-audit risk assessment)
- `src/swallow/governance.py`(codex, 2026-04-28, apply_proposal governance boundary)
- `tests/test_governance.py`(codex, 2026-04-28, governance unit tests)
- `tests/test_invariant_guards.py`(codex, 2026-04-28, canonical apply_proposal guard test)
- `src/swallow/cli.py`(codex, 2026-04-28, stage-promote canonical caller收敛)
- `src/swallow/orchestrator.py`(codex, 2026-04-28, Librarian/task canonical caller收敛)
- `src/swallow/governance.py`(codex, 2026-04-28, route metadata apply_proposal boundary)
- `src/swallow/meta_optimizer.py`(codex, 2026-04-28, reviewed proposal apply wrapper)
- `src/swallow/cli.py`(codex, 2026-04-28, route/proposal apply caller收敛)
- `tests/test_governance.py`(codex, 2026-04-28, route metadata governance test)
- `tests/test_invariant_guards.py`(codex, 2026-04-28, route metadata guard test)
- `docs/active_context.md`(codex, 2026-04-28, M2 review-ready state sync)
- `change.md`(codex, 2026-04-28, stale workflow draft removed)
- `.agents/workflows/model_review.md`(codex, 2026-04-28, conditional model review gate)
- `.claude/skills/model-review/SKILL.md`(codex, 2026-04-28, Claude Code `/model-review` project skill)
- `.agents/workflows/feature.md`(codex, 2026-04-28, feature workflow model review insertion)
- `.agents/claude/rules.md`(codex, 2026-04-28, Claude model review responsibility)
- `.agents/codex/rules.md`(codex, 2026-04-28, Codex pre-implementation gate check)
- `.agents/codex/role.md`(codex, 2026-04-28, Codex local playbooks clarified)
- `.codex/session_bootstrap.md`(codex, 2026-04-28, Codex model review boundary reminder)
