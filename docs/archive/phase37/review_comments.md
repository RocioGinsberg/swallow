---
author: claude
phase: 37
slice: all
status: final
depends_on: [docs/plans/phase37/kickoff.md]
---

> **TL;DR**: Phase 37 实现质量良好，3 个 slice 均满足 kickoff 验收标准。只读约束严格执行，无外部 CDN 依赖，UI 布局符合设计。0 BLOCK，2 CONCERN，0 NOTE。后续 follow-up 已在当前分支吸收，最新测试基线为 262 passed。

# Phase 37 Review — Control Center Baseline (只读 Web 仪表盘)

## 审查范围

- **分支**: `feat/phase37-control-center`
- **Commits**: 4 (S1 API baseline + S2 dashboard + S3 artifact review + closeout)
- **变更量**: +1420 / -22 lines, 11 files
- **测试结果**: 261 passed, 5 subtests, 6.22s

---

## Slice 完成矩阵

| Slice | Kickoff 标准 | 实际交付 | 状态 |
|-------|-------------|---------|------|
| S1: JSON API 层 | FastAPI 7 个只读端点 + `swl serve` CLI 入口 | 8 GET-only routes（health / tasks / task detail / events / artifacts / single artifact / knowledge + static root）；`swl serve --host --port`；lazy import 不影响 CLI | **[PASS]** |
| S2: 单页 HTML 仪表盘 | 左栏任务列表 + 右栏状态/事件/产物；vanilla JS；无构建工具链 | 753 行单文件 HTML；左右分栏 grid 布局；focus 筛选（active/failed/recent/all/needs-review）；事件折叠展开；手动 Refresh；响应式 980px 断点 | **[PASS]** |
| S3: Artifact Review 双栏 | 产物内容查看 + 左右对比 | 双 artifact selector + 并排内容面板；monospace 渲染；只读展示 | **[PASS]** |

---

## 架构一致性审查

### 只读约束验证

**[PASS] 零写入 `.swl/`**
- 全部 8 个路由均为 `@app.get()`，无 POST/PUT/DELETE/PATCH
- 测试 `test_web_api_payloads_are_read_only_and_return_expected_task_data` 通过 checksum 前后对比验证 app 目录无变更
- index.html 中所有 fetch 调用均为默认 GET（无 method override）

### 极简栈验证

**[PASS] 无前端构建工具链**
- 零 npm / node_modules / webpack / vite 依赖
- 零外部 CDN 链接（CSS 内联，字体使用系统 fallback 栈）
- FastAPI 通过 lazy import 引入，不影响 CLI 核心功能
- `test_cli_serve_reports_missing_optional_dependencies_without_breaking_other_commands` 验证 FastAPI 缺失时的优雅降级

### 安全审查

**[PASS] XSS 防护**
- `escapeHtml()` 函数对所有用户可控字段进行 HTML entity 转义
- URL 参数使用 `encodeURIComponent()` 编码

**[PASS] 路径遍历防护（基本层）**
- artifact 路由 `/api/tasks/{task_id}/artifacts/{artifact_name:path}` 通过 `artifact["name"]` 匹配（从 state.artifact_paths 索引，非用户输入构造路径）
- 实际文件读取路径来自 `_collect_artifact_index()` 的可信数据源

### API 设计

**[PASS] RESTful 一致性**
- 路径命名清晰：`/api/tasks` → `/api/tasks/{id}` → `/api/tasks/{id}/events`
- 错误处理：FileNotFoundError → 404 HTTPException
- 所有响应为 JSON（artifact 内容以 JSON object 包裹，含 `exists` / `content` 字段）

### UI 设计

**[PASS] 符合 kickoff spec**
- 左栏任务列表 + focus 筛选
- 右栏核心状态 + 事件时间线 + 产物列表
- Artifact 双栏对比视图
- Refresh 按钮 + 最后刷新时间戳
- 响应式布局（≤980px 单栏折叠）

---

## 测试覆盖审查

| 文件 | 新增测试 | 覆盖评价 |
|------|---------|---------|
| test_web_api.py | 5 | 核心路径覆盖：static HTML 结构 / app 路由暴露 / 全端点 read-only 验证 / focus filter / unknown artifact 404 |
| test_cli.py | 3 | serve 命令：help / dispatch / 依赖缺失降级 |

**总体**: 261 passed（较 Phase 36 的 253 新增 8 个测试）。

---

## CONCERN

### C1: artifact 路由缺少显式路径段校验 [CONCERN]

**位置**: `src/swallow/web/api.py` artifact 端点

`/api/tasks/{task_id}/artifacts/{artifact_name:path}` 接受 `:path` 类型参数，允许 `artifact_name` 包含 `/` 和 `..`。虽然当前实现通过 `artifact["name"]` 匹配（来自可信索引）有效防御了路径遍历，但防御依赖于 `_collect_artifact_index()` 的正确性，没有显式的入口校验。

**当前影响**: 低。攻击者需要 `state.artifact_paths` 中存在恶意路径才能利用，而 state 文件由 CLI 生成。
**建议**: 在 `build_task_artifact_payload()` 入口增加显式校验：
```python
if ".." in artifact_name:
    raise HTTPException(status_code=400, detail="Invalid artifact name")
```
可在本轮 follow-up 或下一轮触碰 web API 时消化。

### C2: focus filter 测试覆盖不完整 [CONCERN]

**位置**: `tests/test_web_api.py`

`_filter_task_states()` 支持 5 种 focus（active / failed / recent / all / needs-review），但测试仅覆盖 active 和 failed。特别是 `needs-review` 的过滤逻辑较复杂（`status == "failed" or phase == "summarize" or executor_status != "completed"`），缺少直接测试。

**当前影响**: 低。过滤逻辑简单且只读，不影响数据安全。
**建议**: Codex 在 follow-up 中补充 needs-review 和 all 的 filter 测试。

---

## 回归安全确认

- 261 tests passed, 0 skips, 0 xfails
- FastAPI 为 lazy import，不影响既有 CLI 功能（通过 test 验证）
- 零新 `.swl/` 写入路径引入
- 新增 `src/swallow/web/` 包为纯新增模块，无回归面

---

## 结论

**Merge ready — 0 BLOCK, 2 CONCERN, 0 NOTE**

Phase 37 成功落地只读 Web 控制中心原型，严格遵守只读约束和极简栈要求。C1 与 C2 已在当前分支继续吸收：artifact 端点新增显式 `..` 校验并返回 400，`needs-review` / `all` focus filter 已补测试覆盖。当前分支处于 merge ready 状态。

---

## Tag 评估

Phase 37 merge 后，建议**打新 tag `v0.2.0`**。理由：

- Control Center 是首个用户可感知的新入口（Web UI），相比 v0.1.0 的纯 CLI 体验有质的变化
- `swl serve` 命令为 operator 提供了全新的交互模式
- Phase 36 的 concern 清理 + Phase 37 的 Web 仪表盘共同构成了有意义的里程碑
- 当前 main 处于稳定状态（261 tests passed，无进行中的重构）
