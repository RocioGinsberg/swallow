---
author: claude
phase: 62
slice: pr-review
status: draft
created_at: 2026-04-28
depends_on:
  - docs/plans/phase62/design_decision.md
  - docs/plans/phase62/risk_assessment.md
  - docs/plans/phase62/design_audit.md
  - docs/plans/phase62/model_review.md
  - docs/design/INVARIANTS.md
---

## TL;DR

Phase 62 (Multi-Perspective Synthesis 实装) 与 design_decision §A–§G(revised-after-model-review)整体对齐:13 条守卫全部落地、`apply_proposal(POLICY)` 走 `_MpsPolicyProposal` + `_validate_target` 扩展、Path A route resolution 经 `route_by_name` / `select_route` 双路径 + transient state isolation、`swl synthesis` 三个子命令(policy set / run / stage)CLI 体系闭合、`StagedCandidate` 字段映射严格匹配既有 schema。`tests` 557 passed / 8 deselected。**0 [BLOCK]、4 [CONCERN]、4 [NOTE]**;主要 concern 是 (a) executor 失败状态未阻断 synthesis 推进、(b) 完整 composed prompt 写入 participant artifact 与 design §B 文意有偏、(c) `participant_id` 唯一性未在 config load 阶段校验、(d) `swl synthesis stage` duplicate 经未捕获 ValueError 暴露。NOTE-D 单独处理 `_MPS_DEFAULT_HTTP_ROUTE` 文档-代码漂移(implementer 主动纠正了 design §B.1 的文字错误,代码侧无需变更,closeout 反向修订 design 表述)。建议 Codex 在合并前消化 [CONCERN-1..4];均不阻塞 Human Merge Gate。

# Phase 62 Review Comments

## 一、Review 范围与方法

- **被 review 提交**(feat branch 范围 `main..HEAD`):
  - `e0dc534 feat(synthesis): add MPS policy plumbing` (M1: governance + paths + models + CLI policy)
  - `35b8768 feat(synthesis): add MPS runtime orchestration` (M2: synthesis.py + CLI run)
  - `fd3a03c feat(synthesis): add MPS staged knowledge bridge` (M3 S4: CLI stage + idempotency)
  - `e6382a0 test(synthesis): cover MPS policy runtime and staging` (M2/M3 测试)
  - `db80022 feat(synthesis): add MPS policy plumbing core` (M1 mps_policy_store.py)
  - `3e3886f docs(phase62): generate and review design decision` (design 文档前置)
- **设计基线**:
  - `docs/plans/phase62/design_decision.md` (revised-after-model-review) §A–§G + §五 13 条守卫
  - `docs/plans/phase62/risk_assessment.md` (revised-after-model-review) R1–R13
  - `docs/plans/phase62/kickoff.md` G1–G4 + Non-Goals
  - `docs/design/INVARIANTS.md` §0 #4 / §4 / §5 / §7 / §9
- **测试**:
  - `.venv/bin/python -m pytest` → 557 passed, 8 deselected (本 phase 净增 ≈ 14 条 = 13 守卫 + 1 cli idempotency)
  - `.venv/bin/python -m pytest tests/test_synthesis.py tests/test_invariant_guards.py -x` → 13 passed
- **未触发 consistency-checker subagent**:本轮 diff 范围与 design 文档重叠度高,主线 review 已完成同样的字段对齐核对;若后续修订涉及 `_PolicyProposal` / `_validate_target` 任何回归,补跑 consistency-checker。

---

## 二、Design 对齐 Checklist

### A. 配置 Schema 与 Policy 数据结构(design_decision §A)

