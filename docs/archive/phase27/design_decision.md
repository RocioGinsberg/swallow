---
author: claude
phase: 27
slice: knowledge-driven-task-grounding-baseline
status: draft
depends_on:
  - docs/plans/phase27/context_brief.md
  - docs/design/KNOWLEDGE_AND_RAG_DESIGN.md
---

**TL;DR**: Phase 27 分三个 slice：① 在 retrieval 阶段过滤出 canonical-sourced items 并生成 `grounding_evidence.json` artifact；② 将 grounding 引用登记到 TaskState 的 `context_refs` 中，确保 resume 稳定性；③ CLI inspect 展示 grounding 状态。不引入向量检索，不直接向 prompt 注入知识，走 artifact 路径。

# Design Decision: Phase 27

## 方案总述

当前系统的 retrieval 已经包含 canonical registry 的记录（通过 `iter_canonical_reuse_items()`），但召回的 canonical 知识存在两个问题：

1. **不可追溯**：canonical items 混在普通 retrieval items 中，没有独立的实体化 artifact。`source_grounding.md` 只是格式化展示，不区分 canonical vs. non-canonical。
2. **不可恢复**：retrieval 结果依赖运行时查询，resume 后可能因 registry 变化而漂移。没有"锁定"机制。

Phase 27 的核心修复：在 retrieval 完成后，从结果中**提取 canonical-sourced items**，生成独立的 `grounding_evidence.json` artifact（锁定），并将其引用写入 TaskState 的 `context_refs`（可追溯）。executor prompt 中已有的 retrieval 展示不变，但 grounding artifact 提供了额外的权威证据层。

## 非目标

- 不引入向量检索或语义搜索
- 不直接向 executor prompt 注入 canonical 知识（走 artifact 路径，由 executor 自行引用）
- 不修改已有 retrieval 评分或排序逻辑
- 不修改 canonical registry 的写入路径
- 不实现 Agentic RAG（意图驱动的多跳推理）

## Slice 拆解

### Slice 1: Grounding Evidence Artifact 生成

**目标**：在 retrieval 完成后，从结果中提取 canonical-sourced items 并生成独立的 grounding artifact。

**影响范围**：
- 新建 `src/swallow/grounding.py`
  - `GroundingEntry` dataclass：
    - `canonical_id: str`
    - `canonical_key: str`
    - `text: str`
    - `citation: str`（格式 `canonical:{canonical_id}`）
    - `source_task_id: str`
    - `evidence_status: str`
    - `score: int`（来自 retrieval 评分）
  - `extract_grounding_entries(retrieval_items) -> list[GroundingEntry]`
    - 过滤 `metadata.storage_scope == "canonical_registry"` 的 items
    - 提取 canonical 元数据构建 GroundingEntry
  - `build_grounding_evidence(entries) -> dict`
    - 返回可序列化的 grounding evidence payload（entries 列表 + 元信息）
  - `build_grounding_evidence_report(evidence) -> str`
    - 生成 markdown 格式的 grounding 报告
- 修改 `src/swallow/harness.py`
  - 在 `write_task_artifacts()` 中，调用 `extract_grounding_entries()` + `build_grounding_evidence()`
  - 写入 `grounding_evidence.json` artifact
  - 写入 `grounding_evidence_report.md` artifact
  - 在 `state.artifact_paths` 中登记两个路径
- 新增 `tests/test_grounding.py`
  - retrieval 含 canonical items → 提取正确
  - retrieval 不含 canonical items → 空 entries
  - grounding report 格式正确

**风险评级**：
- 影响范围: 2（harness artifact 写入路径）
- 可逆性: 1（新增 artifact，删除即回滚）
- 依赖复杂度: 2（依赖 retrieval items 的 metadata 结构）
- **总分: 5 — 中低风险**

**依赖**：无前置依赖。

**验收条件**：
- canonical-sourced retrieval items 被正确提取为 GroundingEntry
- grounding_evidence.json 和 report.md 正确写入 artifacts 目录
- 已有测试全部通过

---

### Slice 2: Context Refs 登记与 Resume 锁定

