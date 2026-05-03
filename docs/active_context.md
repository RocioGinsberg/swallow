# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Architecture / Engineering`
- latest_completed_phase: `LTO-9 Step 2 — broad CLI command-family migration`
- latest_completed_slice: `cli.py 3653 → 2672 行 (-27%) + application/commands 写命令完整化`
- active_track: `Architecture / Engineering`
- active_phase: `LTO-8 Step 2 — harness decomposition`
- active_slice: `M1 baseline and facade characterization complete; awaiting Human review/commit`
- active_branch: `feat/orchestration-lifecycle-decomposition-step2`
- status: `lto8_step2_m1_complete_awaiting_commit`

## 当前状态说明

当前 git 分支为 `feat/orchestration-lifecycle-decomposition-step2`。LTO-8 Step 2 已进入实现阶段,当前 HEAD 为:

- `8106390 docs(plan): add LTO-8 Step 2 plan`

LTO-9 Step 2 已合并到主线:

- `4229680 docs(state): update roadmap`
- `1251c3c LTO-9 Step 2 — broad CLI command-family migration` (merge commit)

LTO-9 Step 2 完整事实与 milestone 细节见 `docs/plans/surface-cli-meta-optimizer-split-step2/closeout.md`(本文不复制)。

LTO-8 Step 2 plan 已由 Codex 起草:

- `docs/plans/orchestration-lifecycle-decomposition-step2/plan.md`
- Plan 选择:把 `harness.py` 压成 import-compatible thin facade;`run_retrieval` / `run_execution` / `write_task_artifacts` 通过 wrapper 保持 patch target,实现逻辑按 retrieval / execution attempts / artifact writer / task report 模块拆分。
- 关键新增设计点:明确 helper-side `append_event` allowlist,仅允许 retrieval / executor / policy / artifact completion telemetry event,不得发 state-transition / waiting_human 类事件。
- Plan audit 5 条 concern 已吸收进 `plan.md`:
  - 新增 `Plan Audit Absorption` 节逐条记录 C-1..C-5 resolution。
  - M4 指定 `tests/test_invariant_guards.py::test_harness_helper_modules_only_emit_allowlisted_event_kinds` 作为 allowlist enforcement。
  - M5 指定 7 个 `write_task_artifacts` policy blocks、event order characterization 与 `test_grounding.py::test_write_task_artifacts_preserves_waiting_human_checkpoint_state` gate。
  - Scope/M1/M2/M3/M5 明确保留 `harness.py` builder re-export、`orchestrator.run_retrieval` / `orchestrator.write_task_artifacts` patch targets。
  - M1/M2 命名新增测试文件:`tests/unit/orchestration/test_harness_facade.py` 与 `tests/unit/orchestration/test_task_report_module.py`。

**簇 C 状态盘点**:LTO-7 / LTO-9(Step 1+Step 2)/ LTO-10 已完全终结;**只剩 LTO-8 Step 2(`harness.py` 拆分,含 event-kind allowlist 新设计点)作为簇 C 终结 phase**。LTO-9 Step 2 顺带完成 application/commands 写命令完整化(原 LTO-5 应用边界部分)。

`docs/roadmap.md` 已由 `roadmap-updater` post-merge 增量更新 + Claude 主线轻量校正,本轮一次性完成 8 项结构调整:

- §一 baseline "当前重构状态" 反映簇 C LTO-9 Step 2 + LTO-10 完全终结、只剩 LTO-8 Step 2。
- §二 簇 B 移除 LTO-3 行(已归档,编号不复用);簇 B 标题改为 "架构重构已开头 seed";12 条 LTO 总数说明编号断在 LTO-13。
- §二 簇 B LTO-5 行 **重命名 + 重定义**:从 "Interface / Application Boundary" 改为 **"Repository / Persistence Ports"**;状态注明 application/commands 与 application/queries 由 LTO-9 Step 1/Step 2 完成;下一类增量改为 "仅由真实需求触发(多 storage backend / test isolation 复杂化 / 远程 sync 评估)"。
- §二 簇 C 标题改为 "子系统解耦四金刚 + 接续";新增 LTO-13 行 **FastAPI Local Web UI Write Surface**(write 路由模式、request body schema、guard 扩展;簇 C 终结后启动)。
- §二 簇 C LTO-9 行标 "已完成"(Step 1 + Step 2);LTO-10 行已是 "已完成"。
- §二 簇 C LTO-8 行 "Step 1 已完成,Step 2 待启动";event-kind allowlist 新设计点已显化。
- §三 当前 ticket 切换:LTO-9 Step 2 出队 → **LTO-8 Step 2** 为当前 ticket;下一选择 = **LTO-13**;候选 = Wiki Compiler / 其他 LTO。
- §四 命名规则与归档:加入 LTO-3 归档说明 + v1.6.0 tag 决策注记。
- §五 推荐顺序更新:`簇 C(LTO-7→8→9→10)→ LTO-13 → Wiki Compiler → Planner/DAG`;LTO-9/LTO-10 顺位行标 "已完成";跨阶段排序依据中加入 LTO-13 说明,Wiki Compiler 依赖项从 "LTO-3/4/6" 改为 "LTO-4/6"。

