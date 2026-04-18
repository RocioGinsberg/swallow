---
author: claude
phase: 45
slice: eval-baseline-deep-ingestion
status: final
depends_on:
  - docs/plans/phase45/kickoff.md
  - docs/plans/phase45/risk_assessment.md
---

> **TL;DR** Phase 45 review: 0 BLOCK / 1 CONCERN / 1 NOTE。Merge ready。Eval 基础设施首次引入，降噪 precision/recall 基线 + Meta-Optimizer 3 scenario eval 通过。ChatGPT 对话树还原正确区分主路径/侧枝。320 passed + 2 eval passed。

# Phase 45 Review Comments

## Review Scope

- 对照 `docs/plans/phase45/kickoff.md` 的方案拆解
- Eval 基础设施正确性（pytest mark 隔离、fixture 路径、基线阈值）
- 对话树还原算法正确性
- Phase scope 守界检查

## Checklist

### S1: Eval 基础设施 + 质量基线

- [PASS] `tests/eval/` 目录结构正确：`conftest.py` + 2 个 eval 测试文件 + `__init__.py`
- [PASS] `pyproject.toml` 注册 `eval` marker + `addopts = "-m 'not eval'"` 确保默认 pytest 不执行 eval
- [PASS] 默认 `pytest`：320 passed, 2 deselected — eval 被正确排除
- [PASS] `pytest -m eval`：2 passed, 320 deselected — eval 独立执行正确
- [PASS] fixture 路径统一到 `tests/fixtures/eval_golden/`，`conftest.py` 的 `FIXTURES_ROOT` 指向正确
- [PASS] Ingestion eval：golden dataset 3 份（chatgpt/claude/open_webui），`test_eval_ingestion_quality.py` 计算 precision/recall，阈值 ≥0.80/≥0.70
- [PASS] Meta-Optimizer eval：3 个 scenario（high_failure_rate / cost_spike / healthy_baseline），`test_eval_meta_optimizer_proposals.py` 验证 expected proposals 覆盖 + forbidden proposals 不出现，覆盖率阈值 ≥2/3
- [PASS] eval 测试使用 `pytestmark = pytest.mark.eval` 标记，不混入默认测试

### S2: ChatGPT 对话树上下文还原

- [PASS] `_select_chatgpt_primary_path()` 实现正确：选择最深路径 + 最新 create_time 的 leaf 作为主路径终点，向上回溯到 root 构建 primary_path set
- [PASS] `_chatgpt_path_depth()` 包含循环检测（`visited` set），防御恶意/畸形 mapping
- [PASS] 侧枝 turn 的 `metadata["branch"] = "abandoned"` 标记正确
- [PASS] 主路径 turn 无 `branch` key — 向后兼容（无分支导出行为不变）
- [PASS] `metadata["parent_turn_id"]` 记录父节点引用，保留树结构追溯能力
- [PASS] filters.py 新增 `ABANDONMENT_KEYWORDS` + `_has_abandonment_signal()`：abandoned branch 中含否定语义的 turn 保留为 `rejected_alternative`，其余 drop
- [PASS] merge 逻辑正确：不跨 branch 边界合并（`merged[-1].metadata.get("branch") != turn.metadata.get("branch")`）
- [PASS] 测试 `test_parse_chatgpt_export_marks_non_primary_branch_as_abandoned`：2 个 assistant 分支（a1=abandoned, a2=primary），验证 metadata 标记
- [PASS] 测试 `test_filter_conversation_turns_drops_abandoned_branch_without_rejection_signal`：验证纯 abandoned 被过滤
- [PASS] 测试 `test_filter_conversation_turns_keeps_abandoned_branch_with_rejection_signal`：验证含否定语义的 abandoned 被保留

### S3: `swl ingest --summary` 结构化摘要

- [PASS] `build_ingestion_summary()` 正确分类：Decisions（决定/decision/outcome）/ Constraints（约束/constraint/non-goal/不做）/ Rejected Alternatives（rejected_alternative signal 或 abandon 关键词）
- [PASS] Statistics 节包含 total_turns / kept_fragments / dropped_chatter / abandoned_branches / precision_estimate
- [PASS] CLI `--summary` 参数注册，输出追加在标准 report 之后
- [PASS] 测试 `test_cli_ingest_summary_includes_decision_and_constraint_sections`：验证 summary 输出包含 Decisions / Constraints / Statistics
- [PASS] 测试 `test_build_ingestion_summary_classifies_fragments_into_decisions_constraints_rejected`：验证分类逻辑

### 架构一致性

- [PASS] eval 测试不修改任何现有代码路径 — 纯新增
- [PASS] 对话树还原只修改 ChatGPT 解析器，Claude/Open WebUI/Markdown 解析器不受影响
- [PASS] `--summary` 为 additive 功能，不影响默认 `swl ingest` 行为
- [PASS] eval 规则遵循 `.agents/shared/rules.md` §十

### Scope 守界

- [PASS] 不引入 LLM 辅助降噪、不引入 eval 框架/平台、不做自动化晋升流、不做 RAG eval

## CONCERN

### C1: `_select_chatgpt_primary_path` 对同深度多叶节点的选择确定性

**位置**: `parsers.py` — `_select_chatgpt_primary_path()`

当多个叶节点具有相同的路径深度时，选择逻辑依赖 `create_time` > `sequence` > `node_id` 三级排序。`node_id` 是 ChatGPT mapping 中的 UUID 字符串，其字典序不一定与用户意图对齐。

在极端情况下（两条等长分支、最后 regenerate 的 create_time 恰好相同），主路径选择可能不符合用户直觉。

**实际影响低**：ChatGPT 的 create_time 精度到秒级 Unix timestamp，两条分支 create_time 完全相同的概率极小。且即使选错主路径，侧枝的 abandoned turn 中含否定语义的仍会被保留为 rejected_alternative，不会完全丢失信息。

**消化时机**: 可在后续 eval 发现实际 precision 下降时再调整，当前不阻断。

## NOTE

### N1: 测试环境已就绪，自动测试已执行

- 默认 `pytest`：320 passed, 2 deselected, 5 subtests passed in 7.00s
- `pytest -m eval`：2 passed, 320 deselected in 0.22s
- 无回归。

## 结论

**Merge ready**。项目首次引入 Eval-Driven Development 基础设施，降噪和提案两条质量基线建立成功。ChatGPT 对话树还原算法实现清晰，循环检测 + 向后兼容处理到位。唯一 CONCERN (C1) 为极低概率的边界情况，不影响当前正确性。
