---
author: claude
phase: phase63
slice: risk-assessment
status: final-after-m0
depends_on: ["docs/plans/phase63/kickoff.md", "docs/plans/phase63/design_decision.md", "docs/plans/phase63/design_audit.md", "docs/plans/phase63/model_review.md", "docs/plans/phase63/m0_audit_report.md", "docs/plans/phase63/context_brief.md"]
---

TL;DR(final-after-m0): **9 条风险条目**(M0 audit 后 scope 收窄,大幅简化)。**1 条高(R3 Repository 抽象层依赖图重塑)、5 条中、3 条低**。S5 整段(原 R9 / R5_NEW / R13)消失因为推迟到 Phase 64;§5 矩阵相关 R12 消失因为不修宪法;R15 §S2 方案选择消失因为 M0 audit 已敲定"删 dead code"。新增 R16(测试 mock 调整等价性,中)。主要缓解手段:S3 等价回归测试先行 + 三 commit 拆分;守卫 disambiguation 用 AST 而非 grep + 闭集扩展;NO_SKIP 红灯已被 M0 pre-empt 拆 G.5。

## 风险矩阵(final-after-m0)

| ID | 风险 | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 等级 |
|----|------|---------|--------|-----------|------|------|
| R1 | identity/workspace 集中化 import 改动 regression | 3 | 2 | 1 | 6 | 中 |
| R2 | `"local"` 字面量 disambiguation 守卫误报/漏报(扩展闭集后) | 2 | 2 | 1 | 5 | 中 |
| R3 | **Repository 抽象层重塑 governance 依赖图破坏既有路径** | 3 | 2 | 2 | 7 | **高** |
| R4 | `_PENDING_PROPOSALS` 重复检测引发 Phase 61/62 测试 fixture 冲突 | 1 | 1 | 1 | 3 | 低 |
| R6 | §9 12 条守卫批量激活暴露既有未发现漂移 | 2 | 2 | 2 | 6 | 中(M0 已 pre-empt) |
| R7 | `test_append_only_tables_reject_update_and_delete` SQLite trigger 基础设施缺失 | 2 | 2 | 2 | 6 | 中 |
| R8 | §9 表实装计数审计错误(已实装条目重复计入 / 遗漏既有实装) | 1 | 1 | 1 | 3 | 低 |
| R11 | Model Review Gate 反馈引入设计修订(已发生,完整消化) | 1 | 1 | 1 | 3 | 低(已闭环) |
| **R16** | **删除 `_route_knowledge_to_staged` 时测试 mock 调整破坏原有断言意图** | 2 | 1 | 2 | 5 | 中 |

**已取消的风险条目**(M0 audit 后或 scope 收窄后消失):
- ~~R5(原 `_PENDING_PROPOSALS` 改为 `DuplicateProposalError` 引发既有测试冲突)~~:实际同 R4,合并
- ~~R9(staged 应用回滚函数失败)~~:S5 整段推迟到 Phase 64,本 phase 不引入回滚机制
- ~~R10(route_change_log / policy_change_log schema 不一致)~~:本 phase 不引入审计 log 表
- ~~R12(§5 矩阵更新下游不一致)~~:本 phase 不修改 §5 矩阵
- ~~R13(store 函数 connection 参数 refactor)~~:S5 推迟到 Phase 64
- ~~R14(M0 audit 暴露大范围 NO_SKIP 红灯)~~:M0 已完成,实际只发现 2 条,均拆 G.5
- ~~R5_NEW(SQLite transaction 实装路径选择失误)~~:S5 推迟到 Phase 64
- ~~R15(§S2 方案选择失误)~~:M0 已敲定"删 dead code",无方案选择问题

---

## 详细分析

### R1 — identity/workspace 集中化 import 改动 regression(中)

**描述**:S1 引入 `swallow.identity.local_actor()` / `swallow.workspace.resolve_path()` 后,需要把现有 actor-semantic `"local"` 与 path 绝对化 `.resolve()` 调用全部改走集中化函数。改动跨 6+ 模块(`models.py` / `orchestrator.py` / `executor.py` / `literature_specialist.py` / `quality_reviewer.py` / `ingestion/pipeline.py` / `web/api.py`)。每处改动都是机械替换,但累计触点多,容易遗漏。

**触发场景**:
- 漏改某处 actor `"local"` 字面量 → S1 守卫 `test_no_hardcoded_local_actor_outside_identity_module` 红灯,需回头修
- 误改 `execution_site="local"`(站点语义)为 `local_actor()` → 行为变化,可能影响 router 路由决策

**缓解**:
- Codex 实装时按 disambiguation rule 分批审计:先列出所有 `"local"` 命中(按 R2 ACTOR_SEMANTIC_KWARGS 闭集分类),再逐文件改
- S1 实装顺序:先引入新模块 + 守卫(初始 expected fail)→ 逐文件迁移 → 守卫由 fail 转 pass
- 全量 pytest + lint 在每次 milestone commit 前运行

