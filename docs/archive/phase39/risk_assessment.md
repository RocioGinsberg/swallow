---
author: claude
phase: 39
slice: ingestion-specialist
status: final
depends_on:
  - docs/plans/phase39/kickoff.md
---

> **TL;DR** Phase 39 整体风险 11/27（低-中）。S1/S2 纯新增代码零耦合，S3 跨模块集成为唯一关注点，需确保 StagedCandidate 注册路径兼容。

# Phase 39 Risk Assessment

## 风险矩阵

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 风险等级 |
|-------|---------|--------|-----------|------|---------|
| S1: Ingestion Parser | 1 — 新增独立包 | 1 — 轻松回滚 | 1 — 无外部依赖 | **3** | 低 |
| S2: Ingestion Filter | 1 — 新增独立模块 | 1 — 轻松回滚 | 1 — 无外部依赖 | **3** | 低 |
| S3: Pipeline + CLI | 2 — 跨模块集成 | 1 — 轻松回滚 | 2 — 依赖 staged_knowledge | **5** | 中 |

**总分: 11/27** — 无高风险 slice，无需额外人工 gate。

## 各 Slice 风险详述

### S1: Ingestion Parser

**风险极低**。新增 `src/swallow/ingestion/` 包，不修改任何现有文件。

- ChatGPT/Claude Web/Open WebUI 导出格式均为公开 JSON 结构，解析逻辑确定性高
- Open WebUI 使用 OpenAI 兼容的 messages 格式，与 ChatGPT 解析器可复用大部分逻辑
- Markdown 按 heading 分段为成熟模式
- 唯一关注：外部导出格式可能随平台更新变化 → 通过解析器内部版本检测 + graceful degradation 缓解

### S2: Ingestion Filter

**风险极低**。规则式降噪，不引入 LLM 调用，不依赖外部模块。

- 关键词匹配列表可能需要后续迭代调整 → 首版保守（高召回低精度），避免误删有价值内容
- 中文/英文混合场景需覆盖 → 测试用例应包含中英文样本

### S3: Pipeline + CLI

**中风险**。唯一需要关注的跨模块集成点：

1. **StagedCandidate 兼容性**：`register_staged_candidate()` 要求 `source_task_id` 非空 → Ingestion pipeline 不在任务上下文中运行，需设计合理的 synthetic task_id 或扩展 StagedCandidate 允许 ingestion 场景
2. **paths.py 扩展**：新增 ingestion 相关路径 helper，需确保不与现有路径冲突
3. **CLI 集成**：`swl ingest` 子命令注册，需确保不影响现有命令帮助文本

**缓解措施**：
- S3 实现前先确认 `StagedCandidate` 的 `source_task_id` 约束，必要时 S3 开头先做最小 schema 适配
- CLI 注册使用现有 Click group 扩展模式，与 Phase 37 `swl serve` 一致

## 与历史 Concern 的交互

- **Phase 36 C1 (save_state → index 一致性)**：Ingestion 不走 save_state 路径，通过 `register_staged_candidate()` 直接写 registry，不受此 concern 影响
- **Phase 38 C1 (fallback 成本统计)**：与 Ingestion 无关

## 整体判断

Phase 39 为低-中风险，主要是新增代码。建议正常推进，无需额外设计 gate。S3 集成时注意 `source_task_id` 约束即可。
