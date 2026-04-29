---
author: claude
phase: phase63
slice: design-decomposition
status: revised-after-model-review
depends_on: ["docs/plans/phase63/kickoff.md", "docs/plans/phase63/context_brief.md", "docs/plans/phase63/design_audit.md", "docs/plans/phase63/model_review.md", "docs/design/INVARIANTS.md", "docs/design/DATA_MODEL.md", "src/swallow/governance.py"]
---

TL;DR(revised-after-model-review): **6 slice / 5 milestone**(新增 M0 pre-implementation audit slice)。M0 audit **3 项**:NO_SKIP guards report-only / store connection 模式 / **`_route_knowledge_to_staged` 触发场景(决定 §S2 走方案 A 还是方案 D)**。M1=S1 §7 集中化 / M2=S2 stagedK 治理(**方案 A:librarian_side_effect token + §5 矩阵更新;方案 D:下沉到 Specialist 内部,§5 不动**)+ S3 Repository 抽象层骨架(含 2 条 bypass 守卫)/ M3=S4 §9 13 条守卫批量(含 NO_SKIP 白名单)/ M4=S5 SQLite transaction-wrapped apply_proposal + append-only 审计 log。**已根据 model_review BLOCK 消化 3 BLOCK + 3 CONCERN**:Q1 §5 矩阵 M0-dependent(若方案 D 不需要更新)、Q2/Q6 增加 2 条 Repository bypass 守卫、Q3 ACTOR 闭集扩展并移除 `action`、Q4 新增 M0 audit slice、Q5 改用 SQLite `BEGIN IMMEDIATE` transaction。完结后 INVARIANTS §9 17 条守卫全部实装,5 条 Phase 61/62 宪法漂移 Open 全部 Resolved。

## 方案总述

Phase 63 是宪法层债务收口 phase。**方案核心**:把 Phase 61(apply_proposal 入口)与 Phase 62(MPS)留下的 5 条已登记 Open 一次性消化,把 INVARIANTS §5 / §7 / §9 三个治理面的代码侧实装拉齐到设计文档定义。**实装路径(revised-after-model-review)**:**M0 pre-implementation audit**(NO_SKIP_GUARDS report-only 扫描 + store 函数 connection 模式调查;若暴露大范围 §0 红灯则拆 Phase 63.5)→ M1 集中化函数 → M2 同步收敛 stagedK + 引入 Repository 骨架 + Repository bypass 守卫 → M3 批量补 §9 守卫 → M4 SQLite transaction-wrapped 事务回滚。**等价性保证**:对外可观测行为零变化(staged candidate 写入语义、apply_proposal 签名、MPS 编排均保持等价,且 SQLite transaction 包裹后中间状态对 reader 不可见)。**§5 矩阵文字本 phase 内更新一行**(Orchestrator 行 stagedK 列):从 "-" 改为说明性文字,显式记录 `librarian_side_effect` token 等价于 W*。

## Slice 拆解

### S0 — Pre-implementation audit(M0 单独 review,**新增 - 消化 model_review Q4/Q5**)

**目标**:在 M1 实装开始前,以**read-only / report-only 模式**完成两项 audit,产出决策依据;不引入任何代码改动(只增 audit 脚本与报告)。

**audit 任务**:
1. **NO_SKIP_GUARDS pre-implementation 扫描**(消化 model_review Q4):用 S4 设计的 AST 守卫逻辑(report-only)扫描既有 src/swallow/ 代码,列出 8 条 NO_SKIP_GUARDS 当前会触发红灯的位置。8 条守卫是:
   - `test_no_executor_can_write_task_table_directly`
   - `test_state_transitions_only_via_orchestrator`
   - `test_validator_returns_verdict_only`
   - `test_path_b_does_not_call_provider_router`
   - `test_specialist_internal_llm_calls_go_through_router`
   - `test_canonical_write_only_via_apply_proposal`(Phase 61 已实装,验证仍通过)
   - `test_only_apply_proposal_calls_private_writers`(Phase 61 已实装)
   - `test_route_metadata_writes_only_via_apply_proposal`(Phase 61 已实装)
2. **store 函数 connection 模式 audit**(消化 model_review Q5):列出 `apply_proposal` 链路上四个核心 store 写函数的 connection 处理模式:
   - `save_route_weights` / `apply_route_weights`(`router.py`)
   - `save_route_capability_profiles` / `apply_route_capability_profiles`(`router.py`)
   - 是否接受外部 `connection` / `cursor` 参数?
   - 内部是否自己 `BEGIN; COMMIT;`?
   - 与 SQLite WAL 默认 isolation 兼容性如何?
   - canonical / policy 链路对应函数同样 audit
3. **`_route_knowledge_to_staged` 触发场景 audit(新增,Human 反馈驱动)**:`orchestrator.py:3131` 的 `_route_knowledge_to_staged` 是按 `state.route_taxonomy_memory_authority ∈ {"canonical-write-forbidden", "staged-knowledge"}` 路由的副作用应用流,**不限于 Librarian Specialist**。本项 audit 必须明确:
   - 当前哪些 task taxonomy 会被 route 到 `taxonomy_memory_authority ∈ {"canonical-write-forbidden", "staged-knowledge"}` 的路由?(grep route table / route policy / taxonomy 配置)
   - 这些 taxonomy 对应的 executor type 是否**全部都是 Librarian Specialist**?
   - 若有非-Librarian executor(General Executor / 其他 Specialist)也走这条流,列出具体 taxonomy + executor 对应关系
   - audit 输出决定 §S2 / §G2 设计走方案 A(librarian_side_effect token + §5 矩阵更新)还是方案 D(把副作用应用下沉到 Specialist 内部,§5 矩阵不动)

**方案 A vs 方案 D 决策点(M0-dependent)**:

| audit 结论 | 推荐方案 | scope 影响 |
|------------|---------|-----------|
| 仅 Librarian Specialist 触发 | **方案 D**(下沉到 Librarian Specialist 内部写 stagedK,Specialist 行 stagedK 列 §5 已 W,不动 INVARIANTS 文字) | Phase 63 scope 不变,§S2 重写为 Specialist-internal 实装 |
| 多种 executor 触发,但全部是 Specialist 类 | **方案 D**(归入对应 Specialist 内部),可能涉及多 Specialist 改动 | Phase 63 scope 略扩,§S2 重写涉及多个 Specialist 模块 |
| 涉及 General Executor | **方案 A**(librarian_side_effect token + §5 矩阵更新),或 Phase 63.5 拆出"task 后处理副作用归属重构" | 由 Human 决策:scope 控制 vs 治理彻底性 |

