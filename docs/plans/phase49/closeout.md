---
author: codex
phase: 49
slice: closeout
status: final
depends_on:
  - docs/plans/phase49/kickoff.md
  - docs/plans/phase49/design_decision.md
  - docs/plans/phase49/risk_assessment.md
  - docs/plans/phase49/review_comments.md
  - docs/plans/phase49/commit_summary.md
  - docs/active_context.md
---

## TL;DR
Phase 49 的四个实现 slice、Claude review 与 closeout 已全部完成，Human 已将分支合并到 `main` 并打出 `v0.7.0`。本轮正式把系统推进到 **Knowledge Era**：知识层 SQLite SSOT、幂等迁移、`LibrarianAgent` 边界与 `sqlite-vec` 可退级检索现已成为稳定基线。

# Phase 49 Closeout

## 结论

Phase 49 `Knowledge SSOT & Vector RAG` 已完成实现、验证、review、merge 与 tag，对外稳定 checkpoint 为 `v0.7.0`。

本轮围绕 kickoff 的三个核心目标完成了知识层的收口：

- knowledge truth 主线：知识读取切换到 SQLite primary，文件系统退化为 mirror / fallback 视图
- knowledge governance 主线：`LibrarianAgent` 接管 canonical 写入边界与结构化 change log
- retrieval 主线：`sqlite-vec` 可选向量检索 + 文本自动降级 + 本地 embedding 质量基线

当前 branch / main 的 Phase 49 提交序列如下：

- `a902a7e` `docs(phase49):initialize phase49`
- `1bc523b` `feat(knowledge): add sqlite-backed knowledge store`
- `08cc7cf` `feat(knowledge): add sqlite knowledge migration`
- `4c0364d` `feat(knowledge): introduce librarian agent boundary`
- `ca3ea43` `feat(retrieval): add sqlite-vec fallback pipeline`
- `dce4d7a` `docs(phase49):close out and review confirm`
- `3323c4b` `merge: Knowledge SSOT & Vector RAG`

## 最终解释修订（post-closeout clarification）

Phase 49 的实现完成后，系统对“知识双层架构”的最终解释应明确修订为：

- **Knowledge Truth Layer**：以 SQLite-backed Evidence / Wiki / canonical records 为 authoritative state
- **Retrieval & Serving Layer**：围绕这些已治理知识对象提供 exact retrieval、policy filtering、vector recall 与 text fallback

也就是说，Phase 49 不应被理解为“先做向量 RAG，再叠一个 Wiki 层”，而应被理解为：

> **先把知识归一为受治理的 truth objects，再把向量检索作为 retrieval augmentation 接入。**

因此，本轮中 `sqlite-vec` 的正确定位是：

- retrieval 侧可选增强能力
- 不是知识主真值
- 不是系统默认入口
- 不取代 canonical / staged / evidence / wiki 等知识对象治理边界

这一定义用于约束后续 phase，避免系统被重新拉回 vector-first 的旧叙事。

## 与 kickoff 完成条件对照

### 已完成

- `swl knowledge migrate --dry-run` 可列出待迁移对象，不写入 SQLite。
- `swl knowledge migrate` 实迁后，`swl doctor` / `swl doctor sqlite` 已补齐知识层健康检查。
- `LibrarianAgent` 已可被 orchestrator 触发，并产出结构化 `KnowledgeChangeLog`。
- `sqlite-vec` 可用时走向量检索，不可用时自动降级到文本匹配并输出 WARN。
- 非 eval 全量 pytest 已通过：`395 passed, 8 deselected, 5 subtests passed`。
- S4 eval 基线已通过：`1 passed`，precision / recall 达到设计阈值。
- 文件系统已不再作为知识读取主路径；当前为 SQLite primary + file fallback。
- 迁移工具幂等，重复执行不会产生重复知识记录。

### 已完成的 tag 对齐

- `README.md` / `README.zh-CN.md` / `AGENTS.md` 已切换到 `v0.7.0`。
- `current_state.md` 已切换到 `v0.7.0` 稳定 checkpoint，并把默认继续方向切到 Phase 50 kickoff 前状态。

## 已完成范围

### S1: Knowledge SQLite Schema & Store Extension

- 新增 `knowledge_evidence` / `knowledge_wiki` SQLite schema 与 CRUD。
- `embedding_blob` 预留列已在 schema 中落地，为后续向量索引扩展留出空间。
- `knowledge_store.py` 与 `store.py` 已切换为 sqlite-primary 读取语义。

