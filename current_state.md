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
- latest_main_checkpoint_phase: `Architecture Recomposition First Branch`
- latest_executed_public_tag: `v1.5.0`
- pending_release_tag: `none`
- current_working_phase: `Provider Router Split / LTO-7 Step 1`
- checkpoint_type: `provider_router_split_review_pass_pending_human_merge`
- active_branch: `feat/provider-router-split`
- last_checked: `2026-05-01`

说明:

- `main` 当前最新 checkpoint 为 `a1e536b docs(state): update roadmap`。
- 最新已执行公开 tag 仍为 `v1.5.0`; annotated tag 指向 `bc8abb1 docs(release): sync v1.5.0 release docs`。
- 当前 feature branch 为 `feat/provider-router-split`。
- 当前最新已提交 feature checkpoint 为 `cbc72ce docs(state): close provider router split implementation`。
- M5 cleanup / closeout 已完成、提交并通过验证。
- Claude PR review 已记录在 `docs/plans/provider-router-split/review_comments.md`，结论为 `PASS` / recommend merge，无 BLOCK。
- Review 产出的 3 个非阻塞 CONCERN 已记录到 `docs/concerns_backlog.md`。
- Provider Router Split closeout 已写入 `docs/plans/provider-router-split/closeout.md`。
- PR 文案已写入仓库根目录 `pr.md`。该文件被 `.gitignore` 忽略，用作本地 PR 创建草稿。

---

## 当前默认继续方向

当前推荐从以下状态继续:

- active_branch: `feat/provider-router-split`
- active_track: `Architecture / Engineering`
- active_phase: `Provider Router Split / LTO-7 Step 1`
- active_slice: `PR review complete; awaiting Human merge decision`
- workflow_status: `pr_review_pass_with_3_concerns_recommend_merge`

下一步:

1. Human review PR and Claude review result.
2. Human merge `feat/provider-router-split` when accepted.
3. Codex performs post-merge state sync on `main`.
4. Roadmap factual update runs after merge.
5. Claude performs tag evaluation; current review recommendation is not to tag LTO-7 alone.

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读:

1. `AGENTS.md`
2. `.agents/shared/read_order.md`
3. `.agents/shared/state_sync_rules.md`
4. `docs/active_context.md`
5. `current_state.md`
6. `docs/plans/provider-router-split/closeout.md`
7. `docs/plans/provider-router-split/review_comments.md`
8. `docs/concerns_backlog.md`
9. `pr.md`
10. `docs/plans/provider-router-split/plan.md`
11. `docs/plans/provider-router-split/plan_audit.md`
12. `docs/roadmap.md`
13. `docs/design/INVARIANTS.md`
14. `docs/design/PROVIDER_ROUTER.md`
15. `docs/design/DATA_MODEL.md`
16. `docs/design/ORCHESTRATION.md`
17. `docs/design/EXECUTOR_REGISTRY.md`
18. `docs/engineering/CODE_ORGANIZATION.md`
19. `docs/engineering/GOF_PATTERN_ALIGNMENT.md`
20. `docs/engineering/TEST_ARCHITECTURE.md`

---

## 最小验证命令

恢复工作前，建议至少执行以下检查:

```bash
git status --short --branch
git branch --show-current
git show --no-patch --decorate --oneline HEAD
git log --oneline --decorate -8
git tag --list 'v*' --sort=-creatordate | head -n 5
```

Provider Router Split PR-ready gate 已跑过:

```bash
.venv/bin/python -m pytest tests/unit/provider_router -q
.venv/bin/python -m pytest tests/test_router.py tests/test_governance.py tests/test_meta_optimizer.py tests/test_phase65_sqlite_truth.py tests/test_invariant_guards.py tests/test_cli.py -q
.venv/bin/python -m pytest tests/test_synthesis.py tests/test_executor_protocol.py tests/test_executor_async.py tests/eval/test_http_executor_eval.py -q
.venv/bin/python -m compileall -q src/swallow
git diff --check
.venv/bin/python -m pytest -q
```

Latest full result:

```text
651 passed, 8 deselected, 10 subtests passed
```

---

## 当前已知边界

- 当前阶段是 `Provider Router Split / LTO-7 Step 1` 的 review complete / merge gate 前状态。
- 不在 `main` 上继续实现。
- 不把 LTO-8 Orchestration、LTO-9 Surface / Meta Optimizer 或 LTO-10 Governance 合并进本 phase。
- 不改变 `docs/design/*.md` 设计语义。
- 不改变 Path A/B/C 语义，不让 Path B 调用 Provider Router。
- 不改变 Control Plane 权限，Provider Router 不做任务域判断、复杂度评估、waiting_human 决策或语义级 retry 决策。
- 不绕过 `apply_proposal` 直接写 route metadata / policy。
- 不引入新的 provider、网络协议、schema migration 或真实模型调用要求。
- `router.py` 是兼容 facade；focused module ownership 见 `docs/plans/provider-router-split/closeout.md`。
- README 当前为单文件双语结构;不要再要求同步不存在的 `README.zh-CN.md`。

---

## 当前建议提交范围

如接受 review 同步与 concerns backlog，建议由 Human 提交:

```bash
git add docs/active_context.md current_state.md docs/plans/provider-router-split/closeout.md docs/plans/provider-router-split/review_comments.md docs/concerns_backlog.md
git commit -m "docs(review): record provider router split review"
```

`pr.md` 已更新但被 `.gitignore` 忽略；Human 更新 PR 描述时可直接使用该本地文件内容。

---

## 本地基础设施

Phase 46 依赖的 Docker 栈位于 `~/ai-stack/`，与仓库分离。

```bash
cd ~/ai-stack
docker compose up -d new-api
docker compose up -d openwebui
docker compose ps
```

验证 new-api 可达:

```bash
curl http://localhost:3000/api/status
```

当前 phase 不要求 live HTTP / API-key dependent test。

---

## 恢复命令

重新打开仓库后，可先执行:

```bash
cd /home/rocio/projects/swallow
sed -n '1,220p' docs/active_context.md
sed -n '1,220p' current_state.md
sed -n '1,220p' docs/plans/provider-router-split/closeout.md
sed -n '1,220p' pr.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