- [PASS] `SynthesisConfig` / `SynthesisParticipant` 在 `models.py:431-446` 落地为 `frozen=True, slots=True` dataclass,字段与 §A.1 完全一致(`participant_id` / `role_prompt` / `route_hint` / `config_id` / `participants` tuple / `rounds` / `arbiter` / `arbiter_prompt_extra`)
- [PASS] `_MpsPolicyProposal` dataclass 新增于 `governance.py:88-92`,**未**修改 `_PolicyProposal`,`_PENDING_PROPOSALS` 共用 namespace 但通过 isinstance 分支隔离(§A.2)
- [PASS] `_validate_target` 已扩展到 `(_PolicyProposal, _MpsPolicyProposal)` 元组(`governance.py:252`),与 model-review BLOCK 修订要求一致;`tests/test_governance.py::test_apply_proposal_accepts_mps_policy_kind` 显式覆盖 dispatch 不抛 TypeError
- [PASS] `_apply_policy` 内部 isinstance 早返回 `_MpsPolicyProposal` 分支(`governance.py:589-600`),返回 `applied_writes=("mps_policy",)`,既有 `_PolicyProposal` 路径文字未动
- [PASS] `register_mps_policy_proposal` 在注册阶段已经过 `validate_mps_policy_value`,hard cap (round_limit ≤ 3) 在 governance 入口拒绝;`mps_participant_limit` 仅 ≥ 1 校验,无 hard max,与 §A.4 + risk §R1 残余风险描述一致
- [PASS] `load_mps_policy(base_dir, kind) -> int | None` 落地于 `governance.py:204-207`(代理到 `mps_policy_store.read_mps_policy`),synthesis.py 的 `_resolve_round_limit` / `_resolve_participant_limit` 用 `or ROUND_DEFAULT` / `or PARTICIPANT_DEFAULT`(§A.5)
- [PASS] `paths.mps_policy_path(base_dir)` 集中持久化路径(`paths.py:205-207`,展开 `.swl/policy/mps_policy.json`),`mps_policy_store.py` 全部 IO 经此 helper,源码无 `".swl"` 字符串字面量(`tests/test_invariant_guards.py::test_mps_policy_writes_via_apply_proposal` 显式断言)
- [PASS] CLI `swl synthesis policy set --kind {mps_round_limit, mps_participant_limit} --value <n>` 落地于 `cli.py:1290-1305`,内部走 `register_mps_policy_proposal` → `apply_proposal(target=POLICY, OperatorToken(source="cli"))`,与 `swl audit policy set` 解耦(§A.3)

### B. Path A route resolution + state isolation(design_decision §B,model-review BLOCK)

- [PASS] `synthesis.py` 显式 import `route_by_name` / `select_route`(`synthesis.py:13`),`tests/test_invariant_guards.py::test_synthesis_uses_provider_router` 守卫覆盖
- [PASS] `_resolve_participant_route`(`synthesis.py:125-137`)实现三路径决策树:有 `route_hint` → `route_by_name` 精确解析 + Path A 校验;无 hint → `select_route(base_state)` 选择 + Path A 校验;非 Path A → 回退 `_default_path_a_route()`
- [PASS] `_participant_state_for_call`(`synthesis.py:140-162`)用 `dataclasses.replace(base_state, ...)` 生成 transient state,fallback / mutation 仅作用 transient;e2e 守卫 `tests/test_synthesis.py::test_synthesis_does_not_mutate_main_task_state` 覆盖
- [PASS] AST 守卫 `tests/test_invariant_guards.py::test_synthesis_clones_state_per_call` 检查 `_participant_state_for_call` 名称、`replace(` 调用、`run_http_executor(transient_state, ...)` / `run_http_executor(arbiter_state, ...)` 模式存在
- [PASS] arbiter 调用同样经 `_resolve_participant_route` + `_participant_state_for_call`(`synthesis.py:352-355`),不直传 base_state
- [NOTE-D] `_MPS_DEFAULT_HTTP_ROUTE = "local-http"`(`synthesis.py:19`)与 design_decision §B.1 line 285 文字"实施时取 `router.route_by_name("local-claude-code")`"不一致 — implementer 选取**正确的** Path A 路由,纠正了 design 文字错误。详见下方"四、NOTE-D"。

### C. role prompt 注入(design_decision §C)

