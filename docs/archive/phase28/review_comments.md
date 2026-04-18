---
author: claude
phase: 28
slice: Knowledge Promotion & Refinement Baseline
status: draft
depends_on: [docs/plans/phase28/design_decision.md]
---

## TL;DR
全部 PASS，无 BLOCK。一个 CONCERN 关于 `build_stage_promote_preflight_notices` 返回类型变更的向后兼容。实现质量高，测试覆盖充分。

---

# Review Comments

## 检查范围
- 对比: `git diff main...feat/phase28-knowledge-promotion`
- 对比 design_decision.md 一致性
- 测试覆盖完整性

---

## Slice 1: `task staged` 聚合浏览命令

- [PASS] `swl task staged` 命令已实现，含 `--status` 和 `--task` 过滤
- [PASS] 默认只显示 pending 状态，符合 design_decision
- [PASS] `summarize_text_preview()` 函数干净，处理空文本和超长文本
- [PASS] `build_task_staged_report()` 输出格式清晰，含 count/filter 元数据
- [PASS] 测试覆盖: `test_cli_task_staged_defaults_to_pending_candidates` + `test_cli_task_staged_filters_by_status_and_task`
- [PASS] help 文本已注册到 help 输出断言列表

---

## Slice 2: 晋升时文本精炼

- [PASS] `--text` 参数已添加到 `knowledge stage-promote`
- [PASS] `build_stage_canonical_record()` 接受 `refined_text` keyword-only 参数，默认空字符串时行为不变
- [PASS] canonical record 使用精炼文本，原始 staged candidate text 不被修改
- [PASS] `decision_note` 自动追加 `[refined]` 标记，审计线索完整
- [PASS] 测试覆盖: `test_cli_stage_promote_accepts_refined_text_without_mutating_staged_candidate` 验证了双侧（staged 不变 + canonical 精炼）

---

## Slice 3: Preflight 冲突提示增强

- [PASS] `build_stage_promote_preflight_notices()` 返回结构化 dict（含 `notice_type`, `canonical_id`, `text_preview`）
- [PASS] `format_stage_promote_preflight_notice()` 输出 `[SUPERSEDE]` / `[IDEMPOTENT]` 标签
- [PASS] `--force` flag 实现正确：supersede 时不带 force 抛 ValueError
- [PASS] idempotent 重复晋升不阻塞，仅打印提示
- [PASS] 测试覆盖: `test_cli_stage_promote_requires_force_for_active_key_match` + `test_cli_stage_promote_with_force_prints_supersede_notice_and_promotes`
- [PASS] 已有的 supersede 测试已适配 `--force`（两处旧测试更新）
- [CONCERN] `build_stage_promote_preflight_notices()` 返回类型从 `list[str]` 变为 `list[dict[str, str]]`，这是内部函数的签名变更。目前无外部调用者，影响为零，但值得记录。

---

## 跨 Slice 检查

- [PASS] 与 design_decision 的一致性: 三个 slice 均按设计实现，无越界
- [PASS] 非目标未被触及: 无 AI 自动决策、无语义去重、无批量晋升
- [PASS] 测试全量通过: 176 passed, 5 subtests passed
- [PASS] 未引入新数据模型字段，StagedCandidate 和 CanonicalRecord 结构不变

---

## 额外观察: 测试修复

diff 中包含若干非 Phase 28 功能的测试修复：
- grounding event 查找改为 `next(event for event in events if ...)` 替代硬编码 index（更健壮）
- `grounding_evidence_override` 参数添加到 mock 签名（适配上游变更）
- RetrievalItem metadata 增加 `storage_scope`、`canonical_id`、`canonical_key` 字段
- 事件索引断言修正（`events[17]` → `events[18]`）

这些是合理的回归修复，不引入新风险。

---

## 结论

**Merge ready.** 无 BLOCK，实现与设计对齐，测试覆盖充分。