**回滚成本**:中。回滚仅需 revert import 改动,但需要确认守卫被同步删除以避免 false-positive。

---

### R2 — `"local"` 字面量 disambiguation 守卫误报/漏报(中)

**描述**:context_brief 显示代码库中 `"local"` 字面量出现 25+ 次,大部分是 `execution_site="local"`(站点语义),少数是 actor `"local"`。两者守卫行为应区分。守卫 pattern 设计错误会导致:
- **误报**:把 `execution_site="local"` 当作 actor 漏改,守卫红灯触发不必要的修改
- **漏报**:某个真实 actor `"local"` 没被守卫识别,绕过集中化要求

**触发场景**:
- 守卫用纯 grep / regex 匹配 `"local"` → 必然误报站点语义
- 守卫用 AST 但 ACTOR_SEMANTIC_KWARGS 闭集不全 → 漏报新引入的 actor 上下文

**缓解**:
- 守卫**必须使用 AST 而非 grep**:扫描 `kwarg.arg in ACTOR_SEMANTIC_KWARGS` 且 `kwarg.value` 是 `ast.Constant("local")` 的位置(`ACTOR_SEMANTIC_KWARGS` 闭集定义见 design_decision §S1 关键设计决策,authoritative)
- AST 守卫的 `ACTOR_SEMANTIC_KWARGS` 闭集作为模块级常量定义在 `tests/test_invariant_guards.py` 顶部,future Phase 引入新 actor 上下文时显式扩展(扩展行为本身需 phase-level review)
- DDL 中 SQL DEFAULT `'local'` 字面量自然不在 AST kwarg 调用语境中,守卫不会命中
- S1 实装时,Codex 应跑一次"audit dry-run":把当前 25+ 命中按 actor / site / 其他三类列出,Claude review 类目正确性
- `action` 已从闭集中移除(model_review Q3 反馈);`models.py:297 action="local"` 由 S1 实装时单独 audit 语义

**回滚成本**:低。守卫规则可以独立修订,不影响实装代码。

---

### R3 — Repository 抽象层重塑 governance 依赖图破坏既有路径(**高**)

**描述**:S3 引入 `swallow/truth/{knowledge,route,policy}.py` 作为 Repository 层,把 `governance.py` 直接 import 的 store 写函数改为 Repository 调用。这是 Phase 61 留下的核心架构债的兑现,governance.py 是治理入口,被多个调用方依赖。重塑过程中容易破坏:
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
- **不引入事务管理**:事务包装留给 Phase 64(候选 H);本 phase Repository 只做透明转发
- **循环 import 预防**:Repository 模块只 import store 函数,不 import governance / orchestrator;若发现循环依赖,在设计层重构而非 lazy import 绕开
- **S3 风险评级标记 [HIGH]**,Codex 实装时优先做"小步迁移":先建 `KnowledgeRepo` 一类、跑全测;再建 `RouteRepo`、跑全测;最后 `PolicyRepo`。三步分别 commit
- **Model Review Gate 已 review** Repository 接口设计(`design_decision.md` §S3 + model_review Q2/Q6 follow-up)

**回滚成本**:中-高。Repository 改动跨模块,回滚需要 revert 多文件;但因为 Phase 63 在 feature branch 上,git revert 整个 commit 是清晰边界。

---

### R4 — `_PENDING_PROPOSALS` 重复检测引发既有测试 fixture 冲突(低)

**描述**:S3 把 `_PENDING_PROPOSALS` 由静默覆盖改为 `DuplicateProposalError`。Phase 61/62 测试 fixture 可能依赖"同一 `(target, proposal_id)` 多次 register"的行为(例如 setup → tear down → 同 ID 重新 register)。

**触发场景**:既有测试套件在 fixture / setup 阶段同 `(target, proposal_id)` 重复 register。

**缓解**:
- Codex 实装时,grep `register_canonical_proposal` / `register_route_metadata_proposal` / `register_policy_proposal` / `register_mps_policy_proposal` 在 tests/ 中的所有调用位置
- 若发现 fixture 冲突,改 fixture 使用唯一 `proposal_id`(ULID),而非削弱 `DuplicateProposalError` 行为
- 若 fixture 真的需要"清空再 register"语义,可在 governance.py 增加 `_clear_pending_proposals_for_test()` 测试辅助函数(仅 tests/ 可用),保持生产代码严格 fail-on-duplicate

**回滚成本**:低。测试 fixture 改动隔离。

---

### R6 — §9 12 条守卫批量激活暴露既有未发现漂移(中,M0 已 pre-empt)

