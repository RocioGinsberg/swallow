---
author: claude
phase: 61
slice: kickoff
status: draft
depends_on:
  - docs/plans/phase61/context_brief.md
  - docs/roadmap.md
  - docs/concerns_backlog.md
  - docs/design/INVARIANTS.md
  - docs/design/SELF_EVOLUTION.md
  - docs/design/DATA_MODEL.md
  - docs/design/INTERACTION.md
---

## TL;DR

Phase 61 把 INVARIANTS §0 第 4 条规定的 `apply_proposal()` 唯一入口在代码里真正落地:实现 `swallow.governance.apply_proposal()` 函数,把当前散布在 `cli.py` / `orchestrator.py` / `meta_optimizer.py` 共 11 处的 canonical / route metadata / policy 写入路径全部收敛到这一入口,补齐 INVARIANTS §9 列出的 3 条 apply_proposal 守卫测试。其余 14 条守卫测试与完整 Repository 抽象层不在本轮范围,记入 concerns_backlog 作为后续债务。

# Phase 61 Kickoff: `apply_proposal()` 入口函数化

## Phase 身份

- **Phase**: 61
- **Primary Track**: Architecture / Governance
- **Secondary Track**: Knowledge / Routing
- **分支建议**: `feat/phase61-apply-proposal`

## 背景与动机

Phase 60 收口后,Claude 在 Meta Docs Sync 收尾轮重读全部 12 份设计文档与代码现状,发现一处宪法级漂移:

- INVARIANTS §0 第 4 条把 `apply_proposal()` 定义为 canonical knowledge / route metadata / policy 三类对象的写入唯一入口
- INVARIANTS §9 列出 3 条对应守卫测试:`test_canonical_write_only_via_apply_proposal` / `test_only_apply_proposal_calls_private_writers` / `test_route_metadata_writes_only_via_apply_proposal`
- ARCHITECTURE / STATE_AND_TRUTH §5.1 / EXECUTOR_REGISTRY / INTERACTION §4.2.3 / SELF_EVOLUTION §3.1 / DATA_MODEL §4.1 等 7+ 处文档把这一函数当作既存基础设施引用
- 代码现状:`grep -rn "apply_proposal" src/ tests/` 零匹配;`swallow.governance` 模块、`KnowledgeRepo` / `RouteRepo` / `PolicyRepo` 类、`OperatorToken` / `ProposalTarget` / `ApplyResult` 类全部不存在
- 实际写入路径:11 处直接调底层 store(`cli.py` 6 处 / `orchestrator.py` 5 处 / `meta_optimizer.py` 2 处)

INVARIANTS 是"只增不改"的项目宪法,代码必须收敛到设计;漂移期越长,新增写路径继续违反宪法的概率越高,治理债务复利累积。Phase 60 已完成,新能力开发不构成更优先,本轮把宪法基线补齐,让候选 E / D 在干净的不变量基础上启动。

## 设计锚点

Phase 61 的实现必须对齐这些设计文档:

- **INVARIANTS.md §0 第 4 条 / §5 写入矩阵 / §9 守卫测试**:`apply_proposal()` 是 canonical / route / policy 写入唯一入口的宪法依据
- **SELF_EVOLUTION.md §3.1**:函数签名(`apply_proposal(proposal_id, operator_token, target) -> ApplyResult`)、`OperatorToken` 类(`source` 字段语义为 `"cli"` / `"system_auto"`)、`apply_proposal` 内部三步流程(load proposal artifact → validate → dispatch)
- **DATA_MODEL.md §4.1**:函数与 Repository 私有方法 `_promote_canonical` / `_apply_metadata_change` / `_apply_policy_change` 的关系——本轮**不**实现完整 Repository 抽象层,只实现 apply_proposal 直接调用现有 store 函数所需的最小封装
- **INTERACTION.md §4.2.1 / §4.2.3**:CLI 与 Control Center 的写操作均通过 governance 函数,不直接写 truth;`swl knowledge promote` / `swl proposal apply` 等 CLI 子命令对应 `apply_proposal()` 的不同 target

## 目标

