---
author: claude
phase: phase65
slice: risk-assessment
status: revised-after-model-review
depends_on: ["docs/plans/phase65/kickoff.md", "docs/plans/phase65/design_decision.md", "docs/plans/phase65/design_audit.md", "docs/plans/phase65/model_review.md", "docs/plans/phase65/context_brief.md", "docs/plans/phase64/closeout.md", "docs/plans/phase63/closeout.md"]
---

TL;DR(revised-after-model-review,2026-04-29): **11 条风险条目**(原 9 条 + 新增 R10/R11 来自 model_review)。**1 高 / 5 中 / 5 低**。S2 事务边界 + in-memory ROUTE_REGISTRY 在 ROLLBACK 后的一致性仍是唯一高风险点(R1);R5 audit snapshot 完整性增补大小测试约束(per CONCERN-7);**R10**(新增):DATA_MODEL §8 与运行时 auto-migrate 矛盾的解决路径执行风险(已采纳路径 i:首次建表不算 migration;残余风险 = 文字 narrowing 不充分);**R11**(新增):§3.4 加 6 列后 SQLite UPSERT 全字段完整性校验(已采纳路径 a:加独立列;残余风险 = bootstrap 漏填字段)。原 R2 schema 不对齐风险因 BLOCK-3 决议消化为已知行动项;原 R8 schema_version 协议落地因 BLOCK-5 narrowing 简化(Phase 65 不引入真正的 migration runner)。

## 风险矩阵(2026-04-29 修订)

| ID | 风险 | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 等级 | 状态 |
|----|------|---------|--------|-----------|------|------|------|
| R1 | S2 事务边界 + in-memory ROUTE_REGISTRY 在 ROLLBACK 后的一致性 | 3 | 2 | 2 | **7** | **高** | active(BLOCK-1/CONCERN-2 增补失败注入矩阵) |
| R2 | DATA_MODEL §3.4/§3.5 schema 与实装隐性不对齐 | 2 | 2 | 1 | 5 | 中 | mitigated(BLOCK-3 决议:加 6 列全部承载) |
| R3 | 一次性 bootstrap import 与 reader 第一次访问时序竞争 | 2 | 1 | 2 | 5 | 中 | active(命名分离为 bootstrap;`BEGIN IMMEDIATE` 互斥) |
| R4 | `_apply_route_review_metadata` 跨多 save 调用的事务边界设计 | 2 | 2 | 2 | 6 | 中 | active(CONCERN-3 增补 artifact 显式归类) |
| R5 | 审计 before/after snapshot 完整性 + 大小 | 2 | 1 | 2 | 5 | 中 | active(CONCERN-7 增补 non-trivial round-trip 测试约束) |
| R6 | 测试 fixture 兼容 — `tmp_path.write_text` 直接写 JSON 的测试需迁移 | 1 | 1 | 1 | 3 | 低 | active |
| R7 | `_BUILTIN_ROUTE_FALLBACKS` import-time 快照与 SQLite 时序 | 1 | 1 | 1 | 3 | 低 | active |
| R8 | `schema_version` 协议落地与 §8 矛盾 | 1 | 1 | 1 | 3 | 低 | mitigated(BLOCK-5 决议:首次建表不算 §8 migration) |
| R9 | Phase 61 留下的"事务回滚"Open 完整闭合验证 | 1 | 1 | 1 | 3 | 低 | active |
| **R10** | **§8 narrowing 不充分,引入 schema 升级时仍需补真正的 migration runner** | 1 | 2 | 1 | 4 | 低-中 | **新增**(BLOCK-5 决议遗产) |
| **R11** | **§3.4 加 6 列后 bootstrap / SQLite UPSERT 漏填字段** | 2 | 1 | 1 | 4 | 低-中 | **新增**(BLOCK-3 决议遗产) |

---

## 详细分析

### R1 — S2 事务边界 + in-memory ROUTE_REGISTRY 在 ROLLBACK 后的一致性(**高**)

