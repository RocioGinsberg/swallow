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
- checkpoint_type: `plan_audit_absorbed_ready_for_gate`
- active_branch: `main`
- last_checked: `2026-05-04`

说明:

- LTO-1 Wiki Compiler 第二阶段已 merge 到 `main` at `21f8dc8 Knowledge Authoring / LLM Wiki Compiler(authoring specialist)`。
- post-merge roadmap 已同步 at `25f7848 docs(state): update roadmap`。
- roadmap 当前近期队列为空,Direction Gate 候选中 **LTO-2 retrieval quality 增量**优先级最高,原因是 LTO-1 stage 2 已把 cross-candidate evidence dedup 风险 Roadmap-Bound 到 LTO-2。
- Codex 已产出 `docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md`;Claude / design-auditor 已产出 `plan_audit.md`(has-concerns;0 blockers / 5 concerns / 2 nits);Codex 已吸收 C1-C5 / N1-N2 到 plan。
- 当前等待 Human Plan Gate。
- 尚未切实现分支,尚未开始代码实现。

---

## 当前默认继续方向

当前推荐从以下状态继续:

- active_branch: `main`
- active_track: `Retrieval Quality`
- active_phase: `lto-2-retrieval-quality-evidence-serving`
- active_slice: `plan-definition`
- workflow_status: `plan_audit_absorbed_ready_for_gate`
- recommended_implementation_branch: `feat/lto-2-retrieval-quality-evidence-serving`

下一步:

1. Human 审阅 `docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md` 与 `plan_audit.md`,执行 Plan Gate。
2. Gate 通过后 Human 从 `main` 切出 `feat/lto-2-retrieval-quality-evidence-serving`。
3. Codex 再开始 M1 Source-anchor identity contract 实现。

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

恢复当前 plan-gate 状态时,建议至少执行以下检查:

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

当前 docs-only validation:

```bash
git diff --check
```

---

## 当前已知边界

- 当前只做 LTO-2 retrieval quality / evidence serving plan gate,不开始实现。
- 实现必须等待 Human Plan Gate。
- 不新增 `know_evidence` 物理表或 DATA_MODEL schema migration,除非 audit / Human 明确升级为本 phase blocker。
- 不 backfill / rewrite 既有 `evidence-<candidate>-<index>` legacy rows。
- Evidence 仍是 supporting material,不是 primary Knowledge Truth。
- 不改变 `apply_proposal` 唯一 canonical / route / policy 写入入口。
- 不绕过 Knowledge Plane facade。
- 不新增 object storage、durable background worker、Graph RAG、项目级全图谱可视化、auth/multi-user、remote worker 或 Planner/DAG。

---

## 当前建议提交范围

当前建议提交 LTO-2 plan-definition docs:

```bash
git add docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md \
  docs/plans/lto-2-retrieval-quality-evidence-serving/plan_audit.md \
  docs/active_context.md current_state.md
git commit -m "docs(plan): add lto-2 retrieval quality plan"
```

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
