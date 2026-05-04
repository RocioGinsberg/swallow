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
- latest_main_checkpoint_phase: `post-LTO-4 Test Architecture;R-entry ready`
- latest_main_checkpoint: `ac2d3ff docs(state): mark lto4 r-entry ready`
- latest_executed_public_tag: `v1.8.0`
- pending_release_tag: `none`
- current_working_phase: `r-entry-real-usage`
- checkpoint_type: `main_post_lto4_r_entry_ready`
- active_branch: `main`
- last_checked: `2026-05-04`

说明:

- LTO-1 Wiki Compiler 第二阶段已 merge 到 `main` at `21f8dc8 Knowledge Authoring / LLM Wiki Compiler(authoring specialist)`,不单独 cut tag。
- LTO-2 Retrieval Quality / Evidence Serving 已 merge 到 `main` at `03744f0`,不单独 cut tag。
- LTO-4 Test Architecture 已按压缩流程完成:CLI test split、shared builders/assertions、AST guard helper extraction、global builder fixture entry;最终 `806/825` collected、`806 passed,19 deselected`。
- 历史 phase 文档已归档到 `docs/archive_phases/` at `795aa4d docs(store): move history plans to archive`;`docs/plans/` 当前只保留 R-entry runbook。
- 当前进入 R-entry Real Usage,入口为 `docs/plans/r-entry-real-usage/plan.md`;目标是用设计文档材料实测 CLI / knowledge / Wiki Compiler / retrieval / Web UI / Tailscale+nginx 展示链路。
- R-entry 不是新开发 phase,不走 plan audit / review / closeout,不 cut tag;真实使用 issue log 是下一 Direction Gate 的主要输入。

---

## 当前默认继续方向

当前推荐从以下状态继续:

- active_branch: `main`
- active_track: `R-entry Real Usage`
- active_phase: `r-entry-real-usage`
- active_slice: `plan ready;design-doc knowledge chain + UI/nginx smoke`
- workflow_status: `r_entry_plan_ready`
- recommended_implementation_branch: `none`

下一步:

1. Human 按 `docs/plans/r-entry-real-usage/plan.md` 执行真实使用 runbook。
2. Human 将实测问题记录到 `$BASE/notes/r-entry-issues.md`。
3. Codex 在实测完成后整理 issue log,辅助下一轮 Direction Gate。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读:

1. `AGENTS.md`
2. `.agents/shared/read_order.md`
3. `.agents/shared/state_sync_rules.md`
4. `docs/active_context.md`
5. `current_state.md`
6. `docs/roadmap.md`
7. `docs/plans/r-entry-real-usage/plan.md`
8. `docs/concerns_backlog.md`
9. `docs/design/INVARIANTS.md`
10. `docs/design/KNOWLEDGE.md`
11. `docs/design/DATA_MODEL.md`
12. `docs/design/HARNESS.md`
13. `docs/engineering/CODE_ORGANIZATION.md`
14. `docs/engineering/TEST_ARCHITECTURE.md`
15. `docs/engineering/ADAPTER_DISCIPLINE.md`

---

## 最小验证命令

恢复当前 R-entry-ready 状态时,建议至少执行以下检查:

```bash
git status --short --branch
git branch --show-current
git show --no-patch --decorate --oneline HEAD
sed -n '1,220p' docs/active_context.md
sed -n '1,220p' current_state.md
sed -n '1,260p' docs/roadmap.md
sed -n '1,260p' docs/plans/r-entry-real-usage/plan.md
sed -n '1,180p' docs/concerns_backlog.md
```

当前 post-merge 状态已记录在 `docs/active_context.md`;最低状态检查:

```bash
git diff --check
```

---

## 当前已知边界

- 当前不处于开发 phase;R-entry 只做真实使用验证与 issue logging。
- 不新增 Dockerfile;当前远端展示只考虑 host `swl serve` loopback + host nginx 反代到 Tailscale。
- 不把 `swl serve` 直接绑定到 `0.0.0.0` / Tailscale IP;不引入认证、多用户、公网语义。
- 不把本轮发现直接改成代码;先记录 issue log,再进入 Direction Gate。
- 不改变 `apply_proposal` 唯一 canonical / route / policy 写入入口。
- 不新增 object storage、durable background worker、Graph RAG、项目级全图谱可视化、remote worker 或 Planner/DAG。

---

## 当前建议提交范围

当前无实现 milestone 建议提交。本轮是 R-entry plan + state / roadmap 文档同步,建议按文档纪律拆成两个提交:

1. `docs/plans/r-entry-real-usage/plan.md`
   - `docs(plan): add r-entry real usage runbook`

2. `docs/active_context.md` + `current_state.md` + `docs/roadmap.md`
   - `docs(state): sync r-entry roadmap and state`

上一提交:`795aa4d docs(store): move history plans to archive`。

---

## 本地基础设施

可选本地 Docker 栈位于 `~/ai-stack/`，与仓库分离。

```bash
cd ~/ai-stack
docker compose up -d new-api
docker compose up -d openwebui
docker compose ps
```

当前 R-entry runbook 可使用本地 Provider Router / API-key 环境做 real Wiki Compiler draft;若环境不可用,先执行 dry-run 与 CLI/UI smoke 并记录缺口。

---

## 恢复命令

重新打开仓库后，可先执行:

```bash
cd /home/rocio/projects/swallow
git status --short --branch
sed -n '1,220p' docs/active_context.md
sed -n '1,220p' current_state.md
sed -n '1,260p' docs/roadmap.md
sed -n '1,260p' docs/plans/r-entry-real-usage/plan.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
