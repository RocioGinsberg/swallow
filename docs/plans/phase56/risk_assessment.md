---
author: claude
phase: 56
slice: risk_assessment
status: draft
depends_on:
  - docs/plans/phase56/kickoff.md
  - docs/plans/phase56/design_decision.md
---

## TL;DR

Phase 56 是系统首次引入新的 LLM 调用。核心风险集中在两处：(1) LLM 返回非 JSON 或格式不符时的 fallback 鲁棒性；(2) 关系建议的 hallucination 导致 operator 信任度下降。两者均有成熟的缓解手段。成本追踪统一是低风险的 additive 变更。整体风险评级：**中**。

---

## 风险矩阵

| ID | 风险 | 概率 | 影响 | 等级 | 消化时机 |
|----|------|-----|-----|------|---------|
| R1 | LLM 返回非 JSON 或格式不符，Agent fallback 逻辑不够鲁棒 | 中 | 中 | **中** | S2/S3 实施时 |
| R2 | 关系建议 hallucination——LLM 推断不存在的关系或错误的关系类型 | 中 | 中 | **中** | S2 实施时 |
| R3 | API key 未配置导致所有 LLM 增强功能静默退化 | 中 | 低 | **低** | S2/S3 实施时 |
| R4 | HTTP executor usage 提取改动影响现有 event truth 链路 | 低 | 中 | **低** | S1 实施时 |
| R5 | `call_agent_llm()` 的 timeout / retry 策略不够完善 | 低 | 低 | **低** | S2 实施时 |
| R6 | `apply-suggestions` 命令在 object_id 不存在时行为不清晰 | 低 | 低 | **低** | S4 实施时 |

---

## 中风险详解

### R1 — LLM 返回格式不符

**描述**：Agent 要求 LLM 返回结构化 JSON（`{"summary": ..., "relation_suggestions": [...]}`），但 LLM 可能返回纯文本、部分 JSON、或结构不符的 JSON。

**触发场景**：
- LLM 返回 markdown 而非 JSON → `json.loads()` 失败
- LLM 返回 JSON 但字段名不同（如 `suggestions` 而非 `relation_suggestions`） → KeyError
- LLM 在 JSON 前后加了解释文本 → 需要提取 JSON 块

**缓解**：
- `call_agent_llm()` 返回后，先尝试 `json.loads(response.content)`
- 失败时尝试从 content 中提取 `{...}` 或 `[...]` 块（regex 提取最外层 JSON）
- 仍然失败则抛出 `AgentLLMUnavailable`，触发 fallback 到启发式
- TDD 测试覆盖：正常 JSON、前后有文本的 JSON、纯文本、空 response

**残留风险**：低。fallback 到启发式是生产安全的。

### R2 — 关系建议 hallucination

**描述**：LLM 可能推断出不合理的关系（如将无关的知识对象标记为 `contradicts`），或引用不存在的 object_id。

**触发场景**：
- LLM 推断 `knowledge-0001 cites knowledge-0099`，但 `knowledge-0099` 不存在
- LLM 推断 `contradicts` 但实际是 `extends`
- LLM 为所有文档对都产生 `related_to`，建议泛滥

**缓解**：
- **operator gate（P7 原则）**：关系建议不自动落库，operator 看完报告后手动确认
- **object_id 验证**：`apply-suggestions` 命令在落库前验证 object_id 存在性，不存在的关系直接跳过并报告
- **confidence 字段**：LLM 输出每条建议的 confidence，operator 可优先处理高置信度建议
- **建议数量限制**：prompt 中限制建议数量（如"最多 5 条最重要的关系"）

**残留风险**：中。LLM hallucination 无法完全消除，但 operator gate 保证不会有错误关系进入图谱。

---

## 低风险详解

### R3 — API key 未配置

**缓解**：Agent 检测到 API key 缺失时直接 fallback 到启发式，在 `ExecutorResult.message` 中提示"LLM enhancement unavailable: API key not configured"。不报错、不中断。

### R4 — HTTP executor usage 提取

**缓解**：`_attach_estimated_usage()` 改为"已有值 > 0 时跳过"的 fallback 模式。即使 usage 提取逻辑有 bug（返回 0），也会 fallback 到 `len // 4`，不会比现状更差。

### R5 — timeout / retry

**缓解**：`call_agent_llm()` 使用单次请求 + configurable timeout（默认 30s）。Agent 的 LLM 调用不做重试——失败直接 fallback 到启发式，比重试更快更可靠。

### R6 — apply-suggestions 的 object_id 验证

**缓解**：`create_knowledge_relation()` 已有 `_resolve_knowledge_object_id()` 验证。不存在的 object_id 会抛 ValueError，`apply-suggestions` 捕获后跳过该条并报告。

---

## 回归风险监控

| 区域 | 监控指标 | 回归信号 |
|------|---------|---------|
| 成本追踪 | `estimated_input_tokens` / `estimated_output_tokens` 在 event truth 中 | HTTP 路径的值从估算值变为精确值（预期变化，不是回归） |
| LiteratureSpecialist | `analysis_method` 字段 | API key 已配置但仍输出 `heuristic`（fallback 不应触发） |
| QualityReviewer | `analysis_method` 字段 | 同上 |
| 关系建议 | `side_effects.relation_suggestions` | 建议列表为空但 LLM 正常返回了分析（prompt 问题） |
| 全量回归 | `pytest --tb=short` | 任何 failure |

---

## 风险吸收判断

**可以接受的风险**：
- R1：多层 JSON 解析 + fallback 到启发式
- R2：operator gate + confidence 字段
- R3：优雅降级 + 提示信息
- R4：fallback-only 模式不会比现状更差
- R5：单次请求 + 快速 fallback
- R6：复用现有 object_id 验证

**Phase 56 整体风险评级：中**

- 2 个中风险（LLM 格式 + hallucination），缓解措施充分
- 4 个低风险，均可接受
- 首次引入 LLM 调用的架构风险通过 fallback 到 Phase 53 启发式完全消除
- 工作量约 34h，低于 Phase 55（40h）