- [PASS] `compose_participant_prompt`(`synthesis.py:165-196`)是 pure function,在 synthesis.py 内拼接 `role_prompt + task_semantics(JSON) + prior_artifacts`,通过 `prompt=` 关键字传入 `run_http_executor`
- [PASS] `tests/test_invariant_guards.py::test_mps_no_chat_message_passing` AST 守卫禁止 `messages` keyword / Name 节点出现
- [CONCERN-2] participant artifact `prompt` 字段直接持久化完整 composed prompt(synthesis.py:229),而 design §B / risk §R4 表述只要求"以 `role_prompt_hash`(SHA-256)记录,而非原文"。详见下方"三、CONCERN-2"。

### D. CLI 入口与 task semantics(design_decision §D)

- [PASS] CLI 仅暴露 `swl synthesis run --task <id> --config <path>`(`cli.py:1316-1320`),`TaskSemantics` 未引入新字段
- [PASS] `synthesis_run_parser` 仅接受 `task_id` / `config_path`,无自动路由 hook;Planner 路径未触碰

### E. Staged knowledge 写入(design_decision §E)

- [PASS] §E.1 仲裁 artifact 进入 staged 仅经 `swl synthesis stage`(`cli.py:2538-2602`),走 Operator/CLI 路径,`StagedCandidate.submitted_by="cli"`
- [PASS] §E.2 `tests/test_invariant_guards.py::test_synthesis_module_does_not_call_submit_staged_candidate` AST 守卫覆盖 synthesis.py 不 import / 不调用 `submit_staged_candidate`(本轮我手工再核对 synthesis.py 全文,确无该 symbol);orchestrator.py:3145 既有路径未触碰,backlog Open 已登记
- [PASS] §E.3 字段映射严格对齐:`text=synthesis_summary` / `source_kind="synthesis"` / `source_task_id=task_id` / `source_object_id=config_id` / `source_ref=arbitration_path.relative_to(base_dir)` / `submitted_by="cli"`,**未**新增 `origin_artifact_ids`
- [PASS] §E.4 idempotency 经 `load_staged_candidates` 检查同 task / 同 `source_object_id` / `status=="pending"`,存在则 `raise ValueError("...already staged...")`;`tests/test_cli.py::test_synthesis_stage_rejects_duplicate` 覆盖
- [CONCERN-4] duplicate 暴露为未捕获 ValueError(stack trace UX 不洁)。详见下方"三、CONCERN-4"。

### F. 仲裁 artifact 物理格式(design_decision §F)

- [PASS] `synthesis_arbitration.json` 落 `paths.artifacts_dir(base_dir, task_id)`(synthesis.py:341 + cli.py:2554),命名固定
- [PASS] schema = `synthesis_arbitration_v1`(synthesis.py:362)
- [PASS] payload 字段:`config_id` / `task_id` / `rounds_executed` / `participants[].round_artifacts` / `arbiter` / `arbiter_decision.{selected_artifact_refs, synthesis_summary, rationale}` / `raw_arbiter_output` / `completed_at` 全部存在
- [PASS] participant artifact 命名 `synthesis_round_{n}_participant_{participant_id}.json`(synthesis.py:217)
- [PASS] event `task.mps_completed` payload 含 `config_id` / `arbitration_artifact_id` / `arbitration_artifact_path` / `rounds_executed` / `participant_count`(synthesis.py:386-399);`event_type` 字段名与既有代码一致(audit Q9 / model-review CONCERN 已解决)
- [PASS] 内容级守卫 `tests/test_synthesis.py::test_mps_arbiter_artifact_required`:`schema == "synthesis_arbitration_v1"` / `config_id == "config-mps"` / `rounds_executed == 2` / 每个 participant `round_artifacts` 长度 = `rounds_executed` / `synthesis_summary` 非空 / event 唯一且不推进 status
- [NOTE-A] event payload 中 `arbitration_artifact_id` 是固定字符串 `"synthesis_arbitration"`(synthesis.py:360),不是 ULID;design §F schema 文本写作 `<ULID>`。单 task 单 artifact 语义可接受,但与 §F 示例文字偏差,建议未来 closeout 同步。

### G. Review Gate 对接(design_decision §G)

- [PASS] MPS 不引入专属 verdict,执行后 task.status 保持 `created`(`tests/test_synthesis.py:92`);Validator/Review Gate 路径未改动

### §五 13 条守卫清单逐项核对

