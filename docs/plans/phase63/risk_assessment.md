---
author: claude
phase: phase63
slice: risk-assessment
status: revised-after-model-review
depends_on: ["docs/plans/phase63/kickoff.md", "docs/plans/phase63/design_decision.md", "docs/plans/phase63/design_audit.md", "docs/plans/phase63/model_review.md", "docs/plans/phase63/context_brief.md"]
---

TL;DR(revised-after-model-review): **15 条风险条目**(新增 R12 §5 矩阵文字更新 / R13 store connection refactor / R14 M0 audit 暴露大范围漂移 / R5_NEW SQLite transaction 路径选择 / R15 §S2 方案选择失误)。**2 条高(R3 Repository 依赖图 + R5_NEW SQLite transaction wrapping)、7 条中、6 条低**。主要缓解手段:M0 pre-implementation audit **3 项**决定 phase scope + S5 实装路径 + §S2 方案选择 / SQLite native transaction 替换 staged 应用以保证 reader 隔离 / 2 条 Repository bypass 守卫防止漂移再生 / NO_SKIP_GUARDS 白名单 + M0 红灯审计早识别风险。**§5 矩阵文字更新 M0-dependent**(若方案 D,§5 不动)。

## 风险矩阵(revised-after-model-review)

| ID | 风险 | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 等级 |
|----|------|---------|--------|-----------|------|------|
| R1 | identity/workspace 集中化 import 改动 regression | 3 | 2 | 1 | 6 | 中 |
| R2 | `"local"` 字面量 disambiguation 守卫误报/漏报 | 2 | 2 | 1 | 5 | 中 |
| R3 | **Repository 抽象层重塑 governance 依赖图破坏既有路径** | 3 | 2 | 2 | 7 | **高** |
| R4 | `librarian_side_effect` token 特权语义边界扩张 | 2 | 1 | 1 | 4 | 低 |
| R5 | `_PENDING_PROPOSALS` 重复检测引发 Phase 61/62 测试 fixture 冲突 | 1 | 1 | 1 | 3 | 低 |
| R6 | §9 14 条守卫批量激活暴露既有未发现漂移,本 phase 范围扩张 | 2 | 2 | 2 | 6 | 中 |
| R7 | `test_append_only_tables_reject_update_and_delete` SQLite trigger 基础设施缺失 | 2 | 2 | 2 | 6 | 中 |
| R8 | §9 表实装计数审计错误(已实装条目重复计入 / 遗漏既有实装) | 1 | 1 | 1 | 3 | 低 |
| ~~R9~~ | ~~事务回滚 staged 应用机制本身失败(回滚函数 bug)~~ | — | — | — | — | **取消**(model_review Q5 BLOCK 后改用 SQLite native transaction;原风险消失) |
| R10 | `route_change_log` / `policy_change_log` schema 与既有 audit log 模式不一致 | 1 | 2 | 1 | 4 | 低 |
| R11 | Model Review Gate 反馈引入设计修订,phase 起步延迟 | 1 | 1 | 1 | 3 | 低(已实际触发,impact 已消化) |
| **R12** | **§5 矩阵文字更新触发既有"不修改 INVARIANTS"假设的下游不一致(仅方案 A 触发,M0-dependent)** | 2 | 2 | 1 | 5 | 中(若方案 D 走起则 0,风险消失) |
| **R13** | **store 函数 connection 参数 refactor 触发回归(S5 Path B 路径)** | 2 | 2 | 2 | 6 | 中 |
| **R14** | **M0 audit 暴露大范围 NO_SKIP 红灯,触发 Phase 63.5 拆分** | 2 | 1 | 1 | 4 | 低-中(若触发,phase scope 调整成本中) |
| **R5_NEW** | **S5 SQLite transaction wrapping 实装路径(A/B/C)选择失误** | 3 | 2 | 2 | 7 | **高**(取决于 M0 audit 结果) |
| **R15** | **§S2 方案选择失误(M0 audit 结论 vs Claude 决策不匹配,Human 反馈驱动)** | 3 | 2 | 1 | 6 | 中 |

---

## 详细分析

### R1 — identity/workspace 集中化 import 改动 regression(中)

