---
author: claude
phase: 55
slice: kickoff
status: draft
depends_on:
  - docs/roadmap.md
  - docs/design/KNOWLEDGE.md
  - docs/design/AGENT_TAXONOMY.md
  - src/swallow/retrieval.py
  - src/swallow/knowledge_store.py
  - src/swallow/sqlite_store.py
---

## TL;DR
Phase 55 打通"本地文件 → 知识入库 → 双链关系 → 图谱检索 → 任务执行"的完整闭环。核心交付：本地文件摄入适配器、`knowledge_relations` SQLite 表与双向遍历、检索管线 Stage 3（Relation Expansion）落地、端到端集成测试。TDD 先行，每个 slice 先写测试定义契约再实现。

# Phase 55 Kickoff: 知识图谱与本地 RAG

## 基本信息

| 字段 | 值 |
|------|-----|
| Phase | 55 |
| Primary Track | Knowledge / RAG |
| Secondary Track | Agent Taxonomy |
| 目标 tag | v1.1.0 (Knowledge Graph Era) |
| 前置 phase | Phase 54 (v1.0.0) |
| 开发方式 | TDD 先行 |

## 战略定位

Foundation Era（Phase 47-54）建立了完整的基础设施：异步底座、知识 SSOT、策略闭环、Agent 体系、并行编排。但系统的知识能力仍有一个关键缺口：**`KNOWLEDGE.md` 设计的 5 阶段检索管线中，Stage 3（Relation Expansion）完全未实现**，且摄入管线仅支持对话导出，不支持任意本地文件。

Phase 55 的使命是**从一个可展示的知识闭环出发**，让系统首次具备：
1. 从本地文件构建知识库的能力
2. 知识对象之间的双链关系（类 LLM wiki 图谱）
3. 基于关系图谱的检索增强

完成后，用户可以将本地 markdown/text 文件摄入系统，建立知识间的关联，并在任务执行时通过图谱检索获得更丰富的上下文。

## 当前知识架构现状

### 已就位

| 组件 | 状态 | 位置 |
|------|------|------|
| 双层架构（Evidence + Wiki） | ✅ 完整 | `knowledge_store.py` |
| 知识生命周期（raw → candidate → verified → canonical） | ✅ 完整 | `knowledge_objects.py` |
| SQLite 存储（`knowledge_evidence` + `knowledge_wiki` 表） | ✅ 完整 | `sqlite_store.py` |
| 检索 Stage 1/2（Exact Match + Metadata Filtering） | ✅ 完整 | `retrieval.py` |
| 检索 Stage 4（Vector Semantic Recall，sqlite-vec） | ✅ 完整 | `retrieval_adapters.py` |
| 检索 Stage 5（Text Fallback） | ✅ 完整 | `retrieval_adapters.py` |
| Staged Knowledge 候选与 Promotion 工作流 | ✅ 完整 | `staged_knowledge.py` + `canonical_registry.py` |
| IngestionSpecialistAgent | ✅ 完整 | `ingestion_specialist.py` |
| LiteratureSpecialistAgent | ✅ 完整 | `literature_specialist.py` |

### 缺口

| 缺口 | 蓝图来源 | 影响 |
|------|---------|------|
| **检索 Stage 3（Relation Expansion）** | `KNOWLEDGE.md` §2 检索管线 | 知识对象之间无关系，检索只能靠语义相似度 |
| **知识关系模型** | `KNOWLEDGE.md` "沿知识对象间关系扩展召回" | 无 `knowledge_relations` 表，无关系类型定义 |
| **本地文件摄入** | `INTERACTION.md` + `KNOWLEDGE.md` | `run_ingestion_pipeline()` 仅支持对话导出格式 |
| **WikiEntry 双向链接** | 当前仅有 `source_evidence_ids`（单向回链） | 无法从 evidence 正向遍历到相关 evidence/wiki |

## 目标 (Goals)

