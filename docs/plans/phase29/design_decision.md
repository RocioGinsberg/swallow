---
author: claude
phase: 29
slice: Provider Dialect Baseline
status: draft
depends_on: [docs/plans/phase29/context_brief.md, docs/roadmap.md]
---

## TL;DR
Phase 29 在 `build_executor_prompt()` 和 executor dispatch 之间插入 dialect adapter 层。最小实现：(1) 定义 `DialectAdapter` 接口 + registry，(2) 将现有 prompt 逻辑重构为 `plain_text` 默认 dialect，(3) 实现一个 `structured_markdown` dialect 作为首个非平文本变体。不新增 provider API 调用，不改动路由选择逻辑。

---

## 方案总述

源码分析发现当前执行路径为：

```
select_route() → build_executor_prompt() → run_*_executor() → ExecutorResult
```

`build_executor_prompt()` (executor.py:278-407) 生成纯文本 key-value 格式的 prompt，所有 executor 都接收相同格式。`RouteSpec.model_hint` 已存在但从未被用于格式选择。

Phase 29 的核心工作是在 prompt 生成和 executor dispatch 之间插入一层 dialect adapter，使得不同 provider 可以接收最适合自身的 prompt 格式。方案遵循已有的 adapter 模式（参考 `retrieval_adapters.py`），不引入新的外部依赖。

---

## Slice 拆解

### Slice 1: DialectAdapter 接口与 Registry

**目标**：定义 dialect adapter 的数据结构和注册机制。

**具体内容**：
- 在 `models.py` 中新增 `DialectSpec` dataclass：
  - `name: str` — dialect 标识（如 "plain_text", "structured_markdown"）
  - `description: str` — 用途说明
  - `supported_model_hints: list[str]` — 匹配的 model_hint 列表
- 在 `executor.py` 中新增：
  - `DialectAdapter` protocol/接口：`format_prompt(raw_prompt: str, state: TaskState, retrieval_items: list[RetrievalItem]) -> str`
  - `BUILTIN_DIALECTS: dict[str, DialectAdapter]` — dialect 注册表
  - `resolve_dialect(model_hint: str) -> DialectAdapter` — 根据 model_hint 查找 dialect，fallback 到 plain_text
- `RouteSpec` 新增可选字段 `dialect_hint: str = ""`（为空时使用 model_hint 自动匹配）

**影响范围**：`models.py`（新增 DialectSpec + RouteSpec 字段）、`executor.py`（新增接口 + registry）

**风险评级**：
- 影响范围：2（跨模块：models + executor）
- 可逆性：1（轻松回滚）
- 依赖复杂度：1（无外部依赖）
- **总分：4（低风险）**

**验收条件**：
- `DialectSpec` 和 `DialectAdapter` 已定义
- `resolve_dialect()` 对已知 model_hint 返回对应 adapter，未知返回 plain_text
- `RouteSpec.dialect_hint` 字段存在且可选

---

### Slice 2: plain_text 默认 Dialect 提取

**目标**：将现有 `build_executor_prompt()` 的逻辑封装为 `plain_text` dialect adapter，保持行为完全不变。

**具体内容**：
- 新增 `PlainTextDialect` 实现 `DialectAdapter`：
  - `format_prompt()` 直接返回原始 prompt（identity transform）
- 注册为 `BUILTIN_DIALECTS["plain_text"]`
- `supported_model_hints`: `["codex", "mock", "mock-remote"]`（所有现有 model_hint）
- 修改 `run_executor_inline()` 流程：
  1. `build_executor_prompt()` 生成 raw prompt
  2. `resolve_dialect(state.route_model_hint)` 获取 adapter
  3. `adapter.format_prompt(raw_prompt, state, retrieval_items)` 转换
  4. 传入 executor
- 验证所有现有测试不变（因为 plain_text 是 identity transform）

**影响范围**：`executor.py`（重构 dispatch 流程）

**风险评级**：
- 影响范围：1（单文件）
- 可逆性：1（轻松回滚）
- 依赖复杂度：2（依赖 Slice 1 的接口）
- **总分：4（低风险）**

**验收条件**：
- 所有现有测试 100% 通过（行为无变化）
- `PlainTextDialect.format_prompt()` 被实际调用（可通过 executor prompt artifact 中的 dialect 标记验证）
- executor prompt artifact 新增 `dialect: plain_text` 元数据行

