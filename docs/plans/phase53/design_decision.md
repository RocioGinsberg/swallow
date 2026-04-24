---
author: claude
phase: 53
slice: design
status: draft
depends_on:
  - docs/plans/phase53/kickoff.md
  - docs/plans/phase53/context_brief.md
  - docs/design/AGENT_TAXONOMY.md
  - src/swallow/executor.py
  - src/swallow/librarian_executor.py
  - src/swallow/meta_optimizer.py
  - src/swallow/ingestion/pipeline.py
  - src/swallow/consistency_audit.py
  - src/swallow/validator.py
  - src/swallow/models.py
---

## TL;DR

Phase 53 将 5 个函数化角色升级为独立 Agent，复用 Phase 51 的 `ExecutorProtocol` + taxonomy profile 模式。核心设计：(1) 包装型 Agent 调用现有函数，不重写逻辑；(2) Literature Specialist / Quality Reviewer 基于启发式规则从零构建最小契约；(3) `resolve_executor` 引入注册表机制替代 if-chain；(4) `memory_authority` 语义通过代码注释 + taxonomy 文档补充列消化 C1。

---

## 核心设计决策

### 决策 1：包装型 Agent 的实现模式

**问题**：Ingestion Specialist / Consistency Reviewer / Validator 已有函数实现，Agent 化时是包装函数还是重写逻辑？

**候选方案**：
- A. 包装：Agent.execute() 内部调用现有函数，转换输入/输出格式
- B. 重写：把函数逻辑搬进 Agent 类，废弃原函数
- C. 混合：核心逻辑搬进 Agent，原函数改为调用 Agent

**选择方案**：A（包装）

**理由**：
- LibrarianAgent / MetaOptimizerAgent 已验证此模式：Agent.execute() 调用 `run_meta_optimizer()` / librarian 内部函数
- 现有函数的 CLI 直接调用路径不受影响（`swl ingest` 继续调用 `run_ingestion_pipeline`）
- 重写风险高：3 个函数各有完整的测试覆盖，搬迁逻辑容易引入回归
- 后续如需重构，可在 Agent 稳定后逐步迁移

**实现模板**（以 IngestionSpecialistAgent 为例）：

```python
INGESTION_SPECIALIST_SYSTEM_ROLE = "specialist"
INGESTION_SPECIALIST_MEMORY_AUTHORITY = "staged-knowledge"
INGESTION_SPECIALIST_EXECUTOR_NAME = "ingestion-specialist"

class IngestionSpecialistAgent:
    agent_name = INGESTION_SPECIALIST_EXECUTOR_NAME
    system_role = INGESTION_SPECIALIST_SYSTEM_ROLE
    memory_authority = INGESTION_SPECIALIST_MEMORY_AUTHORITY

    def execute(self, base_dir, state, card, retrieval_items) -> ExecutorResult:
        source_path = Path(card.input_context.get("source_path", ""))
        format_hint = card.input_context.get("format_hint")
        result = run_ingestion_pipeline(base_dir, source_path, format_hint=format_hint)
        return ExecutorResult(
            executor_name=self.agent_name,
            status="completed",
            message=f"Ingested {len(result.staged_candidates)} candidates from {result.source_path}.",
            output=build_ingestion_summary(result),
            ...
        )

    async def execute_async(self, base_dir, state, card, retrieval_items) -> ExecutorResult:
        return await asyncio.to_thread(self.execute, base_dir, state, card, retrieval_items)

class IngestionSpecialistExecutor(IngestionSpecialistAgent):
    """Compatibility wrapper."""
```

三个包装型 Agent 均遵循此模板，差异仅在输入提取和函数调用。

---

### 决策 2：ConsistencyReviewerAgent 与 fire-and-forget 路径的关系

**问题**：`run_consistency_audit()` 已被 `_maybe_schedule_consistency_audit` 的 `asyncio.create_task` 路径调用。Agent 化后，两条路径如何共存？

**候选方案**：
- A. Agent 包装 `run_consistency_audit()`，fire-and-forget 路径不变——两条独立入口
- B. fire-and-forget 路径改为调用 `ConsistencyReviewerAgent.execute_async()`
- C. 废弃 fire-and-forget 路径，统一走 Agent

**选择方案**：A（两条独立入口并存）

