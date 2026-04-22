---
author: codex
phase: 37
slice: all
status: final
depends_on:
  - docs/plans/phase37/kickoff.md
  - docs/plans/phase36/closeout.md
---

## TL;DR
Phase 37 已完成实现与 slice 拆 commit，当前状态为 **review pending / PR sync ready**。本轮在 `.swl/` 目录之上构建了只读 Web Control Center baseline：S1 提供 JSON API 与 `swl serve` 入口，S2 提供单页 HTML 仪表盘，S3 提供 Artifact Review 双栏查看。整个 Web 层保持严格只读，零写入 `.swl/`，所有状态流转仍走 CLI。当前全量回归基线为 `261 passed in 5.94s`。

# Phase 37 Closeout

## 结论

Phase 37 `Control Center Baseline` 已完成实现与验证，当前分支状态为 **review pending / PR sync ready**。

本轮围绕 kickoff 定义的 3 个 slice，交付了一个本地优先、严格只读、无前端构建工具链的最小 Web workbench：

- S1：只读 JSON API + `swl serve` 启动入口
- S2：单页 HTML 仪表盘，展示任务列表、状态、事件流与 artifact 列表
- S3：Artifact Review 双栏视图，为后续 diff 对比预留结构

当前尚未进入 Claude review，因此本轮 closeout 的语义是“实现完成，等待 review / PR 同步”，而不是 merge ready。

## 已完成范围

### Slice 1: JSON API 层

- 新增 `src/swallow/web/api.py` 与 `src/swallow/web/server.py`
- 通过 `iter_task_states()` / `load_state()` / `load_knowledge_objects()` 等读取层提供只读任务数据
- 暴露 `/api/tasks`、`/api/tasks/{task_id}`、`/events`、`/artifacts`、`/knowledge` 与 `/api/health`
- `src/swallow/cli.py` 新增 `swl serve [--host 127.0.0.1] [--port 8037]`
- FastAPI / uvicorn 为 lazy import，不影响其他 CLI 命令

对应 commit：

- `d90ec37` `feat(control-center): add read-only web api baseline`

### Slice 2: 单页 HTML 仪表盘

- 新增 `src/swallow/web/static/index.html`
- 根路径 `/` 返回 dashboard，`/static` 挂载静态目录
- 左栏任务列表支持 `active / failed / recent / all / needs-review`
- 右栏展示任务核心状态、事件流时间线与 artifact 列表
- 整体保持单文件 HTML + CSS + vanilla JS，无 npm / node / bundler

对应 commit：

- `61295c1` `feat(control-center): add read-only dashboard page`

### Slice 3: Artifact Review 双栏视图

- 将 artifact viewer 扩展为 left / right 两个独立 selector
- 支持同时打开两个 artifact 进行并排查看
- 内容保持 monospace 只读展示，不支持编辑
- API 未扩张；S3 继续复用现有单 artifact 读取端点

对应 commit：

- `709c39e` `feat(control-center): add dual artifact review view`

## 与 kickoff 完成条件对照

### 已完成的目标

- `swl serve` 已存在，默认绑定 `127.0.0.1:8037`
- S1 的所有只读 API 端点已可用
- 零写入 `.swl/` 的只读边界已通过 checksum 测试验证
- 浏览器可访问 `http://127.0.0.1:8037/` 的 dashboard 根页面
- 任务列表、任务状态、事件流、artifact 列表已正确渲染
- Artifact Review 双栏视图已可同时打开两个 artifact
- 无 npm / node_modules / 前端构建步骤
- 全量测试通过

### 未继续扩张的内容

以下方向仍明确不在本 phase 范围内：

- Web UI 写操作：run / retry / acknowledge / knowledge approve
- React / Vue / Svelte / npm 构建工具链
- WebSocket 实时推送
- 用户认证、多租户或远程部署
- Artifact 在线编辑、diff 合并或富交互 review 工作流
- DAG 图形化渲染

## Stop / Go 判断

### Stop 判断

当前 phase 应停止继续扩张，理由如下：

- kickoff 定义的 S1 / S2 / S3 已全部完成，并已按 slice 独立提交
- 只读边界、极简栈与本地优先约束均被满足
- 当前实现已经形成一个完整可演示的 Control Center baseline
- 再继续扩张会自然滑向“写操作控制面 / 实时推送 / 更重前端栈”，超出本轮 scope

### Go 判断

下一步应按如下顺序推进：

1. Human push 当前分支
2. 用根目录 `pr.md` 同步 PR 描述
3. Claude 执行 review
4. 如有 review follow-up，在同一分支继续修正
5. Human 决定 merge

## 当前稳定边界

Phase 37 closeout 后，以下边界应视为当前实现候选的稳定 checkpoint：

- Web 层只读消费 `.swl/`，不负责任何状态流转
- 所有 operator 控制动作仍必须经由 CLI
- 前端仍是单文件 HTML / CSS / JS，不引入前端框架或构建系统
- Artifact Review 当前是并排查看，不是语义 diff 或编辑器
- dashboard 刷新方式仍是手动 refresh，不做实时推送

## 当前已知问题

- Web Control Center 当前依赖 FastAPI / uvicorn；在未安装依赖的环境下，`swl serve` 会返回清晰错误，但不会自动安装依赖
- dashboard 目前为手动 refresh 模式，没有 WebSocket 或后台 polling
- Artifact Review 双栏仍是原文并排查看，不提供 diff 高亮或同步滚动

以上问题均不阻塞进入 review 阶段。

## 测试结果

最终验证结果：

```text
261 passed in 5.94s
```

补充说明：

- `tests/test_web_api.py` 覆盖 JSON API 只读边界、root route 暴露、静态页面结构和双栏 artifact viewer 节点
- `tests/test_cli.py` 覆盖 `serve` help、dispatch 与缺依赖报错路径

## 规则文件同步检查

### 必查

- [x] `docs/plans/phase37/closeout.md`
- [x] `docs/plans/phase37/kickoff.md`
- [x] `docs/active_context.md`
- [x] `current_state.md`
- [x] `./pr.md`

### 条件更新

- [ ] `AGENTS.md`
- [ ] `README.md`
- [ ] `README.zh-CN.md`
- [ ] `docs/plans/phase37/review_comments.md`

说明：

- 当前还未进入 review，因此不存在 `review_comments.md`
- 本轮未改变长期协作规则与 README 级对外叙述，暂不更新 `AGENTS.md` / README

## Git / PR 建议

1. 使用当前根目录 `pr.md` 作为 PR 描述草案
2. Human push `feat/phase37-control-center`
3. PR 描述明确当前为 `review pending`
4. Claude review 后再进入 merge 决策

## 下一轮建议

如果 Phase 37 merge 完成，下一轮应优先考虑 review follow-up 或 roadmap 中与 Control Center 邻接的 operator-facing 能力，但不应默认直接扩张到 Web 写操作或更重前端栈。
