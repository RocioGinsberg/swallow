---
author: claude
phase: phase65
slice: kickoff
status: revised-after-model-review
depends_on: ["docs/plans/phase65/context_brief.md", "docs/plans/phase65/design_audit.md", "docs/plans/phase65/model_review.md", "docs/plans/phase64/closeout.md", "docs/plans/phase63/closeout.md", "docs/roadmap.md", "docs/design/INVARIANTS.md", "docs/design/DATA_MODEL.md", "docs/concerns_backlog.md"]
---

TL;DR(revised-after-model-review,2026-04-29): Phase 65 = roadmap 候选 H,**3 milestone**(M1 schema 兑现 + reader 切 SQLite + 一次性 **bootstrap import** / M2 writer 切 SQLite + `BEGIN IMMEDIATE` 事务包裹(`isolation_level=None` + `sqlite_store.get_connection`)+ 审计表写入 / M3 守卫扩展 + DATA_MODEL.md 同步)。把 route_metadata(`registry / weights / capability_profiles`)与 policy(`audit_trigger_policy / mps_policy`)从 `.swl/*.json` 迁入 SQLite,履行 INVARIANTS P2(SQLite-primary truth)在治理状态上的代码层承诺。新增 `route_change_log` / `policy_change_log` append-only 审计表(扩展 §9 守卫被测表清单)。Phase 64 三层外部化 JSON 作为 bootstrap source,首次启动一次性导入 SQLite(**不写 audit log**;不属于 §8 schema migration)。**触动 DATA_MODEL.md** §3.4(加 6 列承载完整 RouteSpec)/ §3.5 映射表 / §4.2 表清单扩展 / §8 末尾加一行 reference(**§8 既有文字不动**);**INVARIANTS.md 文字不动**。**M1 不可单独 release**:Phase 65 整体 release 必须包含 M1+M2+M3,否则 P2 未真兑现。

## 当前轮次

- track: `Governance`
- phase: `Phase 65`
- 主题: Truth Plane SQLite 一致性(候选 H)
- 入口: Direction Gate 已通过(2026-04-29 Human:Phase 64 merge 后选定 H)

## Phase 65 在 INVARIANTS / DATA_MODEL 框架中的位置

- **INVARIANTS P2(SQLite-primary truth)**:本 phase 是 P2 在治理 truth 面的最终兑现。Phase 63 已经在 `task / event / knowledge` 等命名空间落地 SQLite,Phase 65 把最后剩下的 `route metadata / policy` 也迁入,使 P2 在所有 truth 写入面成立
- **INVARIANTS §0 第 4 条(`apply_proposal` 唯一入口)**:Phase 63 已立,Phase 65 通过事务包裹强化"原子保证"
- **DATA_MODEL §3.4 / §3.5 已定义但未建表**:本 phase 兑现 schema(对齐文档与代码,**修改 DATA_MODEL.md 仅限于补"已实装"标注 / §4.2 表清单 4→6 / §8 migration 协议落地**;不修改既有 schema 字段定义)
- **DATA_MODEL §4.2 append-only 表清单**:本 phase 新增 `route_change_log` / `policy_change_log`,从 4 张扩展到 6 张
- **DATA_MODEL §8 migration 协议**:本 phase 落地 `swallow/migrations/<version>_<slug>.sql` 机制 + `schema_version` 检测(若当前未实装)

## 目标(Goals)

- **G1 — SQLite schema 兑现**
  - 在 `src/swallow/sqlite_store.py:_connect` 中按 DATA_MODEL §3.4 / §3.5 新建表:
    - `route_registry`(主表,RouteSpec metadata,UPSERT 写入)
    - `policy_records`(主表,policy 配置,UPSERT 写入)
  - 新建审计表(append-only,与 `know_change_log` 同款模式):
    - `route_change_log`(actor / target_kind / target_id / before_payload / after_payload / timestamp / proposal_id)
    - `policy_change_log`(同款字段)
  - `APPEND_ONLY_TABLES` 从 `("event_log", "event_telemetry", "route_health", "know_change_log")` 扩展到 6 张表
  - `APPEND_ONLY_TRIGGER_SQLS` 自动覆盖新增表(idempotent,`CREATE TRIGGER IF NOT EXISTS`)