**描述**:S4 批量激活 12 条 §9 表内守卫(其中 NO_SKIP 6 条立即生效,2 条 G.5 占位 skip)。激活后可能发现既有代码中:
- 某 executor 在 task table 直写(违反 `test_no_executor_can_write_task_table_directly`)
- 某 state transition 不经 orchestrator(违反 `test_state_transitions_only_via_orchestrator`)
- Validator 返回非 verdict-only 结构(违反 `test_validator_returns_verdict_only`)
- ID & 不变量类守卫红灯
- UI 边界守卫红灯

每发现一条新漂移,修复可能超出本 phase scope,导致延期。

**M0 audit 已 pre-empt**:M0 NO_SKIP 报告显示 6 条 NO_SKIP_GUARDS 中 6 条全绿(Phase 63 启用范围),仅 G.5 启用范围(Path B + Specialist LLM)有 2 条红灯。R6 在 NO_SKIP 范围内的触发概率显著降低。但 ID & 不变量类 / UI 边界守卫**未被 M0 pre-scan 覆盖**(M0 只扫了 NO_SKIP 8 条),仍有可能在 S4 实装时触发红灯。

**触发场景**:S4 守卫激活后多条守卫红灯,且红灯路径在 `core` 模块上需要重大重构。

**缓解**:
- Codex 在 S4 实装时,**优先记录而非立即修复**:先把所有红灯守卫列出,Claude review 决定哪些必须本 phase 修、哪些登记为 Open 进 concerns_backlog
- **NO_SKIP_GUARDS 白名单**(Phase 63 启用 6 条)红灯**不允许 `pytest.skip`**,必须本 phase 修代码(详见 design_decision §S4 关键设计决策)
- **白名单外**(ID & 不变量类 / UI 边界):红灯可在 Codex 上报、Claude 评估后决定是否 skip + 登记 Open;skip 路径必须配 `# TODO(phase64+): ...` 注释 + 在 `concerns_backlog.md` 登记
- 若超过 3 条红灯需要本 phase 修,Claude 触发 phase-guard 评估是否拆 Phase 63.5 扩展 scope

**回滚成本**:低(守卫本身可独立 skip / unskip,但 NO_SKIP_GUARDS 内的守卫不能用 skip 退路)。

---

### R7 — `test_append_only_tables_reject_update_and_delete` SQLite trigger 基础设施缺失(中)

**描述**:`test_append_only_tables_reject_update_and_delete` 验证 DATA_MODEL §4.2 列出的 append-only 表(`event_log`、`event_telemetry`、`route_health`、`know_change_log`)拒绝 UPDATE / DELETE。SQLite 默认不阻止 UPDATE / DELETE;需要表级 trigger 显式 RAISE。context_brief 指出现有 schema 可能未部署此类 trigger。

**触发场景**:
- 测试 DB 与生产 DB 都没有 trigger,守卫直接红灯
- migration 脚本被遗漏,trigger 仅在新部署存在,既有用户库不一致

**缓解**:
- S4 实装前先 audit:`grep -rn 'CREATE TRIGGER' src/swallow/` 与既有 migration 路径,列出已存在的 trigger
- 若缺失,S4 内补:在 store 初始化路径上 `CREATE TRIGGER IF NOT EXISTS reject_update_<table> BEFORE UPDATE ON <table> BEGIN SELECT RAISE(ABORT, 'append-only'); END;` 与对应 DELETE trigger(idempotent)
- 守卫测试 fixture 在临时 DB 上验证(`tests/conftest.py` 引入 fixture)

**回滚成本**:中。Trigger 一旦创建,后续即使代码 revert,旧 DB 仍有 trigger。但 trigger 是 enforcement 机制,正常使用代码不会触发,无负面影响。

---

### R8 — §9 表实装计数审计错误(低)

**描述**:design_decision 给出"§9 表 17 条 / Phase 61 实装 3 条 / Phase 63 补 14 条(2 条 G.5 占位 skip)"的计数。若实装审计有遗漏(例如 Phase 62 的某守卫名碰巧与 §9 表条目重名,但语义不同),最终可能 §9 表实装数字不为 17。

**触发场景**:Phase 62 引入的某守卫名(如 `test_synthesis_uses_provider_router`)被误认为对应 §9 表的 `test_specialist_internal_llm_calls_go_through_router`。

**缓解**:
- S4 实装前 Codex 做一次精确审计:列出 `tests/test_invariant_guards.py` 中所有 `def test_*` 函数,与 §9 表 17 条名字逐一对照
- 审计结果作为 S4 PR body 一节,Claude review 验证
- design_decision 中已列出 Phase 61 实装的 3 条 + Phase 62 实装的 4 条 MPS 守卫(不在 §9 表内),作为审计 anchor
- M0 audit 已交叉验证 §9 表实装数 = 3(Phase 61),与 design_decision 一致

