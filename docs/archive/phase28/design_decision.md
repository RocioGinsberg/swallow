---
author: claude
phase: 28
slice: Knowledge Promotion & Refinement Baseline
status: draft
depends_on: [docs/plans/phase28/context_brief.md, docs/plans/phase28/design_preview.md]
---

## TL;DR
Phase 28 在已有 `knowledge stage-promote` 基础上补齐三块：(1) `task staged` 聚合浏览命令，(2) 晋升时文本精炼（operator 手动编辑），(3) preflight 冲突提示增强。不新增核心数据模型，主要是 CLI 层 + 薄逻辑层扩展。

---

## 方案总述

源码分析发现 `swl knowledge stage-promote <candidate_id>` 已可工作，`StagedCandidate` 和 `CanonicalRecord` 的数据模型、存储、去重/supersede 逻辑均已就绪。Phase 28 的真正工作是补齐 operator 日常使用时的易用性缺口：

1. **浏览入口缺失**：`knowledge stage-list` 存在但缺乏按任务/状态过滤的聚合视图
2. **精炼能力缺失**：晋升时无法修改 text，只能原样搬运
3. **冲突提示不够显眼**：preflight notices 存在但仅打印文本，operator 容易忽略

方案不改动 `StagedCandidate`/`CanonicalRecord` 的核心字段结构，不改动 `append_canonical_record` 的去重/supersede 逻辑，不引入 AI 自动决策。

---

## Slice 拆解

### Slice 1: `task staged` 聚合浏览命令

**目标**：在 `swl task` 子命令下新增 `staged` 命令，提供面向 operator 的聚合视图。

**具体内容**：
- `swl task staged [--status pending|promoted|rejected] [--task <task_id>]`
- 输出：candidate 列表，含 candidate_id、text 摘要（前 80 字符）、source_task_id、status、submitted_at
- 默认只显示 `pending` 状态
- 复用 `load_staged_candidates()` + 过滤逻辑

**影响范围**：`cli.py`（新增 parser + handler）

**风险评级**：
- 影响范围：1（单文件）
- 可逆性：1（轻松回滚）
- 依赖复杂度：1（无外部依赖）
- **总分：3（低风险）**

**验收条件**：
- `swl task staged` 列出所有 pending candidates
- `--status` 过滤正常工作
- `--task` 按 source_task_id 过滤正常工作
- 空列表时给出友好提示

---

### Slice 2: 晋升时文本精炼

**目标**：扩展 `knowledge stage-promote` 支持晋升时修改 text。

**具体内容**：
- 新增 `--text <refined_text>` 参数到 `swl knowledge stage-promote`
- 如果提供 `--text`，晋升时使用精炼后的文本替代原始 text
- 精炼文本同时写入 canonical record 的 `text` 字段
- 在 `decision_note` 中自动追加 `[refined]` 标记以保留审计线索
- 不修改原始 `StagedCandidate` 的 text（保留原文可追溯）

**影响范围**：`cli.py`（parser 扩展 + handler 修改）、`build_staged_canonical_record()` 需要接受可选 refined_text

**风险评级**：
- 影响范围：1（单文件，薄逻辑层）
- 可逆性：1（轻松回滚）
- 依赖复杂度：2（依赖 `build_staged_canonical_record` + `append_canonical_record`）
- **总分：4（低风险）**

**验收条件**：
- `swl knowledge stage-promote <id> --text "refined content"` 成功晋升
- canonical record 中 text 为精炼后内容
- decision_note 含 `[refined]` 标记
- 原始 staged candidate 的 text 不被修改
- 不带 `--text` 时行为不变

---

### Slice 3: Preflight 冲突提示增强

**目标**：让 supersede/重复检测结果更醒目，增加确认机制。

**具体内容**：
- 增强 `build_stage_promote_preflight_notices()` 的输出格式：
  - 冲突类型明确标注：`[SUPERSEDE]` vs `[IDEMPOTENT]`
  - 显示被影响的 canonical record 摘要（canonical_id、text 前 60 字符）
- 新增 `--force` flag：当存在 supersede 冲突时，默认拒绝晋升并要求 `--force`
- 无冲突时正常晋升，不需要 `--force`

**影响范围**：`cli.py`（handler 修改 + 输出格式）

**风险评级**：
- 影响范围：1（单文件）
- 可逆性：1（轻松回滚）
- 依赖复杂度：2（依赖 `build_stage_promote_preflight_notices` 返回结构）
- **总分：4（低风险）**

**验收条件**：
- 存在 supersede 冲突时，不带 `--force` 拒绝晋升并打印冲突详情
- `--force` 时正常晋升并打印 supersede 结果
- 无冲突时无需 `--force`
- idempotent 重复晋升时给出提示但不阻塞

---

## 依赖说明

```
Slice 1 (task staged)  ← 无依赖，可独立实现
Slice 2 (refinement)   ← 无依赖，可独立实现
Slice 3 (preflight)    ← 无依赖，可独立实现
```

三个 slice 无顺序依赖，可按任意顺序实现。建议按 1→2→3 顺序以保持递进逻辑。

---

## 明确的非目标

- **不做 AI 自动晋升决策**：所有晋升由 operator 显式触发
- **不做语义向量去重**：冲突检测仅基于 canonical_key 精确匹配
- **不做批量晋升**：本轮只支持单条晋升，批量操作留给后续 phase
- **不改动 StagedCandidate 数据模型**：不新增字段
- **不改动 CanonicalRecord 核心结构**：不新增字段
- **不改动 append_canonical_record 的去重/supersede 逻辑**：该逻辑已在 Phase 26 稳定

---

## Branch Advice

- 当前分支: `main`
- 建议操作: Human 审批后新建分支
- 建议分支名: `feat/phase28-knowledge-promotion`
- 建议 PR 范围: Slice 1-3 统一入一个 PR（三个 slice 都是低风险、单文件改动，拆 PR 无收益）

---

## Phase Guard

- [x] 方案不越出 Knowledge Promotion & Refinement Baseline 的 goals
- [x] 方案不触及非目标（无 AI 自动决策、无语义去重、无 agentic RAG）
- [x] Slice 数量 = 3（≤5，合理）