| 守卫 | 落地位置 | 状态 |
|------|---------|------|
| `test_mps_rounds_within_hard_cap` | `tests/test_governance.py:152-159` | [PASS] 注册阶段拒绝 value>3 |
| `test_mps_participants_within_policy_cap` | `tests/test_synthesis.py:54-67` | [PASS] e2e 完整,运行时 enforcement |
| `test_mps_policy_writes_via_apply_proposal` | `tests/test_invariant_guards.py:107-119` | [PASS] save_mps_policy 调用域 + mps_policy_path 唯一来源双断言 |
| `test_apply_proposal_accepts_mps_policy_kind` | `tests/test_governance.py:162-176` | [PASS] `_validate_target` 扩展验证 |
| `test_mps_no_chat_message_passing` | `tests/test_invariant_guards.py:122-130` | [PASS] AST 扫描 messages |
| `test_synthesis_uses_provider_router` | `tests/test_invariant_guards.py:133-146` | [PASS] AST 扫描 import + RouteSpec 字面量 |
| `test_mps_default_route_is_path_a` | `tests/test_invariant_guards.py:149-153` | [PASS] 但与实现 `_route_is_path_a` co-tested,详 NOTE-D |
| `test_synthesis_clones_state_per_call` | `tests/test_invariant_guards.py:156-162` | [PASS] |
| `test_mps_arbiter_artifact_required` | `tests/test_synthesis.py:70-92` | [PASS] 内容级 + event 断言 |
| `test_synthesis_run_rejects_if_arbitration_exists` | `tests/test_synthesis.py:95-103` | [PASS] |
| `test_synthesis_does_not_mutate_main_task_state` | `tests/test_synthesis.py:106-129` | [PASS] 但仅断言 5 字段,详 NOTE-B |
| `test_synthesis_stage_rejects_duplicate` | `tests/test_cli.py:138-205` | [PASS] |
| `test_synthesis_module_does_not_call_submit_staged_candidate` | `tests/test_invariant_guards.py:175-193` | [PASS] |

13/13 全 pass。

---

## 三、CONCERN(共 4 项,无 BLOCK)

### [CONCERN-1] participant executor 失败状态未阻断 synthesis(中)

**位置**:`src/swallow/synthesis.py:218`、`run_synthesis_round` 主循环、`run_synthesis` arbiter 调用

**事实**:`persist_participant_artifact` 用 `output = (executor_result.output or executor_result.message).strip()`,无论 `executor_result.status` 是 `completed` / `failed` / `incomplete`,artifact 一律持久化、循环继续推进。下一轮 `compose_participant_prompt` 把"上一轮失败的 error message"作为 `prior_artifacts.output` 拼进 prompt,arbiter 也不区分 status 对待。

**风险**:
- 4 participants × 2 rounds 中若全部或大量 failed(网络抖动、token 超限、上游 503),arbiter 仍会被调用、艺术性合并 8 段错误文本,得到无效 `synthesis_summary`(只要非空字符串就通过 `if not synthesis_summary: raise` 校验)。
- 失败信号未在 event_log `task.mps_completed` payload 中暴露,Operator 难以在 review 时定位失败轮次。

**建议**(择一):
1. **最小修复**:在 `run_synthesis_round` 内对每个 participant 检查 `executor_result.status != "completed"` → 抛 `RuntimeError`,中断本次 synthesis(对齐"失败即终止"语义)
2. **可观察修复**:不抛错但在 event_log 写 `task.mps_participant_failed` 子事件,arbiter 调用前若失败比例超阈值再终止(更复杂,可作为后续 phase)

design_decision / risk_assessment 均未明文要求此类终止行为,此 concern 暴露的是设计层的隐含未约束语义。建议本 PR 内采用方案 1 + 守卫(`tests/test_synthesis.py::test_mps_aborts_on_participant_failure`)。

---

### [CONCERN-2] participant artifact 写入完整 composed prompt 与 design §B / risk §R4 文意偏离(中)

**位置**:`src/swallow/synthesis.py:229`(`payload["prompt"] = prompt`)

