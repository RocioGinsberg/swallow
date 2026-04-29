---
author: claude
phase: phase65
slice: design-gate
status: review
depends_on:
  - docs/plans/phase65/kickoff.md
  - docs/plans/phase65/design_decision.md
  - docs/plans/phase65/risk_assessment.md
  - docs/plans/phase65/design_audit.md
  - docs/design/INVARIANTS.md
  - docs/design/DATA_MODEL.md
reviewer: external-model
verdict: BLOCK
---

TL;DR: GPT-5 二次核验返回 **BLOCK**(5 BLOCK + 9 CONCERN + 3 PASS)。与 design-auditor 重叠的 SQLite transaction API + connection access pattern 维持 BLOCK;此外把 design-auditor 的 3 个 CONCERN 升级为 BLOCK:**§3.4 schema 字段缺口威胁 P2 兑现性**、**§3.5 policy 持久化语义未定**、**§8 "不允许运行时静默执行"与 dev-mode auto-migrate 直接矛盾**。Claude 必须修订 design_decision.md 解决 5 个 BLOCK 后再过 Human Design Gate。

## Scope

外部第二模型审查范围:`docs/plans/phase65/{kickoff, design_decision, risk_assessment, design_audit}.md` + INVARIANTS P2 / §0 #4 / §9 + DATA_MODEL §3.4 / §3.5 / §4.2 / §8 anchors。

Reviewer:`mcp__gpt5__chat-with-gpt5_5`(项目级 GPT-5 通道,与 Phase 64 model_review 同款配置)。

外部模型只输出 advisory 建议,不做实现 / 不改设计正文 / 不绕过 Human gate。

## Verdict

**BLOCK** — 不批准当前 draft 进入 Human Design Gate;必须修订 design_decision.md 解决 5 个 BLOCK,risk_assessment.md 视情况补 R 条目。

## Findings

### BLOCK

- **[BLOCK-1] SQLite transaction ownership 未指定**(与 design-auditor BLOCKER 1 重叠)
  - 证据:design_decision §S2 pseudocode `conn.execute("BEGIN IMMEDIATE")` 在 Python `sqlite3` 默认 `isolation_level=''` 下会被隐式事务覆盖,触发 `OperationalError: cannot start a transaction within a transaction`。
  - 修复方向:design 必须明确 (a) `isolation_level=None`(autocommit + 显式管理事务) 还是 (b) 在 BEGIN 前 `commit()` 关闭隐式事务;无论选哪一个,都要描述对既有 `with self._connect(base_dir) as connection:` 模式的影响。
  - 影响 scope:每个写路径在该 connection 上的行为,不止 `_apply_metadata_change`。

- **[BLOCK-2] Connection access pattern 是设计决策,不是实现细节**(与 design-auditor BLOCKER 2 重叠)
  - 证据:`router.py` / `truth/route.py` 不能直接访问 `SqliteTaskStore()._connect(base_dir)`(私有方法 + 通过实例) — 必须给出 module-level 可用 accessor 的设计;否则 4 对 save+apply + audit 写不能保证使用同一 connection,事务边界形同虚设。
  - 修复方向:design 必须三选一并写清:(a) 在 `sqlite_store.py` 引入 module-level `get_connection(base_dir)` (b) 在 `router.py` 实例化 `SqliteTaskStore` 并通过 public 接口取 connection (c) 通过依赖注入由 caller 传入 connection。每种选择对 `test_only_apply_proposal_calls_private_writers` 守卫与 mock 模式有不同后果,要在 design 内表态。

- **[BLOCK-3] §3.4 schema 字段缺口直接威胁 P2 兑现性**(将 design-auditor CONCERN A 升级)
  - 证据:实际 RouteSpec 含 `capabilities`(嵌套 dict,6 子字段)、`taxonomy`(嵌套 dict,2 子字段)、`execution_site`、`executor_family`、`executor_name`、`remote_capable`,均未在 DATA_MODEL §3.4 DDL 中。
  - 升级理由:不仅是文档对齐问题 — 若这些字段不能 round-trip 进 SQLite,SQLite 就不是 governance truth,filesystem JSON / in-memory dict 仍承载部分真值,**P2 在 Phase 65 没有真正兑现**(即 Phase 65 直接失败其名义目标)。
  - 修复方向:design_decision §S1 必须给出确定决议:(a) 全部新增独立列(然后改 DATA_MODEL §3.4 加列) (b) 引入 `raw_json TEXT NOT NULL` 全量序列化列 + 可索引字段做 materialized extract (c) 嵌套 dict 拆为独立 JSON TEXT 列(`capabilities_json`、`taxonomy_json`)。Codex 不能在 PR body 中决定这种 schema 形态。

