---
author: claude
phase: 62
slice: risk_assessment
status: revised-after-model-review
created_at: 2026-04-28
revised_at: 2026-04-28
depends_on:
  - docs/plans/phase62/kickoff.md
  - docs/plans/phase62/design_decision.md
  - docs/plans/phase62/design_audit.md
  - docs/plans/phase62/model_review.md
  - docs/plans/phase62/context_brief.md
---

## TL;DR

Phase 62 整体风险偏中。最高风险集中在 **(R1)token 成本失控**、**(R6)Validator 适配缺位** 与 **(R12)Path A 调用绕过 Provider Router**(model-review BLOCK 衍生);原稿 R5(stagedK 误用)在 audit 后已通过缩小守卫范围降级,既有 orchestrator.py:3145 stagedK 直写路径 audit 暴露后登记为 backlog Open,本 phase 不修复但显式可见;原稿 R8 / R9 在 audit 后已通过 design_decision §A.2 / §E.3 修订降级到几乎为零。新增 R10 / R11 / R12 / R13(model-review 修订后)。本稿在 design_audit 与 model_review 之后修订。

# Phase 62 Risk Assessment: Multi-Perspective Synthesis

## 一、风险清单(按严重度)

### R1: Token 成本失控(`mps_round_limit` hard cap 绕过 / `mps_participant_limit` 运行时 cap 绕过) — **高**

**描述**:ORCHESTRATION §5.3 列出的硬上限(rounds ≤ 3,participants ≤ 配置值默认 4)是为防止 9-N 次 Path A 调用导致用户成本不可控。如果实施时 governance 守卫遗漏任何一条 caller 路径,Operator 误改 policy `value=10` 也可能被接受;或者 synthesis.py 启动时未做 policy 校验,直接按 config 文件中的 rounds/participants 执行。

**影响**:
- 短期:单次 MPS 执行可能产生远超预期的 LLM API 成本(N 倍于 9 次的量级)
- 中期:用户对 MPS 失去信任,实际使用率下降,candidate E 价值未兑现
- 长期:成本 governance 与 INVARIANTS §0 第 4 条的 governance boundary 失去公信力

**缓解**:
1. M1 的 governance dispatch 内**双重校验**:既校验 `value > 3`(hard max)直接 reject,也校验 `value < 1`(下限)
2. M2 的 `run_synthesis` 启动前 fetch 当前 policy 值,validate config 字段(rounds / participants 数量)与 policy 之间的关系
3. 守卫测试 `test_mps_rounds_within_hard_cap` 与 `test_mps_participants_within_hard_cap` 覆盖 governance 拒绝路径与 run_synthesis 启动前校验
4. CLI `swl synthesis run` 启动前向用户展示"本次执行预计调用次数 = participants × rounds + 1 仲裁",引导用户预估成本(非强制 gate,但可见性提升)

**残余风险**:user 主动通过 `apply_proposal` 把 `mps_participant_limit` 设到极大值(如 100)绕过 default 4 的成本预期。缓解方式只有 documentation + CLI 提示,代码层不阻拦——这是 ORCHESTRATION §5.3 文字明说的"Operator 可在最大值范围内调整"的设计意图。`mps_participant_limit` 没有 hard max(只有 `mps_round_limit` 有 max=3),设计上由 Operator 自主决策。

---

### R2: orchestrator.py 主链路被改 — **低**

**描述**:context_brief 已识别 MPS 是"sibling path"(平行编排),不应进 `_run_subtask_orchestration`。但实施时若误把 synthesis 入口写进 orchestrator.py 主分支,会让 orchestrator 主循环复杂度上升,与 subtask fan-out / debate loop 路径混淆。

**影响**:
- 短期:orchestrator.py 行数 + 圈复杂度上升,review 体感变差
- 长期:MPS 与 debate / fan-out 的拓扑边界模糊,后续候选 D(Planner / DAG)实施时这条路径上的耦合会复利累积

