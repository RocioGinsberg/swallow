---
author: claude
phase: 62
slice: kickoff
status: draft
created_at: 2026-04-28
depends_on:
  - docs/plans/phase62/context_brief.md
  - docs/roadmap.md
  - docs/concerns_backlog.md
  - docs/design/ORCHESTRATION.md
  - docs/design/INVARIANTS.md
  - docs/design/KNOWLEDGE.md
  - docs/design/STATE_AND_TRUTH.md
---

## TL;DR

Phase 62 把 ORCHESTRATION §5(Multi-Perspective Synthesis,MPS)从设计文档落地为代码:新增独立模块 `src/swallow/synthesis.py` 实现 artifact-pointer 驱动的多 participant + 仲裁编排,并通过 Phase 61 落地的 `apply_proposal()` 入口注册两条新 policy(`mps_round_limit` / `mps_participant_limit`)以强制执行 ORCHESTRATION §5.3 的硬上限。Synthesis 仲裁产物作为 task artifact 由 General Executor 写入,**进入 staged knowledge 通过 Operator CLI(`swl synthesis stage`)显式触发,而非 Orchestrator 自动写入**——这是为遵守 INVARIANTS §5 矩阵(Orchestrator 无 stagedK 写权限)与 §8 永久非目标"自动 knowledge promotion"。本轮拆 3 个 milestone(M1 配置与策略 / M2 编排核心 / M3 staged 集成 + 守卫完整化)。其余 14 条 §9 守卫测试、Repository 抽象层、apply_proposal 事务性回滚均不在本轮范围,沿用 Phase 61 backlog 登记。

# Phase 62 Kickoff: 完整 Multi-Perspective Synthesis(受控多视角综合)

## Phase 身份

- **Phase**: 62
- **Primary Track**: Orchestration
- **Secondary Track**: Knowledge / Governance
- **分支建议**: `feat/phase62-multi-perspective-synthesis`
- **Direction Gate 决策**: 候选 E(roadmap §四),Human 已确认 2026-04-28

## 背景与动机

Phase 61 收敛了 INVARIANTS §0 第 4 条的 `apply_proposal()` 入口,系统不变量观测能力完成阶段性补齐。roadmap §五 在 Phase 61 后推荐顺序为 `E → D`,候选 E 是认知层的下一个跃升点:

- ORCHESTRATION §5 已完整定义 Multi-Perspective Synthesis(原 "Brainstorm Mode"):多 participant 通过 artifact pointer 串联各自 LLM 产出,仲裁者综合成单一 artifact,避免 "群聊" 反模式
- `context_brief.md` 已确认代码侧零实现:`grep -rn "synthesis\|SynthesisConfig\|mps_round_limit" src/` 在核心模块中均无匹配
- A-lite 低摩擦捕获(`swl note` / clipboard / `generic_chat_json`)已落地一段时间,提供了"低摩擦入 staged → 高摩擦出 canonical" 的反馈基础;MPS 是这一闭环中"高质量产出 → staged 候选"的另一条路径
- ORCHESTRATION §5.3 列出硬上限:轮数 default 2 / max 3、参与者 default 4、仲裁必须存在、产出必须是 artifact——这些约束**仅在文档中**,代码无任何强制
- INVARIANTS §5 写权限矩阵明确:Orchestrator 无 stagedK / canonK 写权限,Operator(via CLI)有全部 W;§8 把"自动 knowledge promotion"列为永久非目标(P7/P8)

Phase 61 的治理基础已具备(policy 写入唯一入口),而成本控制 policy(`mps_round_limit` / `mps_participant_limit`)恰好需要这一入口才能合规落地——本 phase 是 candidate E 与 Phase 61 governance 的自然延续,而非耦合扩张。

## Goals(本轮范围)

**G1 - 核心 MPS 编排能力**:
- 新增 `src/swallow/synthesis.py` 模块,实现 ORCHESTRATION §5.2 的 artifact-pointer 编排循环:轮内 participant 顺序调用 Path A → 持久化各自 artifact → 下一轮通过 artifact pointer 召回 → 仲裁者综合
- 新增 `SynthesisConfig` dataclass(在 `src/swallow/models.py`),定义 participants / rounds / arbiter 字段
- 新增 CLI 入口 `swl synthesis run --task <id> --config <path>` 触发 MPS

**G2 - 成本上限的代码级强制**:
- 通过 `apply_proposal(target=ProposalTarget.POLICY)` 注册两条新 policy kind:`mps_round_limit`(default 2,hard max 3)和 `mps_participant_limit`(default 4)
- MPS 编排入口在执行前查询当前 policy 值,超过 hard max(3)直接拒绝,超过当前 default 但未超 max 的需提示用户确认
- 严格遵守 Phase 61 落地的 governance boundary,不绕过 `apply_proposal`

**G3 - 仲裁 artifact 进入 staged knowledge 的合宪路径**:
- 仲裁产出 `synthesis_arbitration.json`,落 `paths.artifacts_dir(base_dir, task_id)`(General Executor `artifact` 列 W,合规)
- 提供 CLI `swl synthesis stage --task <id>`,通过 Operator(via CLI)的 stagedK W 权限把仲裁 artifact 转换为 `StagedCandidate`(同 task / 同 `config_id` 已有 pending candidate 时拒绝重复提交)
- **不**给 Orchestrator 新增 stagedK 写权限;**不**实现自动 promotion(遵守 INVARIANTS §8 永久非目标)

