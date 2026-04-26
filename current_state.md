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
- latest_main_checkpoint_phase: `Phase 57`
- latest_public_tag: `v1.2.0`（retag pending；当前仍指向 Phase 56 旧提交）
- current_working_phase: `Phase 58 Direction Gate`
- checkpoint_type: `post_phase57_main_direction_gate`
- active_branch: `main`
- last_checked: `2026-04-26`

说明：

- `main` 已包含 Phase 57 merge 与后续 roadmap 收口文档更新。
- Phase 57 能力基线为神经 API embedding、LLM rerank、repo/notes 默认 overlap 关闭、Literature Specialist document paths 透传。
- 当前公开 tag `v1.2.0` 仍指向 Phase 56 旧提交；如决定 retag，应先同步 README / AGENTS.md 的 tag-level release docs，再在 release docs commit 上重新打 tag。
- 当前默认动作不是继续扩张 Phase 57，也不是直接实现 Phase 58，而是从 `docs/roadmap.md` 选择下一条路线。

---

## 当前默认继续方向

当前推荐从以下状态继续：

- active_branch: `main`
- active_track: `Direction Selection`
- active_phase: `Phase 58`
- active_slice: `roadmap_direction_gate`
- workflow_status: `phase58_direction_selection`

说明：

- Phase 58 推荐候选仍是 A，但应先做 **A-lite**：`swl note`、`swl ingest --from-clipboard`、staged review visibility 与统一 staged knowledge 出口。
- 完整 `BrainstormOrchestrator` / multi-route synthesis 不应作为第一刀实现；等低摩擦捕获和沉淀通道稳定后再推进。
- 方向确定后先走 Claude kickoff / design_decision / risk_assessment；design gate 通过后再从 `main` 切 `feat/phase58-...` 分支开始实现。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/roadmap.md`
4. `current_state.md`
5. `docs/plans/phase57/closeout.md`
6. `docs/plans/phase57/review_comments.md`
7. `docs/design/ORCHESTRATION.md`
8. `docs/design/KNOWLEDGE.md`
9. `docs/design/PROVIDER_ROUTER.md`

仅在需要时再读取：

- `docs/design/ARCHITECTURE.md`
- `docs/plans/phase57/kickoff.md`
- `docs/plans/phase57/design_decision.md`
- `docs/plans/phase57/risk_assessment.md`
- `docs/plans/phase57/pre_kickoff_real_data_validation.md`
- `pr.md`
- 历史 phase closeout / review_comments

---

## 最小验证命令

恢复工作前，建议至少执行以下检查：

```bash
git status --short
git show --no-patch --decorate --oneline HEAD
git log --oneline --decorate -8
git rev-list -n 1 v1.2.0
```

当前是文档与方向选择阶段，默认不需要跑测试。若准备 release tag 或进入 Phase 58 实现前需要确认 Phase 57 基线，可再运行：

```bash
.venv/bin/python -m pytest tests/test_retrieval_adapters.py tests/test_doctor.py
.venv/bin/python -m pytest tests/test_cli.py -k "literature_specialist_input_context or persists_route_dialect_for_default_aider_route"
.venv/bin/python -m pytest tests/test_specialist_agents.py -k "literature_specialist"
```

---

## 当前已知边界

- vector retrieval 现要求 neural embedding；embedding API 不可用时显式失败，不再回退到 local hash embedding。
- 仅 `sqlite-vec` 缺失时，检索退回 text fallback；这保证了检索链路在缺少向量扩展时仍可用，但不会掩盖 embedding 配置错误。
- `retrieve_context()` 已具备 LLM rerank，但 rerank 是 additive 排序增强，不改变底层召回 truth，也不保证在所有真实数据分布下都显性进入 top-K。
- repo / notes 的默认 overlap 已关闭；chunking 优化仅保留 heading / symbol 分段与 `max_chunk_size`，不回填历史 canonical text 或 staged knowledge truth。
- `literature-specialist` 的 CLI 输入透传已贯通到 `TaskState.input_context` / `TaskCard.input_context`，但未引入新的 specialist 配置层或生命周期语义。
- route capability profiles 已被路由消费，`task_family_scores` / `unsupported_task_types` 不是未使用字段；后续差距是自动学习质量、guard 可观测性与 model-intel 摄入。
- `local-codex` 当前仍是 `local-aider` legacy alias；真实 Codex CLI 接入必须处理 alias migration 与持久化 policy 兼容。
- Phase 58 当前只处于 Direction Gate；不要在 `main` 上开始功能实现。
- notes source type 不应在当前阶段删除；短期策略是收缩其长期检索定位，并把有价值内容导入 governed staged knowledge / artifact refs / explicit refs。

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
sed -n '1,260p' docs/roadmap.md
sed -n '1,220p' current_state.md
```

然后按“恢复时优先读取”的顺序进入当前工作上下文。
