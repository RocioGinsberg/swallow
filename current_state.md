# Current State

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: phase 收口、main 稳定 checkpoint 变化、恢复入口变化、公开 tag 变化
> Anti-scope: 不维护高频推进状态、不复制 roadmap 队列、不替代 closeout 作为 phase 历史

## 文档目的

本文件用于在终端会话中断、重新打开仓库或切换设备后，快速恢复到当前稳定工作位置。

当前高频状态请看:

- `docs/active_context.md`

---

## 当前稳定 checkpoint

- repository_state: `runnable`
- latest_main_checkpoint_phase: `post-LTO-1 Wiki Compiler second-stage roadmap sync`
- latest_main_checkpoint: `25f7848 docs(state): update roadmap`
- latest_executed_public_tag: `v1.8.0`
- pending_release_tag: `none`
- current_working_phase: `lto-2-retrieval-quality-evidence-serving`
- checkpoint_type: `feature_branch_m4_validation_passed_waiting_human_commit`
- active_branch: `feat/lto-2-retrieval-quality-evidence-serving`
- last_checked: `2026-05-04`

说明:

- LTO-1 Wiki Compiler 第二阶段已 merge 到 `main` at `21f8dc8 Knowledge Authoring / LLM Wiki Compiler(authoring specialist)`。
- post-merge roadmap 已同步 at `25f7848 docs(state): update roadmap`。
- roadmap 当前近期队列为空,Direction Gate 候选中 **LTO-2 retrieval quality 增量**优先级最高,原因是 LTO-1 stage 2 已把 cross-candidate evidence dedup 风险 Roadmap-Bound 到 LTO-2。
- Codex 已产出 `docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md`;Claude / design-auditor 已产出 `plan_audit.md`(has-concerns;0 blockers / 5 concerns / 2 nits);Codex 已吸收 C1-C5 / N1-N2 到 plan。
- Human 已提交 plan/audit absorption commit `8878fd7 docs(plan): absorb lto-2 retrieval audit`,并切至 `feat/lto-2-retrieval-quality-evidence-serving`。
- M1 Source-anchor identity contract 已提交为 `f9b683a feat(wiki): add source anchor evidence identity`。
- M2 Governed evidence dedup on promotion 已提交为 `9b0a381 feat(wiki): dedupe source evidence on promotion`。
- M3 Retrieval / EvidencePack dedup 已提交为 `1590e62 feat(retrieval): dedupe evidence serving by source anchor`。
- M4 Operator report quality 已完成实现与 focused validation,等待 Human milestone commit。

---

## 当前默认继续方向

当前推荐从以下状态继续:

- active_branch: `feat/lto-2-retrieval-quality-evidence-serving`
- active_track: `Retrieval Quality`
- active_phase: `lto-2-retrieval-quality-evidence-serving`
- active_slice: `M4 operator report quality`
- workflow_status: `m4_validation_passed_waiting_human_commit`
- recommended_implementation_branch: `feat/lto-2-retrieval-quality-evidence-serving`

下一步:

1. Human 审阅并提交 M4 milestone。
2. Codex 在提交后同步进入 M5 Eval, guards, closeout prep。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读:

1. `AGENTS.md`
2. `.agents/shared/read_order.md`
3. `.agents/shared/state_sync_rules.md`
4. `docs/active_context.md`
5. `current_state.md`
6. `docs/roadmap.md`
7. `docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md`
8. `docs/plans/lto-2-retrieval-quality-evidence-serving/plan_audit.md`
9. `docs/concerns_backlog.md`
10. `docs/design/INVARIANTS.md`
11. `docs/design/KNOWLEDGE.md`
12. `docs/design/DATA_MODEL.md`
13. `docs/design/HARNESS.md`
14. `docs/engineering/CODE_ORGANIZATION.md`
15. `docs/engineering/TEST_ARCHITECTURE.md`
16. `docs/engineering/ADAPTER_DISCIPLINE.md`

---

## 最小验证命令

恢复当前 M4 validation-passed 状态时,建议至少执行以下检查:

```bash
git status --short --branch
git branch --show-current
git show --no-patch --decorate --oneline HEAD
sed -n '1,220p' docs/active_context.md
sed -n '1,220p' current_state.md
sed -n '1,260p' docs/roadmap.md
sed -n '1,260p' docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md
sed -n '1,260p' docs/plans/lto-2-retrieval-quality-evidence-serving/plan_audit.md
```

当前 M4 validation 已记录在 `docs/active_context.md`;最低状态检查:

```bash
git diff --check
```

---

## 当前已知边界

- 当前已完成 LTO-2 M4 Operator report quality,等待 Human 提交后再进入 M5 eval/guards/closeout prep。
- Human Plan Gate 已通过;实现分支为 `feat/lto-2-retrieval-quality-evidence-serving`。
- 不新增 `know_evidence` 物理表或 DATA_MODEL schema migration,除非 audit / Human 明确升级为本 phase blocker。
- 不 backfill / rewrite 既有 `evidence-<candidate>-<index>` legacy rows。
- Evidence 仍是 supporting material,不是 primary Knowledge Truth。
- 不改变 `apply_proposal` 唯一 canonical / route / policy 写入入口。
- 不绕过 Knowledge Plane facade。
- 不新增 object storage、durable background worker、Graph RAG、项目级全图谱可视化、auth/multi-user、remote worker 或 Planner/DAG。

---

## 当前建议提交范围

当前建议提交范围:

- `src/swallow/orchestration/task_report.py`
- `src/swallow/knowledge_retrieval/retrieval.py`
- `src/swallow/knowledge_retrieval/evidence_pack.py`
- `tests/unit/orchestration/test_task_report_module.py`
- `tests/test_evidence_pack.py`
- `tests/test_retrieval_adapters.py`
- `docs/active_context.md`
- `current_state.md`

建议提交信息: `feat(retrieval): surface source-anchor evidence quality`

上一提交:`1590e62 feat(retrieval): dedupe evidence serving by source anchor`。

---

## 本地基础设施

可选本地 Docker 栈位于 `~/ai-stack/`，与仓库分离。

```bash
cd ~/ai-stack
docker compose up -d new-api
docker compose up -d openwebui
docker compose ps
```

当前 LTO-2 plan gate 不要求 live HTTP / API-key dependent test。

---

## 恢复命令

重新打开仓库后，可先执行:

```bash
cd /home/rocio/projects/swallow
git status --short --branch
sed -n '1,220p' docs/active_context.md
sed -n '1,220p' current_state.md
sed -n '1,260p' docs/roadmap.md
sed -n '1,260p' docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md
sed -n '1,260p' docs/plans/lto-2-retrieval-quality-evidence-serving/plan_audit.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
