---
author: claude/context-analyst
phase: 62
slice: context-analysis
status: draft
created_at: 2026-04-28
depends_on:
  - docs/roadmap.md
  - docs/design/ORCHESTRATION.md
  - docs/design/INVARIANTS.md
  - docs/design/KNOWLEDGE.md
  - docs/design/ARCHITECTURE.md
  - docs/design/AGENT_TAXONOMY.md
  - docs/design/PROVIDER_ROUTER.md
  - docs/design/STATE_AND_TRUTH.md
  - docs/concerns_backlog.md
---

TL;DR: Multi-Perspective Synthesis (MPS) is fully designed in ORCHESTRATION §5 but has zero code — no `SynthesisConfig`, no participant fan-out loop, no synthesis artifact type, no staged-knowledge auto-candidate channel. Phase 62 builds the first end-to-end Path A multi-participant synthesis path. The primary risk is token-cost governance: the 2-round / 4-participant hard caps defined in the design must be enforced via `policy_records`, but the `mps_round_limit` / `mps_participant_limit` policy kinds do not yet exist anywhere in code.

---

## Direction Recap

Candidate E — **完整 Multi-Perspective Synthesis** (roadmap §四 候选 E):

> 基于 ORCHESTRATION §5 中 artifact pointer 的多视角并行 + 仲裁,产出结构化 artifact 进入 staged knowledge。可能 slice:`SynthesisConfig` + topology 定义 / multi-route synthesis orchestration / synthesis artifact → staged knowledge 自动候选通道。风险:中到高。

Direction confirmed by Human 2026-04-28 (active_context.md §当前状态说明).

---

## 变更范围

- **直接影响模块**:
  - `src/swallow/orchestrator.py` (3900 lines) — fan-out entry point; `_run_subtask_orchestration` (line 2012) and its async variant (line 2153) are the closest existing parallel execution surface; MPS needs a sibling path that loops over participants, persists per-participant artifacts, then calls an arbiter
  - `src/swallow/executor.py` (1912 lines) — `run_http_executor` (line 1184) / `run_http_executor_async` (line 1304) are the Path A call surface; synthesis participant calls will call these with role-prefixed prompts; `resolve_dialect` (line 448) resolves dialect adapters
  - `src/swallow/subtask_orchestrator.py` (460 lines) — `SubtaskOrchestrator` / `AsyncSubtaskOrchestrator`; MPS is NOT the same as subtask fan-out (subtasks are independent work units; MPS participants collaborate via artifact pointers), but the async execution scaffold here is reusable pattern
  - `src/swallow/governance.py` (582 lines) — `apply_proposal` with `ProposalTarget.POLICY` (line 156+) is the write gate for MPS policy limits; the two new policy kinds (`mps_round_limit`, `mps_participant_limit`) must be applied through this path
  - `src/swallow/staged_knowledge.py` — `StagedCandidate` (line 16) / `submit_staged_candidate` (line 106); synthesis artifact → staged-knowledge auto-candidate channel terminates here
  - `src/swallow/models.py` — new `SynthesisConfig` dataclass or equivalent goes here; `context_pointers` field (line 224) in `TaskState` is the existing artifact pointer surface

- **间接影响模块**:
  - `src/swallow/planner.py` (227 lines) — `plan()` (line 150) currently produces `TaskCard` list; if `SynthesisConfig` is expressed as a task-level annotation, planner may need a new branch to emit an MPS card type (or MPS is invoked outside planner as a separate orchestration path)
  - `src/swallow/router.py` — `dialect_hint` fields (line 281+) on route records feed into participant prompt formatting; no structural change needed, but synthesis must use existing route selection, not bypass it
  - `src/swallow/knowledge_store.py` / `src/swallow/store.py` — synthesis artifacts landing in `.swl/artifacts/<task_id>/` follow existing artifact write path (General Executor truth_writes includes `artifact`); no new write permission needed

---

## 近期相关变更 (git history)

| Commit | 描述 | 相关模块 |
|--------|------|---------|
| c66fa87 | merge: Refine codes after PRD change | governance.py post-61 |
| 54cba4f | docs(phase61): close apply proposal governance review | phase61 closeout |
| 3dc9d93 | docs(governance): policy and concern | governance.py / concerns_backlog |
| e48bf9b | feat(governance): policy apply_proposal boundary | governance.py `_apply_policy` (line 553) |
| b7f0ecf | test(orchestration): relax subtask timeout timing assertion | subtask_orchestrator.py test |
| e54f7a3 | feat(governance): route metadata apply_proposal boundary | governance.py route path |
| c2d4abb | feat(governance): add apply_proposal canonical boundary | governance.py canonical path |
| 78a232f | feat(orchestrator): add subtask summary artifact and timeout guard | orchestrator.py subtask path |
| df89f18 | feat(knowledge): improve staged review visibility | staged_knowledge.py |
| 3f1c38a | feat(knowledge): add clipboard ingest and generic chat json | ingestion / cli.py A-lite capture |

