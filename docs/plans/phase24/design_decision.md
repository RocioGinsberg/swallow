---
author: claude
phase: 24
slice: staged-knowledge-pipeline-baseline
status: draft
depends_on:
  - docs/plans/phase24/context_brief.md
  - docs/design/KNOWLEDGE_AND_RAG_DESIGN.md
  - docs/design/AGENT_TAXONOMY_DESIGN.md
---

**TL;DR**: Phase 24 分三个 slice：① 新建全局 staged knowledge 存储与数据模型；② CLI `stage-list` / `stage-inspect` / `stage-promote` / `stage-reject` 命令；③ orchestrator 中基于 taxonomy 的知识写入路由（canonical-write-forbidden 实体强制写入 staged 而非 canonical）。不做自动晋升，不做跨任务合并，不做 retrieval integration。

# Design Decision: Phase 24

## 方案总述

当前系统的知识生命周期（raw → candidate → verified → canonical）完全绑定在单个 task 内。knowledge objects、review queue、promote/reject 决策都在 `.swl/tasks/{task_id}/` 下，没有跨任务的全局"暂存候选池"。

Phase 24 建立一个**全局 staged knowledge 存储区**（`.swl/staged_knowledge/`），作为 canonical registry 的前置缓冲。核心类比：staged knowledge 就是 PR，canonical registry 就是 main 分支。

本轮只做 baseline 闭环：写入 → 列出 → 查看 → 晋升/拒绝。不做自动化策略、不做 retrieval integration、不做跨任务知识合并。

## 非目标

- 不实现基于 LLM Validator 的自动晋升
- 不实现跨任务知识合并或去重
- 不修改已有 task-local knowledge objects 的流程
- 不将 staged knowledge 纳入 retrieval 检索范围
- 不实现 diff 对比或语义冲突检测
- 不引入新的存储后端（保持 JSON/JSONL 文件）

## Slice 拆解

### Slice 1: Staged Knowledge 数据模型与存储

**目标**：建立全局 staged knowledge 的数据结构和存储路径。

**影响范围**：
- 新建 `src/swallow/staged_knowledge.py`
  - `StagedCandidate` dataclass：
    - `candidate_id: str` — 唯一 ID（格式 `staged-{uuid4_short}`）
    - `text: str` — 知识内容
    - `source_task_id: str` — 来源任务 ID
    - `source_object_id: str` — 来源 knowledge object ID（可为空）
    - `submitted_by: str` — 提交者标识（executor name / agent identity）
    - `submitted_at: str` — 提交时间
    - `taxonomy_role: str` — 提交者的 system_role（用于审计）
    - `taxonomy_memory_authority: str` — 提交者的 memory_authority（用于审计）
    - `status: str` — `"pending"` | `"promoted"` | `"rejected"`
    - `decided_at: str` — 决策时间（空字符串表示未决策）
    - `decided_by: str` — 决策者
    - `decision_note: str` — 决策备注
  - `submit_staged_candidate(base_dir, candidate) -> StagedCandidate` — 写入存储
  - `load_staged_candidates(base_dir) -> list[StagedCandidate]` — 读取全部候选
  - `update_staged_candidate(base_dir, candidate_id, status, decided_by, note) -> StagedCandidate` — 更新状态
- 修改 `src/swallow/paths.py`
  - 新增 `staged_knowledge_root(base_dir) -> Path`：返回 `.swl/staged_knowledge/`
  - 新增 `staged_knowledge_registry_path(base_dir) -> Path`：返回 `.swl/staged_knowledge/registry.jsonl`
- 存储格式：JSONL（每行一个 candidate，append-only 写入，更新通过重写）
- 新增 `tests/test_staged_knowledge.py`
  - submit candidate → 文件写入成功、ID 生成正确
  - load candidates → 返回完整列表
  - update status → promote/reject 正确持久化
  - load empty → 返回空列表

**风险评级**：
- 影响范围: 1（新模块，不改已有代码）
- 可逆性: 1（纯新增）
- 依赖复杂度: 1（无外部依赖）
- **总分: 3 — 低风险**

**依赖**：无前置依赖。

**验收条件**：
- StagedCandidate 可正确序列化/反序列化
- registry.jsonl 的读写操作正确
- 不影响任何已有测试

---

### Slice 2: CLI Staged Knowledge 命令

**目标**：为操作员提供管理 staged knowledge 的 CLI 命令。