**描述**:S1 引入 `swallow.identity.local_actor()` / `swallow.workspace.resolve_path()` 后,需要把现有 actor-semantic `"local"` 与 path 绝对化 `.resolve()` 调用全部改走集中化函数。改动跨 6+ 模块(`models.py` / `orchestrator.py` / `executor.py` / `literature_specialist.py` / `quality_reviewer.py` / `ingestion/pipeline.py` / `web/api.py`)。每处改动都是机械替换,但累计触点多,容易遗漏。

**触发场景**:
- 漏改某处 actor `"local"` 字面量 → S1 守卫 `test_no_hardcoded_local_actor_outside_identity_module` 红灯,需回头修
- 误改 `execution_site="local"`(站点语义)为 `local_actor()` → 行为变化,可能影响 router 路由决策

**缓解**:
- Codex 实装时按 disambiguation rule 分批审计:先列出所有 `"local"` 命中(按 R2 守卫策略分类),再逐文件改
- S1 实装顺序:先引入新模块 + 守卫(初始 expected fail)→ 逐文件迁移 → 守卫由 fail 转 pass
- 全量 pytest + lint 在每次 milestone commit 前运行

**回滚成本**:中。回滚仅需 revert import 改动,但需要确认守卫被同步删除以避免 false-positive。

---

### R2 — `"local"` 字面量 disambiguation 守卫误报/漏报(中)

**描述**:context_brief 显示代码库中 `"local"` 字面量出现 25+ 次,大部分是 `execution_site="local"`(站点语义),少数是 actor `"local"`。两者守卫行为应区分:actor 语义守卫(S1 引入)只允许 `identity.py` 内出现;站点语义守卫不存在(站点字符串保留)。守卫 pattern 设计错误会导致:
- **误报**:把 `execution_site="local"` 当作 actor 漏改,守卫红灯触发不必要的修改
- **漏报**:某个真实 actor `"local"` 没被守卫识别,绕过集中化要求

**触发场景**:
- 守卫用纯 grep / regex 匹配 `"local"` → 必然误报站点语义
- 守卫用 AST 但 kwarg 白名单不全 → 漏报新引入的 actor 上下文