**缓解**:
1. design_decision §A / §三 显式约定:MPS 编排逻辑全部进 `src/swallow/synthesis.py`,**不修改 orchestrator.py 主循环**
2. orchestrator.py 仅在 CLI `swl synthesis run` 入口内 dispatch 到 synthesis.py,该 dispatch 是"调用",不是"嵌入"
3. design audit 阶段重点检查 orchestrator.py 的 diff 是否最小

**残余风险**:CLI dispatch 路径仍可能在 orchestrator.py 留下少量 plumbing(如 task state lifecycle 推进)。这部分必须在 design audit 中量化(预计 ≤ 30 行 diff)。

---

### R3: artifact 命名冲突与目录混乱 — **中**

**描述**:`paths.artifacts_dir(base_dir, task_id)`(展开为 `.swl/tasks/<task_id>/artifacts/`)是已有 task artifact 目录。MPS 4 participants × 2 rounds = 8 个 participant artifact + 1 仲裁 artifact = 单次 MPS 在该目录下产生 9 个文件。如果命名约定不严格(例如 participant_id 不全局唯一,或 round n 起 0 vs 起 1 不一致),会与现有 task artifact 命名冲突。

**影响**:
- 短期:同一 task 跑两次 MPS 会因命名重复覆盖前一次 artifact
- 中期:Validator / Review Gate / `swl synthesis stage` 找不到正确的仲裁 artifact

**缓解**:
1. design_decision §E 明确命名:`synthesis_round_{n}_participant_{participant_id}.json`(participant_id 是 ULID,全局唯一,即便重跑也不冲突)
2. 仲裁 artifact 命名 `synthesis_arbitration.json`——单 task 单次 MPS 仅一份,若重跑 MPS 应在 event_log 写 `mps_re_executed` 并新建 `synthesis_arbitration_<config_id>.json`(`config_id` 是 ULID)
3. round 编号统一从 1 起(对齐 ORCHESTRATION §5.2 中 "轮 n" 表达)

**残余风险**:重跑场景的"是否覆盖"语义需在 implementation 时确定。Phase 62 默认行为:**单 task 单次 MPS 跑完后不允许重跑**(状态机阻塞),Operator 需新建 task 或显式 `swl synthesis reset`(本 phase 不实装,Out-of-Scope)。

---

### R4: role prompt 注入污染 task semantics 持久字段 — **中**

**描述**:design_decision §B 决定 role prompt 在 synthesis.py 内拼接,通过 prompt 字段传入 `run_http_executor`。如果实施时误把 `role_prompt` 写到 `TaskState` / `TaskCard` 等持久字段(为了"复用方便"),会让 task truth 表中出现 transient 字段,污染 truth 层。

**影响**:
- 短期:`TaskState` schema 演进出非语义字段,后续清理成本增加
- 中期:守卫测试 `test_no_foreign_key_across_namespaces` / DATA_MODEL §4.2 不变量可能被破坏

**缓解**:
1. design_decision §B 明确:role prompt 是 transient 字符串,不进 truth 表
2. `compose_participant_prompt` 是 pure function,无副作用,守卫测试可静态扫描
3. participant artifact 中以 `role_prompt_hash`(SHA-256)记录,而非原文,审计可回放但不污染主 schema

**残余风险**:实施时 Codex 若图省事把 role_prompt 写进 `TaskState` 临时字段,需在 PR review 阶段 catch。

---

### R5: stagedK 写权限误用(Phase 62 守卫范围调整) — **中(audit 修订后从"高"降级)**

**描述**:design_decision §D 明确 staged candidate 提交走 Operator/CLI 路径(`swl synthesis stage`)。原稿设想引入 `test_stagedk_write_only_from_specialist_or_cli` AST 守卫,扫描 `submit_staged_candidate` 的所有 caller,禁止 Orchestrator / synthesis.py 直接调用。