候选下下阶段:

- **LTO-13 FastAPI Local Web UI Write Surface**:簇 C 终结(LTO-8 Step 2 merge)后启动;`web/api.py` 当前仅 read-only,首次引入 write 路由需新设计点(request schema / HTTP verb / error mapping / guard 扩展);调用同一份 `application/commands/*` 函数。

LTO-10 Deferred(已记 closeout / roadmap §二):

- Reviewed route metadata 支持内部进一步拆分(若有可读性收益)。
- Durable governance outbox persistence(待事件 schema 与消费者落地;`apply_outbox.py` 当前为 7 行 no-op 占位)。

LTO-9 Step 2 PR review 余项(均合并前已处理或已记录):

- BLOCKER-1 / BLOCKER-2 / CONCERN-1 已在 `7131b59 fix(cli): resolve LTO-9 Step 2 review concerns` 中处理。
- CONCERN-2:Step 1 `cli_commands/route_metadata.py` 仍直调 `apply_proposal`(closeout 已记录,不在 LTO-9 Step 2 范围)。

LTO-7 long-running follow-ups(仍开放):

- CONCERN-2 / CONCERN-3(`provider_router/router.py` 私有名字耦合、fallback 所有权)记录在 `docs/concerns_backlog.md`,触面 only。

## 当前关键文档

1. `docs/active_context.md`(本文)
2. `current_state.md`
3. `docs/roadmap.md`
4. `docs/design/INVARIANTS.md`
5. `docs/design/INTERACTION.md`
6. `docs/design/SELF_EVOLUTION.md`
7. `docs/design/ORCHESTRATION.md`
8. `docs/design/HARNESS.md`
9. `docs/engineering/CODE_ORGANIZATION.md`
10. `docs/engineering/TEST_ARCHITECTURE.md`
11. `docs/concerns_backlog.md`
12. `docs/plans/surface-cli-meta-optimizer-split-step2/closeout.md`
13. `docs/plans/surface-cli-meta-optimizer-split-step2/review_comments.md`
14. `docs/plans/orchestration-lifecycle-decomposition-step2/context_brief.md`(LTO-8 Step 2 brief,335 行,已就绪)
15. `docs/plans/orchestration-lifecycle-decomposition-step2/plan.md`(LTO-8 Step 2 plan;257 行)
16. `docs/plans/orchestration-lifecycle-decomposition-step2/plan_audit.md`(has-concerns,0 blockers / 5 concerns)

## 当前推进

已完成:

- **[Human]** LTO-9 Step 2 merged to `main` at `1251c3c`(含 review-fix 提交 `7131b59` + closeout 提交 `1cf7e2e`)。
- **[Claude / roadmap-updater]** `docs/roadmap.md` 一次性完成 8 项结构调整:
  - LTO-9 Step 2 + LTO-10 完成同步、LTO-3 归档、LTO-5 重命名为 Repository / Persistence Ports、新增 LTO-13、§三 当前 ticket 切到 LTO-8 Step 2、§四 加 LTO-3 归档与 tag 决策、§五 推荐顺序加入 LTO-13。
- **[Claude]** Roadmap 轻量校正(4 处一致性):§二 簇 B 子标题、§二 簇 C 子标题与说明、§三 副标题、§二 总开头 LTO-3 归档说明对齐。
- **[Human]** Direction Gate 已通过:针对下一方向生成 LTO-8 Step 2 `plan.md`。
- **[Codex]** 已起草 LTO-8 Step 2 plan:
  - `docs/plans/orchestration-lifecycle-decomposition-step2/plan.md`
  - 5 milestone:M1 baseline/facade characterization;M2 retrieval/report split;M3 artifact layout/record split;M4 execution attempts/telemetry split;M5 write pipeline cleanup/facade reduction。
  - Plan 明确 `harness.py` 保持 import-compatible facade,并在 M4 预先定义 helper-side event allowlist。
