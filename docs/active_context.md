# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Governance`
- latest_completed_phase: `Phase 64`
- latest_completed_slice: `Governance Boundary LLM Path Closure + route metadata externalization + review follow-up`
- active_track: `Governance`
- active_phase: `Phase 65`
- active_slice: `Phase 65 PR / merge-prep complete`
- active_branch: `feat/phase65-truth-plane-sqlite`
- status: `phase65_pr_ready_pending_human_merge_gate`

## 当前状态说明

Phase 65 PR / merge-prep is complete on `feat/phase65-truth-plane-sqlite`.
The branch is ready for Human PR creation and Merge Gate.

Implemented scope:

- M1/S1: `route_registry` / `policy_records` / `route_change_log` / `policy_change_log` / `schema_version` schema; route registry / route policy / weights / capability profile readers now load from SQLite with legacy JSON bootstrap and default seed fallback.
- M2/S2: route metadata and policy writers now persist SQLite rows; `RouteRepo._apply_metadata_change` and `PolicyRepo._apply_policy_change` own explicit `BEGIN IMMEDIATE` transactions via `sqlite_store.get_connection(base_dir)` (`isolation_level=None`); route rollback redoes in-memory registry state from SQLite; audit rows are written in-transaction.
- M3/S3: append-only guard table set expanded 4 -> 6; `swl migrate --status` reports `schema_version: 1, pending: 0`; `DATA_MODEL.md` synced to Phase 65 schema; `INVARIANTS.md` unchanged.

Latest verification:

- `.venv/bin/python -m pytest tests/test_phase65_sqlite_truth.py -q` -> `21 passed`
- `.venv/bin/python -m pytest tests/test_governance.py -q` -> `10 passed`
- `.venv/bin/python -m pytest tests/test_meta_optimizer.py -q` -> `19 passed`
- `.venv/bin/python -m pytest tests/test_cli.py -q` -> `241 passed, 10 subtests passed`
- `.venv/bin/python -m pytest tests/test_invariant_guards.py -q` -> `25 passed`
- `.venv/bin/python -m pytest -q` -> `610 passed, 8 deselected, 10 subtests passed`
- `.venv/bin/python tests/audit_no_skip_drift.py` -> all 8 tracked guards green
- `git diff --check` -> passed
- `git diff -- docs/design/INVARIANTS.md` -> no output

Review follow-up result:

- BLOCK-1 fixed: `_write_json(application_path, ...)` now logs warning only after SQLite truth commit if the review artifact write fails.
- CONCERN-1 fixed: Phase 65 transaction failure injection coverage expanded in `tests/test_phase65_sqlite_truth.py`.
- CONCERN-2 fixed: non-trivial route round-trip fixture added with 3 routes and 5 task-family scores per route.
- NOTE-1 fixed: `DATA_MODEL.md` §8 `schema_version.slug` now matches implementation as `slug TEXT NOT NULL`.

Merge-prep outputs:

- `docs/plans/phase65/closeout.md` created.
- `docs/concerns_backlog.md` updated:Phase 61 transaction rollback concern resolved by Phase 65; Phase 65 known gaps recorded.
- `pr.md` rewritten for Phase 65 PR creation.
- `review_comments.md` verdict is `APPROVE` after Claude follow-up review.

## 当前关键文档

1. `docs/active_context.md`(本文)
2. `docs/plans/phase65/kickoff.md` / `design_decision.md` / `risk_assessment.md`(revised-after-model-review)
3. `docs/plans/phase65/context_brief.md`(claude/context-analyst)
4. `docs/plans/phase65/design_audit.md`(claude/design-auditor,verdict = NEEDS_REVISION_BEFORE_GATE)
5. `docs/plans/phase65/model_review.md`(claude + external GPT-5,verdict = BLOCK)
6. `docs/plans/phase65/commit_summary.md`(codex, implementation summary)
7. `docs/plans/phase65/consistency_report.md`(claude/consistency-checker, verdict = concerns)
8. `docs/plans/phase65/review_comments.md`(claude, verdict = APPROVE)
9. `docs/design/DATA_MODEL.md`(Phase 65 schema sync; `INVARIANTS.md` unchanged)
10. `docs/concerns_backlog.md`
11. `docs/plans/phase65/closeout.md`(codex, merge-prep closeout)
12. `pr.md`(codex, PR body draft; local ignored file)
13. `current_state.md`(merge 后待同步)
14. `docs/roadmap.md`(merge 后由 roadmap-updater factual update)