**方案 D 概述(若 audit 支持)**:
- 把 `_route_knowledge_to_staged` 函数体从 `orchestrator.py:3131` 移到 Librarian Specialist(或对应 Specialist)的内部 task hook
- 调用时机改为 Specialist task `execute()` 完成时返回 side_effects(对齐 Phase 36 S1 引入的 `_apply_librarian_side_effects()` 模式)
- Specialist 内部直接调 `submit_staged_candidate(...)`(§5 矩阵 Specialist 行 stagedK 列 = `W`,合规)
- INVARIANTS §5 矩阵文字**不动**,§9 守卫 `test_no_executor_can_write_task_table_directly` 等也不需要为 Orchestrator 开特例
- non-goals 不需要收紧到允许 §5 矩阵文字更新

**方案 A 概述(若 audit 强制)**:维持 revised-after-model-review 当前设计 —— 引入 `librarian_side_effect` token + §5 矩阵 Orchestrator 行更新一行。

**影响范围**:
- 新增:`docs/plans/phase63/m0_audit_report.md`(由 Codex 在 M0 内产出,Claude 评审)
- 新增:`tests/audit_no_skip_drift.py`(report-only 扫描脚本,M0 完成后保留作为 S4 守卫的实装基础;不在 pytest collection 中)
- 新增(可能):`tests/audit_route_knowledge_to_staged.py`(audit 第 3 项的扫描脚本,report-only)

**关键设计决策**:
- **M0 是 read-only**:不写任何生产代码,不修改 INVARIANTS / DATA_MODEL,不创建 Repository / identity / workspace 模块
- **report-only 扫描**:不会让 pytest 红灯;只产出 markdown 报告
- **scope decision rule**(更新):Claude 在 M0 报告产出后做**两个**决策:
  - **NO_SKIP audit 决策**:若 NO_SKIP 红灯 ≤ 2 处且涉及简单修复 → Phase 63 维持计划;若 NO_SKIP 红灯 ≥ 3 处或涉及核心模块大幅修复 → 拆 Phase 63 + Phase 63.5
  - **方案 A vs D 决策**:按上方决策表选择 §S2 / §G2 走方案 A 还是方案 D;若选方案 D,§S2 / §G2 / kickoff non-goals / risk_assessment R12 同步重写,**§5 矩阵不再更新**

**验收条件**:
- `docs/plans/phase63/m0_audit_report.md` 产出,包含**三项**audit 的完整结果
- `tests/audit_no_skip_drift.py` 可运行,产出 NO_SKIP 红灯位置列表
- Claude 在 M0 报告基础上做出 phase scope 决策 + §S2 方案选择(A 或 D)

**风险评级**:影响范围 1 / 可逆性 1 / 依赖 1 = 3(低)。M0 是无代码改动的探查 slice,回滚成本最低。

---

### S1 — §7 集中化函数 + 2 条守卫真实化(M1 单独 review)

**目标**:引入 `swallow/identity.py` 与 `swallow/workspace.py`,把 INVARIANTS §7 的 `local_actor()` / `resolve_path()` 集中化要求落到代码;实装 §9 表内 `test_no_hardcoded_local_actor_outside_identity_module` 与 `test_no_absolute_path_in_truth_writes` 两条守卫。

**影响范围**:
- 新增:`src/swallow/identity.py`(导出 `local_actor() -> str`,内部返回 `"local"` 字面量,**唯一**允许的 actor 字面量出现位置)
- 新增:`src/swallow/workspace.py`(导出 `resolve_path(path: Path | str, *, base: Path | None = None) -> Path`,封装 `.resolve()` 调用 + workspace_root 解析)
- 改动(actor-semantic 改走 `local_actor()`):`src/swallow/models.py`(SQL DEFAULT 字符串保持不变;**Python 层 INSERT 时 actor 字段值用 `local_actor()`**;line 297 `action="local"` 由 S1 实装时单独 audit 语义)、`src/swallow/store.py`、`src/swallow/orchestrator.py`(actor 写入点)
- 改动(path 绝对化改走 `resolve_path()`):`src/swallow/orchestrator.py` lines 2595-2630+、`src/swallow/executor.py:791`、`src/swallow/literature_specialist.py:80`、`src/swallow/quality_reviewer.py:41`、`src/swallow/ingestion/pipeline.py` lines 52, 125、`src/swallow/web/api.py` lines 12, 35
- 不动(站点语义保留):`src/swallow/router.py` 11+ 处 `execution_site="local"`、`src/swallow/execution_fit.py`、`src/swallow/cost_estimation.py`、`src/swallow/dialect_data.py` 中的 `execution_site="local"`
- 新增:`tests/test_invariant_guards.py` 增加 `test_no_hardcoded_local_actor_outside_identity_module` / `test_no_absolute_path_in_truth_writes`