**audit 暴露的事实**:`orchestrator.py:3145` 已存在 `submit_staged_candidate(...)` 直接调用,处理 Librarian agent 在任务执行中的 verified knowledge → staged candidate 转换(librarian-side-effect 等价语义)。该调用未走 governance,**Phase 62 不在 scope 内修复**。

**Phase 62 决议(design_decision §D.2)**:
1. **不引入** 原计划的 `test_stagedk_write_only_from_specialist_or_cli` 守卫——加上会因既有路径直接 fail
2. **引入** 缩小版守卫 `test_synthesis_module_does_not_call_submit_staged_candidate`(AST 扫描 synthesis.py 不 import / 不调用 `submit_staged_candidate`)——只保护本 phase 新增模块,不触碰既有路径
3. **登记 backlog Open**:"orchestrator.py:3145 librarian-side-effect 等价 stagedK 写入未经 governance",后续治理 phase 处理(类比 Phase 61 librarian-side-effect 决策)

**影响**:
- 短期:Phase 62 守卫保护范围比原稿小,但保护范围内零盲区(synthesis.py 100% 不写 stagedK)
- 中期:既有 librarian-side-effect 等价路径继续存在,但已显式登记,治理债务可见

**残余风险**:
- 后续若有人在 synthesis.py 之外的新模块写 stagedK(如 hypothetical Phase 63 模块),没有项目级 AST 守卫覆盖。Phase 63+ 可在 governance phase 中补全完整守卫
- 既有 orchestrator.py:3145 路径若被未来代码改动放大(更多 Orchestrator 路径写 stagedK),失去早期发现机会——靠 backlog Open 提示后续 phase 处理

---

### R6: Validator 不识别 synthesis_arbitration.json — **中**

(同原稿)Phase 62 不修改 Validator,接受 verdict 可能不精准;CLI `swl synthesis run` 完成时直接打印 `arbiter_decision.synthesis_summary` + `rationale`。

---

### R7: synthesis 与 debate loop 设计混淆(代码复用诱惑) — **中**

(同原稿)守卫 `test_mps_no_chat_message_passing` 间接保护;design audit 已确认 `_debate_loop_core` 与 synthesis.py 完全独立。

---

### R8: 既有 Phase 61 governance boundary 在新 policy kind 上的回归风险 — **低(audit 修订后)**

**audit 修订**:design_decision §A.2 决议**不**改既有 `_PolicyProposal`,而是新增独立 `_MpsPolicyProposal` + isinstance 分支。这种实现方式 Phase 61 路径**零修改**,回归风险从原稿的"低"再下调一个数量级。

**缓解**:
1. M1 实施时新增 isinstance 分支,既有 `_PolicyProposal` 路径文字未动
2. 验证基线:M1 完成时跑 `pytest tests/test_governance.py tests/test_invariant_guards.py tests/eval/test_eval_meta_optimizer_proposals.py -m eval` 全 pass
3. design audit 已显式确认此处零回归

**残余风险**:无。

---

### R9: `StagedCandidate` schema 字段映射错误(audit 修订) — **低**

**audit 修订**:原稿 design_decision §S4 line 246 使用 `content=` / `source=` / `origin_artifact_ids=[]` 字段名错误。修订后(design_decision §E.3)严格对齐既有 schema(`text` / `source_kind` / `source_task_id` / `source_object_id` / `source_ref`),**不**新增字段,`origin_artifact_ids` 等价信息走 `source_object_id`(承载 `config_id`)。

**残余风险**:无。

---

### R10: `_MpsPolicyProposal` 与 `_PolicyProposal` 共用 `_PENDING_PROPOSALS` namespace — **低**

**描述**:`_PENDING_PROPOSALS` 是 `(ProposalTarget, proposal_id)` → 任意 dataclass 的 dict。新增 `_MpsPolicyProposal` 与 `_PolicyProposal` 共享 `ProposalTarget.POLICY` 作为第一维 key,proposal_id 第二维 key 全局唯一,因此 namespace 冲突理论上不存在。但若两个不同 proposal 类型短期内交错注册而 `proposal_id` 由 caller 提供,理论上有 caller 端 ID 冲突可能。