---

## 当前推进

已完成:

- **[Human]** Phase 63 已 merge 到 `main`(`a1d2418 merge: Governance Closure`)。
- **[Claude]** Phase 64 context / kickoff / design_decision / risk_assessment / model_review / design_audit 已产出并修订到可实现状态。
- **[Human]** Phase 64 Design Gate 已通过;Codex 按 M1 -> M2 -> follow-up -> review follow-up 完成实现。
- **[Codex]** M1/S1 已完成:Path B fallback chain plan 前移到 Orchestrator,Executor 不再调用 route selection helper,`test_path_b_does_not_call_provider_router` 已启用。
- **[Codex]** M1 follow-up 已完成:fallback chain override 外部化到 `.swl/route_fallbacks.json`,避免把早期内置线性链固化成长期契约。
- **[Codex]** M2/S2 已完成:Specialist internal chat-completion 统一经 `router.invoke_completion(...)`,并启用 `test_specialist_internal_llm_calls_go_through_router`。
- **[Codex]** Human-approved route registry externalization 已完成:`routes.default.json` / `.swl/routes.json` / `swl route registry show/apply` / route metadata governance 写入。
- **[Codex]** Human-approved route policy externalization 已完成:`route_policy.default.json` / `.swl/route_policy.json` / `swl route policy show/apply` / route metadata governance 写入。
- **[Codex]** 已新增 `docs/plans/phase64/commit_summary.md`,说明新增外部化内容是 Human-approved follow-up scope,避免 review 误判为设计外漂移。
- **[Claude/consistency-checker]** Phase 64 consistency report 已产出,verdict = `consistent`。
- **[Claude]** Phase 64 PR review 已产出,verdict = APPROVE。
- **[Codex]** 已消化唯一 review CONCERN:promote fallback chain resolver to `router.resolve_fallback_chain(...)`。
- **[Codex]** Phase 64 closeout 已完成;`docs/concerns_backlog.md` 已标记 G.5 guard skip placeholder resolved,并新增 indirect chat-completion URL guard gap Open concern。
- **[Codex]** 当前 merge conflict 已收敛到本文,并按 post-Phase 64 main 状态解析。
- **[Human]** Phase 64 merge 已完成(`7b38aeb Merge branch 'feat/phase64-llm-router-boundary'`,2026-04-29)。
- **[Claude/roadmap-updater]** Phase 64 post-merge factual update 已完成:§三 NO_SKIP 红灯修复行 + 治理守卫收口行 标 [已消化];§四候选 G.5 块 strikethrough(merge 日期 + closeout 引用);§五推荐顺序更新为 G ✓ → G.5 ✓ → H → D;§六治理边界 LLM 路径 + 写入治理两个维度同步标 Phase 64 完成,下一步候选 = 候选 H。
- **[Human]** Direction Gate(2026-04-29)选定下一阶段 = 候选 H(Truth Plane SQLite 一致性);Tag 决策 = 等 H 完成后整体打 `v1.4.0`(治理三段 G + G.5 + H 完整闭合)。
- **[Claude/roadmap-updater]** 已绑定 Phase 65 = 候选 H:§三 Truth Plane SQLite 行 [active in Phase 65];§四候选 H 块 标头改为 "Phase 65 active";§五推荐顺序加 "(Phase 65 active)";§七 Tag/Release 决策追踪节新增 v1.4.0 决议记录。
- **[Claude/context-analyst]** Phase 65 `docs/plans/phase65/context_brief.md` 已产出。关键发现:(a) DATA_MODEL §3.4 / §3.5 表 schema 已定义但 `sqlite_store.py` 未建表,Phase 65 是 schema 兑现 + 实装 phase;(b) `RouteRepo._apply_metadata_change` 当前 4 对 save+apply 无事务,失败导致 in-memory 与 disk 局部不一致;(c) `_emit_event` 桩函数是审计写入位置决策点(Repository 层事务内 vs 事务外);(d) Phase 64 的 5 个加载入口顺序对齐,Phase 65 不改顺序只改 reader 实装;(e) 测试 fixture 中 `tests/test_router.py:242, 265` 等有路径名 assertion 需要随迁移更新。
- **[Claude]** Phase 65 三件套 draft 已完成:**3 milestone / 3 slice**(M1 schema 兑现 + reader 切 SQLite + 一次性 migration / M2 writer 切 SQLite + `BEGIN IMMEDIATE` 事务包裹 + 审计表写入 / M3 守卫扩展 + migration 协议落地 + DATA_MODEL.md 同步)。1 高风险 slice(S2 事务边界 + in-memory ROUTE_REGISTRY redo)。**触动 DATA_MODEL.md** §3.4/§3.5/§4.2/§8(已定义未实装的兑现 + 表清单 4→6 + migration 协议落地);**INVARIANTS.md 文字不动**。Model Review Gate 推荐触发(高风险事务边界 + DATA_MODEL 实装兑现)。
- **[Claude/format-validator]** Phase 65 三件套手工核验 PASS(API quota 异常,subagent 暂调不动;通过 `head -10` 校验 frontmatter + TL;DR + status):author=claude / phase=phase65 / slice 各异 / status=draft / depends_on 含 context_brief.md。
- **[Claude/format-validator]**(2026-04-29 重跑)Phase 65 四件套(含 context_brief)PASS,frontmatter + TL;DR 全齐。
- **[Claude/design-auditor]**(2026-04-29)Phase 65 三件套审计完成,产出 `docs/plans/phase65/design_audit.md`,verdict = NEEDS_REVISION_BEFORE_GATE。Findings:**2 BLOCKER**(BLOCKER-1 Python sqlite3 隐式事务与 `BEGIN IMMEDIATE` 冲突;BLOCKER-2 `_get_connection(base_dir)` 不存在,connection access pattern 缺失)+ **4 CONCERN**(§3.4 schema 字段缺口 / §3.5 policy 持久化映射 / §8 "不允许运行时静默执行" vs dev-mode auto-migrate 直接矛盾 / action enum 不含 migration 路径) + 3 OK。
- **[Claude/model-review]**(2026-04-29)GPT-5 二次核验完成,产出 `docs/plans/phase65/model_review.md`,verdict = **BLOCK**(5 BLOCK + 9 CONCERN + 3 PASS)。把 design-auditor 的 3 个 CONCERN 升级为 BLOCK:**§3.4 schema 字段缺口威胁 P2 兑现性**、**§3.5 policy 持久化语义未定**、**§8 与 dev-mode auto-migrate 直接矛盾**;新增失败注入测试矩阵 + M1/M3 概念分离 + "Phase 65 不允许停在 M1 后" 约束等 9 个 CONCERN。Reviewer = external-model (`mcp__gpt5__chat-with-gpt5_5`)。
- **[Human]**(2026-04-29)Design 决策两条关键路径:BLOCK-5 §8 矛盾 → 路径 (i) 收紧 Phase 65 即"首次建表不算 §8 migration",§8 文字不动;BLOCK-3 §3.4 字段缺口 → 路径 (a) 加 6 个独立列(capabilities_json / taxonomy_json / execution_site / executor_family / executor_name / remote_capable)。
- **[Claude]**(2026-04-29)Phase 65 三件套修订完成至 `status: revised-after-model-review`:
  - `design_decision.md` §S1 加 BLOCK-3 列扩展决议 + BLOCK-2 connection accessor 决议 + CONCERN-4 命名分离 + CONCERN-6 audit enum;§S2 加 BLOCK-1 isolation_level=None + 事务模式模板 + BLOCK-4 policy_records 映射表 + CONCERN-1 redo 时序 + CONCERN-2 失败注入矩阵 + CONCERN-3 artifact 归类 + CONCERN-7 大小测试约束;§S3 加 BLOCK-5 §8 narrowing(首次建表不算 migration)+ DATA_MODEL §3.4 加 6 列 + §8 文字不动 + reference 一行
  - `kickoff.md` G6 改"首次建表 + schema_version 协议"(不再叫 migration);G7 DATA_MODEL §3.4 边界放宽至加 6 列;§完成条件 加"M1 不可单独 release"约束;Model Review Gate 段标 completed
  - `risk_assessment.md` 风险矩阵 9→11 条;R5 增 audit 大小测试约束;R10 新增(§8 narrowing 不充分,Phase 66+ 仍需补 migration runner);R11 新增(§3.4 加 6 列后 bootstrap / UPSERT 漏填字段)
  - 不再触发二次 model_review:5 BLOCK 已通过文字修订消化,internal 一致性由 Human Gate 把关
