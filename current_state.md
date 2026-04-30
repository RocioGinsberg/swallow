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
- latest_main_checkpoint_phase: `Phase 66`
- latest_executed_public_tag: `v1.4.0`
- pending_release_tag: `none`
- current_working_phase: `Phase 67 Candidate P pending review`
- checkpoint_type: `phase67_candidate_p_review_gate`
- active_branch: `feat/phase67-hygiene-io-cli-cleanup`
- last_checked: `2026-04-30`

说明：

- `main` 最新稳定 checkpoint 仍是 Phase 66 merge:`596b54b merge: read-only code hygiene audit of project`。
- 当前工作分支为 `feat/phase67-hygiene-io-cli-cleanup`,Phase 67 L/M/N closeout 已完成;Human 追加要求在 merge 前实现 Candidate P module reorganization,当前等待 Human review / manual commit。
- Phase 67 完成 Phase 66 audit 衍生的 L+M+N consolidated cleanup:
  - M1:7 项 hygiene quick-win。
  - M2:`_io_helpers.py` + JSON / JSONL helper ownership。
  - M3:read-only CLI artifact/report printer dispatch table。
- Candidate P module reorganization 已完成:
  - `src/swallow/` root Python files reduced to `__init__.py` + `_io_helpers.py`。
  - runtime code moved into `truth_governance/`, `orchestration/`, `provider_router/`, `knowledge_retrieval/`, `surface_tools/`。
  - `swl` entry point now targets `swallow.surface_tools.cli:main`。
- Phase 67 final review verdict:`APPROVE`(`docs/plans/phase67/review_comments_block_n.md`)。
- Candidate P final verification:`.venv/bin/python -m pytest -q` → `610 passed, 8 deselected, 10 subtests passed`。
- Phase 67 未修改 `docs/design/`。
- 最新公开 tag 仍为 `v1.4.0`;Phase 67 review 建议 cleanup phase 不打 release tag。

---

## 当前默认继续方向

当前推荐从以下状态继续：

- active_branch: `feat/phase67-hygiene-io-cli-cleanup`
- active_track: `Refactor / Hygiene + Design / Refactor + Refactor / Surface`
- active_phase: `Phase 67`
- active_slice: `Candidate P / Module Reorganization`
- workflow_status: `phase67_candidate_p_complete_pending_human_review`

说明：

- Candidate P 已完成实现和验证,不应继续扩大到 Candidate O / R 或其他 roadmap 项。
- 当前默认动作是 Human review Candidate P diff,提交 module reorganization milestone,然后进入 PR / merge gate。
- merge 后再进行 post-merge state sync / roadmap factual update。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `current_state.md`
4. `.agents/shared/read_order.md`
5. `.agents/shared/state_sync_rules.md`
6. `docs/design/INVARIANTS.md`
7. `docs/plans/phase66/closeout.md`
8. `docs/plans/phase67/closeout.md`
9. `docs/plans/phase67/codex_review_notes_candidate_p.md`
10. `docs/plans/phase67/review_comments_block_n.md`
11. `docs/concerns_backlog.md`
12. `docs/roadmap.md`

仅在需要时再读取：

- `CLAUDE.md`
- `.codex/session_bootstrap.md`
- `.agents/workflows/feature.md`
- `.agents/workflows/tag_release.md`
- `docs/plans/phase66/kickoff.md`
- `docs/plans/phase66/design_decision.md`
- `docs/plans/phase66/risk_assessment.md`
- `docs/plans/phase66/audit_index.md`
- Phase 66 block audit reports
- `docs/plans/phase67/codex_review_notes_block_l.md`
- `docs/plans/phase67/codex_review_notes_block_m.md`
- `docs/plans/phase67/codex_review_notes_block_n.md`
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

当前 Phase 67 merge-gate 状态验证命令：

```bash
git diff --check
git diff -- docs/design
git status --short --branch
.venv/bin/python -m pytest -q
```

Phase 67 Candidate P 最近一次验证：

```bash
git diff --check
# passed

git diff -- docs/design
# no output

.venv/bin/python -m pytest -q
# 610 passed, 8 deselected, 10 subtests passed

.venv/bin/python -m swallow.surface_tools.cli --help
# passed
```

M3 manual verification:

```text
base_dir: /tmp/swallow-phase67-m3-verify
task_id: 87f07afc59a6
commands: summarize, route, validation, knowledge-policy, knowledge-decisions, dispatch
result: matched 6
```

---

## 当前已知边界

- `v1.4.0` tag 已完成；不要删除或重打该 tag。
- Phase 67 Candidate P 已完成实现与验证;不要继续扩大到 Candidate O / R 或其他 roadmap 项。
- Phase 67 review 建议不打新 release tag,除非 Human 另行要求并经过 Claude tag assessment。
- `docs/design/INVARIANTS.md` / `docs/design/DATA_MODEL.md` / `docs/design/KNOWLEDGE.md` 在 Phase 67 中未修改。
- Phase 66 / 67 carry-forward known gaps 仍以 `docs/concerns_backlog.md` 与 phase closeout 为权威来源。
- 不主动推进多租户、分布式 worker、云端 truth 镜像或无边界 UI 扩张。
- 不绕过 `apply_proposal` 直接写 canonical / route / policy。
- README 当前为单文件双语结构;不要再要求同步不存在的 `README.zh-CN.md`。

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
sed -n '1,240p' AGENTS.md
sed -n '1,220p' current_state.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
