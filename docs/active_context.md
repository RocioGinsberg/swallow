# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `Knowledge Authoring`
- latest_completed_phase: `lto-1-wiki-compiler-second-stage`
- latest_completed_slice: `merged to main at 21f8dc8; roadmap synced at 25f7848`
- active_track: `Retrieval Quality`
- active_phase: `lto-2-retrieval-quality-evidence-serving`
- active_slice: `plan-definition`
- active_branch: `main`
- status: `lto2_plan_audit_absorbed_ready_for_gate`

## 当前状态说明

当前 git 分支为 `main`。`docs/roadmap.md` 已把 LTO-1 Wiki Compiler 第二阶段标为完成,并将下一轮 Direction Gate 的最强候选指向 **LTO-2 retrieval quality 增量**。

本轮计划按 roadmap §三 / §五 的最高优先级信号起草:消化 LTO-1 stage 2 留下的 cross-candidate evidence dedup 风险,并把它扩展为 bounded retrieval / EvidencePack / source grounding quality increment。

当前阶段仍处于 plan gate 前:

- Codex 已产出 `docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md`。
- Claude / design-auditor 已产出 `docs/plans/lto-2-retrieval-quality-evidence-serving/plan_audit.md`(has-concerns;0 blockers / 5 concerns / 2 nits)。
- Codex 已吸收 C1-C5 / N1-N2 到 `plan.md`。
- 尚未切实现分支。
- 尚未开始代码实现。
- 下一步由 Human 执行 Plan Gate。

## 当前关键文档

1. `docs/active_context.md`(本文)
2. `current_state.md`
3. `docs/roadmap.md`
4. `docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md`
5. `docs/plans/lto-2-retrieval-quality-evidence-serving/plan_audit.md`
6. `docs/concerns_backlog.md`
7. `docs/design/INVARIANTS.md`
8. `docs/design/KNOWLEDGE.md`
9. `docs/design/DATA_MODEL.md`
10. `docs/design/HARNESS.md`
11. `docs/engineering/CODE_ORGANIZATION.md`
12. `docs/engineering/TEST_ARCHITECTURE.md`
13. `docs/engineering/ADAPTER_DISCIPLINE.md`
14. `docs/plans/retrieval-u-t-y/plan.md`
15. `docs/plans/lto-1-wiki-compiler-second-stage/closeout.md`
16. `docs/plans/lto-1-wiki-compiler-second-stage/review_comments.md`

## 当前推进

已完成:

- **[Human]** LTO-1 Wiki Compiler 第二阶段已 merge 到 `main` at `21f8dc8 Knowledge Authoring / LLM Wiki Compiler(authoring specialist)`。
- **[Claude / roadmap-updater]** post-merge roadmap 已同步 at `25f7848 docs(state): update roadmap`;roadmap 当前近期队列为空,Direction Gate 候选中 LTO-2 retrieval quality 优先级最高。
- **[Codex]** 已阅读 roadmap / active state / LTO-2 相关设计与现有 retrieval/evidence 实现,产出 LTO-2 plan。
- **[Codex]** 已完成 M0 plan/state sync:`docs/active_context.md` 与 `current_state.md` 已切到 LTO-2 plan gate 状态。
- **[Claude / design-auditor]** 已产出 `plan_audit.md`:has-concerns;0 blockers / 5 concerns / 2 nits。
- **[Codex]** 已吸收 audit:
  - C1/C2:固定 `source-anchor-v1` canonical JSON hash 输入、5 字段顺序、`heading_path` list/string 归一化。
  - C3/N1:固定 cross-task lookup 使用 `knowledge_object_exists(base_dir, evidence-src-<key>)`;不做 legacy evidence row backfill。
  - C4:固定 `derived_from` relation id 改为 source object + evidence id pair hash。
  - C5:固定 `source_anchor_key` 由 retrieval pipeline 写入 `RetrievalItem.metadata`,EvidencePack 不做 store lookup。
  - N2:固定 M4 excerpt 来源为 stored `entry_json["preview"]`,不做 fresh raw material resolution。