---

## 关键上下文

### 1. ORCHESTRATION §5 定义的 MPS 结构

设计已完整定义 (ORCHESTRATION.md §5.2):
- 每轮每个 participant 产出一个独立 artifact,通过 `persist_artifact(out_artifact, round=n, by=participant)` 持久化
- 下一轮 / 仲裁通过 `load_artifacts(prior_round_artifacts)` 召回,不共享上下文
- 仲裁者产出最终 artifact 进入 task truth
- 硬性约束 (ORCHESTRATION §5.3): 轮数上限默认 2 / 最大 3(不可配置);参与者上限默认 4;仲裁收口必须存在;产出形态必须是 artifact

**代码中零实现**: `mps_round_limit` / `mps_participant_limit` policy kinds 在 `governance.py` / `models.py` / `orchestrator.py` 中均无匹配。

### 2. Path A 调用链现状

`run_http_executor` (executor.py line 1184) 是 Path A 的物理调用入口。当前它接受 `TaskState` + `retrieval_items`,内部从 `state` 读取 route / dialect 信息,组装 prompt 后调 `httpx.post`。MPS participant 调用需要注入 `role_prompt(participant)` 前缀,但 `TaskState` 没有 `role_prefix` 字段。设计决策要点:role prompt 是额外参数传入,还是 `TaskState` 的子集字段。

### 3. artifact 持久化路径

现有 artifact 写入路径:`.swl/artifacts/<task_id>/` (INVARIANTS §5 矩阵 `artifact` 列)。General Executor 有 `artifact` 写权限。MPS participant 每轮产出的 artifact 命名约定(例如 `mps_round_{n}_participant_{id}.json`)需要在 design_decision 阶段确定 — 目前没有任何命名约定预留。

### 4. staged knowledge 候选通道现状

`submit_staged_candidate` (staged_knowledge.py line 106) 接受 `StagedCandidate` 对象。`StagedCandidate` 字段 (line 16): `candidate_id` / `status` / content 相关字段。synthesis artifact → staged 候选的桥接需要:(a) 确定哪个角色有权调用 `submit_staged_candidate` — 当前 Specialist 有 `staged_knowledge` 写权限 (INVARIANTS §5);(b) Orchestrator / Review Gate 是否在 MPS 完成后自动触发候选提交,或需要 Operator 显式触发。INVARIANTS §8 明确 "隐式全局记忆、自动 knowledge promotion" 是**永久非目标** (P7/P8),因此 "auto-candidate" 的含义只能是"自动进入 staged 待审查",不能是"自动进入 canonical"。

### 5. governance.py 中 policy 写入路径

`_apply_policy` (governance.py line 553) 现有三个路径:audit_trigger_policy / retry_limit / 其他。`mps_round_limit` 和 `mps_participant_limit` 作为新 policy kind,需要通过 `register_policy_proposal` → `apply_proposal(..., target=ProposalTarget.POLICY)` 路径写入。目前 `_PENDING_PROPOSALS` 使用 in-memory 注册表 (governance.py line 88),存在 concerns_backlog Phase 61 记录的内存累积风险 — 但该风险不阻塞 Phase 62 MPS 功能。

### 6. 与 Phase 61 governance 边界的交互

Phase 61 落地的 `apply_proposal()` 三参数入口 (governance.py line 174) 是 MPS policy 写入的唯一合法路径。MPS orchestration 代码不得直接写 `policy_records`,必须通过 `apply_proposal`。仲裁后 synthesis artifact 若需进入 canonical knowledge,同样必须经 `apply_proposal(target=ProposalTarget.CANONICAL_KNOWLEDGE)` — Orchestrator 本身无 canonK 写权限 (INVARIANTS §5 矩阵)。

### 7. LogicalCallRequest / PhysicalCallPlan 未实装

PROVIDER_ROUTER.md §4.1 定义了 `LogicalCallRequest` 和 `PhysicalCallPlan` 接口,但代码中没有这两个类。`run_http_executor` 直接从 `TaskState` 读取路由信息,不经过逻辑/物理分离层。MPS 的 "multi-route synthesis" 在设计文档上指多个 Path A 调用,但不等于代码中存在"多路由"分发机制 — 只是多次调用同一 `run_http_executor` 函数。

---

## 风险信号

