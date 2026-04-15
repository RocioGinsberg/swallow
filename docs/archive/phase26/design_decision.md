---
author: claude
phase: 26
slice: canonical-knowledge-deduplication-and-merge-gate
status: draft
depends_on:
  - docs/plans/phase26/context_brief.md
  - docs/concerns_backlog.md
---

**TL;DR**: Phase 26 分三个 slice：① 修正 `build_stage_canonical_record()` 的 canonical_key 生成逻辑，使同源知识共享同一 key 从而激活已有 supersede 机制；② 在 stage-promote CLI 中增加 dedupe 前置检查和操作员提示；③ 新增 `swl knowledge canonical-audit` 审计命令。store 层的 supersede 逻辑已存在，本轮重点是修正上层调用使其正确利用。

# Design Decision: Phase 26

## 方案总述

深入分析后发现，`store.py` 的 `append_canonical_record()` **已经内置了**完整的 dedupe 和 supersede 逻辑：
- `canonical_id` 相同 → 替换（幂等写入）
- `canonical_key` 相同但 `canonical_id` 不同 → 旧记录标记为 `superseded`

问题出在上层调用：
1. **CLI `build_stage_canonical_record()`** 为每个 staged candidate 生成独立的 `canonical_key`（`staged-candidate:{candidate_id}`），即使两个 candidates 来自同一 task 的同一 knowledge object，key 也不同，supersede 永远不会触发
2. **CLI promote 路径**没有在写入前做 canonical_id 重复检查或操作员提示

本轮的核心修复是**让 canonical_key 正确反映知识的来源身份**，从而激活已有的 supersede 机制，而非重写 store 层。

## 非目标

- 不引入向量语义合并
- 不修改 `append_canonical_record()` 的 store 层逻辑（已有机制足够）
- 不引入自动去重策略（保持操作员手动决策）
- 不修改 task-local 的 knowledge promote 路径（`swl task knowledge-promote`）

## Slice 拆解

### Slice 1: 修正 Canonical Key 生成逻辑

**目标**：让 `build_stage_canonical_record()` 生成正确的 `canonical_key`，使同源知识共享同一 key。

**影响范围**：
- 修改 `src/swallow/cli.py` 中的 `build_stage_canonical_record()`
  - 当前逻辑：`canonical_key = f"task-object:{source_task_id}:{source_object_id}"` 仅在 `source_object_id` 非空时使用，否则用 `staged-candidate:{candidate_id}`
  - 修正后：优先使用 `source_task_id + source_object_id` 组合（与 `canonical_registry.py` 的 `build_canonical_key()` 对齐），这样同一 task 中同一 knowledge object 的多次 staged promote 会共享同一 key，自动触发 supersede
  - 仅当 `source_task_id` 和 `source_object_id` 都为空时才回退到 `staged-candidate:{candidate_id}`
- 修改 `src/swallow/canonical_registry.py`（可选）
  - 如果需要，抽取 `build_canonical_key_from_staged()` 函数使 key 生成逻辑集中
- 新增/扩展测试
  - promote 两个来自同一 source 的 candidates → 第一个 active，第二个触发 supersede
  - promote 两个来自不同 source 的 candidates → 两个都 active
  - promote 无 source_object_id 的 candidate → 回退到 staged-candidate key

**风险评级**：
- 影响范围: 2（CLI + canonical registry 写入行为变化）
- 可逆性: 1（修改 key 生成逻辑，回滚即恢复）
- 依赖复杂度: 2（依赖 store 层已有 supersede 机制）
- **总分: 5 — 中低风险**

**依赖**：无前置依赖。

**验收条件**：
- 同源 candidates 的 promote 触发 supersede
- 不同源 candidates 的 promote 不互相影响
- 已有测试全部通过

---

### Slice 2: Stage-Promote Dedupe 前置检查

**目标**：在 stage-promote 写入前，检查是否存在 canonical_id 重复或 canonical_key 冲突，给操作员明确提示。

