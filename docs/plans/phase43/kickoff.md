---
author: claude
phase: 43
slice: react-degradation
status: draft
depends_on:
  - docs/roadmap.md
  - docs/plans/phase42/closeout.md
---

> **TL;DR** Phase 43 新增 ReAct 降级方言适配器：当目标模型不支持原生 Tool Calling 时，将 Tool Schema 渲染为 ReAct 纯文本引导语，回包阶段通过正则从文本还原为标准工具调用意图。3 个 slice，中风险。

# Phase 43 Kickoff: ReAct 降级方言 (Dynamic Capability Negotiation)

## Track

- **Primary Track**: Execution Topology
- **Secondary Track**: Capabilities

## 目标

让 Swallow 在目标模型不支持原生 Tool Calling（如 Ollama 上的 Qwen、DeepSeek 等本地开源模型）时，仍能通过 ReAct 纯文本方式执行工具调用，确保系统降级环境下不断链。

具体目标：

1. 新增 **`ReActDialect`** 适配器：将抽象 Tool Schema 渲染为 ReAct 格式的纯文本引导语（`Action: [tool_name]\nAction Input: {json}`），拼接到 prompt 末尾
2. 新增 **ReAct 回包解析器**：从模型纯文本输出中，通过正则提取 `Action` / `Action Input` / `Observation` 三元组，还原为标准内部工具调用意图
3. 将 ReActDialect 注册到 `BUILTIN_DIALECTS`，通过 `route_dialect="react"` 或 `model_hint` 匹配自动激活

## 非目标

- **不做多轮 ReAct 循环**：本阶段仅支持单轮 Action → Observation 提取。多轮 ReAct（Thought → Action → Observation → Thought → ...）留待后续 phase
- **不做 Tool Schema 自动发现**：Tool Schema 由 TaskCard 的 `input_schema` / `output_schema` 提供，不从外部注册表动态加载
- **不修改现有 Claude XML / Codex FIM / Structured Markdown 适配器**：仅新增 ReAct 适配器
- **不做 Ollama / vLLM API 集成**：ReAct 适配器只负责 prompt 格式化和输出解析，实际 HTTP 调用仍由 new-api 统一代理
- **不做 confidence scoring**：解析成功/失败为二值判断，不引入置信度评分

## 设计边界

### ReAct Prompt 渲染

当 `route_dialect="react"` 时，`ReActDialect.format_prompt()` 将在 raw prompt 基础上追加以下结构：

```
## Available Tools

You have access to the following tools. To use a tool, respond with:

Action: <tool_name>
Action Input: <json_arguments>

After the tool runs, you will see:

Observation: <tool_result>

Then continue with your response.

### Tools

- tool_name: description
  Parameters: {json_schema}
```

Tool Schema 来源：`TaskCard.input_schema` 中的 `tools` 字段（如存在），或从 `route_capabilities` 推断默认工具集。

如果没有可用工具（`tools` 为空且 `supports_tool_loop=False`），ReActDialect 降级为 `structured_markdown` 行为（不追加 tools section）。

### ReAct 回包解析

从模型输出文本中提取工具调用意图：

```python
# 正则模式
ACTION_PATTERN = r"Action:\s*(.+?)(?:\n|$)"
ACTION_INPUT_PATTERN = r"Action Input:\s*({.*?})(?:\n|$)"  # 贪婪 JSON 对象匹配
OBSERVATION_PATTERN = r"Observation:\s*(.+?)(?:\n|$)"
```

解析结果为 `ReActParseResult`：

```python
@dataclass(slots=True)
class ReActParseResult:
    action: str           # tool name
    action_input: dict    # parsed JSON arguments
    raw_text: str         # 原始输出文本（完整保留）
    parsed: bool          # 是否成功解析出 Action + Action Input
```

**解析失败处理**：如果正则无法提取合法的 Action + Action Input，`parsed=False`，原始文本作为 executor output 直接返回。不抛异常，不重试（重试由 ReviewGate + Debate Loop 处理）。

### 与现有系统的接口

- **`executor.py`**：`BUILTIN_DIALECTS` 新增 `"react": ReActDialect()`
- **`executor.py`**：`resolve_dialect_name()` 对 model_hint 含 `"qwen"` / `"deepseek"` / `"llama"` / `"ollama"` 时返回 `"react"`
- **`dialect_data.py`**：不修改。ReActDialect 通过 `collect_prompt_data()` 获取共享 prompt 数据
- **`models.py`**：`DialectSpec` 不修改。ReActDialect 使用现有 spec 结构
- **`review_gate.py`**：不修改。ReAct 解析失败时 output 可能不符合 output_schema，ReviewGate 会自然拦截并触发 Debate Loop

### ReActDialect 与其他适配器的关系

```
PlainTextDialect      — 零格式化，直接返回 raw prompt
StructuredMarkdownDialect — 结构化 markdown sections
ClaudeXMLDialect      — XML 标签包裹
CodexFIMDialect       — FIM 前缀/后缀分割
ReActDialect (新增)   — ReAct tools section + 回包正则解析
```

ReActDialect 是第一个在 `format_prompt` 之外还参与**输出解析**的适配器。为此需要扩展 `DialectAdapter` protocol：

