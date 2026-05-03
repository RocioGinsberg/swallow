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
- active_phase: `awaiting Direction Gate (LTO-8 Step 2 default)`
- active_slice: `post-merge state synced; ready for LTO-8 Step 2 plan kickoff`
- active_branch: `main`
- status: `lto9_step2_merged_lto10_closed_lto8_step2_default_next`

## 当前状态说明

当前 git 分支为 `main`,工作树干净。LTO-9 Step 2 已合并到主线:

- `1251c3c LTO-9 Step 2 — broad CLI command-family migration` (HEAD)

LTO-9 Step 2 完整事实与 milestone 细节见 `docs/plans/surface-cli-meta-optimizer-split-step2/closeout.md`(本文不复制)。

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

## 当前推进

已完成:

- **[Human]** LTO-9 Step 2 merged to `main` at `1251c3c`(含 review-fix 提交 `7131b59` + closeout 提交 `1cf7e2e`)。
- **[Claude / roadmap-updater]** `docs/roadmap.md` 一次性完成 8 项结构调整:
  - LTO-9 Step 2 + LTO-10 完成同步、LTO-3 归档、LTO-5 重命名为 Repository / Persistence Ports、新增 LTO-13、§三 当前 ticket 切到 LTO-8 Step 2、§四 加 LTO-3 归档与 tag 决策、§五 推荐顺序加入 LTO-13。
- **[Claude]** Roadmap 轻量校正(4 处一致性):§二 簇 B 子标题、§二 簇 C 子标题与说明、§三 副标题、§二 总开头 LTO-3 归档说明对齐。

进行中:

- 无。

待执行:

- **[Human]** Direction Gate 默认确认 LTO-8 Step 2 为下阶段;若需重新评估方向(例如先 LTO-13 / Wiki Compiler / 其他)需显式说明。
- **[Codex]** Direction Gate 通过后起草 LTO-8 Step 2 `plan.md`(基于 `docs/plans/orchestration-lifecycle-decomposition-step2/context_brief.md`,目标路径同目录下 `plan.md`)。
- **[Claude / design-auditor]** plan.md 产出后 plan audit。
- **[Human]** Plan Gate;通过后切 `feat/orchestration-lifecycle-decomposition-step2`(或 Codex 推荐其他名)。

当前阻塞项:

- 无 blocker。等待 Human Direction Gate(默认 LTO-8 Step 2)。

## Tag 状态

- 最新已执行 tag: `v1.5.0`
- tag target: `bc8abb1 docs(release): sync v1.5.0 release docs`
- 当前结论: defer `v1.6.0` 到 LTO-8 Step 2 merge 后,届时簇 C 真正终结,版本号代表 "cluster C closure" 完整信号。理由:LTO-9 Step 2 是 behavior-preserving 重构,无外部能力增量;簇 C 还有 LTO-8 Step 2 这个真正的核心痛点(harness.py 2077 行 + event-kind allowlist 新设计点)未拆。

## 当前下一步

1. **[Human]** Direction Gate:默认确认 LTO-8 Step 2 为下阶段;若需调整请显式说明。
2. **[Codex]** 起草 `docs/plans/orchestration-lifecycle-decomposition-step2/plan.md`(brief 已就绪,335 行)。
3. **[Claude / design-auditor]** plan.md 产出后 plan audit。
4. **[Human]** Plan Gate。

```markdown
direction_gate:
- latest_completed_phase: LTO-9 Step 2 — broad CLI command-family migration
- merge_commit: 1251c3c LTO-9 Step 2 — broad CLI command-family migration
- active_branch: main
- cluster_c_status: LTO-7 + LTO-9 + LTO-10 fully closed; LTO-8 Step 2 is the only remaining cluster C phase
- candidate_next_phase: LTO-8 Step 2 (default; brief ready) | LTO-13 (after cluster C closure) | other
- roadmap: docs/roadmap.md current ticket = LTO-8 Step 2; next choice = LTO-13; candidates = Wiki Compiler / other LTOs
- closeout (prior phase): docs/plans/surface-cli-meta-optimizer-split-step2/closeout.md (status final)
- review (prior phase): recommend-merge after fixes; 0 blockers; 3 polish concerns absorbed/recorded
- structural changes: LTO-3 archived; LTO-5 renamed/redefined as Repository / Persistence Ports; LTO-13 added (FastAPI Local Web UI Write Surface)
- tag_decision: defer v1.6.0 until LTO-8 Step 2 merge (cluster C closure)
- next_gate: Human direction → Codex plan.md → Claude plan_audit → Human Plan Gate
```

## 当前产出物

- `docs/roadmap.md`(claude/roadmap-updater + claude 主线, 2026-05-03, post-merge LTO-9 Step 2 完成 + LTO-3 归档 + LTO-5 重定义 + LTO-13 新增 + §三 切换到 LTO-8 Step 2)
- `docs/plans/surface-cli-meta-optimizer-split-step2/closeout.md`(codex, 2026-05-03, LTO-9 Step 2 closeout final)
- `docs/plans/surface-cli-meta-optimizer-split-step2/review_comments.md`(claude, 2026-05-03, recommend-merge after fixes)
- `docs/plans/orchestration-lifecycle-decomposition-step2/context_brief.md`(claude/context-analyst, 2026-05-02, LTO-8 Step 2 事实盘点;direction gate 通过后启用)
- `docs/active_context.md`(claude, 2026-05-03, post-merge state synced;awaiting Direction Gate;tag 评估记录)