**理由**：
- fire-and-forget 路径是 Phase 51 S3 的核心交付物，已稳定且有测试覆盖
- 该路径的触发条件由 `AuditTriggerPolicy` 控制，与 Agent 的显式调用语义不同
- B 会引入不必要的耦合：fire-and-forget 不需要 `TaskCard` / `TaskState` 等 Agent 入参
- Agent 提供的是 operator 显式调用入口（`swl audit run --task-id`），与自动触发互补

**实现**：
- `ConsistencyReviewerAgent.execute()` 调用 `run_consistency_audit()`
- `_maybe_schedule_consistency_audit` 继续直接调用 `schedule_consistency_audit()`
- 两条路径共享底层 `run_consistency_audit()` 函数

---

### 决策 3：Literature Specialist 最小契约

**问题**：Literature Specialist 无现有实现，最小可行输入/输出契约是什么？

**候选方案**：
- A. 全功能：LLM 驱动的深度解析 + 跨文档比较 + 语义提取
- B. 最小启发式：读取文件、提取标题/章节结构、生成结构化摘要
- C. 占位 stub：返回固定格式的"待实现"输出

**选择方案**：B（最小启发式）

**理由**：
- A 需要 LLM 调用，违反 Phase 53 "不引入新 LLM 调用"的非目标
- C 无实际价值，无法验证 Agent 生命周期的端到端正确性
- B 提供真实的输入/输出流，后续 phase 可接入 LLM 增强

**输入契约**：
```python
card.input_context = {
    "document_paths": ["path/to/doc1.md", "path/to/doc2.md"],
    # goal 从 card.goal 读取
}
```

**输出契约**（`ExecutorResult.output` 为 markdown）：
```markdown
# Literature Analysis

## Documents
- doc1.md: 15 sections, 2340 words
- doc2.md: 8 sections, 1120 words

## Structure Summary
- doc1.md: [section titles extracted from headings]
- doc2.md: [section titles extracted from headings]

## Key Terms
- [top N terms by frequency, excluding stop words]

## Cross-Document Overlap
- [shared section titles or key terms between documents]
```

**实现**：读取 markdown/text 文件 → 正则提取 `#` 标题 → 统计词频 → 交叉比较 → 格式化输出。

---

### 决策 4：Quality Reviewer 最小契约与 Validator 的边界

**问题**：Quality Reviewer 和 Validator 都做"校验"，如何划清边界？

**候选方案**：
- A. 合并为一个 Agent，按 `card.input_context["mode"]` 区分
- B. 正交分工：Validator 检查 task 级完整性，Quality Reviewer 检查单 artifact 内容质量
- C. Quality Reviewer 是 Validator 的超集，Validator 废弃

**选择方案**：B（正交分工）

**理由**：
- `AGENT_TAXONOMY.md §7.3` 明确定义了两个独立角色，合并违反蓝图
- 职责确实不同：Validator 回答"文件都在吗"，Quality Reviewer 回答"内容合格吗"
- 正交分工允许独立演进：Validator 保持轻量规则检查，Quality Reviewer 后续可接入 LLM

**Quality Reviewer 输入契约**：
```python
card.input_context = {
    "artifact_ref": ".swl/tasks/{task_id}/artifacts/executor_output.md",
    "quality_criteria": ["non_empty", "has_structure", "has_actionable_content"],
}
```

**Quality Reviewer 输出契约**（`ExecutorResult.output` 为 markdown）：
```markdown
# Quality Review

- artifact: executor_output.md
- overall_verdict: pass | warn | fail

## Criteria
- non_empty: pass — artifact contains 1240 characters
- has_structure: pass — 3 markdown headings detected
- has_actionable_content: warn — no code blocks or action items detected
```

**内置 quality criteria**（Phase 53 范围）：
- `non_empty`：文件存在且非空
- `has_structure`：包含 markdown 标题（`#` 行）
- `has_actionable_content`：包含代码块、列表项或 action 关键词
- `min_length`：字符数 ≥ 阈值（默认 100）

后续 phase 可扩展为 LLM 驱动的语义质量评估。

---

### 决策 5：`resolve_executor` 扩展策略

**问题**：当前 `resolve_executor` 使用 if-chain（6 个分支），新增 5 个 Agent 后膨胀到 11 个分支。是否引入注册表？

**候选方案**：
- A. 保持 if-chain，按字母序排列
- B. 引入 `EXECUTOR_REGISTRY: dict[str, Callable[[], ExecutorProtocol]]`
- C. 每个 Agent 模块自注册（import side effect）

**选择方案**：B（显式注册表，不依赖 import side effect）

