---
author: claude
phase: 44
slice: control-center-enhancement
status: draft
depends_on:
  - docs/plans/phase44/kickoff.md
---

> **TL;DR** Phase 44 整体风险 13/27（中）。三个 slice 互不依赖，核心风险在 S3 内联图表 JS 复杂度。Scope 膨胀是最高优先级防线：严格只读 + 不引入第三方 JS 库。

# Phase 44 Risk Assessment

## 风险矩阵

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 风险等级 |
|-------|---------|--------|-----------|------|---------|
| S1: 子任务树 | 2 — API + 前端 | 1 — 轻松回滚 | 1 — 读 events | **4** | 低-中 |
| S2: Artifact 对比 | 2 — API + 前端 | 1 — 轻松回滚 | 1 — 复用现有 | **4** | 低-中 |
| S3: 成本/延迟时间线 | 2 — API + 前端 | 1 — 轻松回滚 | 2 — 事件聚合 + 图表 | **5** | 中 |

**总分: 13/27** — 无高风险 slice。

## 各 Slice 风险详述

### S1: 子任务树

**风险低-中**。API 从 events.jsonl 提取 `task.planned` + subtask 事件，逻辑确定性高。

- 需确认事件日志中 `task.planned` 的 payload 包含 card 列表信息（已在 Phase 33 确立）
- 前端树状展示用 HTML nested list 即可，不需要 SVG/Canvas

### S2: Artifact 对比

**风险低-中**。复用现有 `build_task_artifact_payload()` 读取两个 artifact。

- 首版不做 diff 高亮，仅 side-by-side 纯文本展示
- left/right 参数校验需注意 path traversal（已有 `..` 检查基线）

### S3: 成本/延迟时间线

**风险中**。本 phase 唯一复杂点。

**关注点**：

1. **内联 JS 图表**：约 100-150 行 JS 实现最小折线图。需控制复杂度 — 如果超过 200 行 JS，说明 scope 膨胀。备选：用纯 ASCII/HTML table 展示数据，图表降级为可选增量。
2. **事件聚合逻辑**：需正确区分正常执行 vs debate retry（通过 `review_feedback` 字段），与 Phase 42 S3 的 Meta-Optimizer 隔离逻辑保持一致。
3. **空状态处理**：无执行事件的任务应显示友好空状态，不应报错。

## Scope 膨胀专项评估

这是 roadmap 风险批注中标注的**最高关注点**。

**防线清单**：
- [ ] 所有新 API 为 GET，零写入 `.swl/`
- [ ] 单 HTML 文件，无 npm / webpack / 构建步骤
- [ ] 不引入 Chart.js / D3 / 任何第三方 JS 库
- [ ] 不做 diff 高亮算法
- [ ] 不做 WebSocket 实时推送
- [ ] 不做 Approve / Reject 写入操作
- [ ] 不做移动端适配
- [ ] 不做用户认证

如果实现过程中任何一项防线被突破，应立即 scope cut。

## 整体判断

Phase 44 为中风险的前端 + API 扩展工作。核心约束是"只读 + 极简栈"。三个 slice 互不耦合，可顺序推进。如果 S3 图表 JS 复杂度超预期，可降级为 HTML table 展示。
