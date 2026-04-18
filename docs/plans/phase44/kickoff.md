---
author: claude
phase: 44
slice: control-center-enhancement
status: draft
depends_on:
  - docs/roadmap.md
  - docs/plans/phase42/closeout.md
---

> **TL;DR** Phase 44 在 Phase 37 只读 Web 基线上增量扩展：S1 新增子任务树 API + 前端树状展示，S2 新增 Artifact 内容对比 API + 前端双栏审阅区，S3 新增 debate round / cost 时间线 API + 前端曲线图。3 个 slice，中风险。严格只读，零写入 `.swl/`。

# Phase 44 Kickoff: 可视化工作台增强 (Web Control Center Enhancement)

## Track

- **Primary Track**: Workbench / UX
- **Secondary Track**: Core Loop

## 目标

在 Phase 37 建立的只读 Web 基线（`swl serve`）上增量扩展，解决 CLI 审查并行任务和 Artifact 对比时的认知过载问题。

具体目标：

1. **S1**: 子任务树展示 — API 返回父子任务层级结构 + 前端树状可视化，展示子任务并行进度与状态
2. **S2**: Artifact 对比审阅区 — API 返回两个 artifact 的内容 + 前端双栏 side-by-side 展示
3. **S3**: 成本/延迟时间线 — API 从事件日志聚合每轮执行的 latency / cost / debate round + 前端折线图

## 非目标

- **不做写入操作**：零写入 `.swl/`，不做 Approve / Reject 按钮的实际状态变更（展示 UI 但不连接写入 API）
- **不引入前端构建工具链**：继续使用单 HTML 文件 + 内联 CSS/JS，不引入 React / Vue / npm
- **不做实时 WebSocket 推送**：前端通过 polling（手动刷新或可选定时 fetch）获取最新数据
- **不做用户认证/权限**：本地服务，信任所有访问者（Tailscale 内网保护）
- **不做移动端适配**：桌面浏览器优先

## 设计边界

### Phase 37 基线现状

已有 API：
- `GET /api/tasks` — 任务列表（含 focus filter）
- `GET /api/tasks/{id}` — 单任务完整 state
- `GET /api/tasks/{id}/events` — 事件日志
- `GET /api/tasks/{id}/artifacts` — artifact 索引
- `GET /api/tasks/{id}/artifacts/{name}` — 单 artifact 内容
- `GET /api/tasks/{id}/knowledge` — 知识对象

已有前端：单页 HTML，任务列表 + 详情面板 + Artifact Review 双栏（但仅显示单 artifact 内容，无对比）。

### S1: 子任务树 API + 前端

**新增 API**：

```
GET /api/tasks/{id}/subtask-tree
```

返回：
```json
{
  "task_id": "parent-001",
  "status": "completed",
  "children": [
    {
      "card_id": "card-1",
      "subtask_index": 1,
      "goal": "Prepare changes",
      "status": "completed",
      "attempts": 1,
      "executor_name": "local",
      "latency_ms": 120
    },
    {
      "card_id": "card-2",
      "subtask_index": 2,
      "goal": "Verify results",
      "status": "completed",
      "attempts": 2,
      "executor_name": "local",
      "latency_ms": 340,
      "debate_rounds": 1
    }
  ]
}
```

数据来源：从 `events.jsonl` 中提取 `task.planned` 事件的 card 列表 + 各子任务的 `subtask.{idx}.review_gate` / `subtask.{idx}.debate_round` 事件。

**前端**：在任务详情面板中新增"Subtask Tree"标签页。用缩进列表或简单树状图展示父子关系，每个子任务显示状态徽章（completed / failed / waiting_human）+ 尝试次数 + debate round 数。

### S2: Artifact 对比审阅区

**新增 API**：

```
GET /api/tasks/{id}/artifact-diff?left={name_a}&right={name_b}
```

返回：
```json
{
  "task_id": "task-001",
  "left": { "name": "executor_output.md", "content": "..." },
  "right": { "name": "subtask_2_attempt2_executor_output.md", "content": "..." }
}
```

**前端**：在 Artifact Review 面板中新增"Compare"模式。用户选择两个 artifact 后，左右双栏 side-by-side 展示。内容为纯文本/markdown 渲染，不做 diff 高亮（首版保持简单，diff 高亮留作后续增量）。

### S3: 成本/延迟时间线

**新增 API**：

```
GET /api/tasks/{id}/execution-timeline
```

返回：
```json
{
  "task_id": "task-001",
  "entries": [
    {
      "event_type": "executor.completed",
      "round": 0,
      "latency_ms": 120,
      "token_cost": 0.05,
      "is_debate_retry": false,
      "timestamp": "2026-04-19T10:00:00Z"
    },
    {
      "event_type": "executor.completed",
      "round": 1,
      "latency_ms": 180,
      "token_cost": 0.08,
      "is_debate_retry": true,
      "timestamp": "2026-04-19T10:00:30Z"
    }
  ],
  "total_cost": 0.13,
  "total_latency_ms": 300,
  "debate_rounds": 1
}
```