### S2: Knowledge Migration Tool

- 新增 `swl knowledge migrate`，支持 dry-run / 实迁 / 幂等回填。
- 落地 `knowledge_migrations` 元数据表。
- `doctor sqlite` 补齐知识层 schema / 数量 / file-only task 诊断项。

### S3: Librarian Agent Entity

- `LibrarianExecutor` 升级为 `LibrarianAgent` 主体，兼容入口保留。
- canonical knowledge 写入边界在 SQLite 写入入口强制执行。
- `KnowledgeChangeLog` / `KnowledgeChangeEntry` 结构化字段已补齐。

### S4: sqlite-vec RAG Pipeline

- 新增 `VectorRetrievalAdapter` 与 `TextFallbackAdapter`。
- `sqlite-vec` 作为可选依赖放入 `extras_require["vec"]`。
- 缺失 `sqlite-vec` 时通过 `VectorRetrievalUnavailable` 自动回退到文本检索。
- 新增本地 embedding 排序 helper 与 S4 eval 基线。

## Review 结论与 concern 处理

- Claude review 结论：`0 BLOCK / 2 CONCERN / 可以合并`

### Concern 状态

- C1（S3 authority 语义区分）— 已登记到 `docs/concerns_backlog.md`，计划在 Phase 50 将 CLI operator promote 改为 `OPERATOR_CANONICAL_WRITE_AUTHORITY`
- C2（S4 WARN 全局标志线程安全）— 已登记到 `docs/concerns_backlog.md`，计划在 Phase 51 多进程 worker 前改为线程安全事件机制

说明：

- 两个 concern 均不阻塞 merge
- 本轮未对实现追加 follow-up patch，最终合并版本与 review 通过版本一致

## 风险吸收情况

### 已吸收

- R1 知识双重真相风险：读取主路径已切换到 SQLite，文件仅作为过渡 mirror / fallback。
- R2 迁移完整性风险：dry-run、幂等回填、doctor 健康检查与 file-only 保留策略均已覆盖。
- R3 写入权限边界风险：canonical knowledge 写入 authority 已在 `SqliteTaskStore.replace_task_knowledge()` 入口强制执行。
- R4 二进制依赖风险：`sqlite-vec` 缺失时自动回退到文本检索，不中断主路径。
- R5 向量质量风险：S4 eval 已建立 precision / recall 基线，作为后续回归信号。

### 当前边界

- 本轮未引入远程 embedding API，也未改动自动 promotion 语义。
- `sqlite-vec` 当前只作为 retrieval 侧可选能力，并未把向量写入持久化提升为强制路径。
- Web 控制面未扩展知识管理 UI，仍保持 Phase 48 的只读边界。

## 测试结果

最终 review-closeout 参考基线：

```text
.venv/bin/python -m pytest -q -> 395 passed, 8 deselected, 5 subtests passed
.venv/bin/python -m pytest tests/eval/test_vector_retrieval_eval.py -q -m eval -> 1 passed
```

## 规则文件同步检查

### 必查

- [x] `docs/plans/phase49/kickoff.md`
- [x] `docs/plans/phase49/design_decision.md`
- [x] `docs/plans/phase49/risk_assessment.md`
- [x] `docs/plans/phase49/review_comments.md`
- [x] `docs/plans/phase49/commit_summary.md`
- [x] `docs/plans/phase49/closeout.md`
- [x] `docs/active_context.md`

### merge/tag 后已更新

- [x] `docs/concerns_backlog.md`
- [x] `pr.md`
- [x] `current_state.md`
- [x] `AGENTS.md`
- [x] `README.md`
- [x] `README.zh-CN.md`

## Post-Merge 状态

1. Human 已完成 `feat/phase49-knowledge-ssot` → `main` 的 merge。
2. Human 已完成 `v0.7.0` tag。
3. Codex 已按 tag 同步 `current_state.md`、`AGENTS.md`、`README.md` 与 `README.zh-CN.md`。
4. 下一步应转入 Phase 50 kickoff，而不是继续扩张 Phase 49 的知识收口范围。

## 下一轮建议

Phase 49 收口完成后，可按 review concern 与 roadmap 顺序继续：

- Phase 50：消化 `LibrarianAgent` authority 语义 concern，并推进知识治理后续能力
- Phase 51：在更强并发/worker 场景下收紧 retrieval fallback 的线程安全实现
