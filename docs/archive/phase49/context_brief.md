---
author: gemini
phase: 49
slice: kickoff
status: draft
depends_on:
  - docs/roadmap.md
  - docs/plans/phase48/closeout.md
---

## TL;DR
Phase 49 旨在实现知识真值的 SSOT 归一与向量 RAG。核心任务是将 `Evidence Store` 和 `Wiki Store` 从文件系统迁移至 SQLite，落地 `Librarian Agent`，并集成 `sqlite-vec` 提供本地向量检索能力，同时确保环境退级鲁棒性。

# Context Brief: Phase 49 - Knowledge SSOT & Vector RAG

## 变更范围

本 Phase 将对系统的知识层和持久化层进行深度改造，主要影响以下核心组件：

- **知识持久化 (`knowledge_store.py`, `store.py`)**：需要扩展 `SqliteTaskStore` 以支持 `Evidence` 和 `Wiki` 对象的存储，并实现文件系统到 SQLite 的迁移逻辑。
- **知识对象 (`models.py`)**：更新知识对象在 SQLite 中的 Schema 定义，确保事务性和可查询性。
- **知识管理 (`librarian_executor.py`)**：实现 `Librarian Agent` 的实体，包括知识冲突检测、去重、SQLite 写入边界和变更日志。
- **检索 (`retrieval.py`, `retrieval_adapters.py`, `knowledge_index.py`)**：集成 `sqlite-vec`，实现向量索引的构建、更新与查询逻辑。需要设计适配器以支持向量检索和平滑退级到文本匹配。
- **CLI 工具 (`cli.py`)**：可能需要新增命令以触发知识迁移或 `Librarian Agent` 的操作。

## 近期变更摘要 (Git History)

- `docs(sync): sync states and add move to v0.6.0 era` (Recent) - `main` 分支已并入 Phase 48 成果，系统进入 `v0.6.0` (Async Era)。
- `merge: RAG & Knowledge Closure` (Recent) - 这个提交信息似乎有误，Phase 49 尚未开始，需要进一步确认此提交。
- `docs(phase48): close out and PR ready` (Phase 48) - Phase 48 收口，系统具备全异步化与 SQLite 任务真值层。
- `fix(test): runtime guard async to normal test case` (Phase 48) - 测试基础设施适配异步运行时。
- `docs(phase48): sync review followup status` (Phase 48) - 同步 Phase 48 的 review 状态。

## 关键上下文

1.  **“双重真相”风险**：Phase 48 引入的 File Mirroring 机制，虽然保证了任务状态迁移的平滑，但也留下了知识层“文件 + 数据库”双重真值的隐患。Phase 49 必须彻底解决此问题，以 SQLite 作为唯一的知识真值来源，文件系统仅作为导出视图。
2.  **`Librarian Agent` 的职责边界**：`Librarian Agent` 是首个专项智能体，其权限范围（特别是 `Staged-Knowledge` 写入）必须严格控制，确保其作为知识守门人，而非随意写入者。
3.  **`sqlite-vec` 依赖与鲁棒性**：`sqlite-vec` 可能会引入新的二进制依赖。设计时必须强制包含“向量 -> 文本模糊匹配”的自动降级机制，以应对不同环境下的部署挑战，避免 RAG 功能完全失效。
4.  **异步化兼容**：Phase 48 已完成核心链路异步化。Phase 49 的知识层迁移和向量检索必须无缝集成到现有的 `asyncio` 运行时中。

## 风险信号

1.  **数据迁移复杂性**：将现有文件系统中的 `Evidence` 和 `Wiki` 知识迁移到 SQLite 需要考虑数据结构转换、幂等性以及潜在的数据丢失风险。
2.  **`sqlite-vec` 稳定性与性能**：`sqlite-vec` 作为一个相对新的扩展，其在大规模知识对象下的性能和稳定性需要验证。选择合适的 embedding 模型也至关重要。
3.  **`Librarian Agent` 边界溢出**：若 `Librarian Agent` 的写入权限失控，可能导致知识库被污染。需要严格定义其校验和写入流程。
4.  **测试复杂度**：知识迁移、`Librarian Agent` 行为和向量检索的集成测试将非常复杂，需要充分覆盖各种场景和边界条件。

## 建议关注点

- **数据模型设计**：在 `models.py` 中为 `Evidence` 和 `Wiki` 知识对象设计 SQLite Schema 时，要充分考虑未来的向量存储和语义查询需求，避免后期再次重构。
- **`Librarian Agent` 工作流**：明确 `Librarian Agent` 的触发时机（例如任务完成时、周期性扫描），以及其产出物（知识冲突报告、晋升提案）的 Schema。
- **迁移工具**：开发一个健壮的 `swl knowledge migrate` 命令，支持 dry-run 模式和断点续传。
- **RAG Pipeline**：设计灵活的 RAG Pipeline，允许在无法使用向量检索时，自动回退到基于文本的模糊匹配策略。