- **[Codex]** Phase 65 implementation completed(M1+M2+M3):route/policy truth moved to SQLite, explicit transaction + audit rows landed, append-only guard extended, `swl migrate --status` added, DATA_MODEL synced, verification green(`597 passed / 8 deselected / 10 subtests`)。
- **[Claude/consistency-checker]** Phase 65 consistency report 已产出,verdict = `concerns`。
- **[Claude]** Phase 65 review comments 已产出,verdict = `APPROVE_WITH_CONDITIONS`:1 BLOCK-CODE + 2 CONCERN + 1 NOTE。
- **[Codex]** Phase 65 review follow-up 已完成:BLOCK-1 / CONCERN-1 / CONCERN-2 / NOTE-1 均已处理;最新验证绿(`610 passed / 8 deselected / 10 subtests`)。
- **[Claude]** Phase 65 follow-up review 已完成,`review_comments.md` verdict 升级为 `APPROVE`,无 merge-blocker 遗留。
- **[Codex]** Phase 65 merge-prep 已完成:`closeout.md` / `docs/concerns_backlog.md` / `pr.md` 已同步到 PR / Merge Gate 状态。

进行中:

- 无。

待执行:

- **[Human]** Commit merge-prep artifacts, push `feat/phase65-truth-plane-sqlite`, and create PR using `pr.md`.
- **[Human]** Run Merge Gate after PR creation.
- **[Codex / 低优先]** `docs/plans/phase61/closeout.md` 第 81 行 cosmetic doc fix。

