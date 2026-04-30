# Current State

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: phase 收口、main 稳定 checkpoint 变化、恢复入口变化、公开 tag 变化
> Anti-scope: 不维护高频推进状态、不复制 roadmap 队列、不替代 closeout 作为 phase 历史

## 文档目的

本文件用于在终端会话中断、重新打开仓库或切换设备后，快速恢复到当前稳定工作位置。

它回答的问题是：

- 当前最近的稳定 checkpoint 是什么
- 当前默认应从哪里继续
- 恢复前需要先看哪些文件
- 最小验证命令是什么
- 当前已知边界是什么

当前高频状态请看：

- `docs/active_context.md`

---

## 当前稳定 checkpoint

- repository_state: `runnable`
- latest_main_checkpoint_phase: `Phase 68`
- latest_executed_public_tag: `v1.4.0`
- pending_release_tag: `v1.5.0`
- current_working_phase: `v1.5.0 Release Docs / Tag Prep`
- checkpoint_type: `phase68_merged_pending_v1.5.0_tag`
- active_branch: `main`
- last_checked: `2026-04-30`

说明：

- `main` 当前最新 checkpoint 为 `5cb08af merge: update knowledge plane raw material store`。
- Phase 67 已 merge 到 `main`:`eb2c743 merge: code hygiene execute`。
- Phase 68 已 merge 到 `main`:`5cb08af merge: update knowledge plane raw material store`。
- 最新已执行公开 tag 仍为 `v1.4.0`;本轮 release docs 已按 pending tag `v1.5.0` 准备,但 tag 命令尚未执行。
- Phase 67 完成 Phase 66 audit 衍生的 L+M+N cleanup 与 Candidate P module reorganization:
  - root package Python surface 收敛为 `__init__.py` + `_io_helpers.py`。
  - runtime code moved into `truth_governance/`, `orchestration/`, `provider_router/`, `knowledge_retrieval/`, `surface_tools/`。
  - read-only CLI artifact/report dispatch 改为 table-driven。
  - CLI reference 与当前 command map 同步。
- Phase 68 完成 Candidate O raw material storage boundary:
  - 新增 `RawMaterialStore` protocol / URI parser / filesystem backend / content hashing。
  - ingestion file reads 通过 `FilesystemRawMaterialStore`。
  - 新 workspace 内 ingestion source refs 使用 `file://workspace/<relative-path>`。
  - workspace 外 source refs 使用 absolute `file://` URI。
  - librarian artifact evidence checks 接受 `artifact://<task_id>/<artifact_path>` 并兼容 legacy `.swl/tasks/...` refs。
- Phase 68 未修改 Knowledge Truth schema、retrieval source type semantics 或 `docs/design/`。
- `v1.5.0` 建议作为 `v1.4.0` 之后的 storage-abstracted knowledge plane checkpoint。

---

## 当前默认继续方向

当前推荐从以下状态继续：

- active_branch: `main`
- active_track: `Release`
- active_phase: `v1.5.0 Tag Release`
- active_slice: `Release Doc Sync / Tag Prep`
- workflow_status: `v1.5.0_release_docs_ready_for_human_review`

说明：

- Release docs 已准备:
  - `README.md`
  - `current_state.md`
  - `docs/active_context.md`
  - `docs/concerns_backlog.md`
  - `docs/roadmap.md`
- 当前默认动作是 Human review release docs,提交 release docs commit,然后执行 annotated tag。
- Codex 不执行 `git commit`、`git tag` 或 `git push`。
- Human 完成 tag 后,再由 Codex 把 pending tag 状态同步为 executed tag 状态。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `current_state.md`
4. `README.md`
5. `.agents/shared/read_order.md`
6. `.agents/shared/state_sync_rules.md`
7. `.agents/workflows/tag_release.md`
8. `docs/design/INVARIANTS.md`
9. `docs/plans/phase67/closeout.md`
10. `docs/plans/phase68/closeout.md`
11. `docs/concerns_backlog.md`
12. `docs/roadmap.md`

仅在需要时再读取：

- `docs/plans/phase67/codex_review_notes_candidate_p.md`
- `docs/plans/phase68/kickoff.md`
- `docs/plans/phase68/breakdown.md`
- `docs/plans/phase68/codex_review_notes_s1.md`
- `docs/plans/phase68/codex_review_notes_s2.md`
- `docs/plans/phase68/codex_review_notes_s3.md`
- 历史 phase closeout / review_comments / archive 文档

---

## 最小验证命令

恢复工作前，建议至少执行以下检查：

```bash
git status --short --branch
git branch --show-current
git show --no-patch --decorate --oneline HEAD
git log --oneline --decorate -8
git tag --list 'v*' --sort=-creatordate | head -n 5
```

当前 tag release prep 状态验证命令：

```bash
git diff --check
git diff -- docs/design
.venv/bin/python -m compileall -q src/swallow
.venv/bin/python -m pytest -q
```

Release preflight on `main` after release-doc sync:

```bash
git diff --check
# passed

git diff -- docs/design
# no output

.venv/bin/python -m compileall -q src/swallow
# passed

.venv/bin/python -m pytest -q
# 622 passed, 8 deselected, 10 subtests passed
```

---

## 当前已知边界

- `v1.4.0` tag 已完成;不要删除或重打该 tag。
- `v1.5.0` 当前只是 pending release tag;尚未执行 tag 命令。
- Tag 命令只能在 `main` 上、release docs commit 完成后由 Human 执行。
- Phase 67 是 cleanup / module reorganization,单独不构成 release tag;Phase 68 Candidate O raw material boundary 构成本次 `v1.5.0` 的主要 release 信号。
- Phase 68 当前只实现 filesystem backend;不引入真实 S3 / MinIO / OSS client。
- 不主动推进多租户、分布式 worker、云端 truth 镜像或无边界 UI 扩张。
- 不绕过 `apply_proposal` 直接写 canonical / route / policy。
- README 当前为单文件双语结构;不要再要求同步不存在的 `README.zh-CN.md`。

---

## Release Commit / Tag 建议

建议先提交测试稳定性修复:

```bash
git add tests/test_run_task_subtasks.py
git commit -m "test(orchestration): stabilize subtask timeout isolation"
```

再提交 release docs:

```bash
git add README.md current_state.md docs/active_context.md docs/concerns_backlog.md docs/roadmap.md
git commit -m "docs(release): sync v1.5.0 release docs"
```

建议 annotated tag:

```bash
git tag -a v1.5.0 -m "v1.5.0: raw material store boundary"
git push origin main --tags
```

Human 确认 tag 完成后,通知 Codex 同步 tag result:

- `current_state.md`: `latest_executed_public_tag` 从 `v1.4.0` 更新为 `v1.5.0`,`pending_release_tag` 归零。
- `docs/active_context.md`: status 更新为 `v1.5.0_tag_completed`。

---

## 本地基础设施

Phase 46 依赖的 Docker 栈位于 `~/ai-stack/`，与仓库分离。

```bash
cd ~/ai-stack
docker compose up -d new-api
docker compose up -d openwebui
docker compose ps
```

验证 new-api 可达：

```bash
curl http://localhost:3000/api/status
```

---

## 恢复命令

重新打开仓库后，可先执行：

```bash
cd /home/rocio/projects/swallow
sed -n '1,220p' docs/active_context.md
sed -n '1,220p' current_state.md
sed -n '1,120p' README.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
