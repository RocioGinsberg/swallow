---
author: claude
phase: 37
slice: control-center
status: final
depends_on: [docs/roadmap.md, docs/plans/phase36/closeout.md, docs/design/INTERACTION_AND_WORKBENCH.md]
---

> **TL;DR**: Phase 37 在 `.swl/` 目录之上构建只读 Web 控制中心原型。S1 实现 JSON API 层（FastAPI，直接读取 store 模块）；S2 实现单页 HTML 仪表盘（无构建工具链，vanilla JS + fetch）；S3 实现 Artifact Review 双栏视图。严格只读——零写入 `.swl/`，所有状态流转仍走 CLI。

# Phase 37 Kickoff — Control Center Baseline (只读 Web 仪表盘)

## 基本信息

- **Phase**: 37
- **Primary Track**: Workbench / UX
- **Secondary Track**: Core Loop
- **Phase 名称**: Control Center Baseline

---

## 前置依赖与现有基础

- `.swl/` 目录结构已稳定：`tasks/{task_id}/state.json` + `events.jsonl` + `artifacts/` + 15+ JSON 附属文件
- `store.py` 已提供 `load_state()` / `iter_task_states()` / `load_knowledge_objects()` 等读取函数
- CLI 已实现 `task list` / `task inspect` / `task review` / `task artifacts` / `task queue` 等 operator 入口
- `INTERACTION_AND_WORKBENCH.md` §2.3 定义了 Control Center 愿景：Task Tree + Artifact Review Area + 只读消费 `.swl/`
- Phase 33 SubtaskOrchestrator 已支持并行子任务，CLI 逐条审查效率低下是当前最直接的日常痛点
- AGENTS.md 非目标明确排除"无边界扩张 workbench UI"

---

## Phase 37 目标

在 `.swl/` 目录之上构建**只读的本地 Web 控制中心原型**，让 operator 可以通过浏览器审查任务状态、事件流和产出物，替代 CLI 逐条滚动的低效体验。

**核心约束**：
1. **严格只读**：Web 层零写入 `.swl/`，所有状态流转仍走 `swl` CLI
2. **极简栈**：FastAPI（Python 已有）+ vanilla HTML/JS，不引入 React/Vue/npm 构建工具链
3. **本地优先**：默认绑定 `127.0.0.1:8037`，不暴露公网

---

## 非目标（明确排除）

| 排除项 | 理由 |
|--------|------|
| 通过 Web UI 修改任务状态 / 触发 run / approve knowledge | 违反只读约束；状态流转归 CLI |
| React / Vue / Svelte 等前端框架 | 违反极简栈约束；引入 npm/node 依赖 |
| WebSocket 实时推送 | MVP 阶段用 polling 或手动刷新即可 |
| 用户认证 / 多租户 | AGENTS.md 非目标 |
| 远程部署 / Cloudflare Tunnel | 延后到独立 phase |
| Artifact 在线编辑 / diff 合并 | 只读；编辑走 CLI 或编辑器 |
| Open WebUI 集成 | 独立系统，不在本轮 scope |
| Task Tree 的 DAG 图形化渲染 | MVP 用缩进列表表示父子关系即可 |

---

## Slice 拆解

### S1: JSON API 层

**目标**: 提供 REST API 供前端消费，直接复用 `store.py` 读取函数。

**改动范围**:
- `src/swallow/web/__init__.py`（新目录）
- `src/swallow/web/api.py`（新文件）：FastAPI app + API routes
- `src/swallow/web/server.py`（新文件）：启动入口
- `src/swallow/cli.py`：新增 `swl serve [--port 8037] [--host 127.0.0.1]` 子命令

**API 端点设计**:

| 方法 | 路径 | 数据源 | 说明 |
|------|------|--------|------|
| GET | `/api/tasks` | `iter_task_states()` | 任务列表，支持 `?focus=active\|failed\|recent` |
| GET | `/api/tasks/{task_id}` | `load_state()` | 单任务完整状态 |
| GET | `/api/tasks/{task_id}/events` | `events.jsonl` | 事件流（JSONL → JSON array） |
| GET | `/api/tasks/{task_id}/artifacts` | `state.artifact_paths` + 文件读取 | 产物列表 + 内容 |
| GET | `/api/tasks/{task_id}/artifacts/{name}` | 单文件读取 | 单个产物内容（raw text） |
| GET | `/api/tasks/{task_id}/knowledge` | `load_knowledge_objects()` | Knowledge objects 列表 |
| GET | `/api/health` | — | 服务健康检查 |

**验收标准**:
- `swl serve` 启动 FastAPI server，绑定 `127.0.0.1:8037`
- 所有 API 端点返回正确 JSON
- 零写入 `.swl/`（通过 test 验证 API 调用前后 `.swl/` 文件 checksum 不变）
- 无 FastAPI 依赖时 `swl` 其他命令仍正常工作（lazy import）