进行中:

- 无。当前等待 Human Plan Gate。

待执行:

- **[Human]** 审阅 plan + audit,决定是否通过 Human Plan Gate。
- **[Human]** Plan Gate 通过后,从 `main` 切出建议实现分支 `feat/lto-2-retrieval-quality-evidence-serving`。
- **[Codex]** Gate 通过且切分支后再开始 M1 implementation。

## 当前验证

计划产出后需完成:

```bash
git diff --check
git status --short --branch
```

结果:

- `git diff --check` passed。
- `git status --short --branch` 显示当前在 `main...origin/main`,仅有本次 docs plan/state 改动与新增 plan 目录。

本 phase 默认实现期验证计划已写入 `docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md` §Validation Plan。

## 当前阻塞项

- 等待 Human Plan Gate。
- 实现分支尚未创建;当前不得开始代码实现。

## Tag 状态

- 最新已执行 tag: **`v1.8.0`**
- tag target: `d6f2442 docs(release): sync v1.8.0 release docs`
- 标记意义: **LTO-1 Wiki Compiler 第一阶段落地**。
- LTO-1 第二阶段已 merge,但 roadmap / review 建议不单独 cut tag。
- 下一 tag: 无 pending decision;后续可在 LTO-2 retrieval quality / Wiki Compiler 闭环成熟后再评估 `v1.9.0`。

## 当前下一步

1. **[Human]** 审阅已吸收 audit 的 `plan.md` 与 `plan_audit.md`,决定是否通过 Human Plan Gate。
2. **[Human]** Plan Gate 通过后切到 `feat/lto-2-retrieval-quality-evidence-serving`。
3. **[Codex]** 进入 M1 Source-anchor identity contract 实现。

```markdown
plan_gate:
- latest_completed_phase: lto-1-wiki-compiler-second-stage
- latest_completed_merge: 21f8dc8 Knowledge Authoring / LLM Wiki Compiler(authoring specialist)
- latest_roadmap_sync: 25f7848 docs(state): update roadmap
- latest_release_tag: v1.8.0 at d6f2442 docs(release): sync v1.8.0 release docs
- active_branch: main
- active_track: Retrieval Quality
- active_phase: lto-2-retrieval-quality-evidence-serving
- active_slice: plan-definition
- status: lto2_plan_audit_absorbed_ready_for_gate
- roadmap: docs/roadmap.md §三 Direction Gate candidate + §五 recommendation;LTO-2 retrieval quality has strongest current trigger
- plan: docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md (Codex; status: review; audit absorbed)
- plan_audit: docs/plans/lto-2-retrieval-quality-evidence-serving/plan_audit.md (Claude/design-auditor; has-concerns; 0 blockers / 5 concerns / 2 nits)
- concerns_backlog: docs/concerns_backlog.md (LTO-1 stage 2 source-anchor dedup risk is Roadmap-Bound to LTO-2; task-scoped knowledge_evidence schema mismatch remains Active Open/deferred)
- recommended_implementation_branch: feat/lto-2-retrieval-quality-evidence-serving
- next_gate: Human Plan Gate -> branch switch
```

## 当前产出物

- `docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md`(codex, 2026-05-04, LTO-2 retrieval quality / evidence serving phase plan;audit absorbed with explicit C1-C5/N1-N2 decisions)
- `docs/plans/lto-2-retrieval-quality-evidence-serving/plan_audit.md`(claude, 2026-05-04, has-concerns — 0 blockers / 5 concerns / 2 nits; C1–C5 / N1-N2 absorbed into plan.md)
- `docs/active_context.md`(codex, 2026-05-04, plan-definition state sync to `main` + LTO-2 plan gate)
- `current_state.md`(codex, 2026-05-04, recovery checkpoint sync to post-LTO-1-stage2 roadmap state)
