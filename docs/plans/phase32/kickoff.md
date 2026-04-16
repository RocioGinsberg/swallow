---
author: claude
phase: 32
slice: knowledge-dual-layer
status: draft
depends_on: [docs/roadmap.md, docs/plans/phase31/closeout.md, docs/plans/phase32/context_brief.md]
---

> **TL;DR**: Phase 32 将当前扁平的知识对象体系拆分为 Evidence Store（原始证据层）+ Wiki Store（认知层）双层架构，并引入 Librarian Agent 作为唯一的知识晋升守门人。Ingestion Specialist 延后，本轮聚焦写回防线。

# Phase 32 Kickoff — 知识双层架构与 Librarian Agent

## 基本信息

- **Phase**: 32
- **Primary Track**: Retrieval / Memory
- **Secondary Track**: —
- **Phase 名称**: 知识双层架构 + Librarian Agent (写回防线)

---

## 前置依赖与现有基础

Phase 31 已建立稳定的 Runtime v0 checkpoint：

- `TaskCard` + `Planner v0`（规则驱动 1:1 映射）
- `ExecutorProtocol`（统一执行器接口）
- `ReviewGate`（无状态 Schema 校验门禁）
- `run_task()` 三段式流程：Planner → Executor → ReviewGate

**知识层现有代码基础**（Phase 32 直接利用）：

- `knowledge_objects.py`：KnowledgeObject 构建 + stage 流转（raw → candidate → verified → canonical）
- `knowledge_policy.py`：知识策略校验（stage/evidence/reuse 规则）
- `knowledge_review.py`：review queue + decision 机制（promote/reject）
- `knowledge_partition.py`：task_linked vs reusable_candidates 分区
- `staged_knowledge.py`：StagedCandidate 暂存区 + registry 持久化
- `knowledge_index.py`：索引 + invalidation 检测
- `canonical_registry.py` / `canonical_audit.py` / `canonical_reuse.py`：canonical 晋升审计链

**关键观察**：现有代码已有 `raw → candidate → verified → canonical` 的 stage 流转和 review queue，但所有 knowledge objects 存储在同一个扁平结构中（TaskState.knowledge_objects），没有物理分离 Evidence 和 Wiki。晋升操作可由任何调用者触发，缺少 Librarian 守门人角色约束。

---

## 目标

1. **物理分离 Evidence Store 与 Wiki Store**：将现有扁平的 knowledge_objects 拆分为两个独立的存储概念——Evidence（原始证据，raw/candidate/verified 阶段）和 Wiki（经晋升的 canonical 知识条目），各自有独立的数据模型和访问路径。
2. **引入 Librarian Agent 角色与写回防线**：定义 Librarian 作为系统中唯一拥有 `staged-knowledge → canonical-promotion` 权限的 Agent 角色。所有向 Wiki Store 的写入必须经过 Librarian 的提纯工作流，产出 Change Log。
3. **改造 knowledge_review.py 的 decision 流程**：现有的 `apply_knowledge_decision(promote, canonical)` 必须校验调用者的 `memory_authority`，非 Librarian 角色触发 canonical promotion 应被拒绝。

---

## 非目标

- ❌ Ingestion Specialist（外部 AI 会话摄入）——延后至 Phase 32 stretch 或 Phase 33
- ❌ Graph RAG / 社区检测——延后至 Phase 33+
- ❌ Agentic RAG（多跳推理、动态路由工具选择）——延后至 Phase 33+
- ❌ 向量化 / 嵌入 / 实际 RAG 检索管线——本轮只建数据模型和访问契约，不建索引管线
- ❌ Librarian 的周期性记忆衰减——延后，本轮只做"写回守门"，不做"遗忘管理"
- ❌ Wiki 的冲突合并仲裁——延后，本轮只做单条晋升，不处理跨条目矛盾检测

---

## 设计边界

### Evidence Store 边界

- **数据范围**：stage ∈ {raw, candidate, verified} 的所有 knowledge objects
- **存储位置**：`<base_dir>/knowledge/evidence/` 下，每条 evidence 一个 JSON 文件（沿用现有 knowledge_objects 的 schema，增加 `store_type: "evidence"` 标识）
- **访问权限**：任何具有 `task-memory` 或更高 memory_authority 的 Agent 可读可写（写入新的 raw/candidate evidence）
- **晋升出口**：evidence 晋升为 canonical 时，由 Librarian 执行迁移到 Wiki Store

### Wiki Store 边界

- **数据范围**：stage == "canonical" 的知识条目
- **存储位置**：`<base_dir>/knowledge/wiki/` 下，每条 wiki entry 一个 JSON 文件
- **数据模型扩展**：在 KnowledgeObject 基础上增加：
  - `promoted_by: str`（执行晋升的 Librarian 标识）
  - `promoted_at: str`（晋升时间戳）
  - `change_log_ref: str`（关联的 Change Log artifact ID）
  - `source_evidence_ids: list[str]`（晋升来源 evidence 的 object_id 列表）
- **访问权限**：
  - 读取：任何 Agent 可读
  - 写入：仅 `canonical-promotion` memory_authority（即 Librarian）可写
  - 修改/删除：仅 Librarian + human-operator

### Librarian Agent 边界

