---
author: claude
phase: 55
slice: design
status: draft
depends_on:
  - docs/plans/phase55/kickoff.md
  - docs/design/KNOWLEDGE.md
  - src/swallow/sqlite_store.py
  - src/swallow/retrieval.py
  - src/swallow/knowledge_store.py
---

## TL;DR

Phase 55 有 4 个核心设计决策：(1) 本地文件摄入走独立函数而非扩展 `run_ingestion_pipeline()`；(2) 关系表独立于 knowledge_evidence/wiki，用 object_id 而非 task_id+object_id 作为外键；(3) Relation Expansion 插入 `retrieve_context()` 的 verified knowledge 之后、file-based retrieval 之前；(4) 关系由 operator 显式建立，不做自动推断。

---

## 核心设计决策

### 决策 1：本地文件摄入路径

**问题**：本地文件摄入是扩展 `run_ingestion_pipeline()` 还是新建独立函数？

**候选方案**：
- A. 扩展 `run_ingestion_pipeline()`，新增 `format_hint="local_file"`
- B. 新建 `ingest_local_file(path) -> list[StagedCandidate]`，独立于对话摄入
- C. 通过 IngestionSpecialistAgent 统一入口

**选择方案**：B（独立函数）

**理由**：
- `run_ingestion_pipeline()` 的核心逻辑是对话解析（turns → fragments → candidates），本地文件不是对话，强行塞入会污染语义
- A 需要在 pipeline 内部做大量 `if format == "local_file"` 分支，增加复杂度
- C 需要构造 TaskState / TaskCard，对 CLI 直接调用场景过重
- B 最简洁：`ingest_local_file()` 读文件 → 分段 → 产出 StagedCandidate 列表，复用 `persist_staged_candidates()` 持久化

**实现**：

```python
# ingestion/local_file.py

def parse_local_file(path: Path) -> list[dict[str, str]]:
    """Parse a local markdown/text file into knowledge fragments."""
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".md":
        return _split_by_headings(text, source_path=path)
    return [{"title": path.name, "text": text, "source_path": str(path)}]

def ingest_local_file(
    base_dir: Path,
    source_path: Path,
    *,
    dry_run: bool = False,
) -> list[StagedCandidate]:
    """Ingest a local file into staged knowledge candidates."""
    fragments = parse_local_file(source_path)
    candidates = [
        build_staged_candidate(
            text=frag["text"],
            source_kind="local_file_capture",
            source_ref=f"file://{source_path.resolve()}",
            # ...
        )
        for frag in fragments
        if frag["text"].strip()
    ]
    if not dry_run:
        persist_staged_candidates(base_dir, candidates)
    return candidates
```

CLI 入口：`swl knowledge ingest-file <path> [--dry-run] [--summary]`

---

### 决策 2：关系表设计

**问题**：`knowledge_relations` 表的外键应该是 `(task_id, object_id)` 还是单独的 `object_id`？

**候选方案**：
- A. 复合外键 `(task_id, object_id)`，与 `knowledge_evidence` 表对齐
- B. 单独 `object_id`，不绑定 task_id
- C. 引入全局唯一的 `knowledge_node_id`，关系表引用 node_id

**选择方案**：B（单独 object_id）

**理由**：
- 关系是跨 task 的——一个 task 的 evidence 可以 `cites` 另一个 task 的 evidence
- A 的复合外键会让跨 task 关系的查询变复杂（需要同时知道 source_task_id 和 target_task_id）
- C 引入额外的间接层，过度设计
- B 最简洁：`object_id` 在当前系统中已经是 `knowledge-{uuid}` 格式，全局唯一

**schema**：

```sql
CREATE TABLE knowledge_relations (
    relation_id TEXT PRIMARY KEY,
    source_object_id TEXT NOT NULL,
    target_object_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    context TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    created_by TEXT DEFAULT 'operator'
);
```

不加 FOREIGN KEY 约束（object_id 可能在 evidence 或 wiki 表中，跨表外键在 SQLite 中不实用）。通过应用层验证 object_id 存在性。

---

### 决策 3：Relation Expansion 在检索管线中的插入点

**问题**：Relation Expansion 应该在检索管线的哪个位置执行？

**候选方案**：
- A. 在 verified knowledge items 之后、canonical reuse items 之前
- B. 在所有 knowledge items（verified + canonical）收集完毕后、file-based retrieval 之前
- C. 作为独立的后处理步骤，在所有 retrieval 完成后执行

**选择方案**：B（knowledge items 收集完毕后）

