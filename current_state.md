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
- latest_completed_phase: `Phase 51`
- latest_completed_slice: `Policy Closure & Specialist Agent Lifecycle`
- checkpoint_type: `main_tagged_release`
- current_tag: `v0.8.0`
- last_checked: `2026-04-24`

说明：

- Phase 51 已完成实现、review、merge 与 tag，当前 `main` 对齐 `v0.8.0` 稳定 checkpoint。
- `docs/plans/phase51/closeout.md` 已反映上一轮稳定里程碑收口结论。
- 当前仓库的默认恢复入口不再是 Phase 49/50 的 kickoff，而是已完成验证的 Phase 52 feature branch 收口状态。

---

## 当前默认继续方向

当前推荐从以下状态继续：

- active_branch: `feat/phase52_execution_topology`
- active_track: `Core Loop` (Primary) + `Execution Topology` (Secondary)
- active_phase: `Phase 52`
- active_slice: `closeout / validation complete`
- workflow_status: `phase52_implementation_validated`

说明：

- `main` 的稳定基线仍是 `v0.8.0 / Phase 51`，但当前日常开发入口已位于 `feat/phase52_execution_topology`。
- Phase 52 的实现、eval 与全量 pytest 已完成；当前默认继续动作是 review / closeout / merge，而不是重新 kickoff。

---

## 恢复时优先读取

恢复工作时，优先按以下顺序阅读：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/roadmap.md`
4. `current_state.md`
5. `docs/plans/phase52/closeout.md`

仅在需要时再读取：

- `docs/concerns_backlog.md`
- `docs/plans/phase51/closeout.md`
- `docs/system_tracks.md`
- 历史 phase closeout / review_comments

---

## 最小验证命令

恢复工作前，建议至少执行以下检查：

```bash
.venv/bin/python -m pytest --tb=short
.venv/bin/python -m pytest -m eval --tb=short
git show --no-patch --decorate --oneline HEAD
git log --oneline -3
```

---

## 当前已知边界

- Web Control Center 仍保持严格只读；不会写入 `.swl/`，也未引入前端构建工具链。
- SQLite 当前已同时承载 `TaskState` / `EventLog` 与知识层 truth；下一轮默认不再回退到知识层“双重真相”整理。
- 默认 store 已切到 SQLite，但过渡期仍保留 file mirror/fallback；旧 `.swl/` 目录仍建议通过 `swl migrate` 回填。
- `swl knowledge migrate`、`LibrarianAgent` 与 `sqlite-vec` 文本降级检索已成为 `v0.8.0` 稳定基线。
- `AsyncCLIAgentExecutor` 已成为当前 feature branch 的 CLI agent 通用执行路径；merge 前仍以 feature branch 验证结果为准。
- `meta-optimize` 仍是只读分析入口，不会自动采纳策略提案，也不会直接修改 route policy 或 task state。
- route policy / capability profile 当前已兼容 legacy route alias（`local-codex -> local-aider`，`local-cline -> local-claude-code`）。
- `TaskCard.token_cost_limit` 仍按 task 全生命周期聚合真实 `token_cost`，不是按单 card 独立结算。
- 一致性抽检仍是手动、只读入口，不自动进入主任务闭环。
- 真实执行环境下的外部网络、代理与 provider 连通性仍受本地环境约束，`swl doctor` 只负责诊断，不负责修复。

---

## 本地基础设施

Phase 46 依赖的 Docker 栈位于 `~/ai-stack/`，与仓库分离。

```bash
cd ~/ai-stack
docker compose up -d new-api      # 起 new-api（SQLite，端口 3000）
docker compose up -d openwebui    # 可选，起对话面板（端口 3002）
docker compose ps                 # 确认容器状态
```

验证 new-api 可达：

```bash
curl http://localhost:3000/api/status
```

WireGuard 出口代理（`HTTPS_PROXY`）当前未启用，需要时取消 `docker-compose.yml` 中的注释并重启 new-api。

---

## 恢复命令

重新打开仓库后，可先执行：

```bash
cd /home/rocio/projects/swallow
sed -n '1,160p' current_state.md
```

然后按”恢复时优先读取”的顺序进入当前工作上下文。
