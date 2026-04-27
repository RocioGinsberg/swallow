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
- latest_main_checkpoint_phase: `Phase 60`
- latest_public_tag: `v1.3.0`
- current_working_phase: `Meta Docs Sync`
- checkpoint_type: `post_phase60_main_docs_meta`
- active_branch: `main`
- last_checked: `2026-04-27`

说明：

- `main` 已包含 Phase 60 merge（Route-Aware Retrieval Policy + explicit retrieval source override）以及后续 `docs(agents): upgrade cowork mode part 1` 协作文档提交。
- `v1.3.0` 仍是当前公开 tag，对应 Phase 58/59 里程碑；`main` 已继续前进，但尚未为 Phase 60 之后的主线状态打新 tag。
- 当前默认动作不是重开 Phase 60，也不是直接扩张新的产品 phase，而是先完成协作文档 / workflow / state docs 的对齐修补。

---

## 当前默认继续方向

当前推荐从以下状态继续：

- active_branch: `main`
- active_track: `Collaboration / Workflow`
- active_phase: `Meta Docs Sync`
- active_slice: `Cowork Mode Upgrade`
- workflow_status: `docs_meta_alignment`

说明：

- 当前工作是文档与流程整理，不涉及 `src/` / `tests/` 功能实现。
- 可继续留在 `main` 做小范围文档修补，或由 Human 视 diff 大小决定是否切到 `docs/...` 分支。
- 这轮工作的目标是让 AGENTS / shared rules / workflows / state docs 与真实仓库结构一致，再进入下一轮产品 phase 规划。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `change.md`
4. `current_state.md`
5. `.agents/shared/read_order.md`
6. `.agents/workflows/feature.md`
7. `.agents/workflows/tag_release.md`
8. `docs/design/INVARIANTS.md`
9. `docs/roadmap.md`

仅在需要时再读取：

- `CLAUDE.md`
- `.codex/session_bootstrap.md`
- `docs/plans/phase60/closeout.md`
- `docs/concerns_backlog.md`
- `pr.md`
- 历史 phase closeout / review_comments / archive 文档

---

## 最小验证命令

恢复工作前，建议至少执行以下检查：

```bash
git status --short
git branch --show-current
git show --no-patch --decorate --oneline HEAD
git log --oneline --decorate -8
git tag --list 'v*' --sort=-creatordate | head -n 5
```

当前是文档整理阶段，默认不需要跑测试。若需要回归确认 Phase 60 基线，可再运行：

```bash
.venv/bin/python -m pytest tests/ --ignore=tests/eval
```

---

## 当前已知边界

- vector retrieval 现要求 neural embedding；embedding API 不可用时显式失败，不再回退到 local hash embedding。
- 仅 `sqlite-vec` 缺失时，检索退回 text fallback；这保证了检索链路在缺少向量扩展时仍可用，但不会掩盖 embedding 配置错误。
- `retrieve_context()` 已具备 LLM rerank，但 rerank 是 additive 排序增强，不改变底层召回 truth，也不保证在所有真实数据分布下都显性进入 top-K。
- Phase 60 已收紧 retrieval source 默认策略：autonomous CLI coding route 默认 `knowledge`，HTTP route 默认 `knowledge + notes`，`repo` 仅由显式 override 或 legacy fallback 回到主链。
- `literature-specialist` 的 CLI 输入透传已贯通到 `TaskState.input_context` / `TaskCard.input_context`，但未引入新的 specialist 配置层或生命周期语义。
- route capability profiles 已被路由消费，`task_family_scores` / `unsupported_task_types` 不是未使用字段；后续差距是自动学习质量、guard 可观测性与 model-intel 摄入。
- `local-codex` 当前仍是 `local-aider` legacy alias；真实 Codex CLI 接入必须处理 alias migration 与持久化 policy 兼容。
- `docs/design/` 是产品设计真相源；协作规则、release sync 和状态信息不应在 `AGENTS.md` 里重复维护副本。
- README 当前为单文件双语结构；不要再要求同步不存在的 `README.zh-CN.md`。

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