- **[Claude / design-auditor]** Produced plan audit:
  - `docs/plans/orchestration-lifecycle-decomposition-step2/plan_audit.md`
  - verdict: `has-concerns`, 0 blockers / 5 concerns
  - 三条具体代码级 concern 经独立交叉验证:`test_cli.py:36-39` 直接 import 4 个 harness builder 符号(CONCERN-3 成立);`test_debate_loop.py` 5 处 + `test_librarian_executor.py` patch 在 `orchestrator.*` scope(CONCERN-4 成立);`tests/unit/orchestration/` 已存在 6 个测试文件,M1 acceptance 未命名新增文件(CONCERN-5 成立)。
- **[Claude]** Plan audit concerns 概览(均非 blocker):
  - CONCERN-1 (M4): `append_event` allowlist 是新 invariant 设计点但**没有 source-text 测试支撑**;需要命名 guard(如 `test_harness_helper_modules_only_emit_allowlisted_event_kinds`),扫描 helper 模块对禁止 event kind 字符串的引用。
  - CONCERN-2 (M5): `write_task_artifacts` decomposition acceptance hand-wavy — 没列出具体子 helper、没有 sequential `append_event` 顺序的 characterization 测试、`test_grounding.py:205` 的 `waiting_human` rollback 测试未被命名为 binding gate。
  - CONCERN-3 (M3): `test_cli.py` 直接从 `swallow.orchestration.harness` import 4 个 builder 符号(`build_remote_handoff_contract_record` / `build_resume_note` / `build_retrieval_report` / `build_source_grounding`),不在 plan §6 patch-target preservation 列表;M2/M3 移动后必须在 `harness.py` 保留 re-export wrapper,否则 import break。
  - CONCERN-4 (M2/M5): `test_debate_loop.py`(5 处)与 `test_librarian_executor.py` patch 在 `orchestrator.run_retrieval` / `orchestrator.write_task_artifacts` scope,plan §6 仅列了 `harness.*` patch target,未明确 `orchestrator.py` 中 re-import 这两个符号的 wrapper 也必须保持稳定。
  - CONCERN-5 (M1): M1 acceptance "add or expand unit tests" 太弱,未命名要在 `tests/unit/orchestration/` 创建的新测试文件;Step 1 / LTO-9 Step 2 precedent 都要求显式命名。
- **[Codex]** 已吸收 5 条 plan_audit concern 到 `plan.md`:
  - 新增 `Plan Audit Absorption` 节,逐条记录 C-1..C-5 resolution。
  - C-1: M4 加入 named invariant guard `test_harness_helper_modules_only_emit_allowlisted_event_kinds`,扫描 helper module event kind allowlist。
  - C-2: M5 加入 7 个 policy evaluation blocks 目标、sequential event order characterization、`test_grounding.py::test_write_task_artifacts_preserves_waiting_human_checkpoint_state` binding gate。
  - C-3: Scope/M1/M2/M3 明确 `harness.py` compatibility exports 包括 `test_cli.py` 直接 import 的 builder 符号。
  - C-4: Scope/M2/M5 明确 `orchestrator.run_retrieval` / `orchestrator.write_task_artifacts` patch targets 需保持,并把 `tests/test_debate_loop.py` / `tests/test_librarian_executor.py` 加入 gate。
  - C-5: M1/M2 命名新增测试文件 `tests/unit/orchestration/test_harness_facade.py` / `tests/unit/orchestration/test_task_report_module.py`。
- **[Human]** Plan Gate 已通过并切换到实现分支:
  - `feat/orchestration-lifecycle-decomposition-step2`
  - `8106390 docs(plan): add LTO-8 Step 2 plan`
- **[Codex]** M1 baseline and facade characterization 已完成:
  - 新增 `tests/unit/orchestration/test_harness_facade.py`
  - 覆盖 `harness.py` compatibility exports:`run_execution` / `run_retrieval` / `run_retrieval_async` / `write_task_artifacts` / `write_task_artifacts_async` / `build_remote_handoff_contract_record` / `build_remote_handoff_contract_report` / `build_resume_note` / `build_retrieval_report` / `build_source_grounding`
  - 确认 `orchestrator.run_retrieval` / `orchestrator.write_task_artifacts` patch-target names 仍可 import
  - 建立 source grounding / retrieval report / remote handoff / resume note 的 pre-move output characterization

