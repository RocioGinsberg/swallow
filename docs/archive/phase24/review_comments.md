---
author: claude
phase: 24
slice: staged-knowledge-pipeline-baseline
status: draft
depends_on:
  - docs/plans/phase24/design_decision_claude.md
  - docs/plans/phase24/risk_assessment.md
---

**TL;DR**: 三个 slice 全部实现且通过测试（167 passed）。整体 PASS，可合并。一个 CONCERN 关于 stage-promote 时缺少对 canonical registry 去重检查，不阻塞本轮。

# Review Comments: Phase 24

## 测试结果

```
167 passed, 5 subtests passed in 4.56s
```

全部通过，无 failure。较上一轮净增 13 个测试。

---

## Slice 1: Staged Knowledge 数据模型与存储

### [PASS] StagedCandidate dataclass
- 字段完整：candidate_id、text、source_task_id、taxonomy 审计字段、决策字段
- `__post_init__` 自动 strip + ID 生成 + validate，防御性好
- `from_dict()` / `to_dict()` 对称，序列化可靠
- validate() 检查 prefix、非空 text/source_task_id、status 合法性

### [PASS] 存储层
- `.swl/staged_knowledge/registry.jsonl` — JSONL append-only 写入
- `submit_staged_candidate()` 创建目录 + append 写入
- `update_staged_candidate()` 通过 read-modify-write 全文件更新（当前阶段候选数量少，可接受）
- `load_staged_candidates()` 处理空文件和不存在的文件

### [PASS] paths.py
- `staged_knowledge_root()` 和 `staged_knowledge_registry_path()` 与 canonical 路径结构对称

### [PASS] 测试覆盖
- submit → 文件写入、ID 生成
- load → 多条记录完整返回
- update → promote 持久化、decided_at/decided_by 正确
- load empty → 空列表

---

## Slice 2: CLI stage-* 命令

### [PASS] 命令注册
- `swl knowledge` 作为新顶级命令，与 `swl task` 平级 — 正确，因为 staged knowledge 是全局的
- 四个子命令：stage-list、stage-inspect、stage-promote、stage-reject
- help 文档完整

### [PASS] stage-list
- 默认只显示 pending 候选，`--all` 显示全部（含已决策）
- 空列表时输出 "no pending candidates"
- 紧凑格式：candidate_id、source、taxonomy、text 摘要（≤72 字符截断）

### [PASS] stage-inspect
- 完整展示单个候选的所有字段，包含全文 text

### [PASS] stage-promote
- 校验 status == "pending"，已决策的拒绝 re-entry
- `build_stage_canonical_record()` 正确构造 canonical record：
  - canonical_key 基于 source_task_id + source_object_id 或 candidate_id
  - 调用 `append_canonical_record()` 写入 canonical registry
  - 同步更新 canonical_registry_index 和 reuse_policy

### [CONCERN] stage-promote 缺少 canonical 去重检查
- 当前 promote 直接 append canonical record，如果同一 candidate 被（通过某种方式）多次 promote，会产生重复 canonical 记录
- 虽然前置的 `status != "pending"` 检查防止了正常路径的重复，但如果 registry.jsonl 被手动编辑或出现并发写入，理论上可能重复
- **不阻塞本轮**：当前是 baseline，单操作员使用场景下不会出现此问题。后续可在 canonical 层加 dedupe。

### [PASS] stage-reject
- 更新 status 为 "rejected"，记录 note
- 已决策的拒绝 re-entry

### [PASS] 测试覆盖
- stage-list 空列表、stage-inspect 完整内容、stage-promote 写 canonical、stage-reject 更新状态
- re-entry 阻塞（promote 后再 promote/reject → ValueError）
- help 文档存在性验证

---

## Slice 3: Taxonomy-Aware 知识写入路由

### [PASS] _route_knowledge_to_staged() 实现
- 条件判断正确：只对 `canonical-write-forbidden` 和 `staged-knowledge` 触发
- 只处理 `canonicalization_intent == "promote"` 且 `stage == "verified"` 的对象
- 从 knowledge_objects.json 或 state.knowledge_objects 两种来源加载（兼容不同写入时机）
- 正确记录 event: `task.knowledge_staged`，payload 包含 candidate_ids 和 taxonomy 信息

### [PASS] orchestrator 集成
- 在 `run_task()` 的 execution 完成后、save_state 之前调用
- `staged_candidate_count` 写入 task.completed event payload，可审计
- 不改变已有的 knowledge processing 流程

### [PASS] 向下兼容
- 默认路由 taxonomy = `task-state`，不触发 staged 路由
- 端到端测试验证：task-state 路由的任务不产生 staged 记录、不产生 knowledge_staged event

### [PASS] 测试覆盖
- canonical-write-forbidden route + promote-intent knowledge → staged registry 有记录 + knowledge_staged event
- task-state route + promote-intent knowledge → 无 staged 记录 + 无 knowledge_staged event
- 测试使用 patch select_route 注入 restricted taxonomy route，验证链路隔离

---

## 与 design_decision 的一致性检查

| 设计要求 | 实现状态 |
|----------|---------|
| StagedCandidate dataclass | PASS |
| .swl/staged_knowledge/registry.jsonl | PASS |
| CLI swl knowledge stage-list | PASS |
| CLI swl knowledge stage-inspect | PASS |
| CLI swl knowledge stage-promote → canonical | PASS |
| CLI swl knowledge stage-reject | PASS |
| orchestrator taxonomy-aware 路由 | PASS |
| canonical-write-forbidden 自动 staged | PASS |
| task-state 保持现有行为 | PASS |
| event: task.knowledge_staged | PASS |
| 不做自动晋升 | PASS — 纯手动 CLI |
| 不做 retrieval integration | PASS — staged 不进入检索 |

## Phase-Guard 检查

- [x] 未越出 Phase 24 scope
- [x] 未触及 non-goals（无自动晋升、无跨任务合并、无 retrieval integration）
- [x] 已有 task-local knowledge 流程未被修改

## 结论

**PASS, mergeable.** 三个 slice 全部符合设计，167 测试通过，无 BLOCK 项。staged knowledge pipeline baseline 成功建立了"候选写入→列出→审查→晋升/拒绝"的完整闭环。