- **Token 成本失控**: MPS 4 参与者 × 2 轮 + 1 仲裁 = 9 次 Path A 调用。硬上限必须在代码层强制,不能只依赖文档约束。`mps_round_limit` / `mps_participant_limit` policy kinds 完全不存在于代码,Phase 62 必须从零实装。
- **artifact 命名冲突**: 当前 artifact 目录无 MPS-specific 命名约定。多 participant 多轮 artifact 文件如果命名不当会造成 task artifact 目录混乱,影响后续 Review Gate 和知识候选提交。
- **role prompt 注入点不清晰**: `run_http_executor` 接受 `TaskState`,不接受 free-form `role_prefix`。participant role prompt 的注入需要设计决策,否则 executor 无法正确构造 participant-specific prompt。
- **staged-knowledge auto-candidate 写权限归属**: INVARIANTS §5 矩阵中 `stagedK` 列,Specialist 有 `W`、Orchestrator 无权限。如果 Orchestrator 在 MPS 收口后自动提交 staged candidate,需要确认是否要引入新的写权限或通过 Specialist 角色代理。
- **与 debate loop 的设计混淆风险**: orchestrator.py 已有 `_debate_loop_core` / `_run_single_task_with_debate` (line 1064–1252) 实现反馈重试拓扑。MPS 不是 debate 的扩展 — debate 是单 executor 的 retry-with-feedback;MPS 是多 participant 的 artifact-pointer 协作。两者在代码中需要明确分离,不能用同一函数路径实现。
- **concerns_backlog Phase 61 三项未消化债务**: (a) §9 剩余 14 条守卫测试; (b) Repository 抽象层; (c) apply_proposal 事务性回滚。Phase 62 MPS 实现不应依赖或触碰这三项,但需在 design_decision 阶段显式划清边界。

---

## Open Questions (design_decision 必须解决)

1. `SynthesisConfig` 的 schema 定义位置: `models.py` 内新增 dataclass,还是单独的 `synthesis.py` 模块?字段包含 `participants: list[SynthesisParticipant]` / `rounds: int` / `arbiter_prompt: str` 等。
2. role prompt 注入机制: MPS participant 调用如何向 `run_http_executor` 注入 role-prefixed prompt?选项: (a) 新增 `role_prefix` 参数; (b) 在 MPS 编排层预拼接 prompt 后通过 `prompt` 参数传入; (c) 在 `TaskState` 中临时设置某字段。
3. MPS 触发入口: MPS 是新的 CLI 子命令 (`swl synthesis ...`),还是在 task semantics 中通过 `task_family = "synthesis"` 或 `SynthesisConfig` 字段触发?
4. staged-knowledge 自动候选的写权限解: Orchestrator 不能写 `stagedK`。是否需要一个 thin Specialist wrapper 来接受 synthesis artifact 并调用 `submit_staged_candidate`?
5. 仲裁 artifact 的物理格式: JSON schema 待定。它是最终 task artifact(进入 `.swl/artifacts/<task_id>/`)还是另开一个路径?
6. MPS 与现有 Review Gate 的对接: 仲裁完成后是走现有 `review_gate` 函数,还是 MPS 有专属的 verdict 检查路径?

---

## 推荐 Slice 候选 (3-5 个,非最终拆解)

| Slice | 内容 | 依赖 |
|-------|------|------|
| S1: SynthesisConfig + Policy Guards | `SynthesisConfig` dataclass; `mps_round_limit` / `mps_participant_limit` policy kinds; 相关守卫测试 | 无 |
| S2: MPS Participant Loop | 单轮多 participant Path A 调用 + artifact 持久化; role prompt 注入机制; artifact 命名约定 | S1 |
| S3: Multi-Round + Arbiter | 轮间 artifact pointer 传递; 仲裁者调用; 最终 synthesis artifact 产出 | S2 |
| S4: Staged-Knowledge Auto-Candidate | synthesis artifact → `submit_staged_candidate` 通道; 写权限解方案; CLI 展示 | S3 |
| S5: 守卫测试完整化 | `test_mps_rounds_within_hard_cap`; `test_mps_participants_within_hard_cap`; `test_synthesis_artifact_via_apply_proposal_if_canonical`; 补充 §9 相关守卫 | S1–S4 |

---

## Out-of-Scope (本 phase 明确排除)

- concerns_backlog Phase 61 三项: §9 剩余 14 条守卫测试、Repository 抽象层完整实装、apply_proposal 事务性回滚 — 均显式推迟,不并入 Phase 62
- Planner / DAG / Strategy Router 显式化 (候选 D) — 后置
- `LogicalCallRequest` / `PhysicalCallPlan` 抽象层 — PROVIDER_ROUTER 设计预留但未实装,Phase 62 不引入
- Multi-user / 并发写 / distributed worker — INVARIANTS §8 永久非目标
- 能力画像自动学习 — PROVIDER_ROUTER §6.4 远期方向
- 自动 canonical promotion (INVARIANTS §8 永久非目标,P7/P8)