1. **G1 — `apply_proposal()` 函数落地**:在 `src/swallow/governance.py` 中实现 `apply_proposal(proposal_id, operator_token, target) -> ApplyResult`,签名采用 SELF_EVOLUTION.md §3.1 版本(包含 `target` 参数);函数内部按 target 类型 dispatch 到 canonical / route / policy 三条写路径
2. **G2 — Canonical knowledge 写路径收敛**:`cli.py` 中 `swl knowledge stage-promote` / `swl knowledge promote` 类命令、`orchestrator.py` 中 `task knowledge-promote` 路径、`orchestrator.py` 中 Librarian 侧效 dispatch(line 498–499)全部经 `apply_proposal()` 入口
3. **G3 — Route metadata 写路径收敛**:`cli.py` 中 `swl route weights apply` / `swl route capabilities update` / `swl proposal apply` 命令、`meta_optimizer.py` 中 `apply_reviewed_optimization_proposals()` 全部经 `apply_proposal()` 入口
4. **G4 — Policy 写路径收敛 / 边界界定**:`cli.py` 中 `swl audit policy set` 经 `apply_proposal()` 入口;harness.py 中的 per-task 派生配置(`save_route` / `save_knowledge_policy` / `save_retry_policy` / `save_stop_policy` / `save_execution_budget_policy`)**不**纳入,因为它们是 task-scoped 派生而非系统级 policy truth(详见 design_decision §C)
5. **G5 — 3 条守卫测试落地**:`test_canonical_write_only_via_apply_proposal` / `test_only_apply_proposal_calls_private_writers` / `test_route_metadata_writes_only_via_apply_proposal` 全部实装,通过静态扫描(grep / AST)断言"除 governance.py 外,无文件直接调用 `append_canonical_record` / `save_route_weights` / `save_route_capability_profiles` / `save_audit_trigger_policy` 等私有 writer"

## 非目标

- **完整 Repository 抽象层不实现**:`KnowledgeRepo` / `RouteRepo` / `PolicyRepo` 类与 `_promote_canonical` 等私有方法是 DATA_MODEL §4.1 的设计意图,本轮采用最小封装(`apply_proposal()` 直接调现有 store 函数),Repository 抽象层作为后续 phase 工作
- **另外 14 条守卫测试不实装**:INVARIANTS §9 共 17 条守卫测试,本轮只补与 apply_proposal 直接相关的 3 条;另 14 条记入 `docs/concerns_backlog.md`,作为单独的"INVARIANTS guard tests backfill" phase
- **CLI 命令名修正**:INTERACTION.md §4.2.3 中 `swl knowledge promote` 与代码实际 `swl knowledge stage-promote` 不一致,本轮**不**重命名 CLI 命令;只在 governance 层做兼容性 dispatch
- **Migration 路径不纳入**:`knowledge_store.py:migrate_file_knowledge_to_sqlite()` 是 bootstrap 级别写入,使用专门的 `KNOWLEDGE_MIGRATION_WRITE_AUTHORITY`,语义独立于 INVARIANTS §0-4;不强制经 apply_proposal,保持 migration 入口直接性
- **派生写入(canonical_registry_index / canonical_reuse_policy)的语义重新定义**:这两个是从 canonical record 派生的索引/缓存,本轮把它们视为 `apply_proposal(target=canonical)` 的内部副作用,一并经 governance 入口,不单独抽象 target
- **harness.py 的 per-task 派生配置纳入**:`save_route` / `save_knowledge_policy` / `save_retry_policy` / `save_stop_policy` / `save_execution_budget_policy` 在 harness 内是 task-scoped 派生缓存,不是 INVARIANTS §5 矩阵的系统级 route/policy truth,边界保持
- **现有 CLI 接口外观变化**:用户视角的 `swl knowledge stage-promote` / `swl proposal apply` 命令名、参数、输出格式不变;只是内部实现链路收敛
- **proposal artifact schema 重设计**:Meta-Optimizer 现有 `OptimizationProposal` dataclass 与 staged knowledge 的 `StagedCandidate` 各自的格式不变,在 governance 层做适配
- **OperatorToken 多用户语义**:本轮 `operator_token.source` 只支持 `"cli"` / `"system_auto"` / `"librarian_side_effect"` 三种值(见 design_decision §B),不引入 multi-actor / authn / authz

## 设计边界