**影响范围**：
- 修改 `src/swallow/cli.py` 的 `stage-promote` 命令处理
  - 在调用 `append_canonical_record()` 之前，加载已有 canonical records
  - 检查 1：`canonical_id` 重复 → 输出 `(idempotent) re-promoting existing canonical record` 提示，正常继续（幂等行为）
  - 检查 2：`canonical_key` 冲突且有 active 记录 → 输出 `(supersede) will supersede existing active record: {old_canonical_id}` 提示，正常继续（supersede 行为）
  - 这两个检查是**信息提示**而非阻断——操作员看到提示后 promote 仍然执行。如果需要阻断，未来可加 `--force` flag
- 新增测试
  - promote 已有 canonical_id 的记录 → 输出包含 `idempotent`
  - promote 会触发 supersede 的记录 → 输出包含 `supersede`
  - promote 全新记录 → 无额外提示

**风险评级**：
- 影响范围: 1（仅 CLI 输出增强）
- 可逆性: 1（纯增量提示）
- 依赖复杂度: 2（依赖 Slice 1 的 key 修正）
- **总分: 4 — 低风险**

**依赖**：建议在 Slice 1 之后，以确保 key 生成正确。

**验收条件**：
- 操作员在 supersede 场景下看到明确提示
- promote 行为不被阻断（保持现有流程的连贯性）
- 已有测试通过

---

### Slice 3: Canonical Audit 命令

**目标**：新增 `swl knowledge canonical-audit` 命令，帮助操作员检查 canonical registry 的健康度。

**影响范围**：
- 修改 `src/swallow/cli.py`
  - 在 `knowledge` 子命令下新增 `canonical-audit`
  - 输出内容：
    - 总记录数、active 数、superseded 数
    - 重复 canonical_key 检测（列出有多个 active 记录的 key）
    - 孤立记录检测（canonical_key 无对应的 source task/object）
  - 格式保持 CLI 紧凑风格
- 新建 `src/swallow/canonical_audit.py`（可选，如果逻辑较复杂则抽取）
  - `audit_canonical_registry(records) -> AuditResult`
  - `AuditResult`: total、active、superseded、duplicate_keys、orphan_records
- 新增测试
  - 健康 registry → audit 输出 no issues
  - 含重复 active key 的 registry → audit 输出 duplicate warnings
  - 空 registry → audit 输出 empty

**风险评级**：
- 影响范围: 1（新命令，不改已有逻辑）
- 可逆性: 1（纯新增）
- 依赖复杂度: 1（只读 registry）
- **总分: 3 — 低风险**

**依赖**：无硬依赖，但建议在 Slice 1/2 之后以便验证审计功能的完整性。

**验收条件**：
- audit 命令能正确检测重复和孤立记录
- 已有测试通过

---

## 实现顺序

```
Slice 1: canonical_key 生成修正（激活 supersede）
    ↓
Slice 2: stage-promote dedupe 前置检查（操作员提示）
    ↓
Slice 3: canonical-audit 审计命令
```

Slice 1 是核心修复，2 和 3 依赖其 key 逻辑。

## Concerns Backlog 消化

本轮完成后，`docs/concerns_backlog.md` 中的以下条目应移入 Resolved：

| Phase | CONCERN | 消化方式 |
|-------|---------|---------|
| 24 | stage-promote 缺少 canonical 去重检查 | Slice 1 修正 key + Slice 2 前置检查 |

## Branch Advice

- 当前分支: `main`
- 建议操作: 新建分支
- 建议分支名: `feat/phase26-canonical-dedupe`
- 理由: 3 个 slice 紧密关联，单分支单 PR
- PR 策略: 单 PR 合入

## Phase-Guard 检查

- [x] 方案未越出 context_brief 定义的 goals
- [x] 方案未触及 non-goals（无向量合并、无自动去重策略）
- [x] 不修改 store 层 `append_canonical_record()`（已有机制足够）
- [x] Slice 数量 = 3，在建议上限 ≤5 内
- 无 `[SCOPE WARNING]`
