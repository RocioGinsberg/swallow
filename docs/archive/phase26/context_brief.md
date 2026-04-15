---
author: gemini
phase: 26
track: Retrieval / Memory
slice: Canonical Knowledge Deduplication & Merge Gate
---

# Phase 26 Context Brief

## 1. 当前目标 (The Goal)

本阶段属于 `Retrieval / Memory` track，Slice 为 `Canonical Knowledge Deduplication & Merge Gate`。

**核心目标**：为 Canonical Registry 的写入（特别是 `stage-promote` 触发的晋升流程）引入去重（Deduplication）与冲突/版本控制机制，彻底解决 Phase 24 遗留的“盲目 Append 导致脏数据污染”的架构隐患。

## 2. 系统现状 (The Starting Point)

在 Phase 24 中，系统成功构建了 Staged Knowledge 缓冲区。操作员可通过 CLI (`swl knowledge stage-promote <id>`) 将受限知识晋升至 Canonical 注册表。随后在 Phase 25，系统加强了 Capability 的最小权限隔离。

**存在的缺陷**：正如 `docs/concerns_backlog.md` 记录，当前 `cli.py` 和 `canonical_registry.py` 的 promote 逻辑仅仅是简单地构建 `canonical record` 并**直接追加 (append) 到 registry 文件中**。
*   没有任何读取与比对检查 (Read-before-write check)。
*   相同的 `candidate_id` 甚至能被重复 promote 多次。
*   同一源（如相同的 artifact 或 task object）更新后的知识晋升，会产生两条平行的、相互冲突的 Active 记录。

这会导致 RAG 检索池被高度冗余且自相矛盾的事实填满。

## 3. 设计上下文与约束 (Design Context & Constraints)

在处理此问题时，后续的设计（由 Claude 负责）必须遵循以下边界：

*   **去重标识 (Deduplication Key)**：
    *   在 `src/swallow/canonical_registry.py` 中，实际上已经预埋了两个关键属性：`canonical_id` (全局主键) 和 `canonical_key` (用于标识同一信息源，例如 `task-object:<id>` 或 `artifact:<ref>`)。
    *   Dedupe 逻辑应该基于这些标识来工作。
*   **覆盖与版本策略 (Supersede Policy)**：
    *   作为 Truth Layer，`registry.jsonl` 通常是 Append-only 日志，**不建议物理删除历史记录**。
    *   应该引入**“显式覆盖 (Supersede)”语义**：如果新晋升的记录与现存记录的 `canonical_key` 相同，应将旧记录的 `canonical_status` 标记为 `superseded`，并指向新的 `superseded_by: <new_id>`，而新记录正常 appended。
*   **非目标 (Non-Goals)**：
    *   **不引入** 大模型或向量化驱动的“语义相似度融合 (Semantic Merge/Conflict Resolution)”。
    *   **不引入** 跨文件文本的自动拼接合并。一切冲突拦截和覆盖基于精确的 Metadata Identifier (`canonical_id` / `canonical_key`) 和显式操作。

## 4. 关键代码入口 (Key Pointers)

*   **执行入口**: `src/swallow/cli.py` 中的 `knowledge_command == "stage-promote"` 分支（重点查看调用 `append_canonical_record` 之前缺少了什么）。
*   **记录生成**: `src/swallow/canonical_registry.py` (包含 `CANONICAL_REGISTRY_SUPERSEDE_KEY` 的常数预埋以及 `build_canonical_record`)。
*   **存储层**: `src/swallow/store.py`（需要提供支持读取/重写/追加整个 registry 并更新状态的方法，而不仅是 blind append）。
*   **关注点**: `docs/concerns_backlog.md` 需要在此阶段收口。

## 5. Handoff to Claude

请 Claude 接收此上下文，并产出 `docs/plans/phase26/design_decision.md` 与 `docs/plans/phase26/breakdown.md`。

请重点在设计中回答与拆解：
1.  **Dedupe 机制设计**：明确在 `stage-promote` 写入前，如何识别“重复晋升”（相同的 `canonical_id`）和“知识更新”（相同的 `canonical_key`）。
2.  **写盘与 Supersede 逻辑**：明确系统将如何更新旧记录的状态（如通过读取全部记录，修改状态后重新写回，或者仅仅追加覆盖记录并靠加载时 resolve？推荐结合现有 `jsonl` 的解析特征）。
3.  **CLI 行为对齐**：操作员尝试晋升重复的 `candidate_id` 时，系统应当如何返回（报错阻断？提示幂等？）。
4.  提供具体的代码重构步骤和测试验收标准。