**理由**：
- A 会导致 canonical reuse items 无法作为 expansion seed（canonical 对象也可能有关系）
- C 会对 file-based retrieval 的结果也做 expansion，但文件不在关系图谱中，无意义
- B 最合理：先收集所有 knowledge items（verified + canonical），然后从这些 seed 出发做 relation expansion，最后再做 file-based retrieval

**实现**：

```python
# retrieval.py — retrieve_context() 中的插入点

# Stage 1-2: Verified knowledge items
verified_items = list(iter_verified_knowledge_items(...))

# Stage 1-2: Canonical reuse items
canonical_items = list(iter_canonical_reuse_items(...))

# Stage 3: Relation Expansion (NEW)
seed_items = verified_items + canonical_items
expanded_items = expand_by_relations(
    seed_items,
    depth_limit=2,
    min_confidence=0.3,
    decay_factor=0.6,
)

# Stage 4-5: File-based retrieval (unchanged)
file_items = list(iter_file_retrieval_items(...))

# Merge and rank
all_items = seed_items + expanded_items + file_items
```

---

### 决策 4：关系建立方式

**问题**：知识对象之间的关系由谁建立？

**候选方案**：
- A. Operator 通过 CLI 手动建立
- B. LLM 自动推断（摄入时或 promote 时）
- C. 启发式规则（共享关键词、同 task 来源等）
- D. A + C 混合

**选择方案**：A（Operator 手动）

**理由**：
- B 需要 LLM 调用，违反 Phase 55 "不引入新 LLM 调用"的设计边界
- C 的启发式规则容易产生噪声关系，降低图谱质量
- D 增加复杂度，且启发式部分的价值不确定
- A 最简洁：operator 通过 `swl knowledge link` 显式建立关系，关系质量有保证
- 后续 Phase 56 可接入 LLM 辅助推断，但 Phase 55 先建立基础设施

**CLI 接口**：

```bash
# 建立关系
swl knowledge link <source_id> <target_id> --type cites [--confidence 0.9] [--context "A引用了B的结论"]

# 查看关系
swl knowledge links <object_id>

# 删除关系
swl knowledge unlink <relation_id>
```

---

## 与蓝图的对齐

| 蓝图要点 | Phase 55 实现 | 对齐度 |
|---------|-------------|--------|
| **KNOWLEDGE.md §2 Stage 3 Relation Expansion** | `expand_by_relations()` + `retrieve_context()` 集成 | ✅ 完全对齐 |
| **KNOWLEDGE.md "沿知识对象间关系扩展召回"** | BFS 遍历 + 深度限制 + 置信度衰减 | ✅ 完全对齐 |
| **KNOWLEDGE.md 远期方向 Graph RAG** | 双链关系模型为 Graph RAG 基础设施 | ⚠️ 最小实现，社区发现/图摘要留后续 |
| **INTERACTION.md 本地文件摄入** | `swl knowledge ingest-file` CLI 命令 | ✅ 完全对齐 |

---

## 验收条件

| Slice | 验收条件 |
|-------|---------|
| **S1** | ✓ markdown 按 heading 分段为 staged candidates ✓ 纯文本产出单个 candidate ✓ `source_ref` 为 `file://` 格式 ✓ CLI 命令可执行 ✓ dry-run 不持久化 |
| **S2** | ✓ 关系可创建/查询/删除 ✓ 双向遍历 ✓ 关系类型受限 5 种 ✓ CLI link/unlink/links 命令可执行 |
| **S3** | ✓ `retrieve_context()` 结果包含关系扩展对象 ✓ 深度限制生效 ✓ 置信度衰减生效 ✓ 不重复 ✓ metadata 标注 expansion 来源 |
| **S4** | ✓ 端到端集成测试通过 ✓ 全量 pytest 通过 |

---

## 提交序列建议

1. `feat(knowledge): add local file ingestion with markdown section splitting` — S1
2. `test(knowledge): add local file ingestion TDD tests` — S1 测试
3. `feat(knowledge): add knowledge_relations SQLite table and CRUD` — S2
4. `test(knowledge): add relation model TDD tests` — S2 测试
5. `feat(retrieval): implement relation expansion stage in retrieve_context` — S3
6. `test(retrieval): add relation expansion TDD tests` — S3 测试
7. `test(knowledge): add end-to-end knowledge graph RAG integration test` — S4

## 实现时间估算

| 任务 | 估算工时 |
|------|---------|
| S1 - 本地文件摄入 + CLI + 测试 | 10h |
| S2 - 关系模型 + SQLite + CLI + 测试 | 12h |
| S3 - Relation Expansion + 检索集成 + 测试 | 14h |
| S4 - 端到端集成测试 | 4h |
| **总计** | **40h** |
