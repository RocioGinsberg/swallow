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
- latest_main_checkpoint_tag: `v1.2.0`
- current_working_phase: `Phase 57`
- checkpoint_type: `implemented_feature_branch_pending_review`
- active_branch: `feat/phase57-retrieval-quality`
- last_checked: `2026-04-26`

说明：

- `main` 上最近的稳定公开 tag 仍是 `v1.2.0`。
- 当前默认开发恢复入口已切到 `feat/phase57-retrieval-quality`。
- Phase 57 已完成实现、slice 拆 commit 与 closeout 文档收口，当前状态为 **review pending / PR sync ready**。
- 当前默认动作不是继续扩张 Phase 57，而是处理 review gate、吸收 follow-up，并在通过后准备 PR / merge 材料。

---

## 当前默认继续方向

当前推荐从以下状态继续：

- active_branch: `feat/phase57-retrieval-quality`
- active_track: `Knowledge / RAG` (Primary) + `Workbench / UX` (Secondary)
- active_phase: `Phase 57`
- active_slice: `phase_closeout_ready_for_review`
- workflow_status: `phase57_implementation_complete_review_pending`

说明：

- 当前默认动作不是继续开发新 slice，而是发起 Claude review、处理 review follow-up，并同步 PR 材料。
- 如 Phase 57 review / merge 完成，则下一轮默认回到 roadmap，选择新的 kickoff 方向。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/roadmap.md`
4. `current_state.md`
5. `docs/plans/phase57/closeout.md`
6. `docs/plans/phase57/design_decision.md`
7. `docs/plans/phase57/risk_assessment.md`

仅在需要时再读取：

- `docs/plans/phase57/kickoff.md`
- `docs/plans/phase57/pre_kickoff_real_data_validation.md`
- 后续新增的 `docs/plans/phase57/review_comments.md`
- `pr.md`
- 历史 phase closeout / review_comments

---

## 最小验证命令

恢复工作前，建议至少执行以下检查：

```bash
.venv/bin/python -m pytest tests/test_retrieval_adapters.py tests/test_doctor.py
.venv/bin/python -m pytest tests/test_cli.py -k "literature_specialist_input_context or persists_route_dialect_for_default_aider_route"
.venv/bin/python -m pytest tests/test_specialist_agents.py -k "literature_specialist"
git show --no-patch --decorate --oneline HEAD
git log --oneline -6
```

---

## 当前已知边界

- vector retrieval 现要求 neural embedding；embedding API 不可用时显式失败，不再回退到 local hash embedding。
- 仅 `sqlite-vec` 缺失时，检索退回 text fallback；这保证了检索链路在缺少向量扩展时仍可用，但不会掩盖 embedding 配置错误。
- `retrieve_context()` 已具备 LLM rerank，但 rerank 是 additive 排序增强，不改变底层召回 truth，也不保证在所有真实数据分布下都显性进入 top-K。
- chunking 优化仅作用于 retrieve-time 分段，不回填历史 canonical text 或 staged knowledge truth。
- `literature-specialist` 的 CLI 输入透传已贯通到 `TaskState.input_context` / `TaskCard.input_context`，但未引入新的 specialist 配置层或生命周期语义。

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
sed -n '1,260p' docs/plans/phase57/closeout.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
