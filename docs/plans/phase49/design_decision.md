---
author: claude
phase: 49
slice: kickoff
status: draft
depends_on:
  - docs/plans/phase49/context_brief.md
  - docs/plans/phase49/kickoff.md
---

## TL;DR
Phase 49 分四个 slice 推进：先定义知识 SQLite Schema 并扩展 SqliteTaskStore，再实现幂等迁移工具，然后将 LibrarianExecutor 升级为具备独立生命周期的 LibrarianAgent，最后集成 sqlite-vec 向量检索并实现文本降级适配器。

# Design Decision: Phase 49 - 知识真值归一与向量 RAG

## 方案总述

Phase 49 的核心是将知识层从"文件 + 临时索引"的双轨制彻底切换到 SQLite 单一真值。实现路径分四步：首先在 `SqliteTaskStore`（`sqlite_store.py`）中扩展 Evidence/Wiki 的 Schema 与 CRUD 接口；其次提供 `swl knowledge migrate` 迁移工具完成历史数据幂等回填；第三步将现有 `LibrarianExecutor` 升级为具备独立生命周期和受控写入边界的 `LibrarianAgent` 实体；最后集成 `sqlite-vec` 向量检索，并强制实现文本模糊匹配降级路径，确保在无 `sqlite-vec` 环境下系统仍可正常运行。

---

## Slice 拆解

### Slice 1: Knowledge SQLite Schema & Store Extension

**目标**：在 `sqlite_store.py` 中扩展 `SqliteTaskStore`，支持 `Evidence` 和 `WikiEntry` 对象的事务性存储与查询；在 `models.py` 中确认或补充知识对象的 SQLite Schema 定义。

**影响范围**：
- `src/swallow/sqlite_store.py` — 新增 `evidence` / `wiki_entry` 表，CRUD 方法
- `src/swallow/models.py` — 确认 `Evidence` 类定义（如缺失则补充），确保 `KnowledgeObject` / `WikiEntry` 有完整 SQLite 映射
- `src/swallow/knowledge_store.py` — 更新 store 接口，指向 SQLite 实现

**风险评级**：
- 影响范围: 2（单模块，知识层）
- 可逆性: 2（Schema 变更需要迁移脚本）
- 依赖复杂度: 2（依赖内部 SqliteTaskStore）
- **总分: 6 — 中风险**

**验收条件**：
- `SqliteTaskStore` 可写入/读取/删除 `Evidence` 和 `WikiEntry` 对象
- 新增 pytest 覆盖 CRUD 操作与事务边界
- 现有 380+ tests 全部通过

---

### Slice 2: Knowledge Migration Tool

**目标**：实现 `swl knowledge migrate` CLI 命令，将文件系统中的现有知识对象幂等回填至 SQLite；支持 `--dry-run` 模式；迁移完成后文件系统数据保持只读（不删除原始文件）。

**影响范围**：
- `src/swallow/cli.py` — 新增 `knowledge migrate` 子命令
- `src/swallow/knowledge_store.py` — 迁移逻辑（读取文件 → 写入 SQLite，幂等检查）
- `src/swallow/sqlite_store.py` — 依赖 S1 的 CRUD 接口

**风险评级**：
- 影响范围: 3（跨模块，文件系统 + SQLite）
- 可逆性: 2（迁移可重跑，但需要额外工作验证）
- 依赖复杂度: 2（依赖内部模块）
- **总分: 7 — 高风险，建议人工 gate 验证迁移结果**

**验收条件**：
- `swl knowledge migrate --dry-run` 输出待迁移对象列表，不写入 SQLite
- `swl knowledge migrate` 实际迁移后，`swl doctor` 输出包含知识层 SQLite 健康检查
- 重复执行迁移命令不产生重复数据（幂等性）
- 原始文件系统数据不被删除或修改

---

### Slice 3: Librarian Agent Entity

**目标**：将现有 `LibrarianExecutor`（`librarian_executor.py:156`）升级为 `LibrarianAgent`，具备独立生命周期、受控 SQLite 写入边界、知识冲突检测与去重逻辑，产出结构化 `KnowledgeChangeLog`。