**缓解**:
1. `register_*_proposal` 系列函数已校验 `proposal_id` 非空,并以 ULID 或 timestamp 命名空间隔离的方式生成(由 caller 责任)
2. `apply_proposal` 内部已有 isinstance type guard(原 governance.py:217),与新 isinstance 分支配合

**残余风险**:无,沿用 Phase 61 既有约定。

---

### R11: `mps_policy_store.py` 路径 `.swl/policy/mps_policy.json` 与既有目录结构冲突 — **低**

**描述**:Phase 62 新增持久化文件 `.swl/policy/mps_policy.json`。需确认 `.swl/policy/` 目录是否被既有代码占用或 .gitignore 已正确处理。

**缓解**:
1. M1 实施前 `ls -la .swl/policy/`(若现有 working dir 有 base_dir)+ `grep -rn "policy/" src/swallow/paths.py` 确认目录结构
2. 持久化路径通过 `paths.mps_policy_path(base_dir)` helper 集中(model-review 修订);若目录冲突,只改该 helper 一处

**残余风险**:无,实施时易确认。

---

### R12: MPS Path A 调用绕过 Provider Router(model-review BLOCK 衍生) — **中**

**描述**:`run_http_executor` 是低层 HTTP caller,不会自动触发 `router.select_route` / `router.route_by_name`。如果 synthesis.py 实施时偷懒,直接以 `base_state` 调用 `run_http_executor`,会用 task 配置的(可能是 Path B/C 的)route 发出 HTTP payload,违反 INVARIANTS §4(Path A 必须经 Provider Router 治理)。design_decision §B.1 已明确路由解析 seam,但实施时若守卫遗漏特定 caller 路径,仍会绕过。

**影响**:
- 短期:participant 调用以错误 model hint 发出,LLM 输出与 role prompt 不匹配
- 中期:违反宪法但守卫未覆盖,审计盲区
- 长期:其他类似 fan-out / parallel 编排可能复制此模式,扩大不变量缺口

**缓解**:
1. `test_synthesis_uses_provider_router`:AST 扫描 synthesis.py 必须 import `router.route_by_name` 与 `router.select_route`,且不直接构造 `RouteSpec` 字面量
2. `test_mps_default_route_is_path_a`:`_MPS_DEFAULT_HTTP_ROUTE` 解析后 `route.path == "A"`(若 ROUTE_REGISTRY 改名,守卫立即 fail)
3. `test_synthesis_clones_state_per_call`:AST 扫描 `run_http_executor` 调用前必须有 `dataclasses.replace` 或 `_participant_state_for_call`,即只能 transient state 下传(连带断 base_state 直传路径)
4. design_decision §B.1 显式列举三种路径:hint→`route_by_name`、无 hint→`select_route`、fallback→`_MPS_DEFAULT_HTTP_ROUTE`

**残余风险**:`route_hint` 由 Operator 在 SynthesisConfig 中提供时,不经 `select_route` 的 capability boundary guard——这是设计决策(类比 INVARIANTS §7.1 `route_override_hint`),不是缺陷;后续 phase 评估是否引入 hint 与 capability 的双重交叉校验。

---

### R13: `_validate_target` 漏改导致 dispatch 前 TypeError(model-review CONCERN 衍生) — **低**

**描述**:Phase 61 落地的 `apply_proposal` 在 dispatch 前调 `_validate_target`(governance.py:212-218),其中 `ProposalTarget.POLICY` 分支强 type-check `isinstance(proposal, _PolicyProposal)`。若 M1 实施只改 `_apply_policy` 而漏改 `_validate_target`,`_MpsPolicyProposal` 会在 validate 阶段被拒,根本进不到 dispatch。

