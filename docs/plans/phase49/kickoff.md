---
author: claude
phase: 49
slice: kickoff
status: draft
depends_on:
  - docs/plans/phase49/context_brief.md
  - docs/roadmap.md
---

## TL;DR
Phase 49 以"知识真值归一"为核心，将 Evidence/Wiki 知识层从文件系统全量迁移至 SQLite，落地 Librarian Agent 实体，并集成 sqlite-vec 向量检索（含文本降级保障）。本 phase 是 v0.7.0 (Knowledge Era) 的唯一前置。

# Phase 49 Kickoff: 知识真值归一与向量 RAG

## 基本信息

| 字段 | 值 |
|------|-----|
| Phase | 49 |
| Primary Track | Knowledge / RAG |
| Secondary Track | State / Truth |
| 目标 tag | v0.7.0 (Knowledge Era) |
| 前置 phase | Phase 48 (v0.6.0, Async Era) |

## 目标 (Goals)

1. **知识层 SSOT 归一**：将 `Evidence Store` / `Wiki Store` 全量迁移至 SQLite（扩展 `SqliteTaskStore`），废除文件系统作为知识真值，仅保留为可导出视图。
2. **Librarian Agent 实装**：将现有 `LibrarianExecutor` 升级为具备独立生命周期的专项智能体实体，接管知识冲突检测、去重与 SQLite 写入边界，产出结构化变更日志。
3. **向量 RAG 与平滑退级**：集成 `sqlite-vec` 提供本地向量检索能力，强制实现"向量 → 文本模糊匹配"自动降级机制，确保环境鲁棒性。
4. **迁移工具**：提供 `swl knowledge migrate` 命令，支持 dry-run 模式与幂等回填。

## 非目标 (Non-Goals)

- 不做 Meta-Optimizer 提案实装（Phase 50 范围）
- 不做 CLIAgentExecutor 全异步化（Phase 51 范围）
- 不做远程 embedding API 调用（本地优先，无外部 API 依赖）
- 不做自动 knowledge promotion（显式 gate 保持不变）
- 不做 Web UI 知识管理界面扩展
- 不做多租户或分布式知识存储
- 不删除文件系统中的原始知识文件（迁移后保留为只读备份）

## 设计边界

- SQLite 作为唯一知识真值来源，文件系统仅作导出视图
- `LibrarianExecutor` 升级为 `LibrarianAgent`，但不改变其外部触发接口（保持 orchestrator 兼容）
- `sqlite-vec` 为可选依赖，缺失时系统必须自动降级到文本模糊匹配，不得抛出未处理异常
- 所有知识写入路径必须经过 `LibrarianAgent` 的写入边界校验
- 迁移工具必须幂等，支持断点续传，不破坏现有文件系统数据（只读原始文件）

## Slice 列表

| Slice | 名称 | 顺序依赖 |
|-------|------|----------|
| S1 | Knowledge SQLite Schema & Store Extension | 无 |
| S2 | Knowledge Migration Tool | S1 |
| S3 | Librarian Agent Entity | S1 |
| S4 | sqlite-vec RAG Pipeline | S1, S3 |

S2 与 S3 可并行开发（均依赖 S1 完成）。S4 依赖 S3 完成（向量索引需经过 LibrarianAgent 写入边界）。

## 完成条件

- [ ] `swl knowledge migrate --dry-run` 可列出待迁移对象，不写入 SQLite
- [ ] `swl knowledge migrate` 实际迁移后，`swl doctor` 输出包含知识层 SQLite 健康检查
- [ ] `LibrarianAgent` 可被 orchestrator 触发，产出结构化 `KnowledgeChangeLog`
- [ ] 向量检索在 `sqlite-vec` 可用时正常工作，不可用时自动降级到文本匹配
- [ ] 所有现有 pytest 通过（380+ tests），新增知识层 SQLite 相关测试
- [ ] 文件系统不再作为知识读取的主路径（所有读取路径指向 SQLite）
- [ ] 迁移工具幂等：重复执行不产生重复数据