**关键设计决策**:
- **disambiguation 策略(消化 CONCERN S1 #1 + model_review Q3)**:守卫 pattern 用 AST 而非 grep。actor 字面量定义为"出现在 actor-semantic kwarg 上下文中的 `"local"`"。**actor-semantic kwarg 闭集(authoritative,revised-after-model-review,移除 `action` + 扩展常见 actor kwargs)**:
  ```python
  ACTOR_SEMANTIC_KWARGS = frozenset({
      # 直接 actor 标识
      "actor", "actor_name", "actor_id",
      # *_by 模式
      "submitted_by", "performed_by", "created_by", "updated_by",
      "modified_by", "deleted_by", "requested_by", "approved_by",
      "reviewed_by", "applied_by", "committed_by",
      "authored_by", "signed_by", "initiated_by",
      # 调用方 / 主体身份
      "caller", "owner", "owner_id",
      "user", "user_id", "username",
      "principal", "principal_id",
      "operator", "operator_id",
      # 来源标识
      "originator", "agent", "agent_id",
      # Swallow-specific
      "executor_name",
  })
  ```
  此闭集定义在 `tests/test_invariant_guards.py` 顶部作为模块级常量。守卫扫描 AST,识别 `kwarg.arg in ACTOR_SEMANTIC_KWARGS` 且 `kwarg.value` 是 `ast.Constant("local")` 的位置。**`risk_assessment.md` R2 已与本闭集对齐**(同一份白名单)。`execution_site="local"` 是 site-semantic,不在闭集中,守卫不会误报。**`action` 已从闭集中移除**(model_review Q3 反馈:`action` 通常是动作类型,不是身份;`models.py:297 action="local"` 的具体语义由 S1 实装时单独 audit:若是 actor 含义,改字段名;若是动作,保留)。未来若引入新 actor 上下文 kwarg,在该闭集显式扩展(扩展行为本身需 phase-level review)。
- **DDL DEFAULT 字符串豁免(消化 CONCERN S1 #3)**:`models.py` 中 SQL DDL 字符串内的 `DEFAULT 'local'` 字面量(例如 `... actor TEXT DEFAULT 'local' ...` 在 `CREATE TABLE` 字符串中)是嵌入在 Python 字符串内的 SQL 字面量,**不在 actor-semantic kwarg 调用语境中**,守卫 AST 扫描自然不会命中(因为 AST 看到的是 `Constant("CREATE TABLE ... DEFAULT 'local' ...")` 整个字符串,不是 kwarg)。Codex 实装时**保持 DDL 中 `DEFAULT 'local'` 不变**,因为 SQLite default value 在 schema 层固化、运行时不动态调用 Python 函数;Python 层 INSERT 显式传值时,actor 字段的值由 `local_actor()` 提供。
- **identity.py 设计**:仅一个函数 `local_actor() -> str`,无参数,返回 `"local"`。未来切换 multi-actor 时只需替换此函数实现,所有调用方零改动。
- **workspace.py 设计(消化 CONCERN S1 #2)**:`resolve_path(path: Path | str, *, base: Path | None = None) -> Path`。**base 解析优先级(authoritative)**:
  1. 显式传入的 `base` 参数(若非 None) → 直接使用
  2. 环境变量 `SWL_ROOT`(若设置且非空)→ 使用为 base
  3. 当前 workspace 根的 fallback:`Path.cwd()`(仅用于无 SWL_ROOT 的开发环境;生产部署应总是设置 SWL_ROOT)
  
  仅在持久化路径解析时使用 `resolve_path()`。Truth 写入函数禁止接收 `Path.absolute()` 或 `Path.resolve()` 调用结果作为持久化字段(由 §9 `test_no_absolute_path_in_truth_writes` 守卫验证)。

**验收条件**:
- `swallow.identity.local_actor()` / `swallow.workspace.resolve_path()` 存在并被调用
- `grep -rn '"local"' src/swallow/` 在 `identity.py` 与 `tests/` 之外的 **actor-semantic** 命中数为 0(grep + 人工 audit;site-semantic 不计)
- 新增 2 条守卫测试通过
- 全量 pytest 通过(回归无破坏)

**风险评级**:影响范围 3 / 可逆性 2 / 依赖 1 = 6(中);跨多个模块的 import 改动,但每个改动都是机械替换,回滚成本可控。

---

### S2 — stagedK 治理通道(orchestrator.py:3145 收敛 + OperatorToken 扩展)(M2 part)

> **⚠ M0-dependent 双方案待定(2026-04-29 Human 反馈驱动)**:本 slice 当前文字是**方案 A**(librarian_side_effect token + §5 矩阵更新)的版本。M0 audit 第 3 项(`_route_knowledge_to_staged` 触发场景)结论可能驱动改走**方案 D**(把副作用应用下沉到对应 Specialist 内部,§5 矩阵不动)。决策表见 §S0 "方案 A vs 方案 D 决策点"。**Codex 实装本 slice 前必须先看 M0 audit 报告与 Claude 在 active_context 中的方案选择**。
>
> **方案 D 触发时本 slice 重写要点**:`_route_knowledge_to_staged` 函数体从 `orchestrator.py:3131` 移到对应 Specialist 内部 task hook(类比 Phase 36 S1 `_apply_librarian_side_effects()` 模式);Specialist 直接调 `submit_staged_candidate(...)`(§5 Specialist 行 stagedK = `W`,合规);**不引入 `librarian_side_effect` token**;**不更新 INVARIANTS §5 矩阵**;non-goals 不收紧;`OperatorToken` / `_VALID_OPERATOR_SOURCES` / `ProposalTarget` 三个 enum 都不动。

**目标**(方案 A 假设):把 `orchestrator.py:3145` 的 `submit_staged_candidate(...)` 直写改为经 `register_staged_knowledge_proposal(...) → apply_proposal(proposal_id, OperatorToken(source="librarian_side_effect"), target=STAGED_KNOWLEDGE)` 两步通道;扩展 `_VALID_OPERATOR_SOURCES` 增加 `librarian_side_effect`;扩展 `ProposalTarget` enum 增加 `STAGED_KNOWLEDGE = "staged_knowledge"`;不修改 cli.py:2590 与 ingestion/pipeline.py 的合规调用。

**audit 消化(BLOCKER S2 / S3)**:已修正 `apply_proposal` 调用形式与既有签名对齐。
- 既有签名(governance.py:209,DATA_MODEL §4.1):`apply_proposal(proposal_id: str, operator_token: OperatorToken, target: ProposalTarget) -> ApplyResult`
- 既有 `OperatorToken` 字段(governance.py:36):`source: OperatorSource, reason: str | None = None`,**不含 `actor`**(Phase 61 故意省略,不在本 phase scope 扩展)
- 既有调用模式:**两步** —— 先 `register_*_proposal(...)` 把 payload 注册到 `_PENDING_PROPOSALS`(返回 `proposal_id`),再 `apply_proposal(proposal_id, token, target)` 触发分发(内部 `_load_proposal_artifact(proposal_id, target)` 读取)

**影响范围**:
- 改动:`src/swallow/governance.py`:
  - `_VALID_OPERATOR_SOURCES` 增加 `"librarian_side_effect"` 元素(line 33 附近)
  - `ProposalTarget` enum 增加 `STAGED_KNOWLEDGE = "staged_knowledge"`(line 30-33)
  - 新增 `_StagedKnowledgeProposal` dataclass(类比 `_CanonicalProposal` / `_RouteMetadataProposal`,字段对应 `StagedCandidate` payload)
  - 新增 `register_staged_knowledge_proposal(payload: StagedCandidate) -> str` 函数(类比 `register_canonical_proposal`),返回新生成的 `proposal_id`(ULID),写入 `_PENDING_PROPOSALS[(STAGED_KNOWLEDGE, proposal_id)]`
  - `apply_proposal` 内部 dispatch 增加 `STAGED_KNOWLEDGE` 分支:调用新增的 `_apply_staged_knowledge(proposal, operator_token, proposal_id=proposal_id)` 内部函数,内部调用 `submit_staged_candidate`
  - `_validate_target` 增加 `STAGED_KNOWLEDGE` + `_StagedKnowledgeProposal` 校验
- 改动:`src/swallow/orchestrator.py:3145` —— 改为两步调用:
  ```python
  proposal_id = governance.register_staged_knowledge_proposal(
      payload=StagedCandidate(..., submitted_by=state.executor_name, ...)
  )
  governance.apply_proposal(
      proposal_id,
      OperatorToken(source="librarian_side_effect", reason=f"librarian side effect for task {state.task_id}"),
      ProposalTarget.STAGED_KNOWLEDGE,
  )
  ```
- 不动:`cli.py:2590`(Operator path,合规;`source="cli"` 已存在)、`ingestion/pipeline.py` 4 处(Specialist path,合规)
- 新增:`tests/test_invariant_guards.py` 增加 `test_only_orchestrator_uses_librarian_side_effect_token` 守卫

**关键设计决策**:
- **守卫实装策略(消化 BLOCKER S2)**:**AST-based**,与 S1 / S4 一致。具体规则:
  1. 扫描 `src/swallow/` 下所有 `.py` 文件的 AST
  2. 找出所有 `OperatorToken(...)` 调用节点(`ast.Call` 且 callee 是 `Name("OperatorToken")` 或 `Attribute("OperatorToken")`)
  3. 对每个调用,检查关键字参数 `source` 的值是否为字符串字面量 `"librarian_side_effect"`
  4. 若是,记录调用所在文件路径
  5. **断言**:命中文件集合 ⊆ `{"src/swallow/orchestrator.py", "src/swallow/governance.py"}`(后者用于 `_VALID_OPERATOR_SOURCES` 集合定义,不算 token 签发)
  6. **额外断言**:`OperatorToken(source="librarian_side_effect")` 调用形式必须存在于 `orchestrator.py` 至少一次(防止枚举值定义但无 caller 的伪实装)
  7. tests/ 目录豁免(单元测试可以构造任意 token)
- **token 特权语义**:`librarian_side_effect` 是**有限特权扩展**,仅 orchestrator 持有,不暴露给 CLI 子命令、不暴露给 Specialist。守卫验证签发路径
- **等价性保证**:`_apply_staged_knowledge` 内部仍调 `submit_staged_candidate`,行为对外等价,只多了 governance 审计点(写 `event_log` 一条 `kind="apply_proposal"` 记录,target=`staged_knowledge`)
- **§5 矩阵文字更新(消化 model_review Q1 BLOCK)**:**本 phase 内更新 `docs/design/INVARIANTS.md` §5 矩阵 Orchestrator 行 stagedK 列**(从 "-" 改为 "W*(via apply_proposal + librarian_side_effect token)"),并配套补充矩阵下方注脚解释 librarian_side_effect token 的有限特权语义(只能由 orchestrator 签发,内部对应 librarian agent task 执行的 verified knowledge → staged candidate 转换)。这个更新是 S2 实装的必要部分,作为 docs/design 提交进入本 phase PR(独立 commit `docs(design): update §5 matrix for librarian_side_effect token`)。理由:不更新 §5 文字会让 token 引入与本 phase "消化宪法漂移" 的目标自我矛盾。**non-goals 同步收紧**:从"不修改 INVARIANTS 不变量定义文字"细化为"不修改 INVARIANTS §0 / §1 / §2 / §3 / §4 / §6 / §7 / §8 等核心原则文字;§5 矩阵 Orchestrator 行 stagedK 列允许在本 phase 实装内更新一行 + 配套注脚"。
- **proposal_id 生成**:`register_staged_knowledge_proposal` 内部生成 ULID(类比 `register_route_metadata_proposal`),不依赖调用方传入

**验收条件**:
- `grep -n 'submit_staged_candidate' src/swallow/orchestrator.py` 命中 0(已收敛)
- `grep -n '"librarian_side_effect"' src/swallow/` 命中 ≤3(`_VALID_OPERATOR_SOURCES` 集合定义 + `register_staged_knowledge_proposal` 内部 + `orchestrator.py:3145` 调用点)
- `test_only_orchestrator_uses_librarian_side_effect_token` 守卫通过(AST 扫描得到上述命中集)
- `ProposalTarget.STAGED_KNOWLEDGE` 存在
- `governance.register_staged_knowledge_proposal(payload)` / `governance._apply_staged_knowledge(...)` 存在
- 全量 pytest 通过(orchestrator 既有 staged candidate 写入测试零破坏)

**风险评级**:影响范围 2 / 可逆性 2 / 依赖 1 = 5(低-中)。

---

### S3 — Repository 抽象层骨架 + `_PENDING_PROPOSALS` 重复检测(M2 part,**高风险**)

**目标**:引入 `swallow/truth/{knowledge,route,policy}.py` 三个 Repository 模块,封装现有 store 写函数;`governance.py` 不再直接 import store 函数,而是经 Repository 调用;`_PENDING_PROPOSALS` 改为 Repository 管理的注册表,重复 `proposal_id` 第二次 register 抛 `DuplicateProposalError`。

**影响范围**:
- 新增:`src/swallow/truth/__init__.py`、`src/swallow/truth/knowledge.py`(`KnowledgeRepo` 类:`_promote_canonical(...)`)、`src/swallow/truth/route.py`(`RouteRepo` 类:`_apply_metadata_change(...)`)、`src/swallow/truth/policy.py`(`PolicyRepo` 类:`_apply_policy_change(...)`)
- 改动:`src/swallow/governance.py` —— 移除 `from .router import save_route_weights, apply_route_weights, ...` 等直接 import;改为 `from .truth.route import RouteRepo`;`apply_proposal` 内部分发到对应 Repository 方法;`_PENDING_PROPOSALS` 改为 Repository-managed 字典,`register_*` 函数检测 `(target, proposal_id)` 已存在时抛 `DuplicateProposalError`
- 改动:`src/swallow/cli.py` —— 若 CLI 直接 import 任何已 Repository 化的 store 函数,改走 governance 通道(已是 governance 调用方)
- 改动:`tests/test_invariant_guards.py` 更新 `test_only_apply_proposal_calls_private_writers`(已存在 Phase 61 实装,扫描目标扩展到 `truth/*.py` 的 `_promote_canonical` / `_apply_*` 方法)
- 新增:`tests/test_invariant_guards.py` 增加 `test_only_governance_calls_repository_write_methods`(消化 model_review Q2 + Q6:验证 Repository 私有写方法只被 governance.py 调用)
- 新增:`tests/test_invariant_guards.py` 增加 `test_no_module_outside_governance_imports_store_writes`(消化 model_review Q6:验证非 governance / 非 truth/* 模块不能直接 import canonical / route / policy 的 store 写函数,如 `save_route_weights` / `apply_route_weights` / `apply_canonical_promotion` 等)
- 新增:`tests/test_governance.py` 增加 `test_duplicate_proposal_id_raises` 测试

**关键设计决策**:
- **Repository 设计原则**:**最小封装**。Repository 类只做一层方法转发,不引入新业务逻辑、不缓存、不做事务管理。每个 Repository 类的写方法保持与现有 store 函数 1:1 对应
- **现有 store 函数签名映射(消化 CONCERN S3 #2)**:Codex 实装时按以下映射建立 Repository 私有方法。**实装前必须先 grep 现有签名作为最终对照**(签名以 `src/swallow/router.py` / `store.py` / `knowledge_store.py` / `mps_policy_store.py` 当前代码为准):
  | Repository 私有方法 | 转发到 | 来源模块 |
  |---------------------|--------|----------|
  | `KnowledgeRepo._promote_canonical(...)` | `promote_to_canonical` 或 `apply_canonical_promotion`(以现有名为准) | `knowledge_store.py` |
  | `RouteRepo._apply_metadata_change(...)` | 顺序调用 `save_route_weights` → `apply_route_weights` → `save_route_capability_profiles` → `apply_route_capability_profiles` | `router.py` |
  | `RouteRepo.record_health(...)`(public) | `record_route_health` 或同名函数 | `router.py` |
  | `PolicyRepo._apply_policy_change(...)` | `save_policy` / `apply_policy` 或既有 policy store 写函数 | `mps_policy_store.py` 与现有 policy store |
  
  Codex 实装时:S3 PR body 必须包含一份 actual signature mapping table(列出每个 Repository 私有方法的完整 Python 签名 vs 转发的原 store 函数签名),Claude review 时验证一致性。
- **`_promote_canonical` / `_apply_metadata_change` / `_apply_policy_change` 是 private**:DATA_MODEL §4.1 守卫 `test_only_apply_proposal_calls_private_writers` 验证这些方法只能被 `governance.apply_proposal` 调用,不能被外部直接调用。Repository 类的公开方法**只允许 read**(写权限只通过 governance.apply_proposal)
- **Repository bypass 守卫策略(消化 model_review Q2 + Q6)**:Python `_underscore` 是约定不强制,需要硬守卫:
  - **守卫 A**(`test_only_governance_calls_repository_write_methods`,§9 表外):AST 扫描 `src/swallow/` 下所有 `.py` 文件中对 `KnowledgeRepo._promote_canonical` / `RouteRepo._apply_metadata_change` / `PolicyRepo._apply_policy_change`(以及任何以 `_` 开头的 Repository 写方法)的调用。允许调用集合 ⊆ `{src/swallow/governance.py}`(governance 内部 dispatch);tests/ 豁免
  - **守卫 B**(`test_no_module_outside_governance_imports_store_writes`,§9 表外):AST 扫描 `src/swallow/` 下所有 `.py` 文件,寻找对 canonical / route / policy store 写函数的 import:`from .router import (save_route_weights | apply_route_weights | save_route_capability_profiles | apply_route_capability_profiles)`、`from .knowledge_store import (apply_canonical_promotion | promote_to_canonical | ...)`、`from .mps_policy_store import (save_policy | apply_policy | ...)`(具体函数名以 M0 audit 报告中现有 store 函数为准)。允许 import 集合 ⊆ `{src/swallow/governance.py, src/swallow/truth/knowledge.py, src/swallow/truth/route.py, src/swallow/truth/policy.py}`。**例外**:Provider Router 的 `record_health` 等读路径或 health 写路径不在守卫范围内(只针对 canonical / metadata / policy 写函数)
  - 两条守卫都是 §9 表外的"额外架构守卫",不计入 §9 表 17 条守卫
- **`_PENDING_PROPOSALS` key 与 duplicate 检测(消化 CONCERN S3 #3)**:既有实装(governance.py:120 / 154 / 等)使用 `key = (target, normalized_id)` 元组,本 phase **保持元组 key**(与 kickoff §G3 简写"重复 proposal_id"对齐:实质是 `(target, proposal_id)` 元组重复)。`register_*` 函数检测 `key in _PENDING_PROPOSALS` 时抛 `DuplicateProposalError`,异常消息包含 `target.value` 与 `proposal_id`。**kickoff §G3 同步修订为元组 key 描述**(见本 phase revised-after-audit kickoff)。
- **`_PENDING_PROPOSALS` 生命周期**:仍是模块级 in-memory 字典(本 phase 非目标:不引入 durable proposal artifact 层),但增加 register 时的存在检查。**Phase 63 决策:暂不增加 evict / cleanup**(长 process 内存累积仍是 Open),避免本 phase 范围扩张
- **接口签名稳定性**:`apply_proposal(proposal_id: str, operator_token: OperatorToken, target: ProposalTarget) -> ApplyResult` 三参数签名不变(与 governance.py:209 / DATA_MODEL §4.1 一致);Repository 是 governance 内部实装细节,不 leak 到 governance 调用方

**验收条件**:
- `grep -n 'from .router import' src/swallow/governance.py` 不命中 `save_route_weights` / `apply_route_weights` / `save_route_capability_profiles` / `apply_route_capability_profiles`
- `swallow.truth.knowledge.KnowledgeRepo._promote_canonical` / `swallow.truth.route.RouteRepo._apply_metadata_change` / `swallow.truth.policy.PolicyRepo._apply_policy_change` 存在
- `test_duplicate_proposal_id_raises` 通过
- `test_only_apply_proposal_calls_private_writers` 守卫扫描目标更新后通过
- **`test_only_governance_calls_repository_write_methods` 通过**(Repository 私有写方法仅 governance.py 调用)
- **`test_no_module_outside_governance_imports_store_writes` 通过**(非 governance / 非 truth/* 模块不直接 import canonical / route / policy store 写函数)
- 全量 pytest 通过(governance 既有测试零破坏)

**风险评级**:影响范围 3 / 可逆性 2 / 依赖 2 = **7(高风险)**。governance.py 是 Phase 61 引入的核心治理入口,本 slice 重塑其依赖图。建议在 Codex 实现时优先做"等价回归测试"——先跑现有 governance 测试套件,再引入 Repository,逐步迁移。

**SCOPE WARNING(phase-guard)**:本 slice 显著重塑 governance.py 内部结构,虽然对外接口签名不变,但 Codex 实现层面需谨慎避免:
- 不要顺手修改 store 函数本身(non-goal)
- 不要给 Repository 引入读方法(本 phase 只做写收敛)
- 不要做 durable proposal artifact 层(后续 phase 方向)

---

### S4 — §9 剩余 13 条守卫批量实装(M3 单独 review)

**目标**:实装 §9 标准表 17 条中尚未实装的 14 条守卫(Phase 61 已实装 3 条 apply_proposal 守卫;S1 补 2 条 §7 集中化守卫;本 slice 补剩余 12 条 §9 表内 + 1 条 S5 配套事务回滚守卫 = 13 条新增)。

**影响范围**:
- 改动:`tests/test_invariant_guards.py` 增加 13 条守卫(12 条 §9 表内 + 1 条 S5 配套事务回滚守卫):
  - **行为合规类(6 条)**:`test_no_executor_can_write_task_table_directly`、`test_state_transitions_only_via_orchestrator`、`test_path_b_does_not_call_provider_router`、`test_validator_returns_verdict_only`、`test_specialist_internal_llm_calls_go_through_router`、`test_route_override_only_set_by_operator`
  - **ID & 不变量类(5 条)**:`test_all_ids_are_global_unique_no_local_identity`、`test_event_log_has_actor_field`、`test_no_foreign_key_across_namespaces`、`test_append_only_tables_reject_update_and_delete`、`test_artifact_path_resolved_from_id_only`
  - **UI 边界(1 条)**:`test_ui_backend_only_calls_governance_functions`
  - **事务回滚(1 条,S5 配套)**:`test_apply_proposal_rollback_executes_on_failure`
- 可能新增:`tests/conftest.py` 或 `tests/fixtures/` 引入 SQLite trigger 基础设施(若 `test_append_only_tables_reject_update_and_delete` 需要)
- 可能改动:`src/swallow/store.py` / migration 脚本 —— 若 `test_append_only_tables_reject_update_and_delete` 暴露既有 append-only 表缺少 trigger,本 slice 内补齐

**关键设计决策**:
- **守卫实装策略**:静态分析(AST scan)优先,运行时验证次之。每条守卫的验证方式在守卫 docstring 中说明
- **`test_append_only_tables_reject_update_and_delete` 被测表清单(消化 CONCERN S4 #3)**:S4 实装时,守卫被测表清单**仅包含既有 4 张 append-only 表**:`event_log` / `event_telemetry` / `route_health` / `know_change_log`(DATA_MODEL §4.2)。S5 引入的 `route_change_log` / `policy_change_log` 表在 S5 实装内**同步扩展**该守卫的被测表清单(S5 验收条件包含此项)。**Milestone 边界规则**:M3(S4)review 时该守卫只覆盖既有 4 张表;M4(S5)review 时该守卫扩展到 6 张表。Codex 在 S4 实装时在守卫 docstring 中显式标注 `# Phase 63 S5 will extend this list with route_change_log / policy_change_log`。
- **SQLite trigger 部署**:DATA_MODEL §4.2 列出的 append-only 表需要 SQLite UPDATE / DELETE trigger 显式 RAISE。S4 实装时审计现有 schema,若 trigger 缺失,补齐;补齐方式为 store 初始化路径 `CREATE TRIGGER IF NOT EXISTS`(idempotent)。这是 S4 唯一可能引入 schema 变化的位置。
- **暴露既有漂移的处理(消化 CONCERN S4 #1)**:若批量激活后发现既有代码触发某条守卫红灯,**优先修代码、不削弱守卫**。修改超出本 slice 范围时,在 risk_assessment 中标注 R6,由 Claude 评审决定是否拆出独立 slice。**绝对不可 skip 守卫白名单(authoritative)**(与 INVARIANTS §0 四条核心不变量直接对应):
  ```
  NO_SKIP_GUARDS = {
      # §0 第 1 条 — Control 只在 Orchestrator 和 Operator 手里
      "test_no_executor_can_write_task_table_directly",
      "test_state_transitions_only_via_orchestrator",
      "test_validator_returns_verdict_only",
      # §0 第 3 条 + §4 — LLM 调用三条路径
      "test_path_b_does_not_call_provider_router",
      "test_specialist_internal_llm_calls_go_through_router",
      # §0 第 4 条 — apply_proposal 唯一入口(已实装,本 phase 不动)
      "test_canonical_write_only_via_apply_proposal",        # Phase 61 既有
      "test_only_apply_proposal_calls_private_writers",      # Phase 61 既有(S3 更新扫描目标)
      "test_route_metadata_writes_only_via_apply_proposal",  # Phase 61 既有
  }
  ```
  红灯落在以上守卫中任一条 → **不允许 `pytest.skip`,必须本 phase 修代码**。其他 §9 守卫(ID & 不变量类 / UI 边界)红灯可在 Codex 上报、Claude 评估后决定是否 skip + 登记 Open(R6 流程)。
- **`test_only_apply_proposal_calls_private_writers` 与 S3 的关系(消化 CONCERN S4 #2)**:此守卫已在 Phase 61 实装,扫描目标为 governance.py 内的 `_apply_canonical` / `_apply_route_metadata` / `_apply_policy`。S3 引入 Repository 抽象层后,该守卫扫描目标应**扩展**到 `truth/{knowledge,route,policy}.py` 的 `_promote_canonical` / `_apply_metadata_change` / `_apply_policy_change`。**S3 验收条件包含此守卫扫描目标更新;不计入 S4 的"12 条 §9 表内新增"计数**(它是修改既有守卫,不是新增)。修改若破坏该守卫由 S3 PR 负责回归。

**验收条件**:
- INVARIANTS §9 标准表 17 条全部存在于 `tests/test_invariant_guards.py`
- 12 条新守卫全部通过
- `test_append_only_tables_reject_update_and_delete` 在所有 §4.2 append-only 表上通过
- 全量 pytest 通过

**风险评级**:影响范围 1 / 可逆性 1 / 依赖 2 = 4(低)。

---

### S5 — `apply_proposal` SQLite-transaction-wrapped 事务回滚 + append-only 审计 log(M4 单独 review)

**目标**:**用 SQLite transaction 包裹 apply_proposal 内部的多步 store 写**(消化 model_review Q5 BLOCK)。`save_route_weights → apply_route_weights → save_route_capability_profiles → apply_route_capability_profiles` 四步序列全部包在单一 SQLite `BEGIN IMMEDIATE` transaction 内,所有步骤成功才 COMMIT;任一步失败 SQLite 原生 ROLLBACK(无需手工 compensating)。中间状态对 reader 不可见。新增 `route_change_log` / `policy_change_log` append-only 审计表,记录每次 apply / rollback 的轨迹(audit 用,与 transaction 边界**无关**——transaction COMMIT 后才写 audit log)。

**实装路径(M0-dependent,消化 model_review Q5)**:

M0 audit 完成后,根据 store 函数 connection 模式选择实装路径:

- **路径 A(首选 — store 函数已接受外部 connection)**:governance.apply_proposal 引入 `_apply_proposal_in_transaction` context manager,接受 `BEGIN IMMEDIATE`、传入 connection 给四个 store 写函数、全部成功 COMMIT、失败 ROLLBACK。改动量小
- **路径 B(fallback — store 函数硬编码内部 connection)**:store-side refactor — 每个写函数增加 `*, conn: sqlite3.Connection | None = None` 可选参数,默认 None 时打开自己的(行为与既有完全一致),governance 调用时显式传入共享 conn。改动量中,但触发 store 测试回归
- **路径 C(最后 fallback — Path A/B 都不可行)**:引入 staged version table(route_metadata_staging / policy_staging),reader 只看到 latest committed version。改动量大,Phase scope 重评估,可能拆 Phase 63.6

**M0 audit 必须明确**:store 函数当前是 Path A 还是 Path B,以及 Path A/B 的代码改动估算。Claude 在 M0 报告基础上选择路径,记录在 `docs/plans/phase63/m0_audit_report.md` Phase 63 follow-up 节。

**影响范围**:
- 改动:`src/swallow/governance.py` —— 把 `_apply_route_metadata` 与 `_apply_policy` 序列改为 SQLite transaction context;失败时 SQLite ROLLBACK 自动回滚,governance 层 catch 异常并写 audit log `action="rolled_back"`
- 改动(Path A/B 二选一):`src/swallow/router.py` 等 store 模块 —— 接受外部 connection(若 Path B,refactor;若 Path A,M0 已确认)
- 改动:`src/swallow/store.py` 或 migration —— 增加 `route_change_log` / `policy_change_log` 表(schema 与 `know_change_log` 对齐,详见下方 schema 节)
- 新增:`src/swallow/truth/route.py` / `src/swallow/truth/policy.py` 中增加 `_log_change(...)` / `_log_rollback(...)` 私有方法
- 改动:`tests/test_invariant_guards.py` —— **扩展 `test_append_only_tables_reject_update_and_delete` 被测表清单从 4 张到 6 张**(增加 `route_change_log` / `policy_change_log`),与 S4 留下的 docstring TODO 配对(消化 CONCERN S4 #3 的 milestone 边界规则)
- 新增:`tests/test_governance.py` 增加 mid-failure rollback 测试(mock 第二步失败,验证第一步被回滚)

**S5 schema(消化 CONCERN S5 #1 + model_review Q5,与 `know_change_log` 对齐)**:

`know_change_log` 既有 schema(DATA_MODEL §3.3):`change_id` / `target_kind` / `target_id` / `action` / `rationale` / `timestamp` / `actor`。

`route_change_log` 新增 schema(revised-after-model-review,移除 `rollback_failed` 取值):
```sql
CREATE TABLE route_change_log (
    change_id      TEXT PRIMARY KEY,        -- ULID,与 know_change_log 一致
    target_kind    TEXT NOT NULL,           -- 固定为 "route_metadata"
    target_id      TEXT NOT NULL,           -- proposal_id (ULID)
    action         TEXT NOT NULL,           -- {"applied","rolled_back"}(SQLite transaction 自动回滚,无 rollback_failed)
    rationale      TEXT,                    -- 可空,记录操作原因(对齐 know_change_log)
    before_snapshot TEXT,                   -- JSON,pre-write 状态(语义专用,know_change_log 没有)
    after_snapshot  TEXT,                   -- JSON,post-write 状态;rollback 时为 NULL
    timestamp      TEXT NOT NULL,           -- ISO 8601(对齐 know_change_log,不用 created_at)
    actor          TEXT NOT NULL DEFAULT 'local'  -- 对齐 know_change_log;运行时由 local_actor() 提供
);
```

`policy_change_log` 同结构,只是 `target_kind` 固定为 `"policy"`。

**字段对照表**:

| know_change_log | route/policy_change_log | 说明 |
|----------------|------------------------|------|
| change_id | change_id | 一致 |
| target_kind | target_kind | 一致 |
| target_id | target_id | 一致(此处为 proposal_id) |
| action | action | 一致(枚举值不同,均为字符串) |
| rationale | rationale | 一致(可空) |
| (无) | before_snapshot / after_snapshot | route/policy 专用,记录 rollback 所需快照 |
| timestamp | timestamp | 一致(均 ISO 8601 字符串) |
| actor | actor | 一致 |

**关键设计决策**:
- **回滚语义(消化 model_review Q5 BLOCK)**:**SQLite transaction-wrapped(`BEGIN IMMEDIATE`)**。四步 store 写在单一 SQLite transaction 内执行,任一步抛异常 → SQLite ROLLBACK,所有写入回滚,中间状态对其他 reader 不可见。governance 层 catch 异常后写 audit log `action="rolled_back"`(audit log 写入在 transaction COMMIT/ROLLBACK 之外,独立 transaction)。**取消 staged 应用 + 失败回滚 + `rollback_failed` terminal state 设计**(原方案违反"零行为变化")
- **`rollback_weights` / `rollback_capability_profiles` 字段保留作为 audit 审计**:不再用作 compensating rollback 输入(因为 SQLite transaction 已经原生回滚),而作为 `before_snapshot` 的来源(写入 audit log)。`OptimizationProposalApplicationRecord` 字段语义不变,代码层不破坏既有结构
- **审计 log 是 append-only**:`route_change_log` / `policy_change_log` 由 `test_append_only_tables_reject_update_and_delete` 守卫保护(S5 内扩展该守卫被测表清单到包含两张新表)
- **`action` 字段值约束**:运行时**两类**:`"applied"`(成功)、`"rolled_back"`(SQLite transaction 失败回滚)。**`rollback_failed` 不再是 terminal state**(SQLite ROLLBACK 是原子的,不会失败到一半;若 SQLite 本身故障如磁盘损坏,异常向上抛出,governance 不写任何 audit log)
- **schema 增量限制**:仅新增两张 append-only log 表,不修改既有表结构

**验收条件**:
- 模拟 `apply_route_weights`(第二步)失败:**SQLite transaction ROLLBACK 触发,`save_route_weights`(第一步)写入被原生回滚**;route_metadata 与 capability_profiles 都恢复到 pre-write 状态;**reader 看不到任何中间状态**
- `route_change_log` 记录 `action="rolled_back"` + `before_snapshot` 完整 + `after_snapshot=NULL`
- `test_apply_proposal_rollback_executes_on_failure` 通过(S4 已实装该守卫,验证 SQLite ROLLBACK 触发 + reader 隔离)
- `route_change_log` / `policy_change_log` 表存在,DDL 与上方 schema 一致
- `test_append_only_tables_reject_update_and_delete` 守卫被测表清单更新到 6 张表,全部通过
- 全量 pytest 通过

**风险评级**(revised-after-model-review):影响范围 3 / 可逆性 2 / 依赖 2 = **7(高风险)**。store-side connection 参数 refactor(若 Path B)是新增的高风险面;Path C(staged version table)是更高风险 fallback。M0 audit 后再敲定路径。

---

## 依赖与顺序(revised-after-model-review)

```
S0 (M0, audit only) ──┬──> S1 (M1, identity/workspace)
                       └──> Phase scope 决策点(继续 6-slice 或拆 Phase 63.5)

S1 (M1) ──┬──> S4 (M3, §9 守卫批量需要 identity/workspace 集中化函数已存在)
          ├──> S2 (M2, governance 写路径需要 local_actor())
          └──> S3 (M2, Repository 内部 path 处理走 resolve_path())

S3 (M2) ───────> S5 (M4, SQLite transaction wrapping 需要 Repository 抽象层已就位)

S0 (M0) ───────> S5 (M4, SQLite transaction 实装路径 A/B/C 由 M0 audit 决定)

S2 (M2) ───────> S4 (M3, test_only_orchestrator_uses_librarian_side_effect_token 在 S2 内,但其他守卫批量实装应在 S2 完成后)
```

**Codex 推荐实装顺序**:**S0 → S1 → S2 → S3 → S5 → S4**

理由:
- S0 必须先做(M0 audit 决定 phase scope 与 S5 实装路径)
- S5 优先于 S4 因为 S4 内的 `test_apply_proposal_rollback_executes_on_failure` 守卫需要 S5 的 SQLite transaction wrapping 已实装
- milestone review 边界仍为 M0(S0) / M1(S1) / M2(S2+S3) / M3(S4) / M4(S5),即 S4 实装可在 S5 实装完成后回到 M3 milestone 提交

## Milestone 与 review checkpoint(revised-after-model-review)

| Milestone | 包含 slice | review 重点 | 提交节奏 |
|-----------|-----------|------------|---------|
| **M0** | S0 | NO_SKIP audit 报告 + store connection 模式 audit 报告;**Phase scope 决策**(继续 6-slice / 拆 Phase 63.5);**S5 实装路径 A/B/C 选择** | 单独 milestone commit(纯 docs + audit script);**Human 在 M0 完成后审阅决策再继续** |
| **M1** | S1 | identity/workspace 集中化函数设计、disambiguation 策略、扩展 ACTOR_SEMANTIC_KWARGS 闭集 | 单独 milestone commit |
| **M2** | S2 + S3 | governance.py 依赖图重塑等价性、Repository 接口最小性、`librarian_side_effect` token 特权范围、§5 矩阵文字更新、Repository bypass 守卫 | 同轮 review,两个 slice 可分开 commit 也可合并(Codex 实装时决策);**§5 矩阵 docs(design) 更新单独 commit** |
| **M3** | S4 | §9 13 条守卫语义正确性、SQLite trigger 基础设施、NO_SKIP_GUARDS 修复进度 | 单独 milestone commit |
| **M4** | S5 | SQLite transaction wrapping 实装路径(A/B/C 之一)、审计 log schema、reader 隔离测试 | 单独 milestone commit |

## 守卫与测试映射(revised-after-model-review)

| Slice | 新增守卫 | §9 表内 | §9 表外 |
|-------|---------|---------|---------|
| S0 | (无新增守卫,产出 audit 报告) | 0 | 0 |
| S1 | `test_no_hardcoded_local_actor_outside_identity_module` / `test_no_absolute_path_in_truth_writes` | 2 | 0 |
| S2 | `test_only_orchestrator_uses_librarian_side_effect_token` | 0 | 1(librarian_side_effect token 特权守卫) |
| S3 | `test_duplicate_proposal_id_raises` / **`test_only_governance_calls_repository_write_methods`**(model_review Q2/Q6)/ **`test_no_module_outside_governance_imports_store_writes`**(model_review Q6) | 0 | 3(governance 测试 + 2 条 Repository bypass 守卫) |
| S4 | 13 条(12 §9 表内 + 1 S5 配套事务回滚守卫) | 12 | 1 |
| S5 | (S5 不直接引入新守卫,守卫由 S4 提供;S5 内扩展 `test_append_only_tables_reject_update_and_delete` 被测表) | 0 | 0 |
| **合计** | **18 条** | **14** | **5**(本 phase 引入的额外架构守卫,不进 §9 表) |

完结后:INVARIANTS §9 标准表 3(既有 Phase 61 apply_proposal 守卫)+ 14(本 phase 新增 = S1 的 2 + S4 的 12)= **17 条**,与 §9 表 17 条对齐;额外 5 条架构守卫(S2/S3 引入的 token + Repository bypass 防线)是本 phase 的"防止漂移再生"机制,不算 INVARIANTS §9 表。

## phase-guard 检查(revised-after-model-review)

- ✅ 当前方案不越出 kickoff goals(G1-G5 + S0 audit 与 6 个 slice 对应,M0 是 G1-G5 的实装前置而非新 goal)
- ⚠ **kickoff non-goals 已收紧**:从"不修改 INVARIANTS 文字"细化为"不修改 §0/§1/§2/§3/§4/§6/§7/§8 等核心原则文字;§5 矩阵 Orchestrator 行 stagedK 列允许在本 phase 实装内更新一行 + 配套注脚"。这是消化 model_review Q1 BLOCK 的必要 scope 调整,Human Design Gate 时显式审批
- ⚠ **slice 数量 6 个**(超出"≤5 slice"指引一个);**理由**:M0 是 audit-only slice(无代码改动,实质是 phase scope 安全网),不算"功能 slice"。Human Design Gate 时显式审批此例外,或者 M0 可视为 milestone-level 决策点而非独立 slice
- ⚠ S3 仍然高风险(7),S5 升级为高风险(7,SQLite transaction wrapping 涉及 store-side connection refactor);本 phase **2 条高风险 slice**(S3 + S5),建议在 M0 audit 之后由 Claude 重新评估总风险
- ✅ Repository 抽象层 + §5 矩阵更新 + SQLite transaction 三个关键 design 决策已经 model_review BLOCK 反馈消化(2 BLOCK + 2 BLOCK + 1 CONCERN 全部转 ed)

## Branch Advice

- 当前分支:`main`
- 建议操作:Direction Gate 通过后,Human 切出 `feat/phase63-governance-closure`
- 理由:本 phase 范围明确、5 slice / 4 milestone 一次性收口,单 PR 即可
- 建议分支名:`feat/phase63-governance-closure`
- 建议 PR 范围:全部 5 个 slice 一次 PR;但 review milestone 分 4 个(M1 / M2 / M3 / M4),由 Codex 按 milestone 给出 commit 建议,Human 控制提交节奏

## Model Review Gate

**已完成**(2026-04-29,reviewer = external-model GPT-5 via `mcp__gpt5__chat-with-gpt5_5`):**verdict = BLOCK**。3 BLOCK + 3 CONCERN。详见 `docs/plans/phase63/model_review.md`。

**Claude 消化决策摘要**(本 design_decision 已转 revised-after-model-review):
- Q1 [BLOCK]:本 phase 内更新 §5 矩阵 Orchestrator 行 stagedK 列(non-goals 收紧)
- Q5 [BLOCK]:S5 改用 SQLite `BEGIN IMMEDIATE` transaction 包裹四步 store 写
- Q6 [BLOCK]:S3 增加 2 条 Repository bypass 守卫(`test_only_governance_calls_repository_write_methods` + `test_no_module_outside_governance_imports_store_writes`)
- Q2 [CONCERN]:Q6 follow-up 已包含
- Q3 [CONCERN]:扩展 ACTOR_SEMANTIC_KWARGS 闭集 + 移除 `action`
- Q4 [CONCERN]:新增 M0 pre-implementation audit slice(NO_SKIP_GUARDS report-only 扫描 + store connection 模式 audit)

修订后的 design 等待 Human Design Gate 审批。

## 不做的事(精简版,详见 kickoff non-goals,revised-after-model-review)

- 不重写 store 函数本身的语义;Repository 只做最小封装(若 S5 走 Path B,store 函数仅增加可选 connection 参数,行为兼容)
- 不修改 INVARIANTS §0 / §1 / §2 / §3 / §4 / §6 / §7 / §8 等核心原则文字;**§5 矩阵 Orchestrator 行 stagedK 列允许更新一行 + 配套注脚**(消化 model_review Q1 BLOCK)
- 不修改 Phase 60-62 任何对外可观测行为(SQLite transaction wrapping 后中间状态对 reader 不可见,语义比原 staged 应用更严格)
- **不引入 staged 应用 + 失败回滚**(原方案违反 reader 隔离;改用 SQLite native transaction)
- 不引入两阶段提交(SQLite transaction 是单一事务,非两阶段)
- 不引入新 LLM 调用路径
- 不引入 Operator-facing CLI 扩展
- 不在本 phase 完成 durable proposal artifact 层(后续方向)
- 不在本 phase 完成 staged version table 实装(Path C fallback,只在 M0 audit 后被迫选择时才考虑)

## 验收条件(全 phase)

详见 `kickoff.md` §完成条件。本 design_decision 与 kickoff 一致,无补充。