- **G2 — Reader 切 SQLite**
  - `src/swallow/router.py` 中的 `load_route_registry / load_route_policy / load_route_weights / load_route_capability_profiles` 改从 SQLite 加载(SQL SELECT,反序列化为 in-memory dict / RouteSpec)
  - `apply_route_*` helper 不变(签名 + 调用顺序 + ROUTE_REGISTRY mutation 模式)
  - `route_fallbacks.json` 不动(operator-local config seam,Phase 64 决议;不迁 SQLite)
  - 第一次启动若 SQLite `route_registry` / `policy_records` 表为空且 `.swl/*.json` 存在,触发**一次性 migration**:从 JSON 加载 → 写入 SQLite → 标 JSON 文件 deprecated(留作 backup,不删)
  - **routes.default.json / route_policy.default.json**(Phase 64 引入的 immutable seed):保留作为 fallback;若 SQLite 与 .swl/*.json 都缺失,从 default seed 加载 → 写 SQLite

- **G3 — Writer 切 SQLite + 事务包裹**
  - `RouteRepo._apply_metadata_change`(truth/route.py)实装层切 SQLite UPSERT;最外层包 `BEGIN IMMEDIATE` ... `COMMIT`(异常自动 ROLLBACK)
  - `PolicyRepo._apply_policy_change`(truth/policy.py)同款
  - `save_route_*` 函数底层从 JSON 写改为 SQLite UPSERT;**接口签名不变**(测试 mock 透明)
  - 同事务内写入 `route_change_log` / `policy_change_log` 审计行(snapshot 形式记 before / after)

- **G4 — 审计写入位置决策**
  - **决议**(本 kickoff 锁定):审计写入在 `RouteRepo._apply_metadata_change` / `PolicyRepo._apply_policy_change` 内部的事务里,**不在** `governance._emit_event` 外层
  - **rationale**:Repository 层事务内写审计 = 数据变更与审计记录原子绑定,失败回滚一起;`_emit_event` 外层写会破坏审计原子性
  - `governance._emit_event` 桩函数继续保留作为 telemetry / observer 钩子(不写审计 log,留给后续 phase)

- **G5 — `test_append_only_tables_reject_update_and_delete` 守卫扩展**
  - 守卫被测表清单从 4 张扩展到 6 张(新增 `route_change_log` / `policy_change_log`)
  - INSERT fixture 数据按各表 schema 准备
  - 守卫保持 NO_SKIP active(Phase 63 已立)

- **G6 — Schema 首次建表 + `schema_version` 协议落地**(修订:不再叫 migration)
  - **首次建表(table creation)** 由 `sqlite_store.py:_connect` 内 `CREATE TABLE IF NOT EXISTS` 一次性维护;**不属于 DATA_MODEL §8 范围内的 migration**(§8 文字明确"不允许运行时静默执行",此条款仅适用真正的 schema_version 升级)
  - `schema_version` 表(若不存在则建)记录当前 schema 版本;Phase 65 fresh DB 初始化时直接 INSERT `version=1, slug='phase65_initial', applied_at=now()`
  - **`swl migrate` CLI**(M3 内引入)仅作 Phase 66+ 真正 schema 升级入口;Phase 65 内不会被触发(无 pending migration)
  - **`swl migrate --status`** 在 Phase 65 fresh DB 上输出 `schema_version: 1, pending: 0`
  - 既有 `.swl/*.json` 一次性 **bootstrap import** 到 SQLite(M1 内附带;**不属于 §8 migration**;不写 audit log;helper 命名 `_bootstrap_*_from_legacy_json`,与 `swl migrate` 概念区分);bootstrap 完成后 JSON 文件不删,仅 deprecated

- **G7 — DATA_MODEL.md 同步**(修订:§3.4 边界放宽至加 6 列;§8 文字不动)
  - §3.4 **加 6 列**(`capabilities_json` / `taxonomy_json` / `execution_site` / `executor_family` / `executor_name` / `remote_capable`)承载完整 RouteSpec round-trip;含 JSON 字段空值约定说明(空 list `'[]'` / 缺失 `'null'` / SQLite 用 TEXT NOT NULL 替代 JSON 类型);标"已实装(Phase 65)"
  - §3.4 既有列(`route_id` / `model_family` / 等)DDL 字段语义**不动**
  - §3.5 加 round-trip 映射表(audit_trigger_policy → kind='audit_trigger', scope='global', scope_value=NULL / mps_policy → kind='mps', scope='mps_kind', scope_value=mps_kind);标"已实装(Phase 65)";既有列不动
  - §4.2 append-only 表清单从 4 张扩展到 6 张(新增 `route_change_log` / `policy_change_log`)— 本 phase 内修改
  - §8 **既有文字不动**(per model_review BLOCK-5 路径 i);仅末尾加一行 reference:"`首次建表(table creation on fresh DB)` 不属于本节 migration 范围,由 `sqlite_store.py:_connect` 内 `CREATE TABLE IF NOT EXISTS` 一次性维护;`schema_version` 在首次建表后直接 INSERT v=1"
  - **§1 / §2 / §5 / §6 / §7 / §9 既有内容不重写** — 本 phase 仅做"已定义未实装 + 加列补齐 + 表清单扩展 + reference"补丁
  - **INVARIANTS.md 文字不动**

## 非目标(Non-Goals)

- **不修改 INVARIANTS.md 任何文字**(P2 已写,§4 / §9 已写)
- **不引入对象存储后端**(S3 / MinIO / OSS 适配是更后续 phase scope;本 phase 只把 SQLite 作为唯一 truth backend)
- **不重构 `_apply_route_review_metadata`**(governance.py:325-577,~250 行)的业务逻辑;本 phase 只把它最外层的 write 路径切到事务内
- **不修改 `route_fallbacks.json`** operator-local config seam(Phase 64 决议)
- **不动 Phase 63/64 已落地内容**:`identity.py` / `workspace.py` / Repository 抽象层骨架 / `_http_helpers.py` / route_registry/route_policy 三层外部化的 JSON 文件(它们成为 migration source 与 fallback seed,语义不变)
- **不引入 multi-actor / authn / authz**(INVARIANTS §8 永久非目标)
- **不动既有 `events`/`event_log` 双写问题**(Phase 63 review M3-1 backlog,继续 deferred)
- **不引入 metrics 集中 / cost_estimation 集中**(后续方向)

## 设计边界

- 严格遵循 INVARIANTS P2 + §0 第 4 条 + §4 / §9
- Repository 抽象层作为 SQL 切换载体,Phase 63 已建立的接口契约不变(public read methods 不动,private write methods 内部实装切 SQLite)
- 事务边界:`RouteRepo._apply_metadata_change` 内部一次 `BEGIN IMMEDIATE`...`COMMIT`,涵盖所有 payload 类型(registry / policy / weights / capability_profiles)
- 审计写入:Repository 层事务内,绑定数据变更原子性
- 加载顺序:Phase 64 的 5 处入口 + 5 个 apply helper 顺序不变,只改 reader 实装

## 完成条件

**Phase 65 整体 release 必须包含 M1 + M2 + M3 全部 milestone**(per model_review CONCERN-5):
- M1 单独 commit/PR 不允许进入 main(M1 期间 writer 写 JSON / reader 读 SQLite 快照,声称兑现 P2 但实际有数据丢失风险)
- Codex M1 commit 后必须直接接 M2 实装;Human Gate 不会 review M1 单独分支为 ready-to-merge

**测试与功能验收**:
- 全量 pytest 通过(包含 §9 17 条守卫;`test_append_only_tables_reject_update_and_delete` 覆盖 6 张表)
- `tests/test_invariant_guards.py:test_append_only_tables_reject_update_and_delete` 测试 6 张表(包括 `route_change_log` / `policy_change_log`)
- `swl route registry apply <file>` / `swl route policy apply <file>` 写入 SQLite,中途失败 ROLLBACK 验证(integration test)
- `apply_proposal(..., ROUTE_METADATA)` 内部跑事务,任意 save 步骤失败,SQLite 与 in-memory ROUTE_REGISTRY 都不发生局部更新(回归测试)
- **失败注入测试矩阵**(per model_review CONCERN-2,详见 design_decision §S2):8 个 route 注入点 + 4 个 policy 注入点全覆盖
- **完整 RouteSpec round-trip 测试**:含 `capabilities` / `taxonomy` / `execution_site` / `executor_family` / `executor_name` / `remote_capable` / weights / capability_profiles 全字段(per model_review acceptance criteria)
- **完整 policy round-trip 测试**:`audit_trigger_policy` + `mps_policy` 双 kind(per model_review acceptance criteria)
- **Reader 优先级测试**:SQLite > .swl/*.json > *.default.json 三级 fallback 链
- `route_registry` / `policy_records` 两张主表存在于 SQLite schema(`route_registry` 含 §3.4 加 6 列)
- `route_change_log` / `policy_change_log` 两张审计表存在,append-only trigger 启用
- `schema_version` 表存在,Phase 65 fresh DB 初始化时直接 INSERT `version=1, slug='phase65_initial'`
- `swl migrate --status` 输出 `schema version: 1, pending: 0`(无 pending — Phase 65 是首次建表,不算 §8 migration)
- 既有 `.swl/route_weights.json` / `.swl/route_capabilities.json` / `.swl/routes.json` / `.swl/route_policy.json` / `.swl/audit_trigger_policy.json` / `.swl/mps_policy.json` 在首次启动时一次性 **bootstrap import**(命名:`_bootstrap_*_from_legacy_json`)到 SQLite(JSON 文件保留作为 backup,不删;**bootstrap 不写 audit log**,audit history 从 M2 起算)

**文档对齐**:
- `git diff docs/design/INVARIANTS.md` 无任何改动
- `git diff docs/design/DATA_MODEL.md` 仅含 §3.4 加 6 列(capabilities_json / taxonomy_json / execution_site / executor_family / executor_name / remote_capable)+ §3.5 round-trip 映射表 + §4.2 append-only 表清单 4→6 + §8 末尾 reference 一行;**§8 既有文字不变**;§3.4 / §3.5 既有 DDL 字段不动
- `docs/plans/phase65/closeout.md` 完成 + `docs/concerns_backlog.md` 关于 Phase 61 留下的"事务回滚"Open 标 Resolved
- `git diff --check` 通过

## Slice 拆解(详细见 `design_decision.md`)

| Slice | 主题 | Milestone | 风险评级 |
|-------|------|-----------|---------|
| S1 | Schema 兑现 + reader 切 SQLite + 一次性 migration | M1 | 中(5)|
| S2 | Writer 切 SQLite + `BEGIN IMMEDIATE` 事务包裹 + 审计表写入 | M2 | 中-高(7)|
| S3 | §9 守卫扩展 + migration 协议落地 + DATA_MODEL.md 同步 | M3 | 中(5)|

Milestone 分组:
- **M1**(单独 review):S1 — schema + reader + 一次性 migration。**不切 writer**(继续 JSON 写),保证基线安全;一次性 migration 跑完后 SQLite 与 JSON 双写一段时间(read 优先 SQLite,write 仍 JSON)
- **M2**(单独 review):S2 — writer 切 SQLite + 事务 + 审计写入。**事务包裹是高风险点**(事务边界设计错误会导致 multi-payload 部分失败的非原子状态)
- **M3**(单独 review):S3 — 守卫扩展 + migration 工具 + DATA_MODEL.md 同步

**slice 数量 3 个**,符合"≤5 slice"指引;**1 个高风险 slice**(S2),其他 2 个中风险

## Eval 验收

不适用。Phase 65 全部为 schema 迁移 + 事务边界 + 审计 / 守卫,无降噪 / 提案有效性 / 端到端体验质量梯度;pytest(含扩展后的 §9 守卫 + 事务回滚回归测试)即足以验收。

## 风险概述(详细见 `risk_assessment.md`)

- **S2 事务边界设计**(高风险):`_apply_route_review_metadata` 250 行业务逻辑跨多个 save 调用,事务包裹的起止点设计错误会导致部分 commit / 全 rollback 不一致 — 缓解:事务在 `_apply_metadata_change` 内部最外层包,业务逻辑不动
- **DATA_MODEL §3.4 / §3.5 schema 与实装可能存在隐性不对齐**(中风险):文档先于代码 ~2 phase,字段名 / 类型可能在 Phase 65 实装时发现不可行 — 缓解:实装前先 sanity check schema,若需调整先改 DATA_MODEL.md
- **既有 `.swl/*.json` migration 时序**(中风险):一次性 migration 必须在 reader 第一次访问 SQLite 之前完成,否则空 SQLite 表会被 reader 当作"无配置"处理,覆盖既有 JSON 配置 — 缓解:migration 在 schema 创建后立即执行,reader 入口处加 idempotent migration check
- **测试 fixture 兼容**(低-中风险):`tests/test_router.py:242, 265` 等测试用 `tmp_path.write_text(...)` 写 JSON 路径名 assertion;Phase 65 后路径不再是 truth 写路径,需改 fixture
- **`_BUILTIN_ROUTE_FALLBACKS` import-time 快照与 SQLite 时序**(低风险):import-time `routes.default.json` 构建,首次 `apply_route_registry(base_dir)` 后从 SQLite 刷新;若 SQLite 中 registry 与 default 差异大,需要确认刷新顺序
- **Phase 61 留下的 Open 完整闭合**(低风险):本 phase 闭合"`apply_proposal` 事务回滚缺失"Open;closeout 时 backlog 标 Resolved

## Model Review Gate(已闭环)

- 状态:`completed`
- Reviewer:external GPT-5(`mcp__gpt5__chat-with-gpt5_5`)
- Verdict:**BLOCK**(5 BLOCK + 9 CONCERN + 3 PASS)
- 产出物:`docs/plans/phase65/model_review.md`
- 已消化:Human 在 2026-04-29 决策两条关键路径
  - BLOCK-5 §8 矛盾 → 路径 (i) Phase 65 收紧:首次建表不算 §8 migration;§8 文字不动
  - BLOCK-3 §3.4 字段缺口 → 路径 (a) 加 6 个独立列承载完整 RouteSpec
- 三件套已修订至 `revised-after-model-review`:本 kickoff + design_decision + risk_assessment
- 不再触发二次 model_review:5 BLOCK 均为 design 文字明确性,internal 一致性由 Claude 自查 + Human Gate 把关

## Branch Advice

- 当前分支:`main`(Phase 64 已 merge)
- 建议 branch 名:`feat/phase65-truth-plane-sqlite`
- 建议操作:Human Design Gate 通过后 Human 切出该 branch,Codex 在该分支上实装 S1 → S2 → S3

## 完成后的下一步

- Phase 65 closeout 后,触发 `roadmap-updater` subagent 同步 §三 "Truth Plane SQLite 一致性"行标 [已消化];§四候选 H 块 strikethrough;§五 推荐顺序 G ✓ → G.5 ✓ → H ✓ → D
- **Tag 决策**(Direction Gate 已锁定):Phase 65 merge 后以 governance 三段(G + G.5 + H)整体闭合为主题打 `v1.4.0` minor bump
- 后续阶段:候选 D(Planner / DAG / Strategy Router)或候选 R(真实使用反馈观察期),Human 在新 Direction Gate 决定

## 不做的事(详见 non-goals)

- 不修改 INVARIANTS.md
- 不重构 `_apply_route_review_metadata` 业务逻辑
- 不引入对象存储后端
- 不动 `route_fallbacks.json` operator-local seam
- 不动 Phase 63/64 已落地内容
- 不动 `events` / `event_log` 双写问题
- 不引入 metrics / authn / multi-actor

## 验收条件(全 phase)

详见上方 §完成条件。本 kickoff 与 design_decision 一致,无补充。