**描述**:S2 把 `RouteRepo._apply_metadata_change` 整体包 `BEGIN IMMEDIATE` 事务。事务内顺序执行 4 对 save+apply(SQLite UPSERT + in-memory `ROUTE_REGISTRY` mutation)。**关键问题**:
- SQLite 数据由 `BEGIN IMMEDIATE` / `COMMIT` 保证原子性 — 失败 `ROLLBACK` 后 SQLite 回到事务前状态
- **但 `apply_route_*` helper 的副作用是 mutate module-level `ROUTE_REGISTRY` 对象的属性**(Python 层无 transaction rollback 能力)
- 事务中途失败 ROLLBACK 后:SQLite OK,但 `ROUTE_REGISTRY` 已经局部 mutation,**与 SQLite 不一致**

**触发场景**:
- `_apply_metadata_change` 内 route_registry 的 SQL UPSERT 成功 + 进程内 `ROUTE_REGISTRY` 已 mutation,接着 route_capability_profiles 的 SQL UPSERT 失败 → 事务 ROLLBACK,SQLite 中 route_registry 回滚但 `ROUTE_REGISTRY.<route>.fallback_route_name` 等属性已变化
- 后续 reader 调用读 SQLite → 拿到回滚后状态,但 in-memory 是局部 mutation 状态

**缓解**:
- design_decision §S2 已给出方案:**事务 ROLLBACK 后从 SQLite 重新加载,把 in-memory `ROUTE_REGISTRY` 恢复到事务前状态**(等价于 redo)
  ```python
  except Exception:
      conn.execute("ROLLBACK")
      # 等价 redo: 从 SQLite 重新加载 in-memory state
      apply_route_registry(base_dir)
      apply_route_policy(base_dir)
      apply_route_weights(base_dir)
      apply_route_capability_profiles(base_dir)
      raise
  ```
- 这一 redo 步骤本身可能再失败(如 SQLite 损坏),但 SQLite 损坏属于 catastrophic failure;Phase 65 假设 SQLite 健康
- **回归测试**(authoritative,Codex 在 S2 PR body 中实装):
  - 模拟 route_capability_profiles save 阶段抛错(monkeypatch),验证:(a) SQLite ROUTE_REGISTRY 表回滚 (b) in-memory `ROUTE_REGISTRY.<route>.fallback_route_name` 等属性恢复事务前状态
  - 模拟事务后 audit log 写入失败(`route_change_log` INSERT 失败),验证整个事务 ROLLBACK
- model_review Gate 触发(若 Human 同意),GPT-5 视角能核验事务边界设计 + redo 路径

**回滚成本**:中。事务边界改动跨 truth/route.py + truth/policy.py + router.py 多文件;但 Phase 63 立的 Repository 接口不变,逻辑改动可隔离

---

### R2 — DATA_MODEL §3.4/§3.5 schema 与实装可能存在隐性不对齐(中)

**描述**:DATA_MODEL §3.4 的 `route_registry` 表 schema 是 ~2 phase 前定义的(早于 Phase 64 三层外部化)。Phase 64 引入的字段(如 routes.default.json 中的 `taxonomy` 嵌套 + `capabilities` 嵌套 + 多个 hint 字段)可能在 §3.4 的 schema 中**未充分覆盖**。

**触发场景**:
- §3.4 字段 `unsupported_task_types JSON` / `cost_profile JSON` 不足以承载 Phase 64 RouteSpec 全部字段
- §3.4 缺 Phase 64 引入的 `route_taxonomy_role` / `route_taxonomy_memory_authority` 等字段
- §3.5 `policy_records.kind` 枚举未覆盖 Phase 62 引入的 MPS policy

**缓解**:
- design_decision §S1 已规定:**实装前 sanity check schema;若需调整先改 DATA_MODEL.md 再改代码**(per DATA_MODEL.md 顶部"先改文档"原则)
- Codex 在 S1 PR body 中给出"DATA_MODEL §3.4/§3.5 与实装 RouteSpec / policy 字段对照表",列出每个字段是否兼容
- 若发现需调整,先小范围改 DATA_MODEL.md(本 phase scope 内允许的"已定义未实装"补丁),Claude review 时验证字段调整不超 scope
- **极端场景**:若 §3.4 schema 严重过时需重新设计,触发 design 层评估(可能升级 phase scope 或推迟)

**回滚成本**:低-中。schema 调整在 phase 早期发现成本低;migration 已 apply 后再发现需要 schema_version v2 + 新 migration

---

### R3 — 一次性 migration 与 reader 第一次访问时序竞争(中)