```python
class DialectAdapter(Protocol):
    spec: DialectSpec
    def format_prompt(self, raw_prompt: str, state: TaskState, retrieval_items: list[RetrievalItem]) -> str: ...
    def parse_output(self, raw_output: str) -> str: ...  # 新增，默认返回原文
```

其他适配器的 `parse_output` 返回原文不做处理。ReActDialect 的 `parse_output` 执行正则提取并返回结构化结果（或原文）。

## Slice 拆解

### S1: ReAct Prompt 渲染

**目标**：新增 `src/swallow/dialect_adapters/react.py`，实现 `ReActDialect.format_prompt()`，将 Tool Schema 渲染为 ReAct 引导语。

**影响范围**：新增 `react.py`，修改 `dialect_adapters/__init__.py`

**风险评级**：
- 影响范围: 1 (新增独立模块)
- 可逆性: 1 (轻松回滚)
- 依赖复杂度: 1 (复用 dialect_data)
- **总分: 3** — 低风险

**验收条件**：
- `ReActDialect.format_prompt()` 在有 tools 时追加 ReAct tools section
- 无 tools 时降级为 structured_markdown 行为
- Tool Schema JSON 正确渲染
- 测试覆盖有/无 tools 两种场景

### S2: ReAct 回包解析器

**目标**：新增 `ReActParseResult` + `parse_react_output()` 函数，从文本提取 Action / Action Input。扩展 `DialectAdapter` protocol 新增 `parse_output` 方法。

**影响范围**：修改 `react.py`，修改 `executor.py`（`DialectAdapter` protocol + `BUILTIN_DIALECTS`）

**风险评级**：
- 影响范围: 2 (dialect adapter protocol 变更)
- 可逆性: 1 (轻松回滚)
- 依赖复杂度: 2 (正则解析 + protocol 扩展)
- **总分: 5** — 中风险

**验收条件**：
- 合法 ReAct 输出（`Action: xxx\nAction Input: {json}`）正确解析
- 畸形输出（无 Action / 非法 JSON）返回 `parsed=False` + 原文保留
- 多行 Action Input（JSON 跨行）正确处理
- 现有适配器的 `parse_output` 返回原文，不影响现有行为
- 全量 pytest 通过

### S3: 注册 + 路由集成

**目标**：将 ReActDialect 注册到 `BUILTIN_DIALECTS`，在 `resolve_dialect_name()` 中对 `qwen` / `deepseek` / `llama` / `ollama` model_hint 自动匹配。在 executor 调用链中，执行完成后调用 `dialect.parse_output()` 处理输出。

**影响范围**：修改 `executor.py`（注册 + 输出解析调用）、修改 `dialect_adapters/__init__.py`

**风险评级**：
- 影响范围: 2 (executor 输出处理路径)
- 可逆性: 1 (轻松回滚)
- 依赖复杂度: 2 (依赖 S1 + S2)
- **总分: 5** — 中风险

**验收条件**：
- `resolve_dialect_name(model_hint="qwen-72b")` 返回 `"react"`
- `resolve_dialect_name(model_hint="ollama/llama3")` 返回 `"react"`
- 端到端：ReAct dialect 格式化 prompt → executor 执行 → parse_output 处理输出
- 现有 Claude XML / Codex FIM / Structured Markdown 不受影响
- `swl doctor` / `swl task run` 正常工作
- 全量 pytest 通过

## Slice 依赖

```
S1 (Prompt 渲染) → S2 (回包解析) → S3 (注册 + 集成)
```

严格顺序依赖。

## 风险总评

| Slice | 影响 | 可逆 | 依赖 | 总分 | 评级 |
|-------|------|------|------|------|------|
| S1 | 1 | 1 | 1 | 3 | 低 |
| S2 | 2 | 1 | 2 | 5 | 中 |
| S3 | 2 | 1 | 2 | 5 | 中 |
| **合计** | | | | **13/27** | **中** |

主要风险在 S2（正则解析脆弱性）和 S3（executor 输出处理路径变更）。S2 需要高测试覆盖率，包括各种畸形输出场景。

**关键缓解措施**：
- 解析失败返回原文 + `parsed=False`，不抛异常，不阻断执行
- ReviewGate + Debate Loop 天然兜底：解析失败 → output 不符 schema → review 拦截 → feedback retry
- 现有适配器 `parse_output` 为 identity 函数，零行为变更

## 完成条件

1. `ReActDialect` 注册到 `BUILTIN_DIALECTS`，通过 `route_dialect="react"` 或 model_hint 自动激活
2. ReAct prompt 渲染包含 Tool Schema + ReAct 引导语
3. 回包解析器从文本提取 Action / Action Input，失败时返回原文
4. `DialectAdapter` protocol 新增 `parse_output` 方法，现有适配器兼容
5. 全量 pytest 通过，无回归

## Branch Advice

- 当前分支: `main`
- 建议操作: 人工审批 kickoff 后，从 `main` 切出 `feat/phase43-react-dialect`
- 理由: 新增 dialect adapter + protocol 扩展，应在 feature branch 上进行
- 建议 PR 范围: S1 + S2 + S3 合并为单 PR
