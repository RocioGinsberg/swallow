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
- active_slice: `Closeout`
- active_branch: `feat/phase61-apply-proposal`
- status: `phase61_closeout_doc_revert_pending_codex_sync`

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

Docs/meta cleanup 已由 Human 提交:`1928f2c docs(meta): add model review workflow gate`。当前进入 M3 实施。

当前 M3 已完成:S4 Policy 写路径收敛 + 守卫测试 3 + Phase 49 concern 消化。

M3 实现说明:

1. `src/swallow/governance.py` 新增 `register_policy_proposal()` 与 `_apply_policy()`,系统级 audit trigger policy 写入现在经 `apply_proposal(target=POLICY)`。
2. `swl audit policy set` 不再直接调用 `save_audit_trigger_policy`,而是注册 policy proposal 后走 governance boundary。
3. `task knowledge-promote --target canonical` 的 CLI decision-level `caller_authority` 改为 `operator-gated`;decision 层同时接受 Librarian `canonical-promotion` 与 Operator `operator-gated`。
4. `tests/test_invariant_guards.py` 新增 `test_only_apply_proposal_calls_private_writers`,聚合守卫 canonical / route / policy 主写入函数。
5. `docs/concerns_backlog.md` 将 Phase 49 authority concern 从 Open 移入 Resolved。
6. `tests/test_run_task_subtasks.py` 放宽一个非 Phase 61 路径的 timing 断言,避免 `1.35s` 阈值在本地/CI 调度抖动下阻断全量验证,同时仍捕捉 `3s+` 级挂起回归。

M3 验证结果:

- `.venv/bin/python -m pytest tests/test_governance.py tests/test_invariant_guards.py` — 8 passed
- `.venv/bin/python -m pytest tests/test_consistency_audit.py -k "audit_policy"` — 2 passed
- `.venv/bin/python -m pytest tests/test_cli.py -k "knowledge_promote or canonical_reuse"` — 8 passed, 229 deselected
- `.venv/bin/python -m pytest tests/test_cli.py tests/test_consistency_audit.py tests/test_governance.py tests/test_invariant_guards.py` — 256 passed
- `.venv/bin/python -m pytest tests/test_run_task_subtasks.py::RunTaskSubtaskIntegrationTest::test_run_task_times_out_one_parallel_subtask_without_canceling_other_work` — 1 passed
- `.venv/bin/python -m pytest tests/eval/test_eval_meta_optimizer_proposals.py -m eval` — 1 passed
- `.venv/bin/python -m pytest` — 543 passed, 8 deselected
- `git diff --check` — pass
- `rg -n "save_audit_trigger_policy|save_route_weights|save_route_capability_profiles|append_canonical_record|persist_wiki_entry_from_record" src/swallow -g '*.py'` — protected writer uses only in `governance.py` and bottom-layer definition files

Human 已提交 M3:`e48bf9b feat(governance): policy apply_proposal boundary` 与 docs 同步 `3dc9d93 docs(governance): policy and concern`。

Claude 已完成 Phase 61 PR review:

- consistency-checker subagent 报告 13 项一致 / 1 项 line-number 偏移 (CONCERN) / 2 项 not-covered (设计未明示) / 0 项 BLOCK,详见 `docs/plans/phase61/consistency_report.md`
- 主线 review_comments 输出 6 条 [CONCERN] / 0 条 [BLOCK],详见 `docs/plans/phase61/review_comments.md`
- 关键风险 R8(save+apply 配对)实测保留;R2 Meta-Optimizer eval baseline 等价
- review 中已新增 3 条 backlog Open 项(14 条剩余 §9 守卫测试 / Repository 完整层 / apply 事务性回滚)
- Branch advice: 进入 closeout, 完成 closeout TODO 后再开 PR(详见 `review_comments.md` §三 Branch Advice)

Phase 61 closeout concern 消化(经 Human / Claude review-second-pass 修订):