1. **本地文件摄入**：扩展 ingestion pipeline 支持任意 markdown/text 文件，新增 `swl knowledge ingest-file` CLI 命令，产出 staged candidates。
2. **双链关系模型**：新增 `knowledge_relations` SQLite 表，定义关系类型（`refines` / `contradicts` / `cites` / `extends` / `related_to`），支持双向遍历。
3. **检索管线 Stage 3**：在 metadata filtering 和 vector recall 之间插入 Relation Expansion——从匹配的知识对象出发，沿关系图谱扩展召回。
4. **端到端闭环**：本地文件 → 入库 → 建立关系 → 检索时关系扩展 → 任务执行引用图谱知识。

## 非目标 (Non-Goals)

- **不做 Graph RAG 的高级特性**：社区发现、图结构摘要、agentic retrieval 留待 Phase 56+。
- **不接入 LLM**：关系建立基于 operator 显式操作或启发式规则，不引入 LLM 自动推断关系。
- **不做 PDF 解析**：本 phase 仅支持 markdown 和纯文本文件。
- **不改动现有对话导出摄入路径**：`run_ingestion_pipeline()` 的对话解析逻辑不变。
- **不做跨 workspace 知识联邦**。

## Slice 拆解

### S1: 本地文件摄入

**目标**：让用户可以将任意 markdown/text 文件摄入知识库。

**TDD 契约**（先写测试）：
- `test_ingest_local_markdown_creates_staged_candidates`：摄入一个 markdown 文件，验证产出 staged candidates，每个 heading section 对应一个 candidate
- `test_ingest_local_text_creates_single_candidate`：摄入一个纯文本文件，验证产出单个 candidate
- `test_ingest_local_file_preserves_source_ref`：验证 candidate 的 `source_ref` 指向原始文件路径
- `test_ingest_local_file_dry_run_does_not_persist`：`--dry-run` 模式不写入
- `test_cli_knowledge_ingest_file_command`：CLI 命令 `swl knowledge ingest-file <path>` 可执行

**实现要点**：
- 新增 `parse_local_file(path) -> list[KnowledgeFragment]`，按 markdown heading 分段（纯文本不分段）
- 复用 `run_ingestion_pipeline()` 的 staged candidate 持久化逻辑
- CLI 新增 `swl knowledge ingest-file <path> [--dry-run] [--summary]`

**验收条件**：
- markdown 文件按 heading 分段为多个 staged candidates
- 纯文本文件产出单个 staged candidate
- `source_ref` 格式为 `file://<absolute_path>`
- `source_kind` 为 `local_file_capture`
- 全量 pytest 通过

### S2: 双链关系模型

**目标**：建立知识对象之间的双向关系，支持图谱遍历。

**TDD 契约**：
- `test_create_knowledge_relation_persists_to_sqlite`：创建关系后可从 SQLite 读回
- `test_relation_bidirectional_traversal`：从 source 可查到 target，从 target 可查到 source
- `test_relation_type_validation`：非法关系类型被拒绝
- `test_delete_relation`：删除关系后不再可查
- `test_list_relations_for_object`：列出某个知识对象的所有关系（入边 + 出边）
- `test_cli_knowledge_link_command`：CLI 命令 `swl knowledge link <source_id> <target_id> --type <type>` 可执行