**事实**:`persist_participant_artifact` 把整个 `compose_participant_prompt` 返回的字符串(role_prompt + task_semantics JSON + prior_artifacts 包含 output 内容)写进 participant artifact 的 `prompt` 字段。design_decision §B 与 risk_assessment §R4 line 88 明确"participant artifact 中以 `role_prompt_hash`(SHA-256)记录,而非原文,审计可回放但不污染主 schema"。

**风险**:
- N 轮后 prior_artifacts 滚雪球放大:round k 的 prompt 包含 round k-1 的所有 participant outputs;round k+1 的 prompt 又包含 round k 的所有(各自含 round k-1 的)outputs。Disk footprint O(N² × participants × output_size),单次 4×3 synthesis 即可膨胀到几 MB
- 若 participant output 含敏感语料(用户私有 task semantics),完整 prompt 持久化等于"sensitive 数据被多次复制"
- 当前 schema `synthesis_participant_v1` 已记录 `role_prompt_hash`,prompt 字段属于冗余

**建议**:
- 删除 `payload["prompt"]` 字段,保留 `role_prompt_hash`(已存在);如需调试可回放,引入独立 debug-only 标志或 `--persist-prompt` CLI 选项(default off)
- 同时 `synthesis_participant_v1` schema 不需要 schema 版本变更,纯 field 删除是 forward-compatible(老版本 artifact 多一字段不影响读取)

---

### [CONCERN-3] `participant_id` 全局唯一性未在 config load 阶段校验(中)

**位置**:`src/swallow/synthesis.py:71-96`(`synthesis_config_from_dict` / `_coerce_participant`)

**事实**:`synthesis_config_from_dict` 仅校验单个 participant 的 `participant_id` 非空,**未**检查 participants tuple 内 ID 两两互异,**未**检查 arbiter ID 与 participants 不冲突。

**风险**:
- 两个 participant 共享 ID `"p1"` → `persist_participant_artifact` 在 round 1 写两次同名文件 `synthesis_round_1_participant_p1.json`,后写覆盖前写,**静默丢失**一份产出;`_participant_summaries` 的 dict comprehension 也只保留一个 key,合并两个 participant 的 round_artifacts 列表,arbiter 看到的"4 个 participant"实际只有 3 个独立产出 + 1 个混乱列表
- arbiter 与 participant ID 冲突 → `_arbitration_prompt` 把 arbiter prompt 也加进 prior_artifacts,participant 本身不会写到 arbiter artifact(当前没有 arbiter artifact 落 round_n_participant_*.json),所以这个子情形低危,但仍是 schema 隐患

**建议**:
- 在 `synthesis_config_from_dict` 末尾加唯一性校验:
  ```python
  ids = [p.participant_id for p in participants]
  if len(set(ids)) != len(ids):
      raise ValueError("participants[].participant_id must be globally unique")
  if arbiter.participant_id in set(ids):
      raise ValueError("arbiter.participant_id must differ from all participants")
  ```
- 加守卫 `tests/test_synthesis.py::test_config_rejects_duplicate_participant_id`

design_decision §A.1 隐含"`participant_id` ULID 单次 synthesis 内唯一",但实施未做强校验。

---

### [CONCERN-4] `swl synthesis stage` duplicate 经 ValueError 暴露,CLI UX 不洁(低)

**位置**:`src/swallow/cli.py:2576-2580`

**事实**:duplicate 检测后 `raise ValueError("Synthesis arbitration is already staged: ...")`。`main()` 顶层无 try/except 包裹,真实 CLI 调用(`python -m swallow.cli synthesis stage --task ...`)会以 Python traceback 形式终止,exit code 非零(实际上是 1,但来自未捕获异常)。

**测试**:`tests/test_cli.py::test_synthesis_stage_rejects_duplicate` 用 `assertRaisesRegex` 断言异常,符合"raise"行为,但人类用户看到 traceback 是糟糕 UX。

**建议**:
- 将 duplicate 检测的 raise 改为 print error + return 非零 exit code(如 `return 2`),与 CLI 其他错误风格(如 `swl audit policy set` invalid kind)保持一致
- 测试相应改为 assert exit code 非零 + stdout/stderr 包含 `"already staged"`

