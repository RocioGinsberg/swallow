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
- latest_main_checkpoint_phase: `post-LTO-2 Retrieval Source Scoping And Truth Reuse Visibility`
- latest_main_checkpoint: `d598e58 docs(release): sync v1.9.0 release docs`
- latest_executed_public_tag: `v1.9.0`
- pending_release_tag: `none`
- current_working_phase: `none;post-merge checkpoint`
- checkpoint_type: `post_v1.9.0_tag_checkpoint`
- active_branch: `main`
- last_checked: `2026-05-04`

说明:

- LTO-1 Wiki Compiler 第二阶段已 merge 到 `main` at `21f8dc8 Knowledge Authoring / LLM Wiki Compiler(authoring specialist)`,不单独 cut tag。
- LTO-2 Retrieval Quality / Evidence Serving 已 merge 到 `main` at `03744f0`,不单独 cut tag。
- LTO-4 Test Architecture 已按压缩流程完成:CLI test split、shared builders/assertions、AST guard helper extraction、global builder fixture entry;最终 `806/825` collected、`806 passed,19 deselected`。
- 历史 phase 文档已归档到 `docs/archive_phases/` at `795aa4d docs(store): move history plans to archive`;`docs/plans/` 当前保留 R-entry runbook 与已完成的 LTO-2 source scoping phase 文档。
- R-entry Real Usage 已完成本机可验证部分并触发 `lto-2-retrieval-source-scoping`。
- LTO-2 Retrieval Source Scoping And Truth Reuse Visibility 已 merge 到 `main` at `d4288a1`。
- v1.9.0 release docs 已提交为 `d598e58 docs(release): sync v1.9.0 release docs`;tag `v1.9.0` 已打在该 commit。
- Claude review verdict:`acceptable to merge`;0 blocks / 3 tracked concerns。3 个 concerns 已聚合登记为 `docs/concerns_backlog.md` Active Open 的 `LTO-2 Source Scoping review follow-ups`。

---

## 当前默认继续方向

当前推荐从以下状态继续:

- active_branch: `main`
- active_track: `LTO-2 Retrieval Quality / Evidence Serving`
- active_phase: `none;post-merge checkpoint`
- active_slice: `post-v1.9.0 tag checkpoint`
- workflow_status: `tag_complete_ready_for_next_direction`
- recommended_implementation_branch: `none`

下一步:

1. Human 决定下一轮方向:继续 R-entry 真实使用,或从 roadmap Direction Gate 候选中选择下一 phase。
2. 如选择新 phase,Codex 按流程输出 `docs/plans/<phase>/plan.md`。
3. 如继续 R-entry,记录真实使用反馈并按需更新 `docs/plans/r-entry-real-usage/findings.md`。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读:

1. `AGENTS.md`
2. `.agents/shared/read_order.md`
3. `.agents/shared/state_sync_rules.md`
4. `docs/active_context.md`
5. `current_state.md`
6. `docs/roadmap.md`
7. `docs/plans/lto-2-retrieval-source-scoping/plan.md`
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

恢复当前 main post-merge checkpoint 状态时,建议至少执行以下检查:

```bash
git status --short --branch
git branch --show-current
git show --no-patch --decorate --oneline HEAD
sed -n '1,220p' docs/active_context.md
sed -n '1,220p' current_state.md
sed -n '1,260p' docs/roadmap.md
sed -n '1,220p' docs/plans/lto-2-retrieval-source-scoping/closeout.md
sed -n '1,220p' docs/plans/lto-2-retrieval-source-scoping/review_comments.md
sed -n '1,180p' docs/concerns_backlog.md
```

当前 post-merge checkpoint 状态已记录在 `docs/active_context.md`;最低状态检查:

```bash
git diff --check
```

---

## 当前已知边界

- 当前 `main` 已包含 LTO-2 Retrieval Source Scoping And Truth Reuse Visibility merge commit `d4288a1`。
- 不新增 Dockerfile;当前远端展示只考虑 host `swl serve` loopback + host nginx 反代到 Tailscale。
- 不把 `swl serve` 直接绑定到 `0.0.0.0` / Tailscale IP;不引入认证、多用户、公网语义。
- 不改变 `apply_proposal` 唯一 canonical / route / policy 写入入口。
- 不新增 object storage、durable background worker、Graph RAG、项目级全图谱可视化、remote worker 或 Planner/DAG。
- Review concerns C1-C3 已登记为后续项,不在 post-merge state sync 中扩 scope。

---

## 当前建议提交范围

当前 phase 已 merge,release tag 已完成:

- `d4288a1 LTO-2 Retrieval Source Scoping And Truth Reuse Visibility`
- `d598e58 docs(release): sync v1.9.0 release docs`
- `v1.9.0`

当前建议提交 tag 状态同步:

```bash
git add \
  docs/active_context.md \
  current_state.md \
  docs/roadmap.md

git commit -m "docs(state): mark v1.9.0 tagged"
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
sed -n '1,220p' docs/plans/lto-2-retrieval-source-scoping/closeout.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