- **[BLOCK-4] §3.5 policy 持久化语义未定**(将 design-auditor CONCERN B 升级)
  - 证据:`policy_records(kind, scope, scope_value, payload)` 列与现有 `AuditTriggerPolicy` 数据类 + `(mps_kind, mps_value)` 两类 payload 之间没有显式映射。
  - 升级理由:不写 round-trip 表就实装 = S2 测试可能"看起来通过"但 policy 形状静默损坏。这同样威胁 P2 兑现性。
  - 修复方向:design_decision §S2 必须新增 2 行映射表:`audit_trigger_policy → kind='audit_trigger', scope='global', scope_value=NULL, payload=AuditTriggerPolicy.to_dict()`(示例) + `mps_policy → kind='mps', scope='task_family' or similar, scope_value=task_family, payload={...}`。

- **[BLOCK-5] DATA_MODEL §8 "不允许运行时静默执行"与 dev-mode auto-migrate 直接矛盾**(将 design-auditor CONCERN C 升级)
  - 证据:DATA_MODEL §8 文字明确:**"Migration 不允许在运行时静默执行;`swl` 启动时检测 schema 落后会进入 `waiting_human`,提示运行 `swl migrate`"**。design_decision §S3 写"开发模式默认自动 migrate"。
  - 升级理由:这是宪法级 doc 的明文条款 vs Phase 65 设计直接相反。Codex 实装时无所适从。
  - 修复方向二选一:
    - (i) Phase 65 收紧:auto-apply 仅限"fresh empty DB / table 不存在 → 创建" — 不算 "migration"(因为没有从旧 schema 升级到新 schema),并在 §3 / §S3 显式写"创建首批 schema 不视为 §8 范围内的 migration"。
    - (ii) 修订 §8:加例外条款 "single-user 开发模式允许自动 apply;生产模式 `SWL_MIGRATION_MODE=manual` 强制 waiting_human"。但这是宪法级修改,需要 Human 单独批准 — 不应在 Phase 65 closeout 顺手做。
  - 推荐 (i)(scope 更小,符合 single-user / single-machine 项目定位)。

### CONCERN

- **[CONCERN-1] 事务内 SELECT 与 ROLLBACK 后 redo 时机** — 同一事务内的 SELECT 看到自己事务的未 commit 写入是 SQLite 的 expected 行为;但 ROLLBACK 后的 redo 必须发生在 connection 状态干净之后,否则 in-memory `ROUTE_REGISTRY` 可能被失败事务的 snapshot 覆盖。design 应明确 redo 调用前 connection 已经处于 idle 状态。
- **[CONCERN-2] 失败注入测试矩阵覆盖不足** — design 只描述"模拟事务中途失败"。Acceptance test 必须强制覆盖以下注入点:第一次 SQL UPSERT 前 / 第 1/2/3/4 个 stream UPSERT 后 / `apply_route_*` in-memory mutation 后 / audit INSERT 后 commit 前 / commit 后。Policy 路径同款简化版。
- **[CONCERN-3] `_apply_route_review_metadata` artifact 文件需显式归类** — design 把 artifact 文件写排除在事务外;但必须显式声明 artifact 是"derived / cache / audit-adjacent",而非 canonical governance state。否则 P2 仍有"filesystem 持有真值"的隐患。建议在 design_decision §S2 加一行"review record artifact 是 audit-adjacent 派生物,任何 reader 不得把它当作 truth"。
- **[CONCERN-4] M1 一次性 JSON 导入与 M3 schema migration 概念耦合** — 两者都叫"migration"但语义不同:M1 = legacy data import / bootstrap;M3 = schema_version upgrade。建议在 design 内显式分离命名:M1 用 `bootstrap_*` / `import_legacy_*`;M3 才用 `migrate`。否则与 §8 的 human-gated migration 模型冲突,操作员/测试都会困惑。
- **[CONCERN-5] M1 已知不一致只能在 milestone 边界内可接受,不可作为 release 状态** — design 文字承认 M1 期间"writer 写 JSON,reader 读 SQLite 快照"的不一致。Human gate 必须强制要求:**Phase 65 整体 release 不允许停在 M1 后**(否则等于声称兑现 P2 但实际有数据丢失风险)。Codex M1 commit 必须立即承诺接 M2,不能将 M1 单独 PR 上 main。
- **[CONCERN-6] action enum 在 migration/import 路径含义模糊** — design_decision §S1 让 import 写 audit 行 actor='migration',但 action 仅枚举 `upsert | delete`。要么扩 enum 加 `import` / `bootstrap`,要么明确"M1 的 bulk import 不写 audit log,audit history 从 M2 commit 后开始"。建议后者(audit log 从真正的 governance 写入起算,导入不计)。
- **[CONCERN-7] audit snapshot 大小** — `capability_profiles` × `task_family_scores` 嵌套 dict 双倍存储无 cap。单用户单机项目接受,但测试要包含 non-trivial 大小的 round-trip;若超大 payload 导致 proposal apply 失败,需声明这是 intentional("audit 在事务内,大 payload 失败即 governance 失败,符合原子性")。
- **[CONCERN-8] §9 守卫扩展必要但不充分** — `APPEND_ONLY_TABLES` 4→6 拒 UPDATE/DELETE 是基线;但还应测"没有 public Repo method 改 audit 行" + "migration / seed 路径只走 INSERT"。design 已写第一项,需补第二项。
- **[CONCERN-9] §0 #4 入口守卫保留** — 替换 JSON writer 后,新加的 SQL writer helper 必须保持私有 + 只通过 `apply_proposal` 可达;`test_only_apply_proposal_calls_private_writers` 当前已覆盖 6 个保护名,需在 PR 同时验证守卫不被绕过。

