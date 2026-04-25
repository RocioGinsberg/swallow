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
- latest_main_checkpoint_phase: `Phase 56`
- latest_main_checkpoint_tag: `v1.0.0`
- current_working_phase: `Phase 56`
- checkpoint_type: `reviewed_feature_branch_ready_for_merge`
- active_branch: `feat/phase56-llm-enhanced-knowledge`
- last_checked: `2026-04-25`

说明：

- `main` 上最近的稳定公开 tag 仍是 `v1.0.0`，但当前默认开发恢复入口已切到 `feat/phase56-llm-enhanced-knowledge`。
- Phase 56 已完成实现、测试、review 与 closeout，当前状态为 **ready for merge gate**。
- 当前默认动作不是继续扩展 Phase 56，而是处理 merge gate / 分支收口，并为 Phase 57 做入口准备。

---

## 当前默认继续方向

当前推荐从以下状态继续：

- active_branch: `feat/phase56-llm-enhanced-knowledge`
- active_track: `Core Loop` (Primary) + `Knowledge / RAG` (Secondary)
- active_phase: `Phase 56`
- active_slice: `closeout_complete_pending_merge_gate`
- workflow_status: `phase56_review_approved_ready_for_merge`

说明：

- 当前默认动作不是继续开发新 slice，而是处理 merge gate / phase 收口后的分支动作。
- 如 Phase 56 合并完成，则下一轮默认回到 roadmap，选择 Phase 57 kickoff。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/roadmap.md`
4. `current_state.md`
5. `docs/plans/phase56/closeout.md`
6. `docs/plans/phase56/review_comments.md`
7. `docs/plans/phase56/design_decision.md`

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
.venv/bin/python -m pytest tests/test_cli.py tests/test_specialist_agents.py tests/test_executor_protocol.py tests/test_executor_async.py -q --tb=no
git show --no-patch --decorate --oneline HEAD
git log --oneline -4
```

---

## 当前已知边界

- HTTP executor 与 agent LLM 调用现优先消费 API usage；无 usage 时仍回退到估算。
- `LiteratureSpecialist` / `QualityReviewer` 已具备 LLM 增强能力，但仍保持 heuristic fallback，不依赖 LLM 可用性才能运行。
- relation suggestions 当前以 `executor_side_effects.json` 作为 artifact truth，并通过 `swl knowledge apply-suggestions` gated 应用；不自动落库。
- 本阶段不包含 agentic retrieval、多跳检索编排或 relation suggestion 的独立 proposal store。
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
sed -n '1,220p' docs/plans/phase56/closeout.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