**风险**: 3/9（impact 1, reversibility 1, dependency 1）

---

### S2: 单页 HTML 仪表盘

**目标**: 一个 HTML 文件 + vanilla JS，通过 fetch 调用 S1 API 渲染任务仪表盘。

**改动范围**:
- `src/swallow/web/static/index.html`（新文件）：单页应用
- `src/swallow/web/api.py`：挂载 static 目录

**页面结构**:

```
┌─────────────────────────────────────────┐
│  Swallow Control Center    [Refresh]     │
├──────────────┬──────────────────────────┤
│  Task List   │  Task Detail             │
│  ─────────── │  ──────────────          │
│  [active]    │  Status: completed       │
│  [failed]    │  Phase: summarize        │
│  [recent]    │  Route: local-codex      │
│              │  Attempt: #2             │
│  task-001 ● │  ──────────────          │
│  task-002 ○ │  Events (23)             │
│  task-003 ● │  ──────────────          │
│              │  > task.created           │
│              │  > task.run_started       │
│              │  > executor.completed     │
│              │  > ...                    │
│              │  ──────────────          │
│              │  Artifacts (6)            │
│              │  > executor_prompt.md     │
│              │  > executor_output.md     │
└──────────────┴──────────────────────────┘
```

**功能要求**:
- 左栏：任务列表，按 focus 筛选（active / failed / recent / all），显示 status 圆点 + task_id + title
- 右栏上部：选中任务的核心状态（status / phase / route / executor / attempt）
- 右栏中部：事件流时间线（折叠式，点击展开 payload）
- 右栏下部：产物列表（点击查看内容）
- 顶部 Refresh 按钮手动刷新
- 纯 CSS 样式，无外部 CDN 依赖

**验收标准**:
- 浏览器打开 `http://127.0.0.1:8037/` 看到仪表盘
- 任务列表、状态、事件、产物均正确渲染
- 无 npm / node_modules / 构建步骤

**风险**: 3/9（impact 1, reversibility 1, dependency 1）

---

### S3: Artifact Review 双栏视图

**目标**: 在任务详情中提供产物内容查看视图，为后续 diff 对比预留结构。

**改动范围**:
- `src/swallow/web/static/index.html`：扩展 artifact 查看区域
- `src/swallow/web/api.py`：如需要，增加 artifact 对比端点

**功能要求**:
- 点击 artifact 名称 → 右栏展开产物内容（monospace 渲染 markdown/text）
- 支持同时打开两个 artifact 进行左右对比（如 `executor_prompt.md` vs `fallback_primary_executor_prompt.md`）
- 内容为只读展示，不支持编辑

**验收标准**:
- 产物内容正确渲染（保持格式 / 换行 / 缩进）
- 双栏对比可同时展示两个文件
- 无写入操作

**风险**: 2/9（impact 1, reversibility 1, dependency 0）

---

## 依赖关系

```
S1 (JSON API) ──→ S2 (仪表盘 HTML) ──→ S3 (Artifact Review)
```

严格顺序：S2 依赖 S1 的 API，S3 依赖 S2 的页面结构。

---

## 风险总览

| 维度 | S1 | S2 | S3 | 总体 |
|------|----|----|----|----|
| Impact Scope | 1 | 1 | 1 | — |
| Reversibility | 1 | 1 | 1 | — |
| Dependency Complexity | 1 | 1 | 0 | — |
| **Slice Total** | **3/9** | **3/9** | **2/9** | **8/27** |

**Phase 总体风险**: 低（8/27）

**R1**: FastAPI 作为新依赖 — 缓解：lazy import，不影响 CLI 核心功能；FastAPI 是纯 Python，无系统依赖
**R2**: Scope 膨胀 — 缓解：严格限制为只读 + vanilla JS + 无构建工具链；任何超出 scope 的 feature request 延后到独立 phase
**R3**: 前端代码维护负担 — 缓解：单个 HTML 文件，无组件化/路由/状态管理复杂度

---

## 技术选型说明

| 选项 | 选择 | 理由 |
|------|------|------|
| 后端框架 | FastAPI | 纯 Python，与现有 store 模块无缝集成，自带 OpenAPI docs |
| 前端框架 | 无（vanilla HTML/JS） | AGENTS.md 约束"极简栈"，避免 npm 依赖 |
| CSS | 内联或单文件 | 无外部 CDN，离线可用 |
| 实时更新 | 手动 Refresh 按钮 | MVP 阶段不需要 WebSocket |
| 端口 | 8037 | 避免常用端口冲突，"37" 对应 Phase 37 便于记忆 |
| 绑定地址 | 127.0.0.1 | 本地优先，不暴露公网 |
