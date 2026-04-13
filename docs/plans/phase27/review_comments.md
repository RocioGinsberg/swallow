---
author: claude
phase: 27
slice: knowledge-driven-task-grounding-baseline
status: draft
depends_on:
  - docs/plans/phase27/design_decision.md
  - docs/plans/phase27/risk_assessment.md
---

**TL;DR**: 三个 slice 实现与设计一致，但有 1 个 BLOCK：`test_cli_artifact_commands_print_phase1_outputs` 失败——`swl task grounding` 命令的 artifact 映射已从 `source_grounding.md` 改为 `grounding_evidence_report.md`，但该测试的断言未同步更新。修复后可合并。

# Review Comments: Phase 27

## 测试结果

```
1 failed, 7 passed in 0.81s (stopped after first failure)
```

失败测试：`test_cli_artifact_commands_print_phase1_outputs` (line 8024)

---

## [BLOCK] 测试断言与 artifact 映射不一致

`cli.py` 中 `"grounding"` 命令的 artifact 映射已从 `source_grounding.md` 改为 `grounding_evidence_report.md`：
```python
"grounding": "grounding_evidence_report.md",  # was "source_grounding.md"
```

但 `test_cli_artifact_commands_print_phase1_outputs` 行 8024 仍断言：
```python
self.assertIn("Source Grounding", grounding_stdout.getvalue())
```

应改为断言 `"Grounding Evidence"` 或与 `grounding_evidence_report.md` 的实际输出格式对齐。

**修复方式**：更新测试断言，使其匹配新的 grounding_evidence_report.md 内容。

---

## Slice 1: Grounding Evidence Artifact 生成

### [PASS] grounding.py 模块
- `GroundingEntry` dataclass 字段完整：canonical_id、canonical_key、text、citation、source_task_id、evidence_status、score
- `extract_grounding_entries()` 正确过滤 `storage_scope == "canonical_registry"` 的 items
- `build_grounding_evidence()` 生成标准 payload：generated_at、entry_count、citations、entries
- `build_grounding_evidence_report()` 生成可读 markdown

### [PASS] harness 集成
- `write_task_artifacts()` 新增 `grounding_evidence_override` 参数，支持复用锁定的 evidence
- 正确写入 `grounding_evidence.json` 和 `grounding_evidence_report.md`
- artifact_paths 登记 `grounding_evidence_json` 和 `grounding_evidence_report`
- task_memory 中包含 grounding artifact 路径

### [PASS] 测试覆盖（test_grounding.py）
- canonical items 提取正确
- 非 canonical items 被过滤
- 空 retrieval → 空 entries
- harness 端到端写入验证

---

## Slice 2: Context Refs + Resume 锁定

### [PASS] TaskState 字段
- `grounding_refs: list[str]` 和 `grounding_locked: bool` 新增，默认值正确

### [PASS] _resolve_grounding_state() 实现
- 首次执行：从 retrieval items 提取 → 锁定
- resume（grounding_locked=True）：从 artifact 文件加载 → 复用
- 错误处理：artifact 文件不存在或解析失败 → 重新提取

### [PASS] reset_grounding 机制
- `run_task()` 接受 `reset_grounding=True` 参数
- CLI 的 `retry` 和 `rerun` 命令传递 `reset_grounding=True`，`resume` 不传递（保持锁定）
- 设计合理：retry/rerun = 从头开始 → 重新 grounding；resume = 继续 → 保持 grounding

### [PASS] 事件记录
- `grounding.locked` event 正确记录 refs、count、locked 状态、是否复用

### [PASS] 端到端测试
- 首次 run → grounding_refs 填充 + locked=True + reused=False
- resume → grounding_refs 不变 + reused=True
- rerun (reset_grounding=True) → grounding_refs 更新 + reused=False

---

## Slice 3: Inspect Grounding 可视化

### [PASS] format_grounding_summary()
- grounding_locked + refs → `yes / count / ref_list`
- 无 grounding → `- / 0 / -`
- refs 截断前 5 个

### [PASS] inspect 命令
- Route And Topology 区域新增 grounding_locked、grounding_refs_count、grounding_refs

### [PASS] review 命令
- Handoff 区域同步新增 grounding 展示

### [PASS] grounding 报告命令
- `swl task grounding <id>` 读取 `grounding_evidence_report.md`

---

## 与 design_decision 的一致性检查

| 设计要求 | 实现状态 |
|----------|---------|
| GroundingEntry dataclass | PASS |
| extract_grounding_entries 过滤 canonical | PASS |
| grounding_evidence.json artifact | PASS |
| grounding_evidence_report.md artifact | PASS |
| grounding_refs TaskState 字段 | PASS |
| grounding_locked 锁定机制 | PASS |
| resume 复用锁定 artifact | PASS |
| retry/rerun 重置 grounding | PASS |
| grounding.locked event | PASS |
| inspect grounding 展示 | PASS |
| review grounding 展示 | PASS |
| swl task grounding 报告命令 | PASS |
| 不直接注入 prompt | PASS — 走 artifact 路径 |
| 不引入向量检索 | PASS |

## Phase-Guard 检查

- [x] 未越出 Phase 27 scope
- [x] 未触及 non-goals
- [x] grounding 走 artifact 路径，遵守 orchestrator/harness 边界

## 结论

**BLOCK — 需修复 1 个测试断言后可合并。** `test_cli_artifact_commands_print_phase1_outputs` 的 `"Source Grounding"` 断言需改为 `"Grounding Evidence"` 以匹配新的 artifact 映射。其余三个 slice 全部符合设计。
