---
author: codex
phase: 32
slice: knowledge-dual-layer
status: final
depends_on:
  - docs/plans/phase32/kickoff.md
  - docs/plans/phase32/review_comments.md
---

## TL;DR
Phase 32 已完成实现、测试与 review 收口，当前状态为 **PR ready / Merge ready**。本轮把 task knowledge 从单层扁平结构收敛为 `Evidence Store + Wiki Store` 双层模型，并引入 `LibrarianExecutor` 作为 canonical promotion 的唯一规则驱动写回入口；全量回归结果为 `225 passed in 5.89s`。

# Phase 32 Closeout

## 结论

Phase 32 `知识双层架构 + Librarian Agent (写回防线)` 已完成实现、测试与 review 收口准备，当前状态为 **PR ready / Merge ready**。

本轮围绕 kickoff 的 3 个 slice，建立了一个明确的知识写回防线：

- `Evidence Store / Wiki Store`：把原始证据层与 canonical 认知层物理分离
- `caller_authority` 校验：把 canonical promotion 收敛到 `canonical-promotion`
- `LibrarianExecutor`：把 canonical 晋升流程约束为规则驱动的提纯、审计和写回

Claude review 结论为 **0 BLOCK / 0 CONCERN / 1 NOTE / Merge ready**。

## 已完成范围

### Slice 1: Evidence / Wiki 双层存储

- 新增 `knowledge_store.py`，建立 merged view 兼容层
- `save_knowledge_objects()` 现在会同步写入 Evidence Store、Wiki Store 和 legacy `knowledge_objects.json`
- `KnowledgeObject` 增加 `store_type`，新增 `WikiEntry`
- CLI 的 `intake` / `inspect` / `review` / `knowledge-review-queue` / `knowledge-objects-json` 已切到 merged view
- `knowledge stage-promote` 会同步写入 Wiki Store

对应 commit：

- `11aba11` `feat(phase32): add dual-layer knowledge store`
- `0d47845` `docs(phase32): sync s1 progress`

### Slice 2: 权限校验 + Librarian 角色

- `knowledge_review.py::apply_knowledge_decision()` 新增 `caller_authority`
- canonical promotion 现在强制要求 `caller_authority == "canonical-promotion"`
- `models.py` 增加 Librarian taxonomy 常量和 `build_librarian_taxonomy_profile()`
- `orchestrator.py::decide_task_knowledge()` 在未授权晋升时记录 `knowledge.promotion.unauthorized`
- CLI 的 `task knowledge-promote` 以 Librarian authority 执行 canonical promotion

对应 commit：

- `5824659` `feat(phase32): enforce librarian promotion authority`

补充说明：

- `295529b` `docs&feat(phase32):sync omitted changes` 补齐了本轮实现过程中遗漏的代码/状态同步内容，并已纳入当前 branch 历史

### Slice 3: LibrarianExecutor + 流程集成

- 新增 `librarian_executor.py`，实现规则驱动的 canonical promotion 执行器
- `planner.py` 在本地且具 canonical write authority 的 `promotion_ready` 场景下生成 `librarian` TaskCard
- `executor.py` 新增 `librarian` executor 解析分支
- `review_gate.py` 为 Librarian change log 增加 JSON schema 基线校验
- `orchestrator.py` / `cli.py` 将 `librarian_change_log` 纳入 artifact surface
- 新增 `tests/test_librarian_executor.py`，补齐 `run_task()` 端到端晋升链路回归

对应 commit：

- `8a29471` `feat(phase32): add librarian executor flow`

## 与 kickoff 完成条件对照

### 已完成的目标

- Evidence Store 与 Wiki Store 的目录结构和读写 API 已就位
- `TaskState.knowledge_objects` 已作为 merged view 兼容层保留，stage != canonical 条目由 Evidence Store 承载
- Wiki Store 只接受 Librarian 工作流或等价 authority 的 canonical promotion 写入
- `apply_knowledge_decision(promote, canonical)` 已增加 `caller_authority` 校验
- `LibrarianExecutor` 已实现 `ExecutorProtocol`，并完成规则驱动提纯 + change log 生成
- Planner 已可识别 `promotion_ready` evidence 并生成 librarian TaskCard
- 所有现有测试通过
- 双层存储、权限校验、Librarian 工作流端到端测试已补齐

