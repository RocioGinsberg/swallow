---
author: claude
phase: 45
slice: eval-baseline-deep-ingestion
status: draft
depends_on:
  - docs/plans/phase45/kickoff.md
---

> **TL;DR** Phase 45 整体风险 11/27（低-中）。S1/S3 为低风险新增代码，S2 的 ChatGPT 对话树算法为唯一中风险点。eval 基础设施首次引入但不影响现有 pytest 默认行为。

# Phase 45 Risk Assessment

## 风险矩阵

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 风险等级 |
|-------|---------|--------|-----------|------|---------|
| S1: Eval 基础设施 | 1 — 新增目录 | 1 — 轻松回滚 | 1 — 调用已有函数 | **3** | 低 |
| S2: 对话树还原 | 2 — 解析+过滤 | 1 — 轻松回滚 | 2 — 树算法+语义 | **5** | 中 |
| S3: 结构化摘要 | 1 — 新增函数 | 1 — 轻松回滚 | 1 — 基于 signals | **3** | 低 |

**总分: 11/27** — 无高风险 slice。

## 各 Slice 风险详述

### S1: Eval 基础设施

**风险极低**。纯新增目录和文件，不修改任何现有代码路径。

- `addopts = "-m 'not eval'"` 确保默认 pytest 行为零变更
- golden dataset 为静态 fixture 文件，不依赖外部服务
- eval 测试结果为质量信号，不是 merge blocker

**唯一关注**：golden dataset 的标注质量决定了 eval 基线的可信度。标注应由 Human 审核确认。

### S2: 对话树还原

**中风险**。本 phase 唯一需要算法设计的 slice。

**关注点**：

1. **ChatGPT `mapping` 树结构解析**：每个 node 有 `parent` 和 `children` 字段。需要正确处理：孤立节点（无 parent 的非 root 节点）、循环引用（防御性检查）、空 children 列表。
2. **主路径选择算法**：选择"最后修改的 leaf 路径"而非"最长路径"更符合用户意图（用户 regenerate 后通常用最后一次）。需基于 `create_time` 或 node 在 children 数组中的位置判断。
3. **abandoned branch 过滤语义**：过于激进会丢失有价值的"被否方案"记录（为什么否定 A 方案的理由本身是知识）。建议保留 abandoned branch 中含否定关键词的 turn。
4. **向后兼容**：无分支的 ChatGPT 导出（所有 node 线性链接）必须行为不变。S1 的 eval 在此提供回归保护。

**缓解措施**：
- S2 实现前先跑 S1 eval 建立基线
- S2 实现后再跑 S1 eval 确认 precision/recall 不退化
- 树解析增加防御性检查（循环检测、孤立节点处理）

### S3: 结构化摘要

**风险极低**。基于 `ExtractedFragment.signals` 做关键词分类，纯字符串处理。

## Eval 引入的特殊风险

这是项目首次引入 eval 测试。需确认：

1. `pyproject.toml` 的 marker 配置不影响现有 `pytest` 命令的行为（`addopts = "-m 'not eval'"` 只排除 eval 标记的测试）
2. `tests/eval/` 目录下的 fixture 文件（JSON/JSONL）不会被 pytest 误收集为测试模块
3. eval 测试中使用相对路径引用 fixture 文件，不依赖绝对路径

## 整体判断

Phase 45 为低-中风险，核心价值在于**建立质量度量基础设施**——这是从"功能完成即合格"到"体验质量可量化"的范式转变。S2 的对话树算法需要仔细设计，但 S1 的 eval 基线为其提供了回归保护网。