**SQLite schema**：
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
CREATE INDEX idx_kr_source ON knowledge_relations(source_object_id);
CREATE INDEX idx_kr_target ON knowledge_relations(target_object_id);
CREATE INDEX idx_kr_type ON knowledge_relations(relation_type);
```

**关系类型**：
- `refines`：A 是 B 的更具体版本
- `contradicts`：A 与 B 冲突
- `cites`：A 引用 B 作为证据
- `extends`：A 在 B 基础上扩展
- `related_to`：语义相关但无强类型

**实现要点**：
- 新增 `knowledge_relations.py`：relation CRUD + 双向遍历函数
- `sqlite_store.py` 新增 `knowledge_relations` 表的 DDL
- CLI 新增 `swl knowledge link` / `swl knowledge unlink` / `swl knowledge links <object_id>`

**验收条件**：
- 关系可创建、查询、删除
- 双向遍历：`get_relations(object_id)` 返回入边和出边
- 关系类型受限于定义的 5 种
- 全量 pytest 通过

### S3: 检索管线 Stage 3（Relation Expansion）

**目标**：实现 `KNOWLEDGE.md` 设计的 Relation Expansion 阶段。

**TDD 契约**：
- `test_relation_expansion_includes_linked_objects`：检索命中 A，A 有 `cites` 关系到 B，B 出现在结果中
- `test_relation_expansion_respects_depth_limit`：深度限制为 2 时，A→B→C 可达，A→B→C→D 不可达
- `test_relation_expansion_applies_confidence_decay`：跳数越多，score 衰减越大
- `test_relation_expansion_does_not_duplicate`：A 同时被直接命中和关系扩展命中时，不重复
- `test_retrieve_context_integrates_relation_expansion`：`retrieve_context()` 的结果包含关系扩展的对象

**实现要点**：
- `retrieval.py` 新增 `expand_by_relations(seed_items, depth_limit=2, min_confidence=0.3) -> list[RetrievalItem]`
- 在 `retrieve_context()` 中，verified knowledge items 命中后、file-based retrieval 前，插入 relation expansion
- Score 衰减：每跳乘以 `0.6`（可配置）
- 去重：已在 seed 中的对象不重复加入

**验收条件**：
- 关系扩展的对象出现在 `retrieve_context()` 结果中
- metadata 标注 `expansion_source: relation`、`expansion_depth: N`、`expansion_relation_type: <type>`
- 深度限制和置信度阈值生效
- 全量 pytest 通过

### S4: 端到端闭环测试

**目标**：验证完整的知识闭环可展示。

**TDD 契约**：
- `test_end_to_end_local_file_to_retrieval`：
  1. 摄入两个本地 markdown 文件为 staged candidates
  2. Promote 为 verified knowledge
  3. 建立 `cites` 关系
  4. 创建任务，`retrieve_context()` 返回的结果包含直接命中 + 关系扩展的对象
  5. 任务执行时 `retrieval_items` 非空且包含图谱知识

**实现要点**：
- 这是一个集成测试，串联 S1-S3 的全部产出
- 使用 tempdir 隔离，不依赖外部状态

**验收条件**：
- 端到端测试通过
- 全量 pytest 通过

## 设计边界

- **关系是 operator 显式建立的**：本 phase 不做自动关系推断。用户通过 CLI 手动建立关系，或未来 phase 由 LLM 辅助推断。
- **关系表独立于 knowledge_evidence / knowledge_wiki**：关系是跨表的（evidence 之间、evidence 与 wiki 之间均可建立关系），不嵌入到 KnowledgeObject 字段中。
- **Relation Expansion 是检索增强，不是必须路径**：如果没有关系，检索管线退化为现有行为（Stage 1/2/4/5），不影响现有功能。
- **本地文件摄入不改动对话导出路径**：`run_ingestion_pipeline()` 的 `chatgpt_json` / `claude_json` / `open_webui_json` / `markdown`（对话格式）解析逻辑不变。新增的是 `parse_local_file()` 函数，走独立路径。

## 风险评估

| 风险 | 等级 | 缓解 |
|------|------|------|
| `knowledge_relations` 表 schema 设计不够用 | 低 | 最小 schema + 后续可加列，不做过度设计 |
| Relation Expansion 在大图谱上性能问题 | 低 | 深度限制（默认 2）+ 置信度阈值 + 本地知识库规模有限 |
| 本地文件分段策略不够好 | 低 | markdown 按 heading 分段是成熟模式，纯文本不分段 |
| 与现有检索管线的集成点 | 中 | S3 在 `retrieve_context()` 中插入，不改动现有 stage 逻辑 |

**Phase 55 整体风险评级：中**（新增 SQLite schema + 检索管线改造，但基础设施成熟，TDD 控制风险）

## 依赖与前置条件

- Phase 49 (v0.7.0)：知识层 SQLite SSOT、`sqlite-vec` 检索
- Phase 53 (v1.0.0)：IngestionSpecialistAgent、LiteratureSpecialistAgent
- `KNOWLEDGE.md` §2：5 阶段检索管线设计（Stage 3 为本 phase 目标）
