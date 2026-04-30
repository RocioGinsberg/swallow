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
- latest_executed_public_tag: `v1.5.0`
- pending_release_tag: `none`
- current_working_phase: `Candidate R / Real-use Feedback Observation`
- checkpoint_type: `v1.5.0_tagged_r_entry_ready`
- active_branch: `main`
- last_checked: `2026-04-30`

说明：

- `main` 当前最新 checkpoint 为 `bc8abb1 docs(release): sync v1.5.0 release docs`。
- Phase 67 已 merge 到 `main`:`eb2c743 merge: code hygiene execute`。
- Phase 68 已 merge 到 `main`:`5cb08af merge: update knowledge plane raw material store`。
- 最新已执行公开 tag 为 `v1.5.0`;annotated tag 已打在 `bc8abb1`。
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
- `v1.5.0` 是 `v1.4.0` 之后的 storage-abstracted knowledge plane checkpoint。
- R-entry 复核结论:设计不变量与当前实现足以支撑真实使用反馈观察期;剩余 Open concerns 作为观察项 / 使用边界 / 后续设计债处理。

---

## 当前默认继续方向

当前推荐从以下状态继续：

- active_branch: `main`
- active_track: `Operations`
- active_phase: `Candidate R / Real-use Feedback Observation`
- active_slice: `R-entry Readiness Gate`
- workflow_status: `r_entry_ready_after_v1.5.0_tag`

说明：

- `v1.5.0` release docs commit 与 annotated tag 已完成。
- 当前默认动作是进入 Candidate R 真实使用反馈观察期。
- 进入 R 前无需再新增 bugfix phase;若真实样本复现 Open concerns,再按具体问题开 follow-up bugfix / governance / design slice。
- Codex 不执行 `git commit`、`git tag` 或 `git push`。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `current_state.md`
4. `README.md`
5. `.agents/shared/read_order.md`
6. `.agents/shared/state_sync_rules.md`
7. `docs/design/INVARIANTS.md`
8. `docs/design/ARCHITECTURE.md`
9. `docs/design/DATA_MODEL.md`
10. `docs/design/KNOWLEDGE.md`
11. `docs/plans/phase67/closeout.md`
12. `docs/plans/phase68/closeout.md`
13. `docs/concerns_backlog.md`
14. `docs/roadmap.md`

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

当前 R-entry 状态验证命令：

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

R-entry focused design / implementation guard check:

```bash
.venv/bin/python -m pytest tests/test_invariant_guards.py tests/test_raw_material_store.py tests/test_ingestion_pipeline.py tests/test_librarian_executor.py -q
# 51 passed

.venv/bin/python -m pytest tests/test_phase65_sqlite_truth.py -q
# 21 passed
```

---

## 当前已知边界

- `v1.4.0` 与 `v1.5.0` tag 均已完成;不要删除或重打这些 tag。
- Phase 67 是 cleanup / module reorganization,单独不构成 release tag;Phase 68 Candidate O raw material boundary 构成本次 `v1.5.0` 的主要 release 信号。
- Phase 68 当前只实现 filesystem backend;不引入真实 S3 / MinIO / OSS client。
- R 阶段默认使用 fresh v1.5 workspace 或现有 v1 backfill;不要把 schema v2 migration runner、跨进程 durable proposal restore、真实 object-storage backend 当作入口条件。
- 不主动推进多租户、分布式 worker、云端 truth 镜像或无边界 UI 扩张。
- 不绕过 `apply_proposal` 直接写 canonical / route / policy。
- README 当前为单文件双语结构;不要再要求同步不存在的 `README.zh-CN.md`。

---

## R-entry Commit 建议

如接受本轮状态同步与准入判断,建议提交:

```bash
git add current_state.md docs/active_context.md docs/concerns_backlog.md docs/roadmap.md
git commit -m "docs(state): record R-entry readiness"
```

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
