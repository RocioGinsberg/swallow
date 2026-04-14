---
author: claude
phase: 29
slice: Provider Dialect Baseline
status: draft
depends_on: [docs/plans/phase29/design_decision.md]
---

## TL;DR
全部 PASS，无 BLOCK。一个 CONCERN 关于 `StructuredMarkdownDialect` 与 `build_executor_prompt()` 之间的信息重复构建。实现质量高，测试覆盖充分。

---

# Review Comments

## 检查范围
- 对比: `git diff main...feat/phase29-provider-dialect`
- 对比 design_decision.md 一致性
- 测试覆盖完整性
- 涉及文件: models.py, router.py, executor.py, orchestrator.py, harness.py, cli.py, test_cli.py

---

## Slice 1: DialectAdapter 接口与 Registry

- [PASS] `DialectSpec` dataclass 已在 models.py 中定义，含 name/description/supported_model_hints
- [PASS] `DialectAdapter` Protocol 已在 executor.py 中定义，签名 `format_prompt(raw_prompt, state, retrieval_items) -> str`
- [PASS] `BUILTIN_DIALECTS` registry 包含 plain_text 和 structured_markdown
- [PASS] `resolve_dialect_name()` + `resolve_dialect()` 实现正确：dialect_hint 优先 → model_hint 匹配 → fallback plain_text
- [PASS] `RouteSpec.dialect_hint` 字段已新增，默认空字符串
- [PASS] `ExecutorResult.dialect` 字段已新增，默认 "plain_text"
- [PASS] `TaskState.route_dialect` 字段已新增，默认 "plain_text"

---

## Slice 2: plain_text 默认 Dialect 提取

- [PASS] `PlainTextDialect.format_prompt()` 是严格 identity transform（`return raw_prompt`）
- [PASS] `build_formatted_executor_prompt()` 新增为入口，调用 raw prompt → resolve dialect → adapter.format_prompt
- [PASS] `run_executor_inline()` 和 `run_detached_executor()` 都已切换到 `build_formatted_executor_prompt()`
- [PASS] 重构为 if/elif/else 链 + 统一设置 `result.dialect`，比原来的 early return 更清晰
- [PASS] 现有 180 测试全部通过，零回归

---

## Slice 3: structured_markdown Dialect 实现

- [PASS] `StructuredMarkdownDialect` 独立构建 Markdown 输出（不解析 raw_prompt 字符串）
- [PASS] 输出包含所有必要 sections：Task, Route, Task Semantics, Knowledge, Reused Knowledge, Prior Context, Retrieved Context, Instructions
- [PASS] `local-codex` route 已设置 `dialect_hint="structured_markdown"`（router.py）
- [PASS] `build_detached_route()` 正确透传 `dialect_hint`
- [PASS] 测试: `test_build_formatted_executor_prompt_uses_structured_markdown_for_codex_route` 验证 markdown 结构
- [CONCERN] `StructuredMarkdownDialect.format_prompt()` 独立重建了与 `build_executor_prompt()` 几乎相同的信息收集逻辑（state fields、knowledge summaries、retrieval items 格式化）。这意味着两个地方维护相同的数据收集代码。目前可接受（两个 dialect 各自完整），但如果未来增加更多 dialect，应考虑提取公共的"数据收集"层。

---

## Slice 4: CLI 可观测性

- [PASS] `task inspect` 输出新增 `dialect` 字段
- [PASS] `task review` 输出新增 `dialect` 字段
- [PASS] executor prompt artifact 头部新增 `dialect: <name>` 元数据行
- [PASS] executor event payload 含 `dialect` 字段（run_started + terminal event）
- [PASS] route record + route report + summary 均包含 dialect
- [PASS] `orchestrator.py` 在 create_task / run_task / acknowledge_task 三处均同步 `route_dialect`
- [PASS] 测试: `test_provider_dialect_is_visible_in_prompt_artifact_events_inspect_and_review` 完整验证端到端可观测性

---

## 跨 Slice 检查

- [PASS] 与 design_decision 的一致性: 四个 slice 均按设计实现，无越界
- [PASS] 非目标未被触及: 无 provider API 直连、无 Claude XML、无模板系统、无 dialect 自动协商
- [PASS] 测试全量通过: 180 passed, 5 subtests passed
- [PASS] `build_executor_prompt()` 内容逻辑未改动，仅新增 `build_formatted_executor_prompt()` 包装层
- [PASS] 所有 detached executor 错误路径也正确设置了 dialect

---

## 结论

**Merge ready.** 无 BLOCK，实现与设计对齐，测试覆盖充分。