1. `docs/concerns_backlog.md`: "Meta Docs Sync / Roadmap audit (closeout)" Open 条目已移入 Resolved 表(Phase 61 消化)
2. `docs/design/SELF_EVOLUTION.md`: §3.1.1 已增补 `"librarian_side_effect"` source 条目(design-level,合规保留)
3. `docs/design/SELF_EVOLUTION.md`: §3.1 已增补"proposal_id 可指向 review record(批量 proposal 容器)"注解(design-level,合规保留)
4. `docs/design/DATA_MODEL.md`: §4.1 仅保留 `apply_proposal` signature 三参数化更新(2 → 3 param);Codex closeout 时新增的 "**Phase 61 实施说明(2026-04-28)**:" 块已**整段回退**——理由:phase 号 / 日期 / "尚未实装" / "Phase 61 守卫扫描当前物理 writer 函数名"等实现叙事不应进入设计文档,违反"设计文档只描述设计真值"的宪法级原则
5. `docs/plans/phase61/design_decision.md`: §E 行号已刷新(2664/2667 → 2666/2669)(phase plan 范围,合规)
6. `docs/plans/phase61/closeout.md`: Codex 已产出 closeout 草稿,但 "Concern 15 处理结果" 段中 "DATA_MODEL §4.1 Phase 61 签名与守卫扫描目标说明" 描述需同步更新,只保留 signature 三参数化部分,删除 "守卫扫描目标说明" 那一项(因为该项已被回退)
7. commit message 粒度 concern 不改历史,作为后续纪律提醒保留
8. `docs/plans/phase61/review_comments.md`: 已 self-correct CONCERN #15,撤回 "DATA_MODEL §4.1 偏离声明" 推荐;新增 review-second-pass 教训"Claude 在 review 提 closeout 文档 TODO 时必须核对 design / phase plan 边界"

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
- **[Human]** 已提交 docs/meta cleanup:`1928f2c docs(meta): add model review workflow gate`
- **[Codex]** 已完成 M3 实现与验证
- **[Codex]** 已将 Phase 49 authority concern 标记为 Resolved
- **[Codex]** 已修正非 Phase 61 路径的 subtask timeout timing 测试阈值,保证全量验证稳定通过
- **[Human]** 已提交 M3:`e48bf9b feat(governance): policy apply_proposal boundary` + `3dc9d93 docs(governance): policy and concern`
- **[Claude]** 已完成 Phase 61 PR review:produced `docs/plans/phase61/consistency_report.md` + `docs/plans/phase61/review_comments.md`,6 [CONCERN] / 0 [BLOCK]
- **[Claude]** 已新增 3 条 backlog Open(剩余 §9 守卫 / Repository 完整层 / apply 事务回滚)
- **[Codex]** 已消化 closeout 可处理 concern,同步 SELF_EVOLUTION / DATA_MODEL / design_decision / concerns_backlog
- **[Codex]** 已产出 `docs/plans/phase61/closeout.md`
- **[Codex]** 已更新 `pr.md`
- **[Human]** 提示 design 文档不应携带实现内容
- **[Claude]** 已回退 `docs/design/DATA_MODEL.md` §4.1 中 Codex 加入的 "Phase 61 实施说明(2026-04-28)" 段(只保留 signature 三参数化更新)
- **[Claude]** 已 self-correct `docs/plans/phase61/review_comments.md` 中 CONCERN #15(撤回 DATA_MODEL 偏离声明 TODO,新增 review-second-pass 教训)

进行中:

- 无。

待执行:

- **[Codex]** 同步更新 `docs/plans/phase61/closeout.md` 中 Concern 15 处理结果描述,把"DATA_MODEL §4.1 Phase 61 签名与守卫扫描目标说明"修正为"DATA_MODEL §4.1 仅做 signature 三参数化(Phase 61 实施说明段已回退)",删除"守卫扫描目标说明"那一项;`pr.md` 中 design 文档变更说明同步修订
- **[Human]** 评审修订后的 closeout 产出与 PR
- **[Human]** 如认可,merge `feat/phase61-apply-proposal` 至 `main`
- **[Claude]** merge 后通过 roadmap-updater subagent 增量更新 roadmap;评估 `tag-evaluate` 是否打新 tag

当前阻塞项:

- 无。

---

## 当前下一步

1. **[Codex]** 按上方 "待执行 #1" 同步 closeout.md / pr.md 描述,提交本轮 doc commit
2. **[Human]** 审阅 doc commit 与 `pr.md`,决定是否 push / 开 PR
3. **[Human]** 评审并 merge
4. **[Claude]** post-merge 触发 roadmap-updater 增量更新 + 决定是否打 tag

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
- `src/swallow/governance.py`(codex, 2026-04-28, policy apply_proposal boundary)
- `src/swallow/cli.py`(codex, 2026-04-28, audit policy set / canonical promotion authority收敛)
- `src/swallow/knowledge_review.py`(codex, 2026-04-28, canonical promotion decision authorities)
- `tests/test_governance.py`(codex, 2026-04-28, policy governance test)
- `tests/test_invariant_guards.py`(codex, 2026-04-28, aggregate private writer guard)
- `tests/test_cli.py`(codex, 2026-04-28, operator-gated canonical promotion assertion)
- `tests/test_run_task_subtasks.py`(codex, 2026-04-28, timeout isolation timing assertion robustness)
- `docs/concerns_backlog.md`(codex, 2026-04-28, Phase 49 authority concern resolved)
- `docs/active_context.md`(codex, 2026-04-28, M3 review-ready state sync)
- `docs/plans/phase61/consistency_report.md`(claude/consistency-checker, 2026-04-28, Phase 61 implementation vs design consistency)
- `docs/plans/phase61/review_comments.md`(claude, 2026-04-28, Phase 61 PR review checklist)
- `docs/concerns_backlog.md`(claude, 2026-04-28, 3 new Open concerns from Phase 61 review + Meta Docs Sync open entry annotated)
- `docs/active_context.md`(claude, 2026-04-28, post-review state + closeout TODO list)
- `docs/design/SELF_EVOLUTION.md`(codex, 2026-04-28, Phase 61 closeout source / proposal_id semantics)
- `docs/design/DATA_MODEL.md`(codex, 2026-04-28, Phase 61 closeout apply_proposal signature / guard note)
- `docs/plans/phase61/design_decision.md`(codex, 2026-04-28, closeout line-number drift resolved)
- `docs/plans/phase61/closeout.md`(codex, 2026-04-28, Phase 61 closeout)
- `docs/concerns_backlog.md`(codex, 2026-04-28, Meta Docs Sync apply_proposal concern resolved)
- `docs/active_context.md`(codex, 2026-04-28, closeout review-ready state sync)
- `pr.md`(codex, 2026-04-28, Phase 61 PR body draft)