### PASS

- **[PASS-A] Repository 层事务内写 audit 是 single-user / single-machine 场景下正确选择** — 比 outbox pattern 更简单更强;损失 = 异步 telemetry 灵活性,Phase 65 不需要,正确推迟。
- **[PASS-B] `route_fallbacks.json` 维持 JSON operator-local seam 正确** — Phase 64 已分类为 operator-local config seam,不属于 P2 governance truth;Phase 65 不重新动是正确的 scope 控制。
- **[PASS-C] 单机单用户场景下 `BEGIN IMMEDIATE` 足够** — 无需引入 distributed locking / multi-host 协调机制(永久非目标)。

## Missing acceptance criteria / tests

GPT-5 强烈建议 design 在通过 Human gate 前补的测试 / 验收清单(应进入 Phase 65 closeout 验证矩阵):

- 事务模式显式测试:fresh connection + after prior reads/writes 都能跑 `BEGIN IMMEDIATE` 不报错。
- 全 S2 SQL 写 + audit insert 同 connection / 同事务断言。
- 失败注入矩阵:每个注入点(见 CONCERN-2)都有对应 test case。
- ROLLBACK 后断言:SQLite 行未变 / audit 行不存在 / in-memory `ROUTE_REGISTRY` == 事务前 SQLite 快照 / legacy JSON 不被读为 truth。
- 成功 commit 后断言:进程重启从 SQLite 加载所有 4 个 stream / audit 行存在含正确 before/after / 不再写 JSON。
- M1 一次性导入测试:仅在 SQLite 空时跑 / 重复 reader 调用幂等 / 不覆盖既有 SQLite 行 / 部分预存状态确定性 / 忽略 `route_fallbacks.json`。
- Reader 优先级测试:SQLite > .swl/*.json > *.default.json 三级 fallback 链。
- 完整 RouteSpec round-trip:`capabilities` / `taxonomy` / `execution_site` / `executor_family` / `executor_name` / `remote_capable` / weights / capability_profiles 全字段。
- Policy round-trip:`audit_trigger_policy` + `mps_policy` 双 kind。
- Schema migration 协议测试:fresh DB 安全建表 / stale DB manual 模式进 `waiting_human` / `swl migrate --status` 正确输出 / migration 文件正好 apply 一次 + 写 `schema_version`。
- DATA_MODEL §8 行为显式测试:无运行时静默 migration(除非 §8 显式例外被批准)。
- Append-only 强化:UPDATE 拒 / DELETE 拒 / 正常 INSERT 允许 / migration/import 路径行为明确。
- `apply_proposal` 唯一公开 canonical 写入入口断言;私有 `_apply_*_change` 不被外暴露 / 调用。
- `_apply_route_review_metadata` artifact 失败行为:artifact 写失败 → 不 commit;artifact 写成功但后续 SQL ROLLBACK → artifact 显式标 stale 或 reader 不读为 truth。

## Invariant conflicts

- **[BLOCK]** DATA_MODEL §8 vs S3 dev-mode auto-migrate(BLOCK-5)。
- **[BLOCK]** P2 vs §3.4 schema 字段缺口(BLOCK-3)。
- **[CONCERN]** P2 vs review record artifact 在事务外(CONCERN-3)。
- **[CONCERN]** §0 #4 写入入口守卫在 SQLite writer 替换后必须延续(CONCERN-9)。
- **[CONCERN]** §9 守卫扩展时序 — 新 audit 表先建 + 守卫后扩可能短暂弱化(CONCERN-8);M3 应与 M1 表 DDL 同 milestone 落地或验证次序无 gap。
- **[PASS]** §4 LLM 调用契约不被本 phase 触动。

## Scope creep / scope-cutting recommendations

- **核心(必保)**:M1 schema 兑现 + reader 切 + import / M2 writer 切 + 事务 + 审计。两者缺一不能声称 P2 兑现。
- **核心(必保)**:M3 之 §9 append-only 守卫扩展 + 最小 schema 创建 + version 感知。
- **可推迟**:M3 完整 `swl migrate --status` UX、manual 模式打磨、generalized migration framework 超出 Phase 65 第一个 migration 必需的部分 — 可以拆 Phase 65.5 或推迟到下一个 schema 变更 phase。
- **不重审**:`route_fallbacks.json` JSON 状态 — 除非测试发现它实际被作为 canonical route metadata 读取,Phase 65 不动。
- **不引入**:outbox / worker-based audit pattern — 单机单用户无收益。
- **强约束**:DATA_MODEL §3.4 / §3.5 字段补齐不算"casually expanding" — 若 RouteSpec 当前字段缺持久化,Phase 65 必须补,否则不能声称 P2 兑现。

## Claude Follow-Up

**必修**(Claude 在 Design Gate 前必须修订):

1. `design_decision.md §S2 事务边界`:补 SQLite isolation_level / autocommit 决议(BLOCK-1) + connection accessor 决议(BLOCK-2)。
2. `design_decision.md §S1`:补 `route_registry` 字段映射策略(列扩展 vs `raw_json` blob vs 嵌套 JSON 列)(BLOCK-3) — 同步 DATA_MODEL §3.4 的修改边界。
3. `design_decision.md §S2`:补 `policy_records` 列与 audit_trigger_policy / mps_policy 的 round-trip 映射表(BLOCK-4)。
4. `design_decision.md §S3` + `kickoff.md §G6`:解决 §8 "不允许运行时静默执行"矛盾(BLOCK-5)— 推荐采纳"首次建表不算 migration"路径。
5. `design_decision.md §S2`:补 ROLLBACK 后 redo 时序约束(CONCERN-1) + 失败注入测试矩阵(CONCERN-2) + review record artifact 显式归类(CONCERN-3)。
6. `design_decision.md §S1 / §S3`:M1 import 与 M3 schema migrate 概念分离命名(CONCERN-4)。
7. `kickoff.md §完成条件`:补"Phase 65 整体 release 不允许停在 M1 后"约束(CONCERN-5)。
8. `design_decision.md §S2`:audit action enum 决议(CONCERN-6)— 推荐"M1 import 不写 audit log"。
9. `risk_assessment.md`:R5 加 audit snapshot 大小测试约束(CONCERN-7);新增 R10 §8 矛盾解决 + 缓解。

**选修**:

- 把 GPT-5 的"missing acceptance criteria"清单整段并入 `design_decision.md §S1/S2/S3 验收条件`(避免 closeout 时遗漏)。

修订后无需再触发一次 model_review(BLOCK 项均为 design 文字明确性,不需要二次外部审查;internal 一致性由 Claude 自查 + Human Gate 把关)。

## Human Gate Note

Human 在 Design Gate 决策前应核查的 5 项:

1. design_decision.md §S2 已补 SQLite isolation_level + connection accessor 决议(BLOCK-1, BLOCK-2)?
2. design_decision.md §S1 已补 §3.4 字段映射策略,且 DATA_MODEL.md 修改边界相应放宽到"补字段"(BLOCK-3)?
3. design_decision.md §S2 已含 policy_records round-trip 映射表(BLOCK-4)?
4. §8 "不允许运行时静默执行"矛盾如何解决(BLOCK-5)— 推荐"首次建表不算 migration"路径,Human 显式确认是否采纳?
5. kickoff §完成条件 已含"Phase 65 整体 release 不允许停在 M1 后"约束(CONCERN-5)?

5 项都满足 + design_audit.md 标 READY_FOR_HUMAN_GATE 后,可以进入 Direction Gate 批准 + 切 `feat/phase65-truth-plane-sqlite` 分支。

---

## Reviewer Verbatim Excerpt(关键句留档)

> "Do not approve Phase 65 as-is. The direction is sound—SQLite-primary route/policy truth, same-transaction audit rows, and append-only guards are appropriate for Swallow—but the design still has phase-blocking ambiguity around SQLite transaction ownership, connection access, schema/field completeness, and the DATA_MODEL §8 migration contradiction. Require a revised design decision that fixes those points before implementation."

>  "[BLOCK] Schema/field mapping gap can silently violate P2 — If RouteSpec fields added by Phase 64 are not persisted in `route_registry`, SQLite is not the durable governance truth. This is not merely a doc concern: missing `capabilities`, `taxonomy`, executor fields, or `remote_capable` would make JSON/in-memory carry truth not represented in SQLite."