**影响范围**：
- `src/swallow/librarian_executor.py` — 升级为 `LibrarianAgent`，新增冲突检测、去重、变更日志
- `src/swallow/sqlite_store.py` — 依赖 S1 的写入接口
- orchestrator 触发入口 — 更新触发时机（任务完成时作为 side-effect）

**风险评级**：
- 影响范围: 3（跨模块，orchestrator + knowledge layer）
- 可逆性: 2（需要额外工作，但接口保持兼容）
- 依赖复杂度: 2（依赖内部模块）
- **总分: 7 — 高风险，写入权限边界必须严格，建议人工 gate**

**验收条件**：
- `LibrarianAgent` 可被 orchestrator 触发，执行知识冲突检测与去重
- 每次知识写入产出结构化 `KnowledgeChangeLog`（包含 action / source / timestamp）
- 写入边界校验：非 `LibrarianAgent` 路径不得直接写入 canonical knowledge SQLite 表
- 新增 pytest 覆盖冲突检测、去重、变更日志场景

---

### Slice 4: sqlite-vec RAG Pipeline

**目标**：集成 `sqlite-vec` 扩展，实现向量索引的构建、更新与查询；设计 `VectorRetrievalAdapter` 与 `TextFallbackAdapter`，在 `sqlite-vec` 不可用时自动降级到文本模糊匹配。

**影响范围**：
- `src/swallow/retrieval.py` — 新增向量检索路径
- `src/swallow/knowledge_index.py` — 扩展 `build_knowledge_index()` 支持向量索引
- `src/swallow/retrieval_adapters.py` — `VectorRetrievalAdapter` + `TextFallbackAdapter`（如文件不存在则新建）
- `pyproject.toml` — `sqlite-vec` 作为可选依赖（`extras_require["vec"]`）

**风险评级**：
- 影响范围: 2（单模块，retrieval layer）
- 可逆性: 2（需要额外工作）
- 依赖复杂度: 3（依赖外部系统，sqlite-vec 二进制扩展）
- **总分: 7 — 高风险，外部二进制依赖，降级机制是核心安全网**

**验收条件**：
- `sqlite-vec` 可用时，向量检索返回语义相关结果
- `sqlite-vec` 不可用时，系统自动降级到文本模糊匹配，不抛出未处理异常
- 降级行为在日志中可见（`[WARN] sqlite-vec unavailable, falling back to text search`）
- 新增 pytest 覆盖向量检索与降级路径（使用 mock 模拟 sqlite-vec 不可用场景）
- 新增 eval 测试覆盖向量检索质量基线（precision ≥ 0.7 / recall ≥ 0.6）

---

## 依赖说明

```
S1 (Schema) ──→ S2 (Migration)
S1 (Schema) ──→ S3 (Librarian Agent)
               S3 (Librarian Agent) ──→ S4 (RAG Pipeline)
```

S2 与 S3 可并行开发（均依赖 S1 完成）。S4 依赖 S3 完成，因为向量索引写入需经过 LibrarianAgent 的写入边界。

---

## 明确的非目标

- 不实现 embedding 模型的远程 API 调用（本地 embedding 或 TF-IDF 向量化）
- 不删除文件系统中的原始知识文件（迁移后保留为只读备份）
- 不修改现有 `swl knowledge stage-*` 命令的行为
- 不引入新的 orchestrator 拓扑（LibrarianAgent 作为 side-effect 触发，不改变主任务链路）
- 不实现知识版本历史（变更日志只记录最新操作，不做 full audit trail）
- 不做 Web UI 知识管理界面扩展

---

## Branch Advice

- 当前分支: `main`
- 建议操作: 新建分支（设计 gate 通过后）
- 理由: Phase 49 涉及知识层架构性改造，不应在 main 上直接开发
- 建议分支名: `feat/phase49-knowledge-ssot`
- 建议 PR 范围: S1 + S2 + S3 + S4 合并为单 PR（知识层改造是一个完整的架构单元）