**影响**:
- 短期:M1 任何 `apply_proposal(target=POLICY)` MPS proposal 抛 TypeError,所有 `swl synthesis policy set` 失败
- 中期:无,在 M1 阶段就会被 `test_apply_proposal_accepts_mps_policy_kind` 守卫立即捕获

**缓解**:
1. design_decision §A.2 明确 model-review BLOCK 必修项:`_validate_target` 必须**同步**扩展接受 `(_PolicyProposal, _MpsPolicyProposal)`
2. `test_apply_proposal_accepts_mps_policy_kind` 新增守卫,M1 实施未改 `_validate_target` 立即 fail
3. design_audit 二轮已显式标出该改动,Codex 实施时双重提醒

**残余风险**:无。

---

## 二、Phase 61 backlog 三项 Open 与本 phase 的边界

| Phase 61 Open | 本 phase 是否触碰 | 边界声明 |
|---------------|-------------------|----------|
| §9 剩余 14 条守卫测试 | ❌ 不触碰 | 本 phase 仅新增 13 条 MPS 专属守卫,不实装其他 14 条 |
| Repository 抽象层完整实装 | ❌ 不触碰 | governance dispatch 沿用 Phase 61 直调 store,不引入 Repository |
| apply_proposal 事务性回滚 | ❌ 不触碰 | MPS policy 写入失败时,governance 返回 ApplyResult.failed,caller 自行决定是否重试;不实现跨多 store 事务 |

若实施过程中发现 MPS 必须依赖三项中某一项,触发 design audit BLOCKER → 回到 Step 2 修订 design_decision。

---

## 三、整体风险评级

| 类别 | 评级 | 主导风险 |
|------|------|----------|
| **成本/治理** | 中 | R1(token 成本)+ R5(stagedK 守卫缩小但 backlog 显式) |
| **架构侵入度** | 低 | R2(orchestrator 主链路)— 设计已隔离到 synthesis.py |
| **代码语义混淆** | 中 | R7(debate vs MPS)+ R4(role prompt 污染) |
| **既有功能回归** | 极低 | R8(Phase 61 dispatch)+ R13(_validate_target 漏改)— 修订采用 isinstance 分支 + 显式守卫 |
| **新功能精度** | 中 | R6(Validator 适配)— 接受为本 phase 限制 |
| **schema 漂移** | 极低 | R9(StagedCandidate)— 修订严格对齐既有字段不新增 |
| **数据结构演化** | 低 | R10(`_PENDING_PROPOSALS` namespace)+ R11(policy 持久化路径)|
| **不变量绕过** | 中(model-review 新增) | R12(Path A 绕过 Provider Router)— 三条新守卫覆盖 |

**整体评级:中**。本 phase 不破坏既有不变量,新增能力局限在新模块 + 两条新 policy + 新 CLI 子命令组(`swl synthesis`)+ 新 paths helper,影响面可控;主要风险在新能力本身的成本控制、权限边界与路由治理,设计决策与守卫测试已显式覆盖。audit 与 model_review 已暴露 design 与代码现状的偏差并修订到位,Codex 起步无 BLOCKER 阻塞。

## 四、回滚路径

每个 milestone 独立回滚:

- **M1 回滚**:删除 `governance.py` 内 `mps_round_limit` / `mps_participant_limit` dispatch + `models.py` 内 `SynthesisConfig` 类。守卫测试 5 条同步删除。无遗留状态。
- **M2 回滚**:删除 `synthesis.py` 整文件 + `cli.py` 内 `swl synthesis run` 子命令。policy 数据若已写入,Operator 可通过 `swl audit policy set` 显式删除(复用 Phase 61 path)。
- **M3 回滚**:删除 `cli.py` 内 `swl synthesis stage` + 任何 `StagedCandidate` schema 扩展(若做了)。已写入的 staged candidate 通过 staged review CLI 删除(复用现有路径)。

PR 整体回滚:revert merge commit 即可,无 schema 迁移阻塞。
