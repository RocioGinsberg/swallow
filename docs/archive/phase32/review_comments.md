---
author: claude
phase: 32
slice: knowledge-dual-layer
status: final
depends_on: [docs/plans/phase32/kickoff.md]
---

# Phase 32 Review Comments

> 审查范围：`main..feat/phase32-knowledge-dual-layer` (5 commits, +1583/-78 lines, 22 files)
> 测试结果：225 passed, 5 subtests passed in 6.32s
> 审查结论：**Merge ready — 0 BLOCK, 1 NOTE**

---

## Slice 总览与 kickoff 对照

| Slice | kickoff 完成条件 | 实际交付 | 判定 |
|-------|----------------|---------|------|
| S1: Evidence/Wiki 双层存储 | 目录结构 + 读写 API + merged view 兼容 | `knowledge_store.py` 203 行，evidence/wiki 物理分离，legacy merged view 保留，CLI 全部切到 merged view | PASS |
| S2: 权限校验 + Librarian 角色 | `apply_knowledge_decision` 增加 `caller_authority`，非 Librarian 拒绝 canonical | `caller_authority` 参数就位，`PermissionError` 阻断 + `knowledge.promotion.unauthorized` 事件记录 | PASS |
| S3: LibrarianExecutor + 集成 | Executor 实现 + Planner 识别 + ReviewGate 校验 Change Log | `LibrarianExecutor` 366 行，Planner 自动生成 librarian TaskCard，ReviewGate 做 JSON schema 校验 | PASS |

---

## 架构审查

### 双层存储设计（S1）

**优点**：

- 渐进式策略执行到位：`knowledge_store.py` 的 `load_task_knowledge_view()` 合并 legacy + evidence + wiki 三源，现有代码无感知切换。`_merge_task_knowledge_views()` 在 key 冲突时 wiki 优先于 evidence，语义正确。
- `persist_task_knowledge_view()` 同时写入双层物理存储，保持一致性。
- `persist_wiki_entry_from_record()` 在写入 wiki 后删除对应 evidence 文件，避免重复。
- 路径体系清晰：`paths.py` 新增的 `knowledge_evidence_root` / `knowledge_wiki_root` 在 task 级别隔离（`<base>/.swl/knowledge/evidence/<task_id>/`），合理。

### 权限校验（S2）

**优点**：

- `apply_knowledge_decision()` 新增 `caller_authority` 参数，默认值为空字符串，向后兼容现有调用。canonical promotion 时强制校验 `caller_authority == "canonical-promotion"`，否则抛 `PermissionError`。
- `orchestrator.py::decide_task_knowledge()` 捕获 `PermissionError` 后记录 `knowledge.promotion.unauthorized` 事件，不中断任务流程。
- CLI 的 `task knowledge-promote` 以 `LIBRARIAN_MEMORY_AUTHORITY` 执行，人类操作等同 Librarian 权限——与 kickoff 设计一致。

### LibrarianExecutor（S3）

**优点**：

- 严格遵守 v0 规则驱动约束：去重（`seen_canonical_keys`）、格式标准化（`_normalize_text` 合并空白）、来源验证（`_artifact_exists` 检查 artifact_ref 文件是否存在）。
- 完整的 Change Log 产出：每条 entry 记录 before_text / after_text / action / reason / canonical_key，审计链完整。
- skip 原因明确分类：`missing_object_id` / `artifact_ref_missing` / `duplicate_canonical_key_in_batch`，便于排查。
- 与 canonical_registry 和 wiki store 的双写一致：`append_canonical_record()` + `persist_wiki_entry_from_record()` 同步执行。

### Planner 集成（S3）

- `_should_plan_librarian_card()` 检查三个前置条件（有 promotion_ready 条目、local 执行、非 blocked authority），逻辑正确。
- librarian TaskCard 的 `output_schema` 声明了 `required` 和 `const` 字段，ReviewGate 可以用此做 JSON schema 校验。

### ReviewGate 扩展（S3）

- `_validate_output_schema()` 新增了 `required` 字段存在性检查和 `const` 字段值匹配检查，不仅服务 librarian，也为未来其他有结构化输出的 executor 建立了通用基线。

---

## 测试覆盖审查

| 测试文件 | 覆盖范围 | 判定 |
|---------|---------|------|
| `test_knowledge_store.py` (109 行) | 双层存储读写、normalize、split、merge、legacy overlay | 充分 |
| `test_cli.py` (+76 行) | stage-promote 写 Wiki Store、authority 成功/阻断 | 充分 |
| `test_taxonomy.py` (+15 行) | Librarian taxonomy helper | 充分 |
| `test_planner.py` (+45 行) | librarian TaskCard 规划触发 + 非触发条件 | 充分 |
| `test_review_gate.py` (+84 行) | output_schema required/const 校验 pass/fail | 充分 |
| `test_executor_protocol.py` (+6 行) | librarian executor 解析 | 充分 |
| `test_librarian_executor.py` (118 行) | 端到端集成：run_task → librarian → canonical promotion → change log → events | **关键测试，充分** |

---

## NOTE（非阻塞）

### N1: LibrarianExecutor 直接操作 state + 多层持久化

`LibrarianExecutor.execute()` 直接修改 `state.knowledge_objects`、调用 `save_state()`、`save_knowledge_objects()`、`append_canonical_record()` 等——它同时是 executor 和 state mutator。

这在 v0 阶段可以接受（Librarian 本身就是特权角色），但与 Phase 31 建立的"executor 只产出 result，state mutation 由 orchestrator 负责"的原则有偏差。后续如果引入并发或 retry，这个 side effect 需要收回 orchestrator。

**建议**：在 Phase 33 或 Phase 34 的 kickoff 中记录为已知技术债。当前不阻塞 merge。

---

## 回归验证

```
225 passed, 5 subtests passed in 6.32s
```

全量通过，无 skip、无 xfail。

---

## 结论

**Merge ready — 0 BLOCK, 0 CONCERN, 1 NOTE**

Phase 32 的 3 个 Slice 全部满足 kickoff 完成条件。双层存储的渐进式策略保持了回归安全，权限校验防线到位，LibrarianExecutor 的规则驱动实现严格控制在 v0 范围内。N1 作为已知技术债记录，不影响当前 merge。
