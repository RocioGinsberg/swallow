---
author: claude
phase: 28
slice: Knowledge Promotion & Refinement Baseline
status: draft
depends_on: [docs/plans/phase28/design_decision.md]
---

## TL;DR
Phase 28 全 slice 低风险（总分 3-4），无高风险项。主要风险集中在 cli.py 单文件膨胀和 preflight 行为变更的向后兼容。

---

# Risk Assessment

## 风险矩阵

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 评级 |
|:------|:---------|:-------|:-----------|:-----|:-----|
| 1: task staged 聚合浏览 | 1 | 1 | 1 | 3 | 低 |
| 2: 晋升时文本精炼 | 1 | 1 | 2 | 4 | 低 |
| 3: Preflight 冲突提示增强 | 1 | 1 | 2 | 4 | 低 |

无 ≥7 的高风险 slice。

---

## 逐项风险分析

### Slice 1: task staged

**风险点**：无显著风险。纯新增 CLI 命令，不修改已有逻辑。

**缓解措施**：无需特殊缓解。

---

### Slice 2: 晋升时文本精炼

**风险点**：
1. `build_staged_canonical_record()` 目前在 cli.py 内定义（574-597 行），需要修改其签名以接受可选 refined_text。调用方需同步适配。
2. 精炼后的 text 与原始 text 不同，需确保审计线索完整（decision_note 标记）。

**缓解措施**：
1. `refined_text` 作为可选参数，默认 None 时行为不变，向后兼容。
2. 自动追加 `[refined]` 到 decision_note，无需 operator 手动标记。

---

### Slice 3: Preflight 冲突提示增强

**风险点**：
1. **行为变更**：新增 `--force` 机制意味着存在 supersede 冲突时默认拒绝晋升。如果有脚本或自动化依赖当前"无阻塞直接晋升"的行为，会出现 breaking change。
2. `build_stage_promote_preflight_notices()` 返回值结构可能需要区分 notice 类型（supersede vs idempotent），目前返回的是纯字符串列表。

**缓解措施**：
1. 评估当前是否有自动化调用 `knowledge stage-promote`。考虑到本项目以 operator 手动 CLI 为主，breaking change 风险极低。如有顾虑，可将 `--force` 改为 `--confirm` 的 warning 模式而非 blocking 模式。
2. 调整 `build_stage_promote_preflight_notices()` 返回结构化对象（含 notice_type 字段），而非纯字符串，以支持 handler 层区分处理。

---

## 跨 Slice 风险

### cli.py 膨胀

cli.py 已是仓库中最大的文件（2000+ 行）。三个 slice 都在此文件中新增/修改代码。

**缓解建议**：本轮不做 cli.py 拆分（那是单独的 refactor phase），但 Codex 实现时应：
- Slice 1 的 handler 逻辑尽量复用 `load_staged_candidates()` + 简单过滤，不引入复杂格式化逻辑
- 新增的格式化函数放在 handler 附近，保持局部内聚

### 测试覆盖

现有 staged knowledge 测试覆盖需确认。三个 slice 都需要新增对应测试。

---

## 总体评估

Phase 28 是一个低风险的增量改进 phase。所有 slice 都在已有稳定基础上扩展 CLI 层功能，不触及核心数据模型或存储逻辑。建议无需额外人工 gate，按 design_decision 中的顺序直接推进。