**目标**：将 grounding evidence 的引用登记到 TaskState，确保 resume 后 grounding 基础不漂移。

**影响范围**：
- 修改 `src/swallow/models.py`
  - TaskState 新增字段 `grounding_refs: list[str] = field(default_factory=list)`
    - 存储格式：`["canonical:{canonical_id}", ...]`
  - TaskState 新增字段 `grounding_locked: bool = False`
    - True 表示 grounding evidence 已锁定，resume 时不重新召回
- 修改 `src/swallow/orchestrator.py`
  - 在 `run_task()` 的 retrieval 阶段后：
    - 如果 `state.grounding_locked == True`（resume 场景），跳过 grounding 重新提取，直接使用已有 artifact
    - 如果 `state.grounding_locked == False`（首次执行），提取 grounding entries，写入 refs，设置 `grounding_locked = True`
  - 在 event payload 中记录 grounding_refs 和 grounding_locked 状态
- 新增测试
  - 首次 run → grounding_refs 填充 + grounding_locked=True
  - resume 后 run → grounding_refs 不变（锁定）
  - 无 canonical items → grounding_refs 为空，grounding_locked=True（空但锁定）

**风险评级**：
- 影响范围: 2（models + orchestrator）
- 可逆性: 1（新字段有默认值，不破坏反序列化）
- 依赖复杂度: 2（依赖 Slice 1 的 grounding 提取）
- **总分: 5 — 中低风险**

**依赖**：Slice 1 必须先完成。

**验收条件**：
- grounding_refs 正确记录 canonical citations
- resume 后 grounding 不重新提取
- 已有测试全部通过

---

### Slice 3: Inspect Grounding 可视化

**目标**：在 CLI inspect 中展示 grounding 状态，让操作员看到任务的知识锚定情况。

**影响范围**：
- 修改 `src/swallow/cli.py`
  - inspect 命令的 Route And Topology 区域（或新增 Grounding 区域），展示：
    - `grounding_locked: yes/no`
    - `grounding_refs_count: N`
    - `grounding_refs: canonical:{id1}, canonical:{id2}, ...`（紧凑格式，最多显示前 5 个）
  - 数据来源：直接从 TaskState 读取 `grounding_refs` 和 `grounding_locked`
- 新增 CLI 报告命令 `swl task grounding <task_id>`
  - 读取并打印 `grounding_evidence_report.md` artifact
- 新增测试
  - inspect 有 grounding 的任务 → 输出包含 `grounding_locked: yes` + refs
  - inspect 无 grounding 的任务 → 输出 `grounding_locked: -`
  - `swl task grounding <id>` → 输出 grounding report 内容

**风险评级**：
- 影响范围: 1（CLI 渲染层）
- 可逆性: 1（纯增量）
- 依赖复杂度: 2（依赖 Slice 1+2 的 grounding 数据）
- **总分: 4 — 低风险**

**依赖**：Slice 2 必须先完成。

**验收条件**：
- inspect 正确展示 grounding 信息
- grounding 报告命令可用
- 已有测试通过

---

## 实现顺序

```
Slice 1: grounding.py + harness artifact 写入
    ↓
Slice 2: TaskState context_refs + resume 锁定
    ↓
Slice 3: inspect 可视化 + grounding 报告命令
```

严格顺序依赖：1→2→3。

## Branch Advice

- 当前分支: `main`
- 建议操作: 新建分支
- 建议分支名: `feat/phase27-knowledge-grounding`
- 理由: 3 个 slice 紧密关联，单分支单 PR
- PR 策略: 单 PR 合入

## Phase-Guard 检查

- [x] 方案未越出 context_brief 定义的 goals
- [x] 方案未触及 non-goals（无向量检索、无 prompt 直接注入、无 Agentic RAG）
- [x] grounding 走 artifact 路径，遵守 ARCHITECTURE.md 的 orchestrator/harness 边界
- [x] resume 锁定机制确保 STATE_AND_TRUTH_DESIGN.md 的"单一事实源"要求
- [x] Slice 数量 = 3，在建议上限 ≤5 内
- 无 `[SCOPE WARNING]`