1. **唯一新增模块**:`src/swallow/governance.py` —— 包含 `apply_proposal()`、`OperatorToken` dataclass、`ProposalTarget` enum、`ApplyResult` dataclass
2. **现有 store 函数保持不变**:`append_canonical_record` / `persist_wiki_entry_from_record` / `save_route_weights` / `save_route_capability_profiles` / `save_audit_trigger_policy` 等底层函数签名与行为不变;它们继续是真正的物理写入实现,只是 caller 收敛
3. **Caller 改动是同质重构**:11 处 caller 全部改为先构造 `OperatorToken` + `ProposalTarget`,再调 `apply_proposal()`;不引入新业务逻辑
4. **守卫测试通过静态扫描实现**:不要求所有 store 函数变成"private"(命名 `_xxx`),改成基于文件级白名单的 grep / AST 断言,粒度足够 + 实施成本低
5. **OperatorToken 第三种 source 处理 Librarian 侧效**:`orchestrator.py:498–499` 的 Librarian agent 侧效路径不是 CLI 触发,需要 `OperatorToken.source = "librarian_side_effect"` 第三种值;由 Orchestrator 在调用前构造,不污染设计语义中 `"system_auto"` 的 auto_low_risk 含义(详见 design_decision §B)
6. **签名分歧解决**:采用 SELF_EVOLUTION.md §3.1 版本(包含 `target` 参数);DATA_MODEL.md §4.1 的简化签名不予采纳,理由见 design_decision §A
7. **不修改 INVARIANTS / DATA_MODEL / SELF_EVOLUTION 等设计文档**:INVARIANTS 只增不改;本轮代码追上设计,不反向修订宪法

## Concerns Backlog Triage

Phase 61 启动前已复核 `docs/concerns_backlog.md`:

- **直接消化**:Phase 49 的 "CLI operator canonical promotion 的 authority 语义仍未完全统一" concern 与本 phase 直接重叠——`apply_proposal()` 函数化后,caller authority 通过 `OperatorToken.source` 统一管理,可在本 phase 顺带解决,完成后将该 concern 移入 Resolved 表
- **新增背景债务**:本 phase 不处理另外 14 条 INVARIANTS §9 守卫测试,在本轮 closeout 时将"14 条 INVARIANTS guard tests 缺失"作为单独 Open 项登记到 backlog
- **新增背景债务**:DATA_MODEL §4.1 描述的完整 Repository 抽象层(`KnowledgeRepo` / `RouteRepo` / `PolicyRepo` 类)不在本轮实施,本轮 closeout 时也作为 Open 项登记
- **不并入**:Phase 50 `extract_route_weight_proposals_from_report()` 文本反向解析的格式脆弱性、Phase 57 embedding dimensions 固化、Phase 58 Open WebUI auto-detect 等 retrieval / ingestion-adjacent concern,与本 phase 无直接关系
- **不并入**:Phase 59 release-doc sync debt(`AGENTS.md` / `README.md` v1.2.0)保留为 tag-level 文档任务

## Slice 拆分

详细 slice 设计、依赖、风险评级见 `design_decision.md`。Slice 总览:

| Slice | 名称 | 主要改动 | Review checkpoint |
|-------|------|---------|-------------------|
| **S1** | `governance` 模块 + 类型 + 骨架 | 新建 `governance.py`,定义 `OperatorToken` / `ProposalTarget` / `ApplyResult`,`apply_proposal()` 骨架 + dispatch shell | 与 S2 同 milestone:governance API 稳定 |
| **S2** | Canonical 写路径收敛 + 守卫测试 1 | `cli.py:stage-promote` / `orchestrator.py:498–499` 与 `2956 / 2664–2667 / 2963–2965` 全部经 apply_proposal;实装 `test_canonical_write_only_via_apply_proposal` | 与 S1 同 milestone |
| **S3** | Route metadata 写路径收敛 + 守卫测试 2/3 | `cli.py:route weights/capabilities` / `meta_optimizer.py:apply_reviewed_optimization_proposals` 经 apply_proposal;实装 `test_route_metadata_writes_only_via_apply_proposal` 与 `test_only_apply_proposal_calls_private_writers` | 单独 milestone |
| **S4** | Policy 写路径收敛 + Phase 49 concern 消化 | `cli.py:audit policy set` 经 apply_proposal;统一 `task knowledge-promote --target canonical` 的 authority 语义 | 单独 milestone |

总 slice 数:4。符合 Claude rules 第二节"单 phase 建议 ≤5 个 slice"。

## 完成条件