**回滚成本**:低。计数错误只导致守卫遗漏 / 重复,可修订。

---

### R11 — Model Review Gate 反馈(已闭环,低)

**描述**:Model Review verdict = BLOCK,3 BLOCK + 3 CONCERN。所有反馈已通过 final-after-m0 设计修订消化:
- Q1 [BLOCK] §5 矩阵漂移 → §S2 改为删 dead code,§5 矩阵不动
- Q5 [BLOCK] SQLite WAL 中间状态 → S5 推迟到 Phase 64(filesystem JSON 现状不适用 SQLite transaction)
- Q6 [BLOCK] Repository bypass → S3 增加 2 条 bypass 守卫
- Q2/Q3/Q4 [CONCERN] → 已落实

**回滚成本**:低。设计修订已完成,代码尚未启动。

---

### R16 — 删除 `_route_knowledge_to_staged` 时测试 mock 调整破坏原有断言意图(中,新增)

**描述**:S2 删除 `_route_knowledge_to_staged` 函数体 + 调用点 + 测试 mock 路由配置(`tests/test_cli.py:8839 restricted-specialist` / `tests/test_meta_optimizer.py:692 meta-optimizer-local`)。这两个测试 mock 原本是为了构造"被 route 到 staged-knowledge 副作用流"的场景,删除后若调整不当,可能让测试断言失去原意。

**触发场景**:
- 测试断言原本验证"task 完成后 staged candidate 写入 staged_knowledge 表",删除 `_route_knowledge_to_staged` 后断言变成空操作,但测试仍然 pass(伪 pass)
- 测试断言原本验证"restricted route 拒绝 task table 直写",删除 mock 路由配置后改成普通 route,守卫验证失去针对性

**缓解**:
- S2 实装时,Codex 对每个修改的测试 mock,在 PR body 中说明:**修改前的测试意图 / 修改后的测试意图 / 是否等价**
- 若不等价,显式说明 testpart 由哪个新断言/新测试覆盖,或登记为 Open(若覆盖移到 Phase 63.5/64)
- Claude review 时验证测试断言意图保留;若发现"伪 pass",要求 Codex 增加新断言

**回滚成本**:低。测试 mock 改动隔离,可独立 revert。

---

## 总体策略(final-after-m0)

1. **M0(S0)pre-implementation audit 已完成**(commit `c3637b1`):3 项 audit 全部产出报告;Claude 据报告做 3 个决策(删 dead code / S5 推迟到 Phase 64 / NO_SKIP 拆 G.5)
2. **M1(S1)identity/workspace 集中化**:后续所有 slice 的基础前置,确认 R1/R2 缓解策略落地;扩展 ACTOR_SEMANTIC_KWARGS 闭集
3. **M2(S2 + S3)同轮 review**:**S2 删 dead code**(M0 已确认 0 触发,低风险)+ **S3 Repository 抽象层骨架**(高风险)。S3 必须先做等价回归测试,再引入 Repository。Codex 拆 commit:S2 一个 commit / S3 三个 commit(KnowledgeRepo / RouteRepo / PolicyRepo 各一);**Repository bypass 守卫(2 条)与 S3 同轮**;**INVARIANTS §5 矩阵不动**,M2 内无 docs(design) commit
4. **M3(S4)按 NO_SKIP 6 条 + G.5 2 条占位策略**:6 条立即启用 NO_SKIP_GUARDS 红灯不允许 skip;ID & 不变量类 / UI 边界守卫红灯按 R6 流程处理;2 条 G.5 范围守卫以 `pytest.skip(reason="G.5 will enable")` 占位
5. **Model Review Gate 已完成**(verdict = BLOCK,所有反馈已消化)
6. **Phase 63 完成后**:进入 Phase 63.5(候选 G.5)修复 NO_SKIP 红灯 2 条;G.5 完成后进入 Phase 64(候选 H)做 Truth Plane SQLite 一致性 + `apply_proposal` 事务回滚

## 与既有 risk 模式的对照

- 类似 Phase 61(apply_proposal):本 phase 也是宪法层债务收口,模式一致 —— 大量改动表面但对外行为等价
- 类似 Phase 62(MPS):本 phase 也涉及多 milestone 推进 + model_review BLOCK + revised-after-model-review,模式高度一致
- 不类似 Phase 60(retrieval policy):本 phase 不引入 user-facing 行为变化,无 eval 需求
- **新模式**:本 phase 引入 M0 pre-implementation audit slice,作为"早识别风险"机制 —— 实际效果验证(M0 暴露 3 个关键事实大幅收窄 phase scope)。这是治理类 phase 的有用范式,后续治理类 phase(G.5 / H)可直接复用 audit 模板
