# Current State

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
- latest_main_checkpoint_phase: `Phase 54`
- latest_main_checkpoint_tag: `v1.0.0`
- current_working_phase: `Phase 55`
- checkpoint_type: `review_followup_complete_pending_commit_gate`
- active_branch: `main`
- last_checked: `2026-04-25`

说明：

- `main` 上最近的稳定公开 checkpoint 仍是 `Phase 54 / v1.0.0`。
- 当前 git 真相为 `main` 上的未提交工作树，需以此为恢复入口。
- Phase 55 已完成实现、测试、review、closeout 与 review follow-up，当前状态为 **ready for commit gate**。

---

## 当前默认继续方向

当前推荐从以下状态继续：

- active_branch: `main`
- active_track: `Knowledge / RAG` (Primary) + `Evaluation / Policy` (Secondary)
- active_phase: `Phase 55`
- active_slice: `review_followup_complete_pending_commit_gate`
- workflow_status: `phase55_commit_gate_ready`

说明：

- 当前默认动作不是继续开发新 slice，而是处理人工 commit gate。
- commit 完成后，再根据分支策略决定 PR / merge gate；Phase 55 稳定后，下一轮再回到 roadmap 选择 Phase 56 kickoff。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/roadmap.md`
4. `current_state.md`
5. `docs/plans/phase55/closeout.md`
6. `docs/plans/phase55/review_comments.md`
7. `docs/cli_reference.md`

仅在需要时再读取：

- `docs/plans/phase55/kickoff.md`
- `docs/plans/phase55/design_decision.md`
- `docs/plans/phase55/risk_assessment.md`
- `pr.md`
- 历史 phase closeout / review_comments

---

## 最小验证命令

恢复工作前，建议至少执行以下检查：

```bash
.venv/bin/python -m pytest tests/test_ingestion_pipeline.py tests/test_knowledge_relations.py tests/test_retrieval_adapters.py tests/test_sqlite_store.py tests/test_cli.py -k 'ingest or knowledge or retrieval or sqlite_task_store' --tb=short
.venv/bin/python -m pytest tests/test_cli.py -q --tb=no -k "cli_end_to_end_local_file_promotion_link_and_relation_retrieval or create_task_preserves_existing_canonical_reuse_policy or stage_promote_updates_candidate_and_canonical_registry or retrieve_context_includes_canonical_reuse_visible_records"
.venv/bin/python -m pytest tests/test_retrieval_adapters.py tests/test_knowledge_relations.py -q --tb=no
git show --no-patch --decorate --oneline HEAD
git log --oneline -3
```

---

## 当前已知边界

- `knowledge_relations` 当前是 SQLite truth，不提供文件 mirror。
- relation expansion 参数与 `knowledge_priority_bonus` 已集中到 `retrieval_config.py`，但仍是代码默认值，不是 operator-facing runtime config。
- task-run 默认 retrieval 已包含 `knowledge` source；这使 graph-aware retrieval 进入正常执行主链。
- canonical alias (`canonical-*`) 现可通过公共 helper 解析为底层 `source_object_id`，relation CLI 与 retrieval e2e 已覆盖该断点。
- knowledge relation 当前仍依赖全局唯一 `object_id` 假设；若未来 task-local object id 语义改变，需要重新审视关系键设计。
- 本阶段不包含 relation 自动推断、graph summarization、community detection 或 LLM-enhanced retrieval。
- Web Control Center 仍保持只读，不引入新的写路径。

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
sed -n '1,220p' docs/plans/phase55/closeout.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