design_decision §E.4 line 415 仅写"exit code 非零",未约束是否经 traceback 暴露。建议本 PR 内修复使 CLI 行为一致。

---

---

## 四、NOTE(共 4 项,信息级)

### [NOTE-D] design_decision §B.1 文字 vs 实现取值 — implementer 主动纠正了 design 文字错误

**位置**:
- 实现:`src/swallow/synthesis.py:19`(`_MPS_DEFAULT_HTTP_ROUTE = "local-http"`)、`synthesis.py:114-115`(`_route_is_path_a` 用 `executor_name == "http" and transport_kind == "http"`)
- design 文字:`docs/plans/phase62/design_decision.md` §B.1 line 285("实施时取 `router.route_by_name("local-claude-code")`")、line 268(`route.path == "A"`)

**核查 ROUTE_REGISTRY**(`src/swallow/router.py:325-346`、`router.py:469-491`):
| Route | executor_name | transport_kind | backend_kind | INVARIANTS §4 分类 |
|-------|---------------|----------------|--------------|-------------------|
| `local-http` | `http` | `http` | `http_api` | **Path A**(Controlled HTTP / provider-routed)|
| `local-claude-code` | `claude-code` | `local_process` | `local_cli` | **Path B**(CLI 黑箱)|

**判定**:design §B.1 自相矛盾 — 一边强调"MPS participant requires Path A"(line 268)、一边把 Path B 的 `local-claude-code` 标为"标准 Path A HTTP route"(line 285)。implementer 选取 `local-http` 才是**唯一同时满足 §B.1 上下文约束 + INVARIANTS §4 Path A 边界**的选择;若按 design 字面取 `local-claude-code`,反而会让 MPS participant 跑去 CLI 黑箱,违反 §B.1 自身的 `_route_is_path_a` 校验(以及 INVARIANTS §4 Path A 路径治理)。

`_route_is_path_a` 用结构特征(`executor_name == "http" and transport_kind == "http"`)替代 design 文字的 `route.path == "A"` 也是必要的:`RouteSpec`(`models.py:979-1019`)**无 `.path` 字段**,design 写法不可执行。

**结论**:**代码侧无需任何变更**,implementer 做出了正确的工程判断。仅需在 closeout 中显式记录"design §B.1 文字应纠正为 `local-http`"作为审计痕迹。

**建议**:
- 不在本 PR 内修订 design_decision.md(它已经 frozen 进 phase plan)
- 在 closeout.md 内显式记录该项 doc-vs-impl drift 与 implementer 的纠正决定
- 若未来需要"路由 path 分类"成为一等概念,在独立 phase 给 `RouteSpec` 增 `path: Literal["A","B","C"]` 字段,守卫从结构特征切换为字段断言

---

### [NOTE-A] `arbitration_artifact_id` 固定字符串而非 ULID

详见 §二 F 表行。design_decision §F schema 字段表写作 `<ULID>`,实现给定值 `"synthesis_arbitration"`。单 task 单 artifact 语义下不构成数据正确性问题,但与 §F 示例不一致。建议在 closeout 中显式声明:"phase 62 不为单 artifact 生成 ULID;若未来允许同 task 多次 synthesis(reset),此字段需切换为 ULID"。

### [NOTE-B] `test_synthesis_does_not_mutate_main_task_state` 字段覆盖不全

测试仅断言 5 个字段(`route_name` / `route_model_hint` / `route_transport_kind` / `route_taxonomy_role` / `route_taxonomy_memory_authority`)未被改写,但 `_participant_state_for_call` 实际 `replace()` 了 ≈ 17 个字段(包括 `executor_name` / `route_backend` / `route_executor_family` / `route_execution_site` / `route_remote_capable` / `route_dialect` / `route_capabilities` / `topology_*` 等)。理论上 leak 只可能经"mock 直接 mutate base_state"路径,5 字段已足以捕获;但若未来 transient state 通过非 replace 途径回写 base_state,守卫覆盖会有盲区。

