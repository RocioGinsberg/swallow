---
author: claude
phase: 49
slice: review
status: draft
depends_on:
  - docs/plans/phase49/design_decision.md
  - docs/plans/phase49/risk_assessment.md
  - docs/plans/phase49/commit_summary.md
---

## TL;DR
Phase 49 实现与设计文档高度一致，四个 slice 均在 scope 内完成。写入边界、降级路径、幂等迁移三个高风险点均有实质性保障。发现 2 个 CONCERN，无 BLOCK。

# Review Comments: Phase 49 - 知识真值归一与向量 RAG

## 总体评估

- 测试：395 passed，8 deselected，5 subtests passed；eval 1 passed（precision/recall 基线达标）
- Scope：未发现越出 kickoff.md goals 的改动
- 架构一致性：与 `design_decision.md` 的四 slice 拆解完全对应

---

## S1: Knowledge SQLite Schema & Store Extension

- [PASS] `SqliteTaskStore` 新增 `knowledge_evidence` / `knowledge_wiki` 两张表，schema 预留了 `embedding_blob BLOB` 列，满足 S4 向量存储需求，无需后续 ALTER TABLE。
- [PASS] `knowledge_store.py` 的 `_sqlite_knowledge_enabled()` 通过 `SWALLOW_STORE_BACKEND` 环境变量控制，保留了 file-only 降级路径，部署灵活性良好。
- [PASS] `persist_task_knowledge_view` 在 SQLite 写入后仍可选 `mirror_files=True` 保留文件镜像，过渡期兼容性有保障。
- [PASS] 新增 pytest 覆盖 CRUD 与事务边界，现有 380+ tests 全部通过。

---

## S2: Knowledge Migration Tool

- [PASS] `swl knowledge migrate` 支持 `--dry-run`，实迁与 dry-run 路径分离清晰。
- [PASS] 迁移元数据表落地于 `sqlite_store.py`，幂等检查基于 task_id + object_id，不依赖内容 hash，逻辑稳定。
- [PASS] `swl doctor sqlite` 新增 `knowledge_schema_ok`、`knowledge_evidence_count`、`knowledge_wiki_count`、`file_only_knowledge_task_count` 等健康项，迁移后可量化验证。
- [PASS] 原始文件系统数据不被删除，迁移工具只读文件。

---

## S3: Librarian Agent Entity

- [PASS] `LibrarianAgent` 作为独立类落地，`LibrarianExecutor` 保留为兼容封装（`class LibrarianExecutor(LibrarianAgent)`），orchestrator 触发接口无破坏性变更。
- [PASS] `KnowledgeChangeLog` / `KnowledgeChangeEntry` 结构化 dataclass 落地，包含 action / source / timestamp / canonical_key / before_text / after_text，字段完整。
- [PASS] 写入边界通过 `enforce_canonical_knowledge_write_authority` 在 `SqliteTaskStore.replace_task_knowledge` 入口强制执行，非授权 authority 抛出 `PermissionError`，不是软警告。
- [PASS] `CANONICAL_KNOWLEDGE_WRITE_AUTHORITIES` 集合明确列出所有合法 authority（`librarian-agent`、`knowledge-migration`、`operator-gated`、`canonical-promotion`、`test-fixture`），边界清晰。
- [PASS] orchestrator 的 `_apply_librarian_side_effects` 接管全部持久化，`LibrarianAgent.execute` 只返回结构化 payload，符合 Phase 48 确立的 side-effect 收口模式。
- [CONCERN] `cli.py:2087` 的 `stage-promote` 命令使用 `LIBRARIAN_MEMORY_AUTHORITY`（值为 `"canonical-promotion"`）作为 `caller_authority`，而非 `LIBRARIAN_AGENT_WRITE_AUTHORITY`（值为 `"librarian-agent"`）。两个常量均在 `CANONICAL_KNOWLEDGE_WRITE_AUTHORITIES` 中，功能上不影响，但语义上 CLI operator 手动 promote 与 LibrarianAgent 自动 promote 使用了同一 authority 标识，未来审计时难以区分来源。建议 Phase 50 将 CLI operator promote 路径切换为 `OPERATOR_CANONICAL_WRITE_AUTHORITY`。

---

## S4: sqlite-vec RAG Pipeline

- [PASS] `VectorRetrievalAdapter._load_module()` 通过 `importlib.import_module` 捕获 `ImportError` 并抛出 `VectorRetrievalUnavailable`，`retrieval.py:373` 捕获该异常并自动切换到 `TextFallbackAdapter`，降级路径完整。
- [PASS] `SQLITE_VEC_FALLBACK_WARNING` 常量统一定义，降级日志可见，满足 design_decision 的 WARN 要求。
- [PASS] `_warn_sqlite_vec_fallback_once()` 通过模块级 `_sqlite_vec_warning_emitted` 全局标志避免日志刷屏，设计合理。
- [PASS] `build_local_embedding` 使用 blake2b hash + bigram 加权的本地向量化方案，无外部 API 依赖，满足 non-goal 约束。
- [PASS] `sqlite-vec` 作为 `extras_require["vec"]` 可选依赖，不污染默认安装。
- [PASS] eval 测试 `test_vector_retrieval_eval.py` 验证 precision ≥ 0.70 / recall ≥ 0.60，基线达标。
- [CONCERN] `_sqlite_vec_warning_emitted` 是模块级全局变量，在多线程或多进程场景下存在竞态（两个线程可能同时读到 `False` 并各自发出一次 WARN）。当前系统以 asyncio 单线程为主，实际影响极低，但若未来引入多进程 worker（Phase 51 方向），需要改为线程安全的 `threading.Event` 或 `asyncio.Event`。建议登记到 concerns_backlog，Phase 51 前消化。

---

## Scope 检查（phase-guard）

- [PASS] 未发现越出 kickoff.md goals 的改动。
- [PASS] 未触及 non-goals：无远程 embedding API 调用、无自动 knowledge promotion、无 Web UI 扩展、无多租户逻辑。
- [PASS] Slice 数量为 4，符合 ≤5 的规则。
- [PASS] orchestrator 改动（36 行新增）仅限于 LibrarianAgent side-effect 接入与 write_authority 传递，未引入新拓扑。

---

## 验收条件对照

| 验收条件 | 状态 |
|---------|------|
| `swl knowledge migrate --dry-run` 可列出待迁移对象 | ✅ |
| `swl knowledge migrate` 后 `swl doctor` 含知识层健康检查 | ✅ |
| `LibrarianAgent` 可被 orchestrator 触发，产出 `KnowledgeChangeLog` | ✅ |
| 向量检索 sqlite-vec 可用时正常工作 | ✅ |
| sqlite-vec 不可用时自动降级，不抛未处理异常 | ✅ |
| 所有现有 pytest 通过（395 passed） | ✅ |
| 文件系统不再作为知识读取主路径 | ✅（SQLite primary，file fallback） |
| 迁移工具幂等 | ✅ |

---

## 结论

**可以合并。** 两个 CONCERN 均不阻塞 merge，已登记到 concerns_backlog 待后续消化。

## Branch Advice

- 当前分支: `feat/phase49-knowledge-ssot`
- 建议操作: 开 PR → merge 到 `main`
- 理由: 四个 slice 全部完成，测试全绿，无 BLOCK
- 建议 PR 范围: 全部四个 slice 合并为单 PR（知识层改造是完整架构单元）
- Tag 建议: Phase 49 merge 后建议打 `v0.7.0` (Knowledge Era)，标志知识真值归一与向量检索能力正式闭环