- **角色定义**：`taxonomy_role: "specialist"`, `taxonomy_memory_authority: "canonical-promotion"`
- **v0 职责**（本轮）：
  1. 接收一批 `verified` + `artifact_backed` 的 evidence objects
  2. 执行降噪提纯（v0 阶段为规则驱动：去重、格式标准化、来源指针验证）
  3. 生成 Change Log artifact（记录每条晋升的 before/after + 理由）
  4. 执行 canonical promotion，将条目迁移至 Wiki Store
- **不做**（本轮）：
  - 不调用 LLM 进行语义级提纯（v0 是规则驱动）
  - 不做冲突合并仲裁
  - 不做周期性衰减扫描
  - 不处理外部会话摄入

### 权限校验改造边界

- `knowledge_review.py::apply_knowledge_decision()` 新增 `caller_authority: str` 参数
- 当 `decision_type == "promote"` 且 `decision_target == "canonical"` 时，校验 `caller_authority == "canonical-promotion"`
- 校验失败抛出 `PermissionError`，并记录 `knowledge.promotion.unauthorized` 事件

### 与 Runtime v0 的集成边界

- Librarian 的提纯工作流通过 `ExecutorProtocol` 接入（实现 `LibrarianExecutor`）
- Planner 在检测到 evidence 中存在 `promotion_ready` 条目时，可生成 librarian 类型的 TaskCard
- ReviewGate 在 Librarian 产出后校验 Change Log 的 schema 完整性

---

## 完成条件

1. Evidence Store 和 Wiki Store 的目录结构与读写 API 就位（`knowledge_store.py`）
2. 现有 `TaskState.knowledge_objects` 中 stage != canonical 的条目可迁移至 Evidence Store
3. Wiki Store 只接受通过 Librarian 工作流的 canonical promotion 写入
4. `apply_knowledge_decision(promote, canonical)` 增加 `caller_authority` 校验
5. `LibrarianExecutor` 实现 `ExecutorProtocol`，完成规则驱动的提纯 + Change Log 生成
6. Planner 可识别 `promotion_ready` evidence 并生成 librarian TaskCard
7. 所有现有测试通过（回归安全）
8. 新增测试覆盖：双层存储读写、权限校验、Librarian 工作流端到端

---

## Slice 拆解

| Slice | 目标 | 关键文件 | 风险评级 |
|-------|------|----------|----------|
| S1: Evidence/Wiki 双层存储 | 定义双层数据模型与读写 API，建立目录结构 | 新建 `knowledge_store.py`，改 `models.py`（WikiEntry 扩展字段） | 低 (影响 1 / 可逆 1 / 依赖 1 = 3) |
| S2: 权限校验 + Librarian 角色 | 改造 promotion 校验，定义 Librarian 角色约束 | 改 `knowledge_review.py`，改 `models.py`（agent role 常量） | 低 (影响 2 / 可逆 1 / 依赖 1 = 4) |
| S3: LibrarianExecutor + 流程集成 | 实现 Librarian 执行器，Planner 识别 + ReviewGate 校验 Change Log | 新建 `librarian_executor.py`，改 `planner.py`，改 `review_gate.py` | 中 (影响 2 / 可逆 2 / 依赖 2 = 6) |

### 依赖关系

```
S1 (双层存储)
  └──→ S2 (权限校验)
         └──→ S3 (Librarian 集成)
```

串行推进。S2 需要 S1 的 Wiki Store 写入 API 才能实现权限校验。S3 需要 S1+S2 就位才能做端到端集成。

---

## 风险评估

### R1: 存储迁移兼容性（中）
- **风险**：现有测试假设 knowledge_objects 全部在 TaskState 内，双层拆分可能破坏大量测试
- **缓解**：S1 采用渐进式策略——双层存储作为新的访问层，TaskState.knowledge_objects 暂时保留为"视图"（读取时合并两层），避免一次性破坏回归
- **检验**：S1 完成后全量测试必须通过

### R2: Scope 膨胀（中）
- **风险**：Librarian 的"提纯"逻辑容易发散（想加 LLM 调用、冲突检测、衰减）
- **缓解**：v0 严格限制为规则驱动（去重 + 格式标准化 + 来源验证），不引入 LLM 调用
- **检验**：LibrarianExecutor 代码中不出现 model/LLM 调用

### R3: 权限模型破坏现有流程（低）
- **风险**：新增 caller_authority 校验可能阻断现有的 CLI 手动 promote 流程
- **缓解**：CLI 的 `swl knowledge promote` 命令默认以 `canonical-promotion` authority 执行（人类操作等同 Librarian 权限），只阻断自动化 Agent 的未授权晋升
- **检验**：现有 CLI knowledge 子命令测试全部通过

---

## 风险评分

| 维度 | 评分 (1-3) | 说明 |
|------|-----------|------|
| 影响范围 | 2 | 改动知识层核心，但不触及 orchestrator 主循环 |
| 可逆性 | 1 | 双层存储可回退为扁平结构，权限校验可关闭 |
| 外部依赖 | 1 | 纯内部重构，不依赖外部服务 |
| 状态突变 | 2 | 知识存储位置变化，需要迁移策略 |
| 并发风险 | 1 | 当前单线程执行，无并发写入竞争 |
| **总分** | **7/15** | **低风险** |