**G4 - 守卫测试落地**(共 13 条,详见 design_decision §五):
- 配置 / 策略层(M1 / S1):`test_mps_rounds_within_hard_cap` / `test_mps_participants_within_policy_cap`(stub) / `test_mps_policy_writes_via_apply_proposal` / `test_apply_proposal_accepts_mps_policy_kind`
- 编排层(M2 / S2):`test_mps_no_chat_message_passing` / `test_synthesis_uses_provider_router` / `test_mps_default_route_is_path_a` / `test_synthesis_clones_state_per_call`
- 编排层(M2 / S3):`test_mps_arbiter_artifact_required`(内容级断言) / `test_synthesis_run_rejects_if_arbitration_exists` / `test_synthesis_does_not_mutate_main_task_state`(同时升级 `test_mps_participants_within_policy_cap` 到完整 e2e)
- Staged 层(M3 / S4):`test_synthesis_stage_rejects_duplicate`
- Staged 层(M3 / S5):`test_synthesis_module_does_not_call_submit_staged_candidate`

## Non-Goals(显式排除)

- **Planner 自动路由到 MPS**:本 phase 仅 CLI 入口,task semantics 字段保留扩展空间但 Planner 不会自动选择 MPS 拓扑(候选 D 范围)
- **`LogicalCallRequest` / `PhysicalCallPlan` 抽象层**:PROVIDER_ROUTER §4.1 设计预留但代码未实装,本轮不引入(超出 candidate E 边界)
- **debate-loop 与 MPS 合并**:`orchestrator.py` 已有 `_debate_loop_core`(feedback-driven retry,单 executor),与 MPS(多 participant artifact 协作)是两个不同拓扑,本 phase 不复用同一函数路径,代码层独立
- **synthesis artifact 自动进入 canonical knowledge**:违反 INVARIANTS §8 永久非目标 P7 / P8,永远不做
- **Orchestrator 的 stagedK 写权限**:违反 INVARIANTS §5 矩阵,本 phase 通过 Operator CLI 路径绕过,不修改矩阵
- **Phase 61 三项遗留 backlog**:§9 剩余 14 条守卫测试、Repository 抽象层完整实装、apply_proposal 事务性回滚——均显式推迟
- **Multi-Model Evaluation**(ORCHESTRATION §5.4 区分项):MPS 的目标是"产生新的综合方案",不实装"多模型同任务质量比较"
- **任意 participant 上限突破**:即便 Operator 通过 CLI 修改 policy 试图设置 rounds=5,governance 层硬拒(ORCHESTRATION §5.3 hard max 3)

## Completion Conditions

- M1 / M2 / M3 三个 milestone 各自的 slice 全部代码 + 测试落地,full pytest pass(预期数量 = 当前 543 + 新增 ≈ 25)
- 五条新守卫测试均跑通,且无对现有 17 条 §9 守卫的弱化或删除
- `docs/concerns_backlog.md` 同步:任何本 phase 暴露但不解决的 Open 项必须登记
- `docs/plans/phase62/closeout.md` 出具,记录每条 Goal / Non-Goal 的实际达成情况
- Phase 62 PR review 由 Claude 主线产出 `review_comments.md`,0 [BLOCK]
- Codex 完成 `pr.md` 与 PR body 同步;Human Merge Gate 通过

## Scope Guard(`phase-guard` 检查清单)

| 检查项 | 状态 |
|--------|------|
| 是否仅落地 candidate E?| ✅(MPS 编排 + 配置 + 守卫)|
| 是否触及 candidate D(Planner / DAG)?| ❌ 不触及,不引入 Planner 自动路由 |
| 是否触及 INVARIANTS §5 矩阵?| ❌ 不修改矩阵,通过 Operator CLI 路径处理 stagedK |
| 是否触及 §8 永久非目标?| ❌ 不引入自动 promotion,不上云,不接管推进语义 |
| 是否绕过 Phase 61 governance boundary?| ❌ 新 policy kind 走 `apply_proposal` |
| 是否扩展 OperatorToken.source enum?| ❌ 不扩展,沿用 Phase 61 三值 |
| 是否新增 Specialist?| ❌ 不新增 agent,不修改 §5 矩阵 |

## Branch Advice

- **分支名**:`feat/phase62-multi-perspective-synthesis`
- **commit 节奏**:per-milestone(M1 / M2 / M3 各一次或多次,milestone 内允许 per-slice commit)
- **PR 策略**:Phase 62 一个 PR,在三个 milestone 全部完成 + Claude review 通过后开 PR
- **Phase 61 残留 doc cosmetic fix**(`closeout.md` 第 81 行 / `pr.md` 第 80 行):可在本 feature branch 第一次 docs commit 中顺手处理,不单独走分支

## 关键依赖文档

1. `docs/plans/phase62/context_brief.md`(此 phase 上下文 brief)
2. `docs/design/ORCHESTRATION.md` §5 与 §6.6(MPS 设计与协同拓扑)
3. `docs/design/INVARIANTS.md` §0 / §5 / §8 / §9(写权限矩阵 + 永久非目标 + 守卫测试)
4. `docs/design/KNOWLEDGE.md`(staged candidate 通道)
5. `docs/design/STATE_AND_TRUTH.md`(artifact 写入路径 + truth 层关系)
6. `docs/concerns_backlog.md`(Phase 61 三项 Open 显式排除依据)
7. `docs/plans/phase61/closeout.md`(governance boundary 现状,作为 phase62 实现的不变量)
