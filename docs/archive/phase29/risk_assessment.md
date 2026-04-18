---
author: claude
phase: 29
slice: Provider Dialect Baseline
status: draft
depends_on: [docs/plans/phase29/design_decision.md]
---

## TL;DR
Phase 29 总体中低风险（总分 4-5）。核心风险在 Slice 2 重构——必须确保现有行为零变化。Slice 3 引入首个非默认 dialect，需要充分测试 markdown 输出质量。无高风险项。

---

# Risk Assessment

## 风险矩阵

| Slice | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 评级 |
|:------|:---------|:-------|:-----------|:-----|:-----|
| 1: DialectAdapter 接口与 Registry | 2 | 1 | 1 | 4 | 低 |
| 2: plain_text 默认 Dialect 提取 | 1 | 1 | 2 | 4 | 低 |
| 3: structured_markdown Dialect | 2 | 1 | 2 | 5 | 中低 |
| 4: CLI 可观测性 | 2 | 1 | 2 | 5 | 中低 |

无 ≥7 的高风险 slice。

---

## 逐项风险分析

### Slice 1: DialectAdapter 接口与 Registry

**风险点**：无显著风险。纯新增数据结构和注册机制。

**唯一关注**：`RouteSpec` 新增 `dialect_hint` 字段会影响 BUILTIN_ROUTES 字典。需确认所有现有 route 的默认值为空字符串，不破坏 `to_dict()` / `from_dict()` 如果存在的话。

**缓解措施**：`dialect_hint` 默认空字符串，现有 route 无需修改。

---

### Slice 2: plain_text 默认 Dialect 提取

**风险点**：
1. **重构风险**：修改 `run_executor_inline()` 的调用链路。如果 dialect 层引入任何微妙变化（如换行符差异），现有测试可能 fail。
2. **prompt artifact 变化**：如果在 prompt 头部添加 `dialect: plain_text` 元数据行，依赖 prompt 内容精确匹配的测试会失败。

**缓解措施**：
1. `PlainTextDialect.format_prompt()` 必须是严格的 identity transform（`return raw_prompt`），不做任何修改。
2. dialect 元数据行写入单独的 artifact 文件（如 `executor_dialect.txt`），或追加到 executor event payload，不修改 prompt 本身。

---

### Slice 3: structured_markdown Dialect

**风险点**：
1. **prompt 质量**：markdown 格式的 prompt 是否真的比 plain text 更适合 codex CLI？如果 codex 对 heading/list 格式响应更差，可能影响执行质量。
2. **格式转换正确性**：raw prompt 的 key-value 结构是隐式的（按行分割，无明确分隔符），解析时可能出错。

**缓解措施**：
1. **不改变信息内容**，只改变排版。即使 markdown 格式略差，也不会丢失信息。如果实际测试发现 codex 对 markdown 响应更差，可以快速将 `local-codex` 的 `dialect_hint` 改回空（退回 plain_text）。
2. 不做 raw prompt 解析。`StructuredMarkdownDialect.format_prompt()` 应直接接收结构化参数（state + retrieval_items），独立构建 markdown 输出，而非解析 raw prompt 字符串。这意味着 `DialectAdapter.format_prompt()` 签名需要同时接收 raw_prompt 和原始数据。

---

### Slice 4: CLI 可观测性

**风险点**：无显著风险。纯展示层增加字段。

**缓解措施**：无需特殊缓解。

---

## 跨 Slice 风险

### 测试策略

Slice 2 是安全关键点。建议的测试策略：

1. Slice 2 完成后，运行全量测试确认零回归
2. Slice 3 新增 dialect-specific 测试，不修改已有测试
3. Slice 4 在 inspect/review 相关测试中追加 dialect 字段断言

### `build_executor_prompt()` 的双重角色

当前 `build_executor_prompt()` 同时负责信息收集和格式化。引入 dialect 后，如果 `StructuredMarkdownDialect` 需要独立格式化，`build_executor_prompt()` 可能需要拆分为"收集数据"和"格式化输出"两步。这不在设计边界内但 Codex 实现时可能自然需要。

**建议**：如果拆分必要，控制在 executor.py 内部，不扩散到其他模块。

---

## 总体评估

Phase 29 是中低风险的架构扩展 phase。Slice 2 是关键安全网，必须保证零回归。Slice 3 是首个验证点，允许快速退回。建议按严格顺序推进，Slice 2 完成后做一次全量测试确认。
