---
author: claude
phase: 43
slice: react-degradation
status: draft
depends_on:
  - docs/plans/phase43/kickoff.md
---

> **TL;DR** Phase 43 整体风险 13/27（中）。核心风险在 S2 正则解析和 S3 executor 输出路径变更。解析失败不阻断执行 + ReviewGate/Debate Loop 天然兜底是主要缓解手段。

# Phase 43 Risk Assessment

## 风险矩阵

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 风险等级 |
|-------|---------|--------|-----------|------|---------|
| S1: Prompt 渲染 | 1 — 新增模块 | 1 — 轻松回滚 | 1 — 复用 dialect_data | **3** | 低 |
| S2: 回包解析 | 2 — protocol 扩展 | 1 — 轻松回滚 | 2 — 正则解析 | **5** | 中 |
| S3: 注册 + 集成 | 2 — executor 路径 | 1 — 轻松回滚 | 2 — 依赖 S1+S2 | **5** | 中 |

**总分: 13/27** — 无高风险 slice。

## 各 Slice 风险详述

### S1: ReAct Prompt 渲染

**风险低**。纯新增代码，与现有适配器并列。

- Tool Schema 来自 `TaskCard.input_schema`，格式确定性高
- 无 tools 时降级为 structured_markdown 行为，不会产生空 prompt

### S2: ReAct 回包解析

**中风险**。本 phase 的核心风险点。

**关注点**：

1. **正则脆弱性**：模型可能输出非标准 ReAct 格式（大小写不一致、多余空格、Action Input 不是合法 JSON、JSON 跨多行、Action 后跟冒号和空格的变体）。需要测试覆盖至少以下场景：
   - 标准格式：`Action: tool\nAction Input: {"key": "value"}`
   - 大小写变体：`action:` / `ACTION:`
   - JSON 跨行：`Action Input: {\n  "key": "value"\n}`
   - 无 Action Input（只有 Action）
   - 完全无法解析（普通文本）
   - Action Input 不是合法 JSON
   - 多个 Action 块（取第一个）

2. **DialectAdapter protocol 扩展**：新增 `parse_output` 方法。由于 Python Protocol 不强制实现所有方法，现有适配器只需新增一个返回原文的 `parse_output` 即可。但需确认 `PlainTextDialect` / `StructuredMarkdownDialect` / `ClaudeXMLDialect` / `CodexFIMDialect` 四个类都加上此方法。

3. **Action Input JSON 解析**：`json.loads` 对不合法 JSON 直接 fail → `parsed=False`。不做 JSON 修复/推测。

### S3: 注册 + 集成

**中风险**。修改 executor 输出处理路径。

**关注点**：

1. **`parse_output` 调用位置**：应在 executor 返回 `ExecutorResult` 之后、写入 artifact 之前调用。需确保不破坏现有的 `executor_output.md` artifact 写入（artifact 应写原始输出，parse_output 的结果用于后续逻辑消费）。
2. **model_hint 匹配范围**：`qwen` / `deepseek` / `llama` / `ollama` 作为 hint 前缀匹配可能过于宽泛。如果用户使用 `deepseek-coder` 等代码专用模型，可能更适合 `codex_fim` 而非 `react`。建议匹配优先级为：explicit `route_dialect` > `codex_fim` (code models) > `react` (generic local models)。
3. **现有测试兼容性**：所有使用 mock executor 的测试默认走 `plain_text` 或 `structured_markdown`，不会触发 ReAct 路径。但需验证 `resolve_dialect_name` 对现有 model_hint（`claude` / `codex` / `local`）的返回值不变。

**缓解措施**：
- S3 实现前先写 `resolve_dialect_name` 的回归测试，确保现有 hint 返回值不变
- `parse_output` 调用为 opt-in：仅在 dialect 是 `react` 时执行实际解析，其他 dialect 透传

## 与现有防线的协同

ReAct 解析失败的兜底链路已经完备：

```
ReAct 解析失败 (parsed=False)
  → output 是原始文本，不符合 output_schema
  → ReviewGate 拦截 (output_schema check failed)
  → Debate Loop 生成 feedback
  → Executor 重试（feedback 提示"返回符合 schema 的 JSON"）
  → 最多 3 轮后熔断到 waiting_human
```

这意味着 ReAct 解析器**不需要做到完美** — 它只需要处理常见格式，边缘 case 由现有审查机制兜底。

## 整体判断

Phase 43 为中风险，核心在 S2 的正则解析质量。但由于 ReviewGate + Debate Loop 的天然兜底，解析失败不会导致系统静默错误。建议 S2 完成后由 Human 审查 diff 再进入 S3。