**描述**:M1 引入"SQLite 表空 + JSON 存在 → 一次性 migrate"。**关键时序**:
- 进程启动后第一次调用 `apply_route_registry(base_dir)`
- helper 检查 SQLite `route_registry` 表是否为空
- 空 → 触发 migration → 从 .swl/routes.json 加载 → 写 SQLite
- 非空 → 直接读 SQLite

**触发场景**:
- 多进程并发启动(如 web/api.py 多 worker):两个进程同时检查 SQLite 表为空,同时跑 migration → SQLite 写入冲突 / 重复
- migration 中途进程崩溃:SQLite 部分写入,下次启动 reader 检查"非空"而跳过 migration → migrated 数据局部缺失

**缓解**:
- migration helper 用 `BEGIN IMMEDIATE` 包裹整个 migration(`INSERT OR REPLACE` 全量数据 + COMMIT),保证原子性 + 多进程互斥(`BEGIN IMMEDIATE` 锁)
- migration 完成后立即写 `route_change_log` 一行 actor='migration'`,作为"migration 已完成"标记
- 后续启动检查"`route_registry` 非空"是足够的 idempotency 标识(因为 migration 是事务原子)
- 多进程启动场景:第二个进程的 `BEGIN IMMEDIATE` 等第一个完成后看到非空,跳过 migration — 安全

**回滚成本**:低。migration 路径独立,失败 ROLLBACK 后下次启动重试

---

### R4 — `_apply_route_review_metadata` 跨多 save 调用的事务边界设计(中)

**描述**:`governance.py:_apply_route_review_metadata`(line 325-577,~250 行)是 meta-optimizer review apply 路径,内部调用多个 save_* + write_json (review record artifact 文件)。**事务包裹的边界问题**:
- SQL writes 在 `_apply_metadata_change` 内部事务里(M2 实装)
- review record artifact 文件写入(`_write_json(application_path, ...)`)**不在事务内**(filesystem write,不属于 SQLite truth)

**触发场景**:
- SQL commit 成功 + review record write 失败 → SQLite 已写但 artifact 文件缺失,后续审计无法回溯
- review record write 成功 + SQL commit 失败 → artifact 文件留下,SQLite 回滚 → 不一致

**缓解**:
- design_decision §S2 已说明:本 phase **不修复**此问题(超 scope,review record 是 audit artifact 而非 truth);closeout 登记 backlog Open
- review record write 在 SQL commit 后再写(at-least-once 语义,失败时记日志但不影响 truth)
- 实装层面:`_apply_route_review_metadata` 把 SQL writes 与 artifact write 拆开,SQL 在 `_apply_metadata_change` 内部事务,artifact 在事务外(commit 后)
- 这是已知不完美,Phase 65 接受;后续 phase 可引入"Repository 层 file artifact write 也走事务"机制(类比 Outbox pattern)

**回滚成本**:零(已知不完美,不修复)

---

### R5 — 审计 before/after snapshot 完整性 + 大小(中,2026-04-29 修订)

**描述**:`route_change_log` / `policy_change_log` 的 `before_payload` / `after_payload` 字段记录变更前后的 JSON snapshot。**完整性问题**:
- 仅记录"本次 proposal 改动的字段"vs"全量 snapshot" — Codex 实装选错,审计回溯能力不同
- before snapshot 在事务内 SELECT,after snapshot 也在事务内 SELECT,**两者必须在同一 SQLite snapshot view**(否则可能混入并发修改,虽然 BEGIN IMMEDIATE 已经互斥)
- snapshot 序列化 JSON 时丢字段(如 RouteSpec 嵌套 dataclass 序列化路径错置)

**触发场景**:
- 仅记改动字段 → 后续审计回溯需要 reconstruct 完整 RouteSpec 状态时缺数据
- before / after 时序错置 → audit log 显示"变更后状态"实际是变更前

**缓解**:
- design_decision §S2 推荐**全量 snapshot**(每次 audit 行存一份完整 dict;成本可接受)
- before snapshot 在事务开始后 + UPSERT 前 SELECT;after snapshot 在 UPSERT 后 + COMMIT 前 SELECT(BEGIN IMMEDIATE 保证 view 一致)
- snapshot 序列化复用既有 `RouteSpec.to_dict()` / `dataclasses.asdict`,Phase 64 已有的成熟路径
- Codex 在 S2 PR body 中给出 before / after 示例数据 + 字段完整性证明
- **新增(model_review CONCERN-7)**:S2 PR 必须含 non-trivial round-trip 测试 — fixture 包含 ≥3 routes × 5+ task_family_scores entries 的 capability_profiles,验证 audit 行 JSON 完整可反序列化
- **新增**:超大 payload(>1MB)导致 SQLite 写失败 → 该次 proposal apply 整体 ROLLBACK,这是 intentional behavior(audit 在事务内,大 payload 失败即 governance 失败,符合原子性);closeout 文字声明

**回滚成本**:低。审计 schema 字段调整在 Phase 65 早期发现成本低

---

### R6 — 测试 fixture 兼容(低)

**描述**:context_brief 已确认大量测试用 `save_route_registry(tmp_path, ...)` / `apply_route_registry(tmp_path)` 模式,Phase 65 后这些 helper 内部从 JSON 写改为 SQL UPSERT — **接口签名不变,测试自动跟随**。但 `tests/test_router.py:242, 265` 等测试有路径名 assertion(`routes.json` / `route_policy.json`),Phase 65 后这些路径不再是 truth 写路径,assertion 需更新或删除

**触发场景**:测试 fixture 直接断言 `assert (tmp_path / ".swl" / "routes.json").exists()` — Phase 65 后 SQLite 是 truth,JSON 文件不再被 writer 创建(除非 migrate 还在保留 JSON,具体看 migration 后是否 untouch JSON)

**缓解**:
- Codex 实装时 grep `tests/test_router.py` 中所有 `routes.json` / `route_policy.json` 路径名 assertion,逐个 audit:
  - 若是验证 reader fallback 链(JSON 作为 fallback source),保留
  - 若是验证 writer 写 JSON,改为验证 SQLite 行存在
- S2 PR body 中给出测试 fixture 迁移清单
- 测试 mock 模式不变(`patch("swallow.router.save_route_registry", ...)`)

**回滚成本**:低。测试单点 fix

---

### R7 — `_BUILTIN_ROUTE_FALLBACKS` import-time 快照与 SQLite 时序(低)

**描述**:`router.py:530 _BUILTIN_ROUTE_FALLBACKS = {route.name: route.fallback_route_name for route in ROUTE_REGISTRY.values()}` 在模块 import 时构建,从 `routes.default.json` 加载的初始 ROUTE_REGISTRY 快照。Phase 65 后:
- import-time:`ROUTE_REGISTRY` 仍从 routes.default.json 构建(import-time 无 base_dir)
- 首次 `apply_route_registry(base_dir)`:从 SQLite 加载 → 刷新 ROUTE_REGISTRY + `_BUILTIN_ROUTE_FALLBACKS`
- `apply_route_fallbacks(base_dir)` 以 `_BUILTIN_ROUTE_FALLBACKS` 为 baseline 叠加 `.swl/route_fallbacks.json` override

**触发场景**:
- SQLite 中 registry 与 default 差异大(operator 改了多个 fallback)
- 首次 `apply_route_registry` 之前其他代码访问 `_BUILTIN_ROUTE_FALLBACKS`(如 fallback override 计算)→ 拿到 default 快照,覆盖后才正确

**缓解**:
- Phase 64 已确认 5 处加载顺序在 `apply_route_fallbacks` 之前都先调 `apply_route_registry`(顺序对齐)
- Phase 65 不改加载顺序,只改 reader 实装
- `_BUILTIN_ROUTE_FALLBACKS` 在每次 `apply_route_registry` 后同步刷新(随 ROUTE_REGISTRY 更新)
- 边界情况:进程刚启动 + 5 个加载入口都未跑过(罕见),fallback override 计算用 default 快照 — Phase 65 不改此现状

**回滚成本**:零(已知设计现状,不变化)

---

### R8 — `schema_version` 协议落地缺失或与现状不符(低)

**描述**:DATA_MODEL §8 定义 migration 协议,但代码层可能尚未实装 `schema_version` 表 + version 检测。Phase 65 引入第一个 migration(`001_phase65_route_policy_sqlite.sql`),需要把协议从纸面落地到代码

**触发场景**:
- 既有部署没有 `schema_version` 表 → Phase 65 启动时如何识别"需 migrate"
- `swl migrate` CLI 与 `_connect` 自动 migrate 的协调

**缓解**:
- design_decision §S3 已规定:`schema_version` 表 IF NOT EXISTS 创建;不存在 = 默认 version 0;版本 < EXPECTED_SCHEMA_VERSION 触发 migrate
- 开发模式默认自动 migrate;生产模式 placeholder(本 phase 不实装)
- `swl migrate --status` / `swl migrate` CLI 是 escape hatch,生产部署可手动控制

**回滚成本**:低。schema_version 表 IF NOT EXISTS 创建幂等

---

### R9 — Phase 61 留下的"事务回滚"Open 完整闭合验证(低)

**描述**:Phase 61 closeout 登记的 Open:"`apply_proposal` 4 步序列(save → apply → save → apply)缺事务保证,中途失败导致 in-memory 不一致"。Phase 65 是该 Open 的最终消化路径

**触发场景**:closeout 时 backlog 标 Resolved 但实装未充分验证

**缓解**:
- Phase 65 closeout 验证清单包含"模拟事务中途失败 → SQLite ROLLBACK + in-memory redo → 一致性验证"(R1 缓解的回归测试)
- 通过后 backlog Open 标 Resolved
- closeout 引用 R1 的回归测试用例作为闭合证据

**回滚成本**:零(文档对齐)

---

### R10 — §8 narrowing 不充分,Phase 66+ 引入 schema 升级时仍需补真正的 migration runner(低-中,**新增**)

**描述**:Phase 65 采纳 BLOCK-5 路径 (i):"首次建表不算 §8 migration"。此 narrowing 让 Phase 65 内不需要实装 migration runner,只需 `CREATE TABLE IF NOT EXISTS` + 直接 INSERT `schema_version=1`。但 Phase 66+ 真正出现 schema 升级时(改字段类型 / drop 列 / rename 等),仍需补完整 migration 协议:

- `swl migrate` CLI 实际 apply 多个 pending migration script 的能力
- `EXPECTED_SCHEMA_VERSION` 与当前 SQLite version 比对的入口
- `waiting_human` 状态接入(per §8 文字)
- migration script 失败回滚策略

**触发场景**:Phase 66+ 第一次真正 schema 升级时,Codex 发现 Phase 65 留下的 stub(`schema_version` 表 + `swl migrate --status`)不足以 apply v1 → v2 真实 migration,需要从头补 runner。

**缓解**:
- design_decision §S3 已显式声明:Phase 65 不引入 migration runner;`swl migrate` CLI 的 status 路径仅作 placeholder;真正 runner 留 Phase 66+
- closeout 登记 backlog Open:"migration runner 完整实装"
- 文档(DATA_MODEL §8)末尾 reference 一行明确"首次建表不属本节"边界,避免未来误解

**回滚成本**:零(Phase 65 内不引入即不需回滚)。Phase 66+ 时再考虑实装成本。

---

### R11 — §3.4 加 6 列后 bootstrap / SQLite UPSERT 漏填字段(低-中,**新增**)

**描述**:Phase 65 采纳 BLOCK-3 路径 (a):DATA_MODEL §3.4 加 6 列(`capabilities_json` / `taxonomy_json` / `execution_site` / `executor_family` / `executor_name` / `remote_capable`)承载完整 RouteSpec。**风险**:Codex 实装 bootstrap helper / `save_route_registry` SQL UPSERT 时漏填某个字段,导致 SQLite round-trip 后 RouteSpec 缺字段(P2 兑现性破坏 — SQLite 仍非完整 truth)。

**触发场景**:
- bootstrap helper 从 `routes.default.json` 读取后,只写部分列就 INSERT(漏 `taxonomy_json` 等)
- M2 `save_route_registry_via_sql` 漏写新列,SQL UPSERT 后旧列保留新列默认空 → reader 读到空 capabilities

**缓解**:
- kickoff §完成条件已增加:**完整 RouteSpec round-trip 测试**(per model_review acceptance criteria),含 6 列全字段
- 测试断言:从 `routes.default.json` 读 → bootstrap → SQLite SELECT → 反序列化为 RouteSpec → 与原 JSON 字段集严格相等(`assert RouteSpec.from_dict(loaded) == RouteSpec.from_dict(original)`)
- Codex 在 S1 / S2 PR body 中给出全字段对照表(JSON key vs SQLite 列名 vs RouteSpec 属性)
- design_decision §S1 修订决议中已给出 SQL DDL + 列扩展 + 空值约定的 authoritative 形态,Codex 不需自决

**回滚成本**:中。Phase 65 早期(M1 完成时)发现成本低;若 M2 commit 后才发现,需同时修 SQL UPSERT 与 round-trip 测试,但 schema_version 不变(列已建)。

---

## 总体策略

1. **S1 → S2 → S3 顺序实装**(无并行,无倒序):每个 milestone 独立 review + commit gate
2. **S2 是 Phase 65 唯一高风险 slice**,model_review Gate 推荐触发(若 Human 同意);Codex 在 S2 PR body 中提供:
   - 事务边界 + in-memory ROUTE_REGISTRY redo 路径的完整 pseudocode
   - 失败场景回归测试(monkeypatch 模拟 save 失败)
   - audit before/after snapshot 示例数据 + 字段完整性证明
   - `_apply_route_review_metadata` 事务边界声明(SQL 在事务内,artifact write 在事务外)
3. **DATA_MODEL.md 修改严格限定**在 §3.4 / §3.5 / §4.2 / §8 的"已定义未实装"补丁;不重写既有 DDL / 不修改既有字段语义;Codex 实装前 sanity check schema 与既有 RouteSpec 字段对应
4. **既有测试零迁移目标**:save_* / apply_* / load_* helper 接口签名不变;mock 模式 `patch("swallow.router.save_*", ...)` 继续有效;路径名 assertion 测试需迁移(R6)
5. **`.swl/*.json` 文件保留作为 backup**:Phase 65 不删 JSON 文件,migration 后内容不再被 writer 触动
6. **Phase 61 留下的"事务回滚"Open 闭合验证**:Phase 65 closeout 引用 S2 回归测试 + backlog 标 Resolved

## 与既有 risk 模式的对照

- **类似 Phase 63 R3(Repository 抽象层重塑)**:本 phase R1(事务边界)同样是 governance 层的核心结构改动;但 scope 更聚焦(事务边界 vs 抽象层 4 类),风险等级 7 vs 7
- **类似 Phase 64 R3(helper 抽取破循环)**:本 phase R3(migration 时序)是另一个"架构整理引发的时序问题",但 SQLite `BEGIN IMMEDIATE` 已经提供 mutex,风险更低
- **新模式**:Phase 65 是首次"实装层兑现已定义但未实装的 DATA_MODEL schema"动作(R2);后续若再有此类 phase,可复用本 phase 的 schema sanity check + DATA_MODEL.md 局部补丁模式

## 与 INVARIANTS 的对照(本 phase 强约束)

| INVARIANTS 条目 | Phase 65 落地方式 |
|----------------|----------------|
| **P2(SQLite-primary truth)** | route metadata + policy 迁入 SQLite,履行 P2 在治理状态上的代码层承诺 |
| §0 第 4 条(`apply_proposal` 唯一入口) | 通过事务包裹强化原子保证;Repository 写边界守卫保持 active |
| §4 LLM 调用契约 | Phase 64 已落地,本 phase 不动 |
| §9 不变量守卫 | `test_append_only_tables_reject_update_and_delete` 扩展含 6 张表;§9 17 条全 active 不变 |
| §0 第 1 条(Control)| Phase 64 已落地,本 phase 不动 |
| §5 Truth 写权限矩阵 | 不动 |
| §7 集中化函数 | 不动 |

## 与 DATA_MODEL.md 的对照

| DATA_MODEL 条目 | Phase 65 触动方式 |
|----------------|-----------------|
| §3.4 Route 命名空间 schema | 兑现实装(`route_registry` 表建);加"已实装(Phase 65)"标注;不动既有 DDL 字段 |
| §3.5 Policy 命名空间 schema | 兑现实装(`policy_records` 表建);加"已实装(Phase 65)"标注 |
| §4.1 单一写入入口 | 不动(Phase 63 已立) |
| §4.2 Append-only 表清单 | **从 4 张扩展到 6 张**(新增 `route_change_log` / `policy_change_log`) |
| §5 跨命名空间引用规则 | 不动 |
| §6 文件系统约束 | 不动(`.swl/*.json` 仍存在,只是 deprecated;路径 helper 保留) |
| §7 ID 与 Actor 约束 | 不动 |
| §8 Migration 与版本 | **协议落地**:`swallow/migrations/001_*.sql` 引入 + `schema_version` 表 + `swl migrate` CLI |
| §9 与其他文档接口 | 不动 |