**缓解**:
- 守卫**必须使用 AST 而非 grep**:扫描 `kwarg.arg in ACTOR_SEMANTIC_KWARGS` 且 `kwarg.value` 是 `ast.Constant("local")` 的位置(`ACTOR_SEMANTIC_KWARGS` 闭集定义见 design_decision §S1 关键设计决策,authoritative)
- AST 守卫的 `ACTOR_SEMANTIC_KWARGS` 闭集作为模块级常量定义在 `tests/test_invariant_guards.py` 顶部,future Phase 引入新 actor 上下文时显式扩展(扩展行为本身需 phase-level review)
- DDL 中 SQL DEFAULT `'local'` 字面量自然不在 AST kwarg 调用语境中,守卫不会命中(消化 design_audit CONCERN S1 #3)
- S1 实装时,Codex 应跑一次"audit dry-run":把当前 25+ 命中按 actor / site / 其他三类列出,Claude review 类目正确性

**回滚成本**:低。守卫规则可以独立修订,不影响实装代码。

---

### R3 — Repository 抽象层重塑 governance 依赖图破坏既有路径(**高**)

**描述**:S3 引入 `swallow/truth/{knowledge,route,policy}.py` 作为 Repository 层,把 `governance.py` 直接 import 的 `save_route_weights` / `apply_route_weights` / `save_route_capability_profiles` / `apply_route_capability_profiles` 改为 Repository 调用。这是 Phase 61 留下的核心架构债的兑现,governance.py 是治理入口,被多个调用方依赖。重塑过程中容易破坏:
- Phase 61 既有 governance 测试(`test_governance.py`)
- Phase 62 MPS policy apply_proposal 路径
- CLI `swl audit policy` / `swl synthesis policy` 等子命令

**触发场景**:
- Repository 类的私有方法签名与原 store 函数不完全等价(参数顺序、可选参数默认值差异)
- `_PENDING_PROPOSALS` 改为 Repository-managed 后,既有测试 fixture 假设了"重复 register 静默覆盖"的行为
- Repository 引入循环 import(`truth/route.py` 调用 `router.py`,`router.py` 又被 `governance.py` 引用)

**缓解**:
- **等价回归测试先行**:Codex 在 S3 实装前,先记录 governance 既有测试套件状态(全部 pass);引入 Repository 后,测试套件必须保持全 pass
- **Repository 接口设计原则**:严格 1:1 对应原 store 函数签名,不引入新参数 / 不改变返回类型 / 不引入新异常
- **循环 import 预防**:Repository 模块只 import store 函数,不 import governance / orchestrator;若发现循环依赖,在设计层重构而非 lazy import 绕开
- **S3 风险评级标记 [HIGH]**,Codex 实装时优先做"小步迁移":先建 `KnowledgeRepo` 一类、跑全测;再建 `RouteRepo`、跑全测;最后 `PolicyRepo`。三步分别 commit
- **Model Review Gate 重点 review** Repository 接口设计

**回滚成本**:中-高。Repository 改动跨模块,回滚需要 revert 多文件;但因为 Phase 63 在 feature branch 上,git revert 整个 commit 是清晰边界。

---

### R4 — `librarian_side_effect` token 特权语义边界扩张(低)

**描述**:S2 引入 `OperatorToken.source = "librarian_side_effect"` 新枚举值,允许 orchestrator 把 Librarian agent 的 verified knowledge → staged candidate 转换走 governance 通道。该 token 是有限特权扩展。风险是后续 phase 可能误用此 token 类型把更多直写路径"合法化",侵蚀 §5 矩阵约束。

**触发场景**:后续 phase 在 CLI / Specialist 中直接构造 `OperatorToken(source="librarian_side_effect")`。

**缓解**:
- S2 内引入守卫 `test_only_orchestrator_uses_librarian_side_effect_token`(AST 扫描 `OperatorToken(source="librarian_side_effect")` 调用位置,只允许 orchestrator.py)
- 在 design_decision §S2 关键决策中显式记录:此 token 是**有限特权**,后续 phase 若要在其他模块使用必须经新 phase-level review

**回滚成本**:低。token 类型可以独立 deprecate。

---

### R5 — `_PENDING_PROPOSALS` 重复检测引发 Phase 61/62 测试 fixture 冲突(低)

**描述**:S3 把 `_PENDING_PROPOSALS` 由静默覆盖改为 `DuplicateProposalError`。Phase 61/62 测试 fixture 可能依赖"同一 `proposal_id` 多次 register"的行为(例如 setup → tear down → 同 ID 重新 register)。

**触发场景**:既有测试套件在 fixture / setup 阶段同 `proposal_id` 重复 register。

**缓解**:
- Codex 实装时,grep `register_canonical_proposal` / `register_route_proposal` / `register_policy_proposal` 在 tests/ 中的所有调用位置
- 若发现 fixture 冲突,改 fixture 使用唯一 `proposal_id`(ULID),而非削弱 `DuplicateProposalError` 行为
- 若 fixture 真的需要"清空再 register"语义,可在 governance.py 增加 `_clear_pending_proposals_for_test()` 测试辅助函数(仅 tests/ 可用),保持生产代码严格 fail-on-duplicate

**回滚成本**:低。测试 fixture 改动隔离。

---

### R6 — §9 14 条守卫批量激活暴露既有未发现漂移,本 phase 范围扩张(中)

**描述**:S4 批量激活 12 条 §9 表内守卫(加 S1 的 2 条共 14 条)。激活后可能发现既有代码中:
- 某 executor 在 task table 直写(违反 `test_no_executor_can_write_task_table_directly`)
- 某 state transition 不经 orchestrator(违反 `test_state_transitions_only_via_orchestrator`)
- Path B 调用 Provider Router(违反 `test_path_b_does_not_call_provider_router`)
- Validator 返回非 verdict-only 结构(违反 `test_validator_returns_verdict_only`)
- ……

每发现一条新漂移,修复可能超出本 phase scope,导致延期。

**触发场景**:S4 守卫激活后多条守卫红灯,且红灯路径在 `core` 模块上需要重大重构。

**缓解**:
- Codex 在 S4 实装时,**优先记录而非立即修复**:先把所有红灯守卫列出,Claude review 决定哪些必须本 phase 修、哪些登记为 Open 进 concerns_backlog
- **NO_SKIP_GUARDS 白名单(authoritative,定义见 design_decision §S4 关键设计决策)**:落入此白名单的守卫红灯不允许 `pytest.skip`,必须本 phase 修。包括与 INVARIANTS §0 四条核心不变量直接对应的守卫:
  - `test_no_executor_can_write_task_table_directly`(§0 第 1 条)
  - `test_state_transitions_only_via_orchestrator`(§0 第 1 条)
  - `test_validator_returns_verdict_only`(§0 第 1 条)
  - `test_path_b_does_not_call_provider_router`(§0 第 3 条 + §4)
  - `test_specialist_internal_llm_calls_go_through_router`(§0 第 3 条 + §4)
  - `test_canonical_write_only_via_apply_proposal`(§0 第 4 条,Phase 61 既有)
  - `test_only_apply_proposal_calls_private_writers`(§0 第 4 条,Phase 61 既有)
  - `test_route_metadata_writes_only_via_apply_proposal`(§0 第 4 条,Phase 61 既有)
- **白名单外**(ID & 不变量类 / UI 边界):红灯可在 Codex 上报、Claude 评估后决定是否 skip + 登记 Open;skip 路径必须配 `# TODO(phase64+): ...` 注释 + 在 `concerns_backlog.md` 登记
- 若超过 3 条红灯需要本 phase 修,Claude 触发 phase-guard 评估是否拆 Phase 64

**回滚成本**:低(守卫本身可独立 skip / unskip,但 NO_SKIP_GUARDS 内的守卫不能用 skip 退路)。

---

### R7 — `test_append_only_tables_reject_update_and_delete` SQLite trigger 基础设施缺失(中)

**描述**:`test_append_only_tables_reject_update_and_delete` 验证 DATA_MODEL §4.2 列出的 append-only 表(`event_log`、`know_change_log` 等)拒绝 UPDATE / DELETE。SQLite 默认不阻止 UPDATE / DELETE;需要表级 trigger 显式 RAISE。context_brief 指出现有 schema 可能未部署此类 trigger。

**触发场景**:
- 测试 DB 与生产 DB 都没有 trigger,守卫直接红灯
- migration 脚本被遗漏,trigger 仅在新部署存在,既有用户库不一致

**缓解**:
- S4 实装前先 audit:`grep -rn 'CREATE TRIGGER' src/swallow/` 与 `migration/*.sql`,列出已存在的 trigger
- 若缺失,S4 内补:在 `models.py` `CREATE TABLE` 后追加 `CREATE TRIGGER IF NOT EXISTS reject_update_<table> BEFORE UPDATE ON <table> BEGIN SELECT RAISE(ABORT, 'append-only'); END;` 与对应 DELETE trigger
- migration 增量:对既有用户库,引入 `swl doctor migrate-triggers` 子命令(若需要)。**Phase 63 内不引入 doctor 子命令,改为在 store 初始化路径上 `CREATE TRIGGER IF NOT EXISTS`**(idempotent)
- 守卫测试 fixture 在临时 DB 上验证(`tests/conftest.py` 引入 fixture)

**回滚成本**:中。Trigger 一旦创建,后续即使代码 revert,旧 DB 仍有 trigger。但 trigger 是 enforcement 机制,正常使用代码不会触发,无负面影响。

---

### R8 — §9 表实装计数审计错误(低)

**描述**:context_brief 与 design_decision 给出"§9 表 17 条 / Phase 61 实装 3 条 / Phase 63 补 14 条"的计数。若实装审计有遗漏(例如 Phase 62 的某条 MPS 守卫名碰巧与 §9 表条目重名,但语义不同),最终可能 §9 表实装数字不为 17。

**触发场景**:Phase 62 引入的某守卫名(如 `test_synthesis_uses_provider_router`)被误认为对应 §9 表的 `test_specialist_internal_llm_calls_go_through_router`。

**缓解**:
- S4 实装前 Codex 做一次精确审计:列出 `tests/test_invariant_guards.py` 中所有 `def test_*` 函数,与 §9 表 17 条名字逐一对照
- 审计结果作为 S4 PR body 一节,Claude review 验证
- design_decision 中已列出 Phase 61 实装的 3 条(见守卫与测试映射表),作为审计 anchor

**回滚成本**:低。计数错误只导致守卫遗漏 / 重复,可修订。

---

### ~~R9 — 事务回滚 staged 应用机制本身失败~~(取消,已被 R5_NEW 替代)

**描述**:原 R9 描述 staged 应用方案的回滚函数失败风险。**Model review Q5 BLOCK 后,该方案已被 SQLite native transaction(`BEGIN IMMEDIATE`)替代**。SQLite ROLLBACK 是原子的,不会失败到一半;若 SQLite 本身故障(磁盘损坏等),异常向上抛出,不进入 `rollback_failed` 复合状态。原风险消失,被 R5_NEW(SQLite transaction 实装路径选择)替代。

---

### R10 — `route_change_log` / `policy_change_log` schema 与既有 audit log 模式不一致(低)

**描述**:DATA_MODEL §3 既有 `know_change_log`。S5 新增 `route_change_log` / `policy_change_log`,字段命名 / JSON schema 应与 know_change_log 保持一致(例如 `change_id` 用 ULID、`timestamp` / `actor` / `target_kind` / `action` 字段名一致)。

**消化(design_audit CONCERN S5 #1)**:design_decision §S5 已给出**完整 DDL**与对照表,字段命名已对齐 `know_change_log`(`timestamp`/`actor`/`target_kind`/`target_id`/`action`/`rationale`),仅 `before_snapshot` / `after_snapshot` 是 route/policy 专用语义字段(rollback 需要快照,know_change_log 不需要)。R10 余风险降低到"实装时 SQL DDL 字符串与 design 文档之间的细节误差"。

**触发场景**:Codex 实装时 DDL 与 design_decision 文档不严格一致(例如字段类型 `TEXT` 写成 `VARCHAR`,或 PRIMARY KEY 标注遗漏)。

**缓解**:
- S5 实装时 Codex PR body 必须包含 DDL diff,Claude review 时与 design_decision §S5 schema 节逐字段比对
- 守卫 `test_append_only_tables_reject_update_and_delete` 在 S5 内扩展到包含两张新表(对齐 design_decision §S5 验收条件),trigger 部署在 store 初始化路径

**回滚成本**:低。Schema 增量,可 ALTER TABLE 修订(虽然实际中通常 drop + recreate 在迁移脚本中处理)。

---

### R11 — Model Review Gate 反馈引入设计修订,phase 起步延迟(低,已实际发生)

**描述**:design_decision §Model Review 标 required;第二模型已给出 BLOCK + revised-after-model-review。本风险已转化为实际处理(model_review.md verdict = BLOCK,3 BLOCK + 3 CONCERN)。

**实际处理结果**:
- Q1 [BLOCK] 消化:本 phase 内更新 §5 矩阵文字 + non-goals 收紧(派生 R12)
- Q5 [BLOCK] 消化:S5 改用 SQLite native transaction(派生 R13 + R5_NEW)
- Q6 [BLOCK] 消化:S3 增加 2 条 Repository bypass 守卫
- Q2/Q3/Q4 [CONCERN] 消化:扩展 ACTOR 闭集 + 新增 M0 audit slice
- Phase scope 从 5 slice 扩展到 6 slice(M0 + S1-S5)

**回滚成本**:低。设计修订已完成,代码尚未启动。

---

### R12 — §5 矩阵文字更新触发既有"不修改 INVARIANTS"假设的下游不一致(中,**仅方案 A 触发,M0-dependent**)

**描述**:本 phase 在方案 A 选择下,在 S2 内更新 INVARIANTS §5 矩阵 Orchestrator 行 stagedK 列文字(从 "-" 改为 "W*(via apply_proposal + librarian_side_effect token)")。这与"不修改 INVARIANTS 文字"的既有 non-goal(以及其他 phase 文档中类似假设)有冲突。下游 phase 文档(如 closeout / 后续 phase 的 kickoff)可能引用过时的"§5 矩阵文字未变"假设。

**M0-dependency**:若 M0 audit 第 3 项结论支持方案 D(`_route_knowledge_to_staged` 仅 Specialist 类 executor 触发),则本风险**消失**(方案 D 不更新 §5 矩阵)。

**触发场景**(仅方案 A):
- 后续 phase 在 phase-guard 检查时引用 INVARIANTS §5 矩阵旧文字
- 设计文档(`docs/design/SELF_EVOLUTION.md` / `docs/design/EXECUTOR_REGISTRY.md` 等)引用 §5 矩阵旧描述,本 phase 更新后未同步

**缓解**:
- 仅在选定方案 A 后激活以下缓解:
  - S2 内 grep `docs/design/*.md` 检查是否有引用 §5 矩阵 Orchestrator 行 stagedK 的位置;若有,同步更新(独立 commit)
  - §5 矩阵更新作为本 phase 的 docs(design) commit 单独提交,git log 上一眼可见
  - closeout 中显式记录"§5 矩阵已在本 phase 内更新一行,所有引用方应使用更新后版本"
- 选定方案 D 时,本风险无效

**回滚成本**:低-中。文档级别改动,可 git revert。

---

### R13 — store 函数 connection 参数 refactor 触发回归(中,S5 Path B 路径)

**描述**:S5 SQLite transaction wrapping 若选择 Path B(store-side connection 参数 refactor),需要 `save_route_weights` / `apply_route_weights` / `save_route_capability_profiles` / `apply_route_capability_profiles` 等 store 写函数增加 `*, conn: sqlite3.Connection | None = None` 可选参数。这触发 store 模块的接口改动 + 既有调用方(governance / cli / Specialist)的回归测试。

**触发场景**:
- M0 audit 显示 store 函数硬编码内部 connection,选择 Path B
- 既有调用方依赖 store 函数自己 commit 行为,refactor 后需要确认 default None 时行为完全等价
- 既有 store 测试 fixture 假设 store 函数 self-contained,refactor 可能破坏

**缓解**:
- M0 audit 输出明确 Path A / B / C 选择 + 改动估算;Claude review 后再敲定
- Path B refactor 时,store 函数接受 `conn=None` 时**完全等价于既有行为**(打开自己的 connection + commit);仅当 conn 显式传入时不打开自己的 connection
- store 既有测试套件作为 regression 基准,refactor 后必须保持全 pass
- 若 Path B refactor 暴露超过 5 个 store 函数需要改动,触发 phase-guard 评估是否升级为单独 milestone(M4.5)

**回滚成本**:中。store-side 改动,但因为接口向后兼容(default None),回滚仅需 revert refactor commit。

---

### R14 — M0 audit 暴露大范围 NO_SKIP 红灯,触发 Phase 63.5 拆分(低-中)

**描述**:M0 NO_SKIP_GUARDS 报告显示 ≥ 3 处红灯 OR 涉及核心模块大幅修复(如多模块 task table 直写、state transition 不经 orchestrator)。此时 Phase 63 维持 6-slice plan 不现实,需要拆 Phase 63.5 专做 invariant remediation。

**触发场景**:
- M0 报告显示 `test_no_executor_can_write_task_table_directly` 多模块红灯
- M0 报告显示 `test_state_transitions_only_via_orchestrator` 涉及多 executor / multiple state transition entry points

**缓解**:
- M0 是本 phase 的"早识别风险"机制,触发拆分是预期行为而非意外
- 拆分流程预先准备:Phase 63.5 kickoff 在 M0 触发时由 Claude 起草,active_context 显式登记新方向 + roadmap-updater 增补 §三(非 §3 差距条目,但是 Phase 63 内的子方向)
- Phase 63 scope 退到不含 NO_SKIP 严格执行(NO_SKIP guards 改为 report-only 或 warning),Phase 63.5 完成后再启用 enforcement

**回滚成本**:低-中。Phase scope 调整成本中,但 phase 文档级别。

---

### R5_NEW — S5 SQLite transaction wrapping 实装路径(A/B/C)选择失误(高,M0-dependent)

**描述**:S5 实装路径取决于 M0 audit:
- Path A(首选):store 函数已接受外部 connection 参数,governance 层加 transaction wrapper 即可
- Path B(fallback):store 函数硬编码 connection,需 refactor 增加 conn 参数
- Path C(最后 fallback):上述都不可行,引入 staged version table

选错路径会导致:
- Path A 选 B/C → over-engineering,scope 扩张
- Path B 选 A → 实装失败,因为 store 函数不接受 conn
- Path B 选 C → over-engineering,scope 大幅扩张
- Path C 是唯一可行但选 A/B → 实装失败

**触发场景**:M0 audit 报告不准确或 Claude 评审决策错误。

**缓解**:
- M0 audit 报告必须明确 Path A / B 的代码改动估算,Claude 评审时严格按 audit 结论选
- Path A 是默认假设,因为最干净;若 audit 发现 store 函数硬编码 connection,降级 Path B
- Path C 触发条件严格:Path A/B 都不可行(例如 store 函数依赖 thread-local connection / 跨进程 / 等高度耦合)。若 Path C 触发,触发 phase-guard 评估是否拆 Phase 63.6
- design_decision §S5 已显式陈述"实装路径 M0-dependent",Codex 实装时严格按选定路径

**回滚成本**:中-高。若选错路径开始实装,回滚需要 revert 多个 store / governance commit,但因为是 feature branch,git revert 边界清晰。

---

### R15 — §S2 方案选择失误(中,Human 反馈驱动)

**描述**:Human 在 design review 后指出 `_route_knowledge_to_staged` 实际是按 `taxonomy_memory_authority` 路由的通用副作用流(不限于 Librarian)。M0 audit 第 3 项决定走方案 A(librarian_side_effect token + §5 矩阵更新)还是方案 D(下沉到 Specialist 内部 + §5 不动)。

**潜在失误模式**:
- M0 audit 报告把"非 Specialist executor 触发"错误识别为"仅 Specialist 触发" → Claude 选方案 D → 实装时发现 General Executor 也走这条流,被迫退回方案 A 或 scope 扩张
- M0 audit 报告把"仅 Specialist 触发"错误识别为"非 Specialist 也触发" → Claude 选方案 A → 增加了不必要的 token 类型 + §5 矩阵修订(反向治理)
- audit 时点的代码状态 vs 实装时点的代码状态不一致(Phase 63 实装期间引入新 task taxonomy)→ 选定方案不再适用

**缓解**:
- M0 audit 输出必须明确给出**完整 executor type 列表**(配合 grep / route table dump),不只是"是/否"二元结论
- M0 audit 报告作为 PR body 的一部分,Claude 评审时与 Human 共同确认方案选择
- audit 报告留痕:`tests/audit_route_knowledge_to_staged.py` 保留为 report-only 工具,后续 phase 可重跑确认现状未变
- M2 实装(S2)开始前,Codex 重跑 audit 脚本确认 audit 结果仍然有效(若实装期间已经过几个 phase 的演进,可能需要重 audit)
- 若实装中途发现方案选择错误,触发 phase-guard:回到 design 修订(选另一方案),不强行打补丁

**回滚成本**:中。方案 A → 方案 D 或反过来都是 feature branch 内的 design 修订 + 实装重写,但范围限定在 S2 一个 slice 内,M2 milestone 边界清晰。

---

## 总体策略(revised-after-model-review)

1. **先做 M0(S0)pre-implementation audit**:**3 项 audit**(NO_SKIP 红灯 + store connection 模式 + `_route_knowledge_to_staged` 触发场景),Claude 在报告基础上做**3 个**决策:
   - phase scope(维持 6-slice / 拆 Phase 63.5)
   - S5 实装路径(A/B/C)
   - **§S2 方案选择(A vs D)**
   Human 在 M0 完成后审阅决策再继续
2. **M1(S1)identity/workspace 集中化**:后续所有 slice 的基础前置,确认 R1/R2 缓解策略落地;扩展 ACTOR_SEMANTIC_KWARGS 闭集
3. **M2(S2 + S3)同轮 review**:**S2 按 M0 选定的方案 A 或 D 实装**(不在 M2 内重新决策);S3 高风险,Codex 必须先做等价回归测试,再引入 Repository。建议 Codex 拆 commit:S2 一个或多个 commit(方案 A 含 §5 矩阵 docs(design) commit)/ S3 三个 commit(KnowledgeRepo / RouteRepo / PolicyRepo 各一);**Repository bypass 守卫(2 条)与 S3 同轮**
4. **M3(S4)按 R6 策略**:NO_SKIP_GUARDS 严格执行(M0 报告已 pre-empt 大范围红灯);其他守卫红灯按既有流程
5. **M4(S5)单独 review**:**SQLite transaction wrapping** 是新机制,review 重点在 reader 隔离测试 + R5_NEW 路径选择正确性 + R13 store-side refactor 回归
6. **Model Review Gate**:已完成(verdict = BLOCK),所有反馈已消化为 revised-after-model-review;Human 反馈进一步驱动 §S2 双方案设计

## 与既有 risk 模式的对照

- 类似 Phase 61(apply_proposal):本 phase 也是宪法层债务收口,模式一致 —— 大量改动表面但对外行为等价
- 类似 Phase 62(MPS):本 phase 也涉及多 milestone 推进 + model_review BLOCK + revised-after-model-review,模式高度一致
- 不类似 Phase 60(retrieval policy):本 phase 不引入 user-facing 行为变化,无 eval 需求
- **新模式**:本 phase 引入 M0 pre-implementation audit slice,作为"早识别风险"机制,这是治理类 phase 的有用范式(后续治理类 phase 可参考)