### 未继续扩张的内容

以下方向仍保持为非目标或延后项，不应视为本 phase 遗失 bug：

- Ingestion Specialist / 外部会话摄入
- Graph RAG / 社区检测 / 嵌入索引
- LLM 驱动的 Librarian 语义提纯
- Wiki 冲突合并仲裁 / 自动 canonical merge
- 周期性记忆衰减
- staged knowledge 自动晋升或 retrieval 直连

## stop / go 判断

### stop 判断

当前 phase 可以停止继续扩张，理由如下：

- kickoff 中定义的双层存储、权限防线和 Librarian 集成都已完成
- canonical 写回已被收敛到显式 authority 和可审计的 change log 路径
- 现有 task/retrieval/review CLI surface 保持兼容，没有把 scope 扩大到 ingestion / semantic merge / vector retrieval
- 全量测试通过，Claude review 无阻塞项

### go 判断

下一轮不应继续以“顺手补一点 Librarian 能力”为名扩张 Phase 32。merge 后应回到 `docs/roadmap.md` 选择新的正式 phase，并通过新的 kickoff 明确是否进入：

- Ingestion Specialist / 会话摄入
- staged knowledge retrieval integration
- 更严格的 executor / orchestrator side effect 收敛
- 更高阶的 canonical conflict / merge 策略

## 当前稳定边界

Phase 32 closeout 后，以下边界应视为当前稳定 checkpoint：

- Evidence 与 Wiki 已是物理分层存储，`knowledge_objects.json` 仅保留为兼容镜像
- canonical promotion 必须经过 `canonical-promotion` authority
- `LibrarianExecutor` 当前是规则驱动执行器，不调用 LLM 做语义提纯
- Planner 仍保持 Runtime v0 的单卡模式，只是在满足条件时切换到 `librarian` executor
- ReviewGate 只做 schema 基线校验，不改变最终 completion / retry 决策

## 当前已知问题

- `LibrarianExecutor.execute()` 仍直接执行 state mutation 和多层持久化；该技术债已记录在 `docs/concerns_backlog.md`
- `knowledge_objects.json` 作为兼容镜像仍然保留，后续是否弱化为只读镜像需要单独 phase 决策
- 当前 Librarian 流程只处理单批次、单任务内晋升，不处理跨任务冲突与语义去重

以上问题均已在 review 中记录，不阻塞当前 merge。

## 测试结果

最终验证结果：

```text
225 passed in 5.89s
```

补充说明：

- `tests/test_knowledge_store.py` 覆盖双层存储读写与 merged view 行为
- `tests/test_cli.py` 覆盖 stage-promote、authority 阻断和兼容 surface
- `tests/test_taxonomy.py` 覆盖 Librarian taxonomy helper
- `tests/test_planner.py` / `tests/test_executor_protocol.py` / `tests/test_review_gate.py` 覆盖 S3 的 planner / executor / schema gate
- `tests/test_librarian_executor.py` 覆盖 `run_task() -> librarian -> canonical promotion -> change log -> events`

## 规则文件同步检查

### 必查

- [x] `docs/plans/phase32/closeout.md`
- [x] `current_state.md`
- [x] `docs/active_context.md`
- [x] `./pr.md`

### 条件更新

- [ ] `AGENTS.md`
- [ ] `README.md`
- [ ] `README.zh-CN.md`

说明：

- 本轮未改变长期协作规则、入口读取顺序或对外使用方式，因此无需同步 `AGENTS.md` / README

## Git 收口建议

1. 保持当前 5 个 commit 历史，不再压缩
2. 使用根目录 `pr.md` 作为 PR 描述
3. Human push `feat/phase32-knowledge-dual-layer`
4. Human 创建 PR，并确认 `review_comments.md`、`closeout.md`、`pr.md` 已同步到当前实现状态
5. merge 后再把 `docs/active_context.md` 与 `current_state.md` 切到下一轮 kickoff 入口状态

## 下一轮建议

merge 完成后，不要继续在 Phase 32 分支上扩张 Librarian 或 knowledge 写回逻辑。应回到 `docs/roadmap.md` 选择下一轮方向，并以新的 kickoff 决定是否推进 ingestion、retrieval integration 或更高阶的 canonical 治理能力。