**理由**：
- 11 个 if-chain 可读性差，新增 Agent 需要修改 `executor.py` 核心函数
- C 的 import side effect 不可控：import 顺序、循环依赖、测试隔离都是问题
- B 的注册表在 `executor.py` 中集中定义，延迟 import 保持现有模式

**实现**：

```python
def _lazy_librarian() -> ExecutorProtocol:
    from .librarian_executor import LibrarianExecutor
    return LibrarianExecutor()

def _lazy_meta_optimizer() -> ExecutorProtocol:
    from .meta_optimizer import MetaOptimizerExecutor
    return MetaOptimizerExecutor()

def _lazy_ingestion_specialist() -> ExecutorProtocol:
    from .ingestion_specialist import IngestionSpecialistExecutor
    return IngestionSpecialistExecutor()

# ... 同理 consistency-reviewer, validator, literature-specialist, quality-reviewer

EXECUTOR_REGISTRY: dict[str, Callable[[], ExecutorProtocol]] = {
    "librarian": _lazy_librarian,
    "meta-optimizer": _lazy_meta_optimizer,
    "meta_optimizer": _lazy_meta_optimizer,
    "ingestion-specialist": _lazy_ingestion_specialist,
    "consistency-reviewer": _lazy_consistency_reviewer,
    "validator": _lazy_validator,
    "literature-specialist": _lazy_literature_specialist,
    "quality-reviewer": _lazy_quality_reviewer,
}

def resolve_executor(executor_type: str, executor_name: str) -> ExecutorProtocol:
    raw_name = (executor_name or "").strip().lower()
    normalized_name = normalize_executor_name(executor_name)
    normalized_type = (executor_type or "").strip().lower()

    factory = EXECUTOR_REGISTRY.get(raw_name) or EXECUTOR_REGISTRY.get(normalized_type)
    if factory is not None:
        return factory()
    if normalized_name in {"mock", "mock-remote"} or normalized_type == "mock":
        return MockExecutor()
    if normalized_name == "http" or normalized_type in {"http", "api"}:
        return HTTPExecutor()
    if normalized_name in CLI_AGENT_CONFIGS:
        return AsyncCLIAgentExecutor(CLI_AGENT_CONFIGS[normalized_name])
    return LocalCLIExecutor()
```

mock / http / CLI agent 保留在 if-chain 中（它们不是 specialist/validator Agent，不适合放注册表）。

---

### 决策 6：C1 消化方式

**问题**：Phase 51 C1 指出 `memory_authority = "canonical-write-forbidden"` 容易被误解为"完全只读"。如何消化？

**候选方案**：
- A. 代码层面：在 `MEMORY_AUTHORITIES` 定义处添加注释
- B. 文档层面：在 `AGENT_TAXONOMY.md §5` 补充"允许的 side effect"列
- C. 代码 + 文档双管齐下

**选择方案**：C（代码 + 文档）

**理由**：
- 仅代码注释容易被忽略
- 仅文档更新不够——开发者看代码时需要就地理解语义
- Phase 53 引入 5 个新 Agent，每个都有 `memory_authority`，此时是最佳消化时机

**实现**：

1. `models.py` 的 `MEMORY_AUTHORITIES` 定义处：
```python
MEMORY_AUTHORITIES: tuple[str, ...] = (
    "stateless",           # No cross-call memory; only explicit input parameters
    "task-state",          # Read/write task truth and event truth
    "task-memory",         # Read/write local memory within current task cycle (resume notes, compressed summaries)
    "staged-knowledge",    # May generate or modify staged knowledge candidates (pending review)
    "canonical-write-forbidden",  # May NOT write to canonical knowledge store; MAY write proposals, reports, artifacts
    "canonical-promotion", # May promote staged knowledge to canonical (narrowest, most sensitive)
)
```

2. `AGENT_TAXONOMY.md §5` 表格增加"允许的 side effect"列：

| 权限等级 | 含义 | 允许的 side effect |
|---|---|---|
| Stateless | 除明确入参外不跨调用保留记忆 | 无 |
| Task-State Access | 可读写 task truth / event truth | task artifacts |
| Task-Memory | 可在当前任务周期内读写局部记忆 | resume notes, compressed summaries |
| Staged-Knowledge | 有权生成或修改待审查的知识候选对象 | staged candidates, ingestion artifacts |
| Canonical-Write-Forbidden | 禁止直接突变 canonical knowledge truth | proposals, reports, audit artifacts, optimization bundles |
| Canonical Promotion Authority | 最窄最敏感的权限域 | canonical records, change logs |