当前阻塞项:

- 无。

---

## 当前下一步

1. **[Human]** Commit current merge-prep docs and review resolution.
2. **[Human]** Push branch and create PR using `pr.md`.
3. **[Human]** Merge Gate:confirm PR description matches `pr.md` and `review_comments.md` verdict remains `APPROVE`.
4. **[Codex]** After merge to `main`, update `current_state.md` and `docs/active_context.md`.

```markdown
design_audit:
- status: completed
- artifact: docs/plans/phase65/design_audit.md
- verdict: NEEDS_REVISION_BEFORE_GATE (2 BLOCKER + 4 CONCERN + 3 OK)
- next: findings consumed by revised design; implementation now ready for review
```

```markdown
model_review:
- status: completed
- artifact: docs/plans/phase65/model_review.md
- reviewer: external-model (GPT-5 via mcp__gpt5__chat-with-gpt5_5)
- verdict: BLOCK (5 BLOCK + 9 CONCERN + 3 PASS)
- next: BLOCK items consumed by revised design; no second model_review required per phase plan
```

---

## 当前产出物

- `docs/plans/phase64/context_brief.md`(claude/context-analyst, 2026-04-29)
- `docs/plans/phase64/kickoff.md`(claude, 2026-04-29)
- `docs/plans/phase64/design_decision.md`(claude, 2026-04-29)
- `docs/plans/phase64/risk_assessment.md`(claude, 2026-04-29)
- `docs/plans/phase64/model_review.md`(claude, 2026-04-29)
- `docs/plans/phase64/design_audit.md`(claude/design-auditor, 2026-04-29)
- `docs/plans/phase64/commit_summary.md`(codex, 2026-04-29)
- `docs/plans/phase64/consistency_report.md`(claude/consistency-checker, 2026-04-29)
- `docs/plans/phase64/review_comments.md`(claude, 2026-04-29)
- `docs/plans/phase64/closeout.md`(codex, 2026-04-29)
- `docs/concerns_backlog.md`(codex, 2026-04-29)
- `src/swallow/_http_helpers.py`(codex, Phase 64)
- `src/swallow/routes.default.json`(codex, Phase 64)
- `src/swallow/route_policy.default.json`(codex, Phase 64)
- `src/swallow/router.py` / `src/swallow/orchestrator.py` / `src/swallow/executor.py` / `src/swallow/synthesis.py` / `src/swallow/agent_llm.py` / `src/swallow/cli.py` / `src/swallow/governance.py` / `src/swallow/paths.py` / `src/swallow/truth/route.py`(codex, Phase 64 implementation)
- `tests/test_router.py` / `tests/test_executor_protocol.py` / `tests/test_executor_async.py` / `tests/test_synthesis.py` / `tests/test_invariant_guards.py` / `tests/test_cli.py` / `tests/test_governance.py` / `tests/audit_no_skip_drift.py`(codex, Phase 64 verification)
- `pr.md`(codex, local ignored Phase 64 PR body)
- `docs/active_context.md`(codex, 2026-04-29, Phase 64 merge resolution)
- `docs/plans/phase65/context_brief.md`(claude/context-analyst, 2026-04-29)
- `docs/plans/phase65/kickoff.md`(claude, 2026-04-29, revised-after-model-review)
- `docs/plans/phase65/design_decision.md`(claude, 2026-04-29, revised-after-model-review)
- `docs/plans/phase65/risk_assessment.md`(claude, 2026-04-29, revised-after-model-review)
- `docs/plans/phase65/design_audit.md`(claude/design-auditor, 2026-04-29, verdict = NEEDS_REVISION_BEFORE_GATE)
- `docs/plans/phase65/model_review.md`(claude + external GPT-5, 2026-04-29, verdict = BLOCK)
- `docs/plans/phase65/commit_summary.md`(codex, 2026-04-30, implementation + review follow-up summary)
- `docs/plans/phase65/consistency_report.md`(claude/consistency-checker, 2026-04-30, verdict = concerns)
- `docs/plans/phase65/review_comments.md`(claude, 2026-04-30, verdict = APPROVE)
- `docs/plans/phase65/closeout.md`(codex, 2026-04-30, merge-prep closeout)
- `docs/concerns_backlog.md`(codex, 2026-04-30, Phase 65 closeout updates)
- `pr.md`(codex, 2026-04-30, Phase 65 PR body draft)
- `docs/design/DATA_MODEL.md`(codex, Phase 65 schema sync + review NOTE-1 fix; `INVARIANTS.md` unchanged)
- `src/swallow/sqlite_store.py` / `src/swallow/router.py` / `src/swallow/truth/route.py` / `src/swallow/truth/policy.py` / `src/swallow/consistency_audit.py` / `src/swallow/mps_policy_store.py` / `src/swallow/governance.py` / `src/swallow/cli.py`(codex, Phase 65 implementation)
- `tests/test_phase65_sqlite_truth.py` / `tests/test_invariant_guards.py` / `tests/test_router.py` / `tests/test_governance.py` / `tests/test_cli.py` / `tests/test_meta_optimizer.py`(codex, Phase 65 tests / fixture migration / review follow-up coverage)
