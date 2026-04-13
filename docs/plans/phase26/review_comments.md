---
author: claude
phase: 26
slice: canonical-knowledge-deduplication-and-merge-gate
status: draft
depends_on:
  - docs/plans/phase26/design_decision.md
  - docs/plans/phase26/risk_assessment.md
---

**TL;DR**: 三个 slice 全部实现且通过测试（188 passed）。整体 PASS，可合并。无 CONCERN，Phase 24 遗留的 concerns_backlog 条目可标记 Resolved。

# Review Comments: Phase 26

## 测试结果

```
188 passed, 5 subtests passed in 4.77s
```

全部通过，无 failure。较上一轮净增 10 个测试。

---

## Slice 1: Canonical Key 修正

### [PASS] build_staged_canonical_key() 抽取
- 新函数 `build_staged_canonical_key()` 在 `canonical_registry.py` 中集中管理 staged promote 的 key 生成
- 逻辑与 `build_canonical_key()` 对齐：优先 `task-object:{task_id}:{object_id}`，无 source_object_id 时回退到 `staged-candidate:{candidate_id}`
- `cli.py` 的 `build_stage_canonical_record()` 改为调用此函数，不再自行拼接

### [PASS] Supersede 行为验证
- 测试覆盖：同源（同 task + 同 object_id）的两次 promote → 第一条 superseded，第二条 active
- 测试覆盖：不同源的两次 promote → 两条都 active
- 测试覆盖：无 source_object_id → 回退到 staged-candidate key

### [PASS] 向下兼容
- 已有 stage-promote 测试（Phase 24）继续通过
- canonical registry 的 supersede 机制未被修改，只是被正确激活

---

## Slice 2: Dedupe 前置检查

### [PASS] build_stage_promote_preflight_notices()
- canonical_id 重复 → `(idempotent)` 提示
- canonical_key 冲突且有 active 记录 → `(supersede)` 提示
- 无冲突 → 无提示
- 提示是**信息性的**，不阻断 promote 操作——正确的设计选择

### [PASS] CLI 集成
- promote 前先 load canonical records 并调用 preflight
- notices 输出在 promote 确认信息之前

### [PASS] 测试覆盖
- idempotent 场景（预置 canonical record + 再次 promote 同 candidate）→ 输出包含 `(idempotent)`
- supersede 场景（两次 promote 同源）→ 第二次输出包含 `(supersede)`
- 全新记录 → 不包含任何 preflight notice

---

## Slice 3: Canonical Audit 命令

### [PASS] canonical_audit.py 模块
- `CanonicalAuditResult` dataclass：total、active、superseded、duplicate_active_keys、orphan_records
- `audit_canonical_registry()` 实现完整：
  - 检测同一 canonical_key 有多个 active 记录（duplicate）
  - 检测 source_task_id + source_object_id 在 task 的 knowledge_objects.json 中不存在（orphan）
- `_source_object_exists()` 做了正确的文件存在 + JSON 内容检查

### [PASS] CLI 集成
- `swl knowledge canonical-audit` 命令注册正确
- 输出格式紧凑：总数 + 分类 + 具体问题列表
- 无问题时输出 `no issues`

### [PASS] 测试覆盖
- 空 registry → no issues
- 含 duplicate active keys → 列出冲突 key 和对应 ids
- 含 orphan records → 列出孤立 canonical_id
- 健康 registry（有 source task + knowledge object）→ no issues

---

## 与 design_decision 的一致性检查

| 设计要求 | 实现状态 |
|----------|---------|
| build_staged_canonical_key() 集中化 | PASS |
| 同源 promote 触发 supersede | PASS |
| 不同源 promote 独立 active | PASS |
| 无 source_object_id 回退 key | PASS |
| idempotent preflight notice | PASS |
| supersede preflight notice | PASS |
| canonical-audit 命令 | PASS |
| duplicate_active_keys 检测 | PASS |
| orphan_records 检测 | PASS |
| 不修改 store 层 append_canonical_record | PASS |
| 不引入向量合并 | PASS |

## Concerns Backlog 消化

Phase 24 Open 条目 `stage-promote 缺少 canonical 去重检查` → **Resolved by Phase 26 Slice 1+2**。

## Phase-Guard 检查

- [x] 未越出 Phase 26 scope
- [x] 未触及 non-goals（无向量合并、无自动策略）
- [x] store 层 append_canonical_record 未被修改

## 结论

**PASS, mergeable.** 三个 slice 全部符合设计，188 测试通过，无 BLOCK 项，无 CONCERN。Phase 24 遗留的技术债已消化。