---

### 决策 7：新 Agent 文件组织

**问题**：5 个新 Agent 放在哪里？

**候选方案**：
- A. 每个 Agent 独立文件（`ingestion_specialist.py`、`consistency_reviewer.py` 等）
- B. 按 system_role 分组（`specialist_agents.py`、`validator_agents.py`）
- C. 统一放在 `agents/` 子目录

**选择方案**：A（每个 Agent 独立文件）

**理由**：
- 与 `librarian_executor.py` / `meta_optimizer.py` 模式一致
- 每个 Agent 有独立的 import 依赖（ingestion 依赖 `ingestion/pipeline.py`，consistency 依赖 `consistency_audit.py`），分文件避免不必要的 import 耦合
- 延迟 import 在 `resolve_executor` 中按需加载，不增加启动时间

**文件清单**：
- `src/swallow/ingestion_specialist.py` — IngestionSpecialistAgent
- `src/swallow/consistency_reviewer.py` — ConsistencyReviewerAgent
- `src/swallow/validator_agent.py` — ValidatorAgent（避免与 `validator.py` 冲突）
- `src/swallow/literature_specialist.py` — LiteratureSpecialistAgent
- `src/swallow/quality_reviewer.py` — QualityReviewerAgent

---

## 与蓝图的对齐

| 蓝图要点 | Phase 53 实现 | 对齐度 |
|---------|-------------|--------|
| **§7.3 Ingestion Specialist** | 包装 `run_ingestion_pipeline()`，`staged-knowledge` 权限 | ✅ 完全对齐 |
| **§7.3 Literature Specialist** | 启发式文档解析，`task-memory` 权限 | ⚠️ 最小实现，后续接 LLM |
| **§7.3 Quality Reviewer** | 规则式质量检查，`stateless` 权限 | ⚠️ 最小实现，后续接 LLM |
| **§7.3 Consistency Reviewer** | 包装 `run_consistency_audit()`，`stateless` 权限 | ✅ 完全对齐 |
| **§3 Validator** | 包装 `validate_run_outputs()`，`stateless` 权限 | ✅ 完全对齐 |
| **§5 Memory Authority** | 补充"允许的 side effect"列 | ✅ 消化 C1 |
| **§8 新实体安全预设** | 所有新 Agent 默认 `stateless` 或 `task-memory`，不放宽 | ✅ 完全对齐 |

---

## 验收条件

| Slice | 验收条件 |
|-------|---------|
| **S1** | ✓ IngestionSpecialistAgent / ConsistencyReviewerAgent / ValidatorAgent 实装 ✓ 三者均实现 ExecutorProtocol ✓ resolve_executor 识别三个名称 ✓ 单元测试覆盖 execute + taxonomy profile ✓ 现有函数调用方不受影响 |
| **S2** | ✓ LiteratureSpecialistAgent / QualityReviewerAgent 实装 ✓ 输入/输出契约有单元测试（正常 + 缺失输入 + 空文档）✓ resolve_executor 识别两个名称 ✓ 集成测试验证与 run_task 协作 |
| **S3** | ✓ MEMORY_AUTHORITIES 定义处有语义注释 ✓ AGENT_TAXONOMY.md §5 补充"允许的 side effect"列 ✓ resolve_executor 注册表机制落地 ✓ 全量 pytest 通过 |

---

## 提交序列建议

1. `refactor(executor): introduce EXECUTOR_REGISTRY for specialist/validator agents` — 注册表机制，保留现有 Agent 注册
2. `feat(agent): add IngestionSpecialistAgent` — S1 第一个包装型 Agent
3. `feat(agent): add ConsistencyReviewerAgent` — S1 第二个包装型 Agent
4. `feat(agent): add ValidatorAgent` — S1 第三个包装型 Agent
5. `feat(agent): add LiteratureSpecialistAgent` — S2 启发式文档解析
6. `feat(agent): add QualityReviewerAgent` — S2 规则式质量检查
7. `docs(taxonomy): clarify memory_authority semantics and side effects` — S3 C1 消化
8. `test(agents): add integration coverage for all specialist/validator agents` — 集成测试

## 实现时间估算

| 任务 | 估算工时 |
|------|---------|
| S1 - 3 个包装型 Agent | 14h |
| S2 - 2 个新建 Agent | 16h |
| S3 - C1 消化 + resolve_executor 注册表 | 6h |
| 测试与集成 | 12h |
| 文档更新 | 4h |
| **总计** | **52h** |