**影响范围**：
- 修改 `src/swallow/cli.py`
  - 新增 `swl knowledge stage-list` — 列出所有 pending 候选（紧凑格式：candidate_id、text 摘要、来源 task、提交者 taxonomy、提交时间）
  - 新增 `swl knowledge stage-inspect <candidate_id>` — 查看单个候选的完整内容
  - 新增 `swl knowledge stage-promote <candidate_id>` — 将候选晋升到 canonical registry
  - 新增 `swl knowledge stage-reject <candidate_id>` — 拒绝候选
  - `stage-promote` 实现：
    1. 读取 candidate，校验 status == "pending"
    2. 调用已有的 canonical registry 写入逻辑（`append_canonical_record`）
    3. 更新 candidate status 为 "promoted"
  - `stage-reject` 实现：
    1. 读取 candidate，校验 status == "pending"
    2. 更新 candidate status 为 "rejected"
- 命令注册在新的 `knowledge` 顶级子命令下（与现有的 `task` 顶级命令平级），因为 staged knowledge 是全局的，不绑定单个 task
- 新增测试
  - stage-list 空列表 → 输出 "no pending candidates"
  - submit + stage-list → 显示候选
  - stage-promote → candidate 状态变更 + canonical registry 有新记录
  - stage-reject → candidate 状态变更
  - 对已决策的 candidate 再次 promote/reject → 报错

**风险评级**：
- 影响范围: 2（cli.py + staged_knowledge.py + canonical registry 集成）
- 可逆性: 1（新命令，删除即回滚）
- 依赖复杂度: 2（依赖 Slice 1 + 已有 canonical registry）
- **总分: 5 — 中低风险**

**依赖**：Slice 1 必须先完成。

**验收条件**：
- 四个命令均可正常执行
- promote 后 canonical registry 有对应记录
- 已有 CLI 测试不破

---

### Slice 3: Taxonomy-Aware 知识写入路由

**目标**：在 orchestrator 层，基于执行实体的 taxonomy memory_authority，自动将知识写入路由到 staged 而非 canonical。

**影响范围**：
- 修改 `src/swallow/orchestrator.py`
  - 在任务完成后的知识处理流程中（`run_task` 的 summarize 阶段之后），检查 `state.route_taxonomy_memory_authority`：
    - 如果是 `"canonical-write-forbidden"` 或 `"staged-knowledge"`：将满足晋升条件的 knowledge objects 自动提交到 staged knowledge（而非直接走 canonical promote）
    - 如果是 `"task-state"` 或更高权限：保持现有行为不变
  - 新增 `_route_knowledge_to_staged(base_dir, state, knowledge_objects)` 内部函数
    - 遍历 knowledge objects 中 `canonicalization_intent == "promote"` 且 `stage == "verified"` 的对象
    - 为每个创建 StagedCandidate 并提交
    - 记录 event: `task.knowledge_staged`
- 新增测试
  - canonical-write-forbidden executor 产出的 promote-intent knowledge → 自动进入 staged
  - general-executor (task-state) 产出的 knowledge → 保持现有行为（不自动 staged）
  - staged candidate 的 source_task_id 和 taxonomy 字段正确

**风险评级**：
- 影响范围: 2（orchestrator 知识处理路径）
- 可逆性: 2（修改了已有流程的分支逻辑）
- 依赖复杂度: 2（依赖 Slice 1 + 已有 knowledge objects 流程）
- **总分: 6 — 中等风险**

**依赖**：Slice 1 必须先完成。可与 Slice 2 并行或在其之后。

**验收条件**：
- canonical-write-forbidden 实体的知识自动进入 staged
- task-state 实体的知识流程不受影响
- 已有测试全部通过

---

## 实现顺序

```
Slice 1: StagedCandidate 数据模型与存储
    ↓
Slice 2: CLI stage-list / stage-inspect / stage-promote / stage-reject
    ↓  (可与 Slice 3 并行，但建议 2 先行以便手动验证)
Slice 3: Taxonomy-aware 知识写入路由
```

Slice 1 是基础，2 和 3 都依赖它。建议按 1→2→3 顺序实现。

## Branch Advice

- 当前分支: `main`
- 建议操作: 新建分支
- 建议分支名: `feat/phase24-staged-knowledge-pipeline`
- 理由: 3 个 slice 紧密关联，单分支单 PR
- PR 策略: 单 PR 合入

## Phase-Guard 检查

- [x] 方案未越出 context_brief 定义的 goals（只做 baseline 管道）
- [x] 方案未触及 non-goals（无自动晋升、无 retrieval integration、无跨任务合并）
- [x] 不修改已有 task-local knowledge 流程（Slice 3 只在特定 taxonomy 下增加分支）
- [x] Slice 数量 = 3，在建议上限 ≤5 内
- 无 `[SCOPE WARNING]`