数据来源：从 `events.jsonl` 中按时间序列提取 `executor.completed` / `executor.failed` / `task.debate_round` 事件的 `latency_ms` / `token_cost` / `review_feedback` 字段。

**前端**：在任务详情面板中新增"Timeline"标签页。用内联 SVG 或 Canvas 绘制简单折线图（x 轴为 round/时间，y 轴为 cost 和 latency 双 y 轴）。不引入 Chart.js 等第三方库，用约 100 行内联 JS 实现最小折线图。

### 与现有模块的接口

- **`web/api.py`**：新增 3 个 API endpoint + 3 个 payload builder 函数
- **`web/static/index.html`**：扩展现有单页 HTML，新增 3 个标签页/面板
- **不修改** `store.py` / `orchestrator.py` / `models.py` 等核心模块

### 约束重申

1. **严格只读**：所有新 API 为 GET，不写入 `.swl/`
2. **极简栈**：单 HTML + 内联 CSS/JS + FastAPI JSON API，不引入构建工具
3. **数据源唯一**：全部从 `.swl/tasks/{id}/` 下的文件读取，不引入额外存储

## Slice 拆解

### S1: 子任务树 API + 前端

**目标**：新增 `/api/tasks/{id}/subtask-tree` + 前端树状展示。

**影响范围**：修改 `web/api.py`、`web/static/index.html`

**风险评级**：
- 影响范围: 2 (API + 前端)
- 可逆性: 1 (轻松回滚)
- 依赖复杂度: 1 (读取 events.jsonl)
- **总分: 4** — 低-中风险

**验收条件**：
- API 返回正确的子任务树结构（从事件日志提取）
- 无子任务的任务返回空 children
- 前端展示树状列表，每个子任务显示状态 + 尝试次数
- API 测试覆盖

### S2: Artifact 对比审阅区

**目标**：新增 `/api/tasks/{id}/artifact-diff` + 前端双栏展示。

**影响范围**：修改 `web/api.py`、`web/static/index.html`

**风险评级**：
- 影响范围: 2 (API + 前端)
- 可逆性: 1 (轻松回滚)
- 依赖复杂度: 1 (复用现有 artifact 读取)
- **总分: 4** — 低-中风险

**验收条件**：
- API 返回两个 artifact 的 name + content
- left/right 参数缺失或 artifact 不存在时返回 4xx
- 前端双栏 side-by-side 展示两个 artifact 内容
- API 测试覆盖

### S3: 成本/延迟时间线

**目标**：新增 `/api/tasks/{id}/execution-timeline` + 前端折线图。

**影响范围**：修改 `web/api.py`、`web/static/index.html`

**风险评级**：
- 影响范围: 2 (API + 前端)
- 可逆性: 1 (轻松回滚)
- 依赖复杂度: 2 (事件日志聚合 + 内联图表 JS)
- **总分: 5** — 中风险

**验收条件**：
- API 按时间序列返回每轮执行的 latency / cost / debate 标记
- debate retry 事件正确标记 `is_debate_retry`
- 前端折线图显示 cost 和 latency 随 round/时间变化
- 无执行事件时显示空状态
- API 测试覆盖

## Slice 依赖

```
S1 (子任务树) — 独立
S2 (Artifact 对比) — 独立
S3 (时间线) — 独立
```

三个 slice 互不依赖，但建议顺序实现（前端代码在同一 HTML 文件中，顺序推进避免合并冲突）。

## 风险总评

| Slice | 影响 | 可逆 | 依赖 | 总分 | 评级 |
|-------|------|------|------|------|------|
| S1 | 2 | 1 | 1 | 4 | 低-中 |
| S2 | 2 | 1 | 1 | 4 | 低-中 |
| S3 | 2 | 1 | 2 | 5 | 中 |
| **合计** | | | | **13/27** | **中** |

主要风险在 S3 的前端图表实现（内联 JS 复杂度）。S1/S2 为标准 API + 前端扩展，风险可控。

**Scope 膨胀防线**：
- 不做写入（最高优先级约束）
- 不引入第三方 JS 库
- 不做 diff 高亮（首版纯文本对比）
- 不做 WebSocket 实时推送

## 完成条件

1. 子任务树 API + 前端树状展示可用
2. Artifact 对比 API + 前端双栏展示可用
3. 成本/延迟时间线 API + 前端折线图可用
4. 所有新 API 有测试覆盖
5. 严格只读：零写入 `.swl/`
6. 全量 pytest 通过，无回归

## Branch Advice

- 当前分支: `main`
- 建议操作: 人工审批 kickoff 后，从 `main` 切出 `feat/phase44-control-center`
- 理由: 前端 + API 扩展，应在 feature branch 上进行
- 建议 PR 范围: S1 + S2 + S3 合并为单 PR（同一 HTML 文件，拆分 PR 会产生合并冲突）