**建议**:把守卫的 before/after 对比扩展到 `_participant_state_for_call` 内 replace 所有字段,或改为 `dataclasses.asdict(state)` 整体快照对比。当前为 NOTE 级,不阻塞合并。

### [NOTE-C] `_validate_config` 在 re-run 检查之前运行

`run_synthesis`(synthesis.py:339-343)先 `_validate_config`(可抛 `ValueError`)再检查 `arbitration_path.exists()`(抛 `RuntimeError`)。两次 stage 同 task 但 config 错误时,用户先看到 `ValueError`,而不是更精确的 `RuntimeError("synthesis already completed")`。

**建议**(可选):颠倒顺序,先 re-run 检查再 validate;不影响 happy path,UX 微调。当前为 NOTE 级。

---

## 五、Branch Advice

- **PR 创建建议**:
  - **可以创建 PR**(0 BLOCK,4 CONCERN 全部可在本 PR 内消化,4 NOTE 进 closeout 留痕)
  - 建议 Codex 在创建 PR 前优先消化 CONCERN-1 / CONCERN-3:它们是"运行时正确性"层面的隐患,合并后再补会显得草率
  - CONCERN-2 / CONCERN-4 影响小但建议同 PR 处理,避免 closeout 后立即开补丁 PR
  - NOTE-A / NOTE-D 进 closeout(NOTE-D 含 design §B.1 文字纠正)
- **PR scope**:`feat/phase62-multi-perspective-synthesis` 当前 5 个实现 commit + 1 个 docs commit(`3e3886f docs(phase62)`),scope 与 kickoff Goals 一致;**不**包含 `docs/active_context.md` 的状态 commit(待 review 完成后由 Codex 单独 `docs(state)` commit)
- **后续 commit 建议**:
  - 若 Codex 接受 CONCERN-1/2/3/4 修复:每条独立 commit,scope = `feat(synthesis)` 或 `fix(synthesis)`,跟随当前 milestone branch
  - 不要 squash 进现有 milestone commit,保留 review trail
- **PR 描述**:由 Codex 按 `.agents/templates/pr_body.md` 起草 `./pr.md`,引用本 review 的 CONCERN/NOTE 处理状态

---

## 六、Concerns Backlog 同步建议

本轮 review 暴露的项目中:
- **CONCERN-1 / 2 / 3 / 4**:建议 Codex 在本 PR 内消化,不写入 backlog(避免"Concern 立刻被记录又立刻被消化"的噪声)
- **NOTE-A / B / C / D**:不写入 backlog(NOTE-D 在 closeout.md 中显式记录 design §B.1 文字纠正)

如果 Codex 决定将 CONCERN-1 / 3 推迟到下一 phase,需要时再追加 backlog 条目。Phase 62 audit 阶段已经登记的 2 条 backlog Open(orchestrator.py:3145 stagedK 直写 / INVARIANTS §7 集中化函数缺失)本轮 review 未发现新触动。

---

## 七、整体评估

| 维度 | 评估 |
|------|------|
| 与 design_decision §A–§G 对齐度 | **高**(13/13 守卫落地,所有 §A.x / §B.x / §E.x 检查项 PASS) |
| INVARIANTS 合规 | **高**(§0.4 apply_proposal 入口、§4 Path A 经 Provider Router、§5 stagedK 经 Operator/CLI 边界、§7 paths 集中化)|
| 测试质量 | **中-高**(13 守卫 + e2e 覆盖率合理;3 个 NOTE 是覆盖深度建议) |
| 代码风格与既有约定一致性 | **高**(沿用 frozen dataclass / 模块隔离 / pure function / governance pattern) |
| 用户可见 UX | **中**(CONCERN-4 traceback、CONCERN-1 silent failure 是合并前应消化的瑕疵) |
| 治理债务清晰度 | **高**(audit/model-review 暴露的所有 BLOCKER/BLOCK 均已修复;backlog 显式登记 2 条已知漂移)|

**整体结论**:✅ **review 通过(条件)**。Codex 消化 CONCERN-1..4 后即可进入 Human Merge Gate;CONCERN-5 + NOTE-A/B/C 转入 closeout。