进行中:

- 无。

待执行:

- **[Human]** 审查并提交 M1 baseline/facade characterization。
- **[Codex]** Human 提交 M1 后开始 M2 retrieval and retrieval-report split。

当前阻塞项:

- 无 blocker。等待 Human review / commit M1。

## Tag 状态

- 最新已执行 tag: `v1.5.0`
- tag target: `bc8abb1 docs(release): sync v1.5.0 release docs`
- 当前结论: defer `v1.6.0` 到 LTO-8 Step 2 merge 后,届时簇 C 真正终结,版本号代表 "cluster C closure" 完整信号。理由:LTO-9 Step 2 是 behavior-preserving 重构,无外部能力增量;簇 C 还有 LTO-8 Step 2 这个真正的核心痛点(harness.py 2077 行 + event-kind allowlist 新设计点)未拆。

## 当前下一步

1. **[Human]** 审查并提交 M1 baseline/facade characterization。
2. **[Codex]** Human 提交 M1 后开始 M2 retrieval and retrieval-report split。

```markdown
plan_gate:
- latest_completed_phase: LTO-9 Step 2 — broad CLI command-family migration
- merge_commit (prior): 1251c3c LTO-9 Step 2 — broad CLI command-family migration
- active_branch: feat/orchestration-lifecycle-decomposition-step2
- active_phase: LTO-8 Step 2 — harness decomposition (cluster C closure phase)
- active_slice: M1 baseline and facade characterization complete; awaiting Human review/commit
- cluster_c_status: LTO-7 + LTO-9 + LTO-10 fully closed; LTO-8 Step 2 = cluster C closure
- roadmap: docs/roadmap.md current ticket = LTO-8 Step 2; next choice = LTO-13; candidates = Wiki Compiler / other LTOs
- context_brief: docs/plans/orchestration-lifecycle-decomposition-step2/context_brief.md (335 lines)
- plan: docs/plans/orchestration-lifecycle-decomposition-step2/plan.md (audit concerns absorbed)
- plan_audit: docs/plans/orchestration-lifecycle-decomposition-step2/plan_audit.md
- audit_verdict: has-concerns, 0 blockers, 5 concerns absorbed in plan.md
- closeout (prior phase): docs/plans/surface-cli-meta-optimizer-split-step2/closeout.md (status final)
- review (prior phase): recommend-merge after fixes; 0 blockers; 3 polish concerns
- new_invariant_design_point: helper-side append_event allowlist (12 telemetry kinds; state-transition kinds disallowed)
- tag_decision: defer v1.6.0 until LTO-8 Step 2 merge (cluster C closure)
- next_gate: Human M1 review/commit → Codex M2 implementation
```

## 当前产出物

- `docs/roadmap.md`(claude/roadmap-updater + claude 主线, 2026-05-03, post-merge LTO-9 Step 2 完成 + LTO-3 归档 + LTO-5 重定义 + LTO-13 新增 + §三 切换到 LTO-8 Step 2)
- `docs/plans/surface-cli-meta-optimizer-split-step2/closeout.md`(codex, 2026-05-03, LTO-9 Step 2 closeout final)
- `docs/plans/surface-cli-meta-optimizer-split-step2/review_comments.md`(claude, 2026-05-03, recommend-merge after fixes)
- `docs/plans/orchestration-lifecycle-decomposition-step2/context_brief.md`(claude/context-analyst, 2026-05-02, LTO-8 Step 2 事实盘点;direction gate 通过后启用)
- `docs/plans/orchestration-lifecycle-decomposition-step2/plan.md`(codex, 2026-05-03, LTO-8 Step 2 harness decomposition plan;已吸收 plan_audit 5 条 concern)
- `docs/plans/orchestration-lifecycle-decomposition-step2/plan_audit.md`(claude/design-auditor, 2026-05-03, has-concerns, 0 blockers / 5 concerns)
- `tests/unit/orchestration/test_harness_facade.py`(codex, 2026-05-03, M1 harness facade compatibility + builder characterization)
- `docs/active_context.md`(codex, 2026-05-03, M1 complete;awaiting Human review/commit)

## 当前验证结果

```bash
.venv/bin/python -m pytest tests/unit/orchestration/test_harness_facade.py -q
# 7 passed

.venv/bin/python -m pytest tests/unit/orchestration -q
# 42 passed

.venv/bin/python -m pytest tests/test_invariant_guards.py -q
# 26 passed

git diff --check
# passed
```