1. **`apply_proposal()` 函数已实装**:`src/swallow/governance.py` 文件存在,函数签名与 SELF_EVOLUTION.md §3.1 一致,接受 `proposal_id` / `operator_token` / `target` 三个参数,返回 `ApplyResult`
2. **11 处直接写路径全部收敛**:context_brief 表格中列出的 canonical / route / policy 写路径,caller 改为通过 `apply_proposal()`;改动后 `grep -rn "append_canonical_record\|save_route_weights\|save_route_capability_profiles\|save_audit_trigger_policy" src/` 输出仅在 `governance.py` 与底层 store 文件中匹配
3. **3 条守卫测试通过**:`test_canonical_write_only_via_apply_proposal` / `test_only_apply_proposal_calls_private_writers` / `test_route_metadata_writes_only_via_apply_proposal` 全部 PASS
4. **现有功能测试无 regression**:`tests/test_cli.py` / `tests/test_meta_optimizer.py` / `tests/test_librarian_executor.py` / `tests/test_knowledge_store.py` / `tests/eval/test_eval_meta_optimizer_proposals.py` 全部 PASS
5. **Phase 49 concern 消化**:`task knowledge-promote --target canonical` 的 authority 语义统一,通过 OperatorToken 在 governance 层管理;concerns_backlog Phase 49 行移入 Resolved
6. **新增 backlog 条目**:14 条剩余守卫测试 + Repository 抽象层完整实现,作为 Open 条目登入 concerns_backlog
7. **CLI 用户视角无变化**:所有 `swl` 命令外观、参数、输出格式不变

## Eval 验收条件

本 phase 是 architectural fix,不引入新功能,行为应**与改动前完全等价**。Eval 不需要,但需要回归层面:

| Slice | Eval 需要 | 说明 |
|-------|----------|------|
| S1 (governance 骨架) | 否 | 纯类型定义 + 函数骨架,无业务行为 |
| S2 (Canonical 收敛) | 否 | caller 切换;现有 `tests/test_cli.py::test_stage_promote_*` 与 `tests/test_librarian_executor.py` 应不变通过 |
| S3 (Route 收敛) | 否 | caller 切换;现有 `tests/eval/test_eval_meta_optimizer_proposals.py` 应不变通过——这是关键回归信号,因为 Meta-Optimizer 是 route policy 的最大消费者 |
| S4 (Policy 收敛 + Phase 49) | 否 | caller 切换;`test_audit_*` / `task knowledge-promote` 相关测试应不变通过 |

如果 S3 后 Meta-Optimizer eval 行为发生变化,说明 governance 层引入了非透明语义,必须暂停并审查。

## Branch Advice

- **当前分支**: `main`(干净)
- **建议操作**: 创建新分支 `feat/phase61-apply-proposal`,在本分支上完成全部 4 个 slice
- **建议分支名**: `feat/phase61-apply-proposal`
- **建议 PR 范围**: 4 个 slice 全部合入单个 PR;由于是 architectural fix,分散 PR 反而增加 review 难度,且 caller 收敛中间态会有不一致期(部分经 apply_proposal,部分直接写),不利于守卫测试的稳定通过

## 风险预告

详见 `risk_assessment.md`,关键风险:

1. **Librarian 侧效路径(orchestrator.py:498–499)的 OperatorToken 设计**——非 CLI 触发,需要第三种 source 值,设计不当会污染 SELF_EVOLUTION.md §3.1 中 `"system_auto"` 的 auto_low_risk 语义
2. **`save_canonical_registry_index` 与 `save_canonical_reuse_policy` 的语义归属**——是 canonical truth 的派生还是独立 truth?本轮判定为派生(随 canonical 写一并发生);若实施时发现派生时机有独立调用,需 design_decision 阶段再讨论
3. **Meta-Optimizer eval 回归**——`apply_reviewed_optimization_proposals()` 的内部实现变化可能影响 proposal 解析顺序、错误处理、JSON 序列化时机;`tests/eval/test_eval_meta_optimizer_proposals.py` 是关键 sentinel
4. **守卫测试的静态扫描粒度**——基于文件白名单的 grep / AST 扫描可能误判(例如测试代码内的 mock 或 fixture);需要明确"测试代码豁免"机制
5. **harness.py per-task 派生配置的边界争议**——`save_route` / `save_knowledge_policy` 等 5 个 harness 函数定义为"task-scoped 派生缓存",边界判定可能在 design audit 时被挑战