---

### Slice 3: structured_markdown Dialect 实现

**目标**：实现首个非 plain_text 的 dialect，验证 adapter 层可用。

**具体内容**：
- 新增 `StructuredMarkdownDialect` 实现 `DialectAdapter`：
  - 将 raw prompt 中的 key-value 块转换为 Markdown heading + list 结构
  - Task metadata → `## Task` section
  - Route info → `## Route` section
  - Knowledge objects → `## Knowledge` section
  - Retrieval results → `## Retrieved Context` section
  - Instructions → `## Instructions` section
- 注册为 `BUILTIN_DIALECTS["structured_markdown"]`
- `supported_model_hints`: 暂不绑定任何现有 model_hint（需要手动通过 `dialect_hint` 指定或未来新 route 使用）
- 在 `BUILTIN_ROUTES` 中为 `local-codex` route 新增 `dialect_hint: "structured_markdown"`（因为 codex CLI 本身支持 markdown）

**影响范围**：`executor.py`（新增 adapter 实现）、`router.py`（local-codex route 配置更新）

**风险评级**：
- 影响范围：2（executor + router 配置）
- 可逆性：1（轻松回滚）
- 依赖复杂度：2（依赖 Slice 1-2 的 adapter 层）
- **总分：5（中低风险）**

**验收条件**：
- `StructuredMarkdownDialect.format_prompt()` 输出合法 Markdown
- 通过 `dialect_hint="structured_markdown"` 的 route 使用该 dialect
- 新增测试验证 markdown 输出结构（含必要 sections）
- 现有 mock/note-only/summary route 行为不变（仍使用 plain_text）

---

### Slice 4: CLI 可观测性 (Secondary Track 5)

**目标**：在 operator 可视入口中暴露 dialect 信息。

**具体内容**：
- `task inspect` 输出新增 `dialect` 字段（显示当前 route 使用的 dialect 名）
- `task review` 输出中包含 dialect 信息
- executor prompt artifact 文件顶部新增 `dialect: <name>` 元数据行
- executor event payload 新增 `dialect` 字段

**影响范围**：`cli.py`（inspect/review 输出）、`harness.py`（event payload）

**风险评级**：
- 影响范围：2（cli + harness）
- 可逆性：1（轻松回滚）
- 依赖复杂度：2（依赖 Slice 1-3）
- **总分：5（中低风险）**

**验收条件**：
- `task inspect` 显示 dialect 名
- executor event 包含 `dialect` 字段
- prompt artifact 头部标注 dialect

---

## 依赖说明

```
Slice 1 (接口与 registry) ← 无依赖
        ↓
Slice 2 (plain_text 提取) ← 依赖 Slice 1
        ↓
Slice 3 (structured_markdown) ← 依赖 Slice 1-2
        ↓
Slice 4 (CLI 可观测性) ← 依赖 Slice 1-3
```

严格顺序依赖。Slice 2 是关键安全网——确保重构不破坏现有行为。

---

## 明确的非目标

- **不做 provider API 直连**：本轮不引入 Anthropic SDK 或 OpenAI SDK 调用，所有执行仍通过 subprocess
- **不做 Claude XML dialect**：structured_markdown 是首个验证，Claude-specific XML 格式留给后续 phase
- **不做 prompt 模板系统**：dialect adapter 是格式转换层，不是模板引擎
- **不改动路由选择逻辑**：route selection 机制不变，只新增 dialect_hint 字段
- **不做 dialect 自动协商**：model_hint → dialect 映射是静态配置，不是运行时协商
- **不改动 `build_executor_prompt()` 的内容逻辑**：信息收集不变，只是输出格式变化

---

## Branch Advice

- 当前分支: `main`
- 建议操作: Human 审批后新建分支
- 建议分支名: `feat/phase29-provider-dialect`
- 建议 PR 范围: Slice 1-4 统一入一个 PR（4 个 slice 是严格顺序依赖，拆 PR 无意义）

---

## Phase Guard

- [x] 方案不越出 Provider Dialect Baseline 的 goals
- [x] 方案不触及非目标（无 API 直连、无 Claude XML、无模板系统）
- [x] Slice 数量 = 4（≤5，合理）
- [x] Primary Track: Execution Topology，Secondary Track: Workbench/UX — 符合 roadmap 队列定义
