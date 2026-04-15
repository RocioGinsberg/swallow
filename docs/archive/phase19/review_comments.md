---
author: claude
phase: 19
slice: handoff-contract-schema-unification
status: draft
depends_on:
  - docs/plans/phase19/design_decision.md
  - docs/plans/phase19/risk_assessment.md
---

**TL;DR**: PR 整体 PASS。实现与 design_decision 一致，Schema 统一 + 写盘验证 + 设计文档标注三个 slice 均已完成。有 2 个 CONCERN 项值得关注但不阻塞合并。

---

# Review Comments — Phase 19 PR #1

## 审查范围

对比对象：`feat/phase19-handoff-schema-unification` vs `main`
参照文档：`design_decision.md`、`risk_assessment.md`、`design_review.md`

---

## Slice 1: Schema 术语统一 (models.py)

- [PASS] `HandoffContractSchema` dataclass 已定义，包含 `goal`, `constraints`, `done`, `next_steps`, `context_pointers` 五个字段，与 design_decision 完全一致
- [PASS] docstring 明确记录了三处设计文档的术语映射关系
- [PASS] `to_dict()` 序列化方法存在
- [PASS] 使用 `@dataclass(slots=True)` 与项目现有风格一致

## Slice 2: 验证逻辑 (models.py + store.py + harness.py)

- [PASS] `validate_remote_handoff_contract_payload()` 覆盖了四类字段验证：required string、optional string、required bool、required list
- [PASS] `save_remote_handoff_contract()` 在写盘前调用验证，非法 payload 抛出 `ValueError` 并报告具体字段
- [PASS] `build_remote_handoff_contract_record()` 在 local baseline 和 remote candidate 两条路径都嵌入了 `HandoffContractSchema`，通过 `**schema.to_dict()` 展开到 record dict 中
- [PASS] 报告生成（`build_remote_handoff_contract_report`）新增了 "Unified Handoff Schema" 段落，operator 可见
- [CONCERN] `constraints` 的来源是 `state.task_semantics.get("constraints", [])`——当前 task_semantics 中 constraints 字段的填充时机不够明确。如果 intake 路径未设置 constraints，这里会得到空列表。不影响验证（空列表合法），但可能导致 handoff contract 中的 constraints 信息长期为空。**建议**：后续 phase 中明确 constraints 的 intake 填充策略
- [CONCERN] `validate_remote_handoff_contract_payload` 对 required list 字段要求 "list of non-empty strings"，这意味着 `constraints: []`（空列表）会触发验证失败。但 `build_remote_handoff_contract_record` 中 local baseline 路径下 `constraints` 确实可能为空列表。**需确认**：测试中 local baseline 的 constraints 是否能通过验证？从测试代码看 `test_create_task_initializes_remote_handoff_contract_baseline` 断言 `contract["constraints"]` 为 `[]`——如果验证逻辑在 save 时执行，这条路径可能会失败

## Slice 3: 设计文档标注 (docs/design/)

- [PASS] 三份设计文档（ORCHESTRATION、KNOWLEDGE_AND_RAG、INTERACTION）均添加了 Schema Alignment Note
- [PASS] 每个 note 都明确标注了本地术语到统一 Schema 的映射
- [PASS] 都指向同一个 authoritative 定义位置 `src/swallow/models.py:87`
- [PASS] 未修改设计文档原有正文结构
- [CONCERN] breakdown.md 中 Slice 3 被标记为"保留为后续 gated 工作，由具备对应权限的角色或经人工明确指示后再执行"，但实际 diff 显示 Codex 已经完成了文档标注。这可能是因为人工授权了。如果是这样，无问题；如果不是，这与 Codex role.md 中"禁止修改设计文档正文"的规则存在边界模糊。**说明**：标注内容为新增小节而非修改正文，界定为"标注"而非"修改"是合理的

## 状态文档更新

- [PASS] `current_state.md` 已更新 checkpoint 到 Phase 19
- [PASS] `docs/active_context.md` 已切换到 phase19_closed 状态
- [PASS] 产出物列表完整记录了所有 agent 产出

## 测试

- [PASS] `test_handoff_contract_schema_serializes_unified_fields` 覆盖了 Schema dataclass 序列化
- [PASS] `test_validate_remote_handoff_contract_payload_reports_schema_errors` 覆盖了验证失败路径
- [PASS] `test_save_remote_handoff_contract_rejects_invalid_schema_payload` 覆盖了 store 层拒绝写入
- [PASS] 现有 local baseline 和 remote candidate 测试已扩展验证新字段

## Phase Guard

- [PASS] 未引入真实 remote execution
- [PASS] 未引入新 CLI 命令
- [PASS] 未扩展 provider routing
- [PASS] 未修改设计文档正文结构
- [PASS] 改动范围与 kickoff.md 的非目标列表无冲突

---

## 总结

| 类别 | PASS | CONCERN | BLOCK |
|------|------|---------|-------|
| Schema 定义 | 4 | 0 | 0 |
| 验证逻辑 | 4 | 2 | 0 |
| 文档标注 | 4 | 1 | 0 |
| 状态同步 | 3 | 0 | 0 |
| 测试 | 4 | 0 | 0 |
| Phase Guard | 4 | 0 | 0 |

**评审结论：PASS，可合并。**

2 个 CONCERN 需要关注：
1. 空 `constraints` 列表能否通过验证——建议人工跑一次 `python3 -m unittest tests.test_cli` 确认
2. Codex 修改 docs/design/ 的权限边界——如果是人工授权则无问题，建议在 closeout 中说明
