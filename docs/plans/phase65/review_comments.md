---
author: claude
phase: phase65
slice: pr-review
status: review
depends_on:
  - docs/plans/phase65/kickoff.md
  - docs/plans/phase65/design_decision.md
  - docs/plans/phase65/risk_assessment.md
  - docs/plans/phase65/design_audit.md
  - docs/plans/phase65/model_review.md
  - docs/plans/phase65/consistency_report.md
  - docs/plans/phase65/commit_summary.md
  - docs/design/INVARIANTS.md
  - docs/design/DATA_MODEL.md
verdict: APPROVE_WITH_CONDITIONS
---

TL;DR: 实装质量高,**5 BLOCK 全部 consistent**(transaction ownership / connection accessor / §3.4 加 6 列 / policy 映射 / §8 narrowing 全对齐 design)。但合并前需消化 **1 BLOCK + 2 CONCERN**:(B-1) `_write_json(application_path, ...)` 在 SQL COMMIT 之后无 try/except,异常会传播导致 caller 拿到错误状态(违反 design_decision §S2 CONCERN-3 "log warning only / at-least-once" 文字);(C-1) 失败注入测试矩阵只覆盖 12 个 case 中的 2 个;(C-2) 非 trivial round-trip 测试规格不达标(单 route × 2 score,设计要求 ≥3 routes × 5+ scores)。另有 1 NOTE(DATA_MODEL §8 schema_version DDL `slug TEXT` 缺 `NOT NULL`,与代码不同步)。Verdict = **APPROVE_WITH_CONDITIONS**:B-1 必修才 merge;C-1/C-2 可登记 closeout backlog 后 merge,但建议补齐再 merge。

## 审查范围

- branch:`feat/phase65-truth-plane-sqlite`(对比 `main`)
- commits:`1b934c4`(phase 文档初始化)+ `77991d3`(实装,13 文件 +1296/-129)+ `1f258a7`(DATA_MODEL 同步)+ `6cc16ee`(state)
- 已先行产出:`docs/plans/phase65/consistency_report.md`(verdict = `concerns`)
- 验证基线(commit_summary 报告):`pytest -q` → 597 passed / 8 deselected / 10 subtests;`audit_no_skip_drift.py` 全 8 守卫绿;`git diff --check` pass;`INVARIANTS.md` diff 空

## Verdict

**APPROVE_WITH_CONDITIONS** — BLOCK-1 必修才 merge;CONCERN-1 / CONCERN-2 强烈建议补齐,否则 closeout 显式登记为 known gap。

按 .agents 工作流分级:
- 0 BLOCK-DESIGN(无设计漂移,5 BLOCK 全消化)
- **1 BLOCK-CODE**(artifact write 异常处理缺失)
- **2 CONCERN**(测试覆盖不达标:注入矩阵 + 非 trivial round-trip)
- 1 NOTE(DATA_MODEL §8 文档与代码细微不同步)

## Findings

### [BLOCK-1] `_write_json(application_path, ...)` 缺 try/except,违反 CONCERN-3 at-least-once 语义

- **位置**:`src/swallow/governance.py:577-578`
- **设计文档**:`docs/plans/phase65/design_decision.md` §S2 CONCERN-3 显式声明:
  > "review record artifact 是 audit-adjacent 派生物 [...] 它的失败语义是 at-least-once:SQL commit 成功后才写 artifact;artifact 写失败仅 log warning,不影响 SQL truth(Phase 65 已知限制,不修复;closeout 登记 backlog Open)"
- **当前实装**:
  ```python
  application_path = optimization_proposal_application_path(proposal.base_dir, application_record.application_id)
  _write_json(application_path, application_record.to_dict())  # ← 无 try/except
  return ApplyResult(...)
  ```
- **问题**:
  1. SQL transaction 已 COMMIT(`RouteRepo()._apply_metadata_change` 已返回),SQLite truth 写入完成,审计行已落表
  2. 此时若 `_write_json` 抛异常(磁盘满 / 权限错误 / I/O race),异常向上传播给 `apply_proposal` 的 caller
  3. caller(CLI / orchestrator)看到 `apply_proposal` 抛错,在语义上会以为"governance 写入失败" — 但实际上 SQLite truth 已经 commit 且不可回滚
  4. 这违反 design 文字承诺:artifact 失败应仅 log warning,不影响 SQL truth 的对外可见性
- **修复**:
  ```python
  application_path = optimization_proposal_application_path(proposal.base_dir, application_record.application_id)
  try:
      _write_json(application_path, application_record.to_dict())
  except OSError as exc:
      logger.warning(
          "review record artifact write failed; SQLite truth already committed",
          extra={"application_id": application_record.application_id, "path": str(application_path), "error": repr(exc)},
      )
  ```
  + 在 `closeout.md` 登记 backlog Open:"`_apply_route_review_metadata` 的 review record artifact write 在事务外,失败仅 log warning;后续 phase 可考虑 outbox / 标 stale 等更强语义"
- **PR body 同步**:design 还要求"PR body 含 `grep application_path` 验证说明"。当前 `commit_summary.md` 未含此验证记录。Codex 在 closeout / PR body 中需补一段:
  > "grep `application_path` 与 `optimization_proposal_application_path` 的 read 调用 — 仅 governance 写入侧使用 + report 生成侧 read,无 reader 把 artifact 当作 truth 决策输入"
- **严重度**:BLOCK(merge 前必修,改动小,~5 行 + 一行 import + 一段 PR body 文字)

### [CONCERN-1] 失败注入测试矩阵 — 12 个要求 case 中只实装 2 个

- **位置**:`tests/test_phase65_sqlite_truth.py:129-189`
- **设计文档**:`design_decision.md` §S2 CONCERN-2 表列出 12 个独立 test case(route 8 注入点 + policy 4 注入点),每个独立 test
- **当前实装**:
  - route 路径:1 个 case(`test_route_metadata_transaction_rolls_back_sqlite_audit_and_in_memory`)— 覆盖注入点 5(save_route_capability_profiles 后)+ 注入点 6(in-memory mutation 后,因 rollback redo 包含 in-memory 恢复)
  - policy 路径:1 个 case(`test_policy_transaction_rolls_back_policy_record_and_audit`)— 覆盖注入点 4(`_write_policy_change_log` 失败 ≈ audit INSERT 后 commit 前)
- **缺口**(10 个 case):
  - route 注入点 1(第一次 SQL UPSERT 前)
  - route 注入点 2(route_registry UPSERT 后)
  - route 注入点 3(route_policy UPSERT 后)
  - route 注入点 4(route_weights UPSERT 后)
  - route 注入点 7(audit INSERT 后 commit 前)
  - route 注入点 8(commit 成功后 caller 异常 — 验证非 ROLLBACK 场景)
  - policy 注入点 1(audit_trigger_policy UPSERT)
  - policy 注入点 2(mps_policy UPSERT)
  - policy 注入点 3(in-memory mutation 后)
- **风险**:R1(高,事务边界)主要靠这个矩阵兜底。当前覆盖只验了"capability_profiles 失败 → ROLLBACK + redo" 与 "policy audit 失败 → ROLLBACK",其他 8 个失败窗口缺验证。事务实装实质上依赖 `BEGIN IMMEDIATE` 标准行为,逻辑上正确;但 design 文字明确要求矩阵覆盖。
- **修复路径(二选一)**:
  - (a) **推荐**:补齐 10 个 monkeypatch 注入 case 进 `test_phase65_sqlite_truth.py`(每个 ~10 行 boilerplate,大致 ~100 行新代码 + 共享 fixture),再 commit
  - (b) `closeout.md` 登记 known gap:"失败注入测试矩阵覆盖 2/12;事务边界正确性靠 SQLite `BEGIN IMMEDIATE` 标准行为 + 已有 ROLLBACK redo 测试兜底;补齐工作进 backlog"
- **严重度**:CONCERN(merge 不阻塞,但显式承诺设计 → 实装不达标,建议合并前补齐)

### [CONCERN-2] 非 trivial round-trip 测试规格不达标

- **位置**:`tests/test_phase65_sqlite_truth.py:96-107`(`test_route_registry_round_trips_full_route_spec_through_sqlite`)
- **设计文档**:`design_decision.md` §S2 CONCERN-7:
  > "S2 PR 必须含 non-trivial round-trip 测试:fixture 包含 ≥3 routes × 5+ task_family_scores entries 的 capability_profiles,验证 audit 行 JSON 完整可反序列化"
- **当前实装**:测试用单个 route(`local-codex`)+ 2 个 task_family_scores(`review: 0.91, execution: 0.44`)
- **未验证**:超大 payload(>1MB)导致 SQLite 写失败 → 该次 proposal apply 整体 ROLLBACK 的 intentional behavior(R5 / risk_assessment 已声明,但无测试)
- **风险**:R5 / R11(audit snapshot 大小、`§3.4 加 6 列后 bootstrap / SQLite UPSERT 漏填字段`)— 当前 round-trip 字段覆盖到位(capabilities + taxonomy + executor_* + remote_capable),但**规模**没达标。
- **修复路径(二选一)**:
  - (a) **推荐**:加一个 `test_route_registry_round_trip_with_non_trivial_capability_profiles` — 3 routes × 5 task_family_scores,验证 audit before/after JSON 完整反序列化;~30 行
  - (b) closeout 登记 known gap
- **严重度**:CONCERN

### [NOTE-1] DATA_MODEL §8 `schema_version` DDL `slug TEXT` 缺 `NOT NULL`

- **位置**:`docs/design/DATA_MODEL.md:392`
- **代码 + design_decision**:`sqlite_store.py:206-210` 与 `design_decision.md` §S3 关键设计决策段都写 `slug TEXT NOT NULL`
- **DATA_MODEL.md**:
  ```sql
  CREATE TABLE schema_version (
      version          INTEGER NOT NULL,
      applied_at       TEXT NOT NULL,
      slug             TEXT          -- 缺 NOT NULL
  );
  ```
- **影响**:文档参考价值打折(下一次 phase 若有人按 DATA_MODEL §8 的 DDL 复刻 schema 会落差);**不影响实装正确性**(代码 + design_decision 一致)
- **修复**:在 §8 的 `slug TEXT` 后加 `NOT NULL`(一字之差);可与 closeout 一并提交,不阻塞 merge
- **严重度**:NOTE

## 已确认 PASS 项(摘要)

来自 consistency report,我手工核验关键代码后确认全部成立,不再展开:

- ✅ BLOCK-1 SQLite isolation_level=None + 显式事务管理(`sqlite_store.py:328` + `truth/route.py:37,67,70` + `truth/policy.py:31-69`)
- ✅ BLOCK-2 module-level `get_connection(base_dir)`(`sqlite_store.py:312`)+ router/truth 全用此 accessor,不直连 `_connect`
- ✅ BLOCK-3 §3.4 加 6 列 DDL(`sqlite_store.py:157-163`)+ DATA_MODEL §3.4 同步含全 6 列 + 空值约定
- ✅ BLOCK-4 policy 映射 — audit_trigger 用 `kind='audit_trigger', scope='global'`(`consistency_audit.py:239-258`);mps 用 `kind='mps', scope='mps_kind', scope_value=<mps_kind>`(`mps_policy_store.py:112-133`);反序列化失败回退 default 不抛异常
- ✅ BLOCK-5 §8 narrowing — 无 `migrations/` 目录(选项 A 落地);`schema_version` 在首次建表后 `INSERT OR IGNORE VALUES (1, ..., 'phase65_initial')`;`swl migrate --status` 输出 `schema_version: 1, pending: 0`;§8 既有三条规则文字保持不变,仅末尾加一行 reference
- ✅ CONCERN-4 命名分离 — 仅 `_bootstrap_*_from_legacy_json`,无 `_migrate_route_metadata` / `_migrate_policy`
- ✅ CONCERN-5 M1 不可单独 release — 单 feature commit `77991d3` 含 M1+M2+M3 完整内容
- ✅ CONCERN-6 bootstrap 不写 audit log — 4 个 bootstrap helper 均无 `route_change_log` / `policy_change_log` INSERT
- ✅ DATA_MODEL §3.4 / §3.5 / §4.2 修改边界 + INVARIANTS.md 零修改(`git diff INVARIANTS.md` 输出为空)
- ✅ append-only 守卫 6 张表覆盖 + `set(APPEND_ONLY_TABLES) == set(insert_sql)` 断言
- ✅ scope 控制 — 无越界:`route_fallbacks.json` 未触动;`_apply_route_review_metadata` 仅加 `proposal_id` 透传,业务逻辑未重构;`apply_atomic_text_updates` 已被 SQLite UPSERT 替代,符合 P2

## 已知 backlog(closeout 时显式登记)

无论 BLOCK-1 / CONCERN-1 / CONCERN-2 是否补齐再 merge,以下 known gap 需在 closeout 登记 Open(per design 文字声明,不阻塞 merge):

1. **review record artifact 写在事务外的语义弱保证**(design CONCERN-3 / R4 / risk_assessment R10 引申):artifact 失败仅 log warning;不引入 outbox / mark-stale 等更强语义。后续 phase 可重新评估。
2. **audit snapshot 无大小上限**(design CONCERN-7 / R5):超大 payload(>1MB)导致 SQLite 写失败 → 整体 ROLLBACK 是 intentional;无 size cap 与无 truncation policy。
3. **migration runner 完整实装推迟到 Phase 66+**(design BLOCK-5 narrowing 决议 / R10):Phase 65 内 schema 仅靠 `CREATE TABLE IF NOT EXISTS` 维护;`schema_version` 与 `swl migrate --status` 是 placeholder;真正 v1 → v2 升级路径留 Phase 66+ 启用。
4. **events / event_log 双写**(Phase 63 review M3-1 backlog):本 phase 不动,继续 deferred。
5. **Phase 61 留下的"事务回滚"Open 闭合**(R9):由本 phase 的 `BEGIN IMMEDIATE` 实装 + 已有 2 个失败注入测试 + 待补 10 个矩阵 case 综合闭合;closeout 标 Resolved。

## Branch / Merge 建议

- 当前 branch:`feat/phase65-truth-plane-sqlite`
- merge 前 must-fix:
  - [ ] BLOCK-1:`governance.py:577-578` 加 try/except + log warning;补 import logger;PR body 加 `application_path` 验证段
- merge 前 should-fix(强烈建议):
  - [ ] CONCERN-1:补齐 10 个失败注入 case(或 closeout 显式标 known gap)
  - [ ] CONCERN-2:补一个 ≥3 routes × 5+ scores 的 round-trip case(或 closeout 显式标 known gap)
- merge 前 nice-to-fix(NOTE 级):
  - [ ] NOTE-1:DATA_MODEL §8 `slug TEXT` → `slug TEXT NOT NULL`(一字补齐)
- 修复后(或登记 known gap 后)Codex 应 update closeout.md + 把 review_comments 标 Resolved 后再请求 Human 进 Merge Gate。

## Tag / Release

- Phase 65 = roadmap 候选 H = 治理三段(G + G.5 + H)最后一段
- merge 后 = `v1.4.0` minor bump 时机(per Direction Gate 2026-04-29 决议),由 Human 在 merge 后单独决定打 tag。
- 无需在 review 阶段做 tag 决策。

## 给 Codex 的 follow-up 清单

1. `governance.py:577-578` 加 try/except + log warning(BLOCK-1)
2. PR body / commit_summary 加 `application_path` 验证段(BLOCK-1 文档要求)
3. (强烈建议)`tests/test_phase65_sqlite_truth.py` 补齐 10 个失败注入 case + 1 个非 trivial round-trip case(CONCERN-1 / CONCERN-2)
4. `docs/design/DATA_MODEL.md:392` `slug TEXT` → `slug TEXT NOT NULL`(NOTE-1)
5. `docs/plans/phase65/closeout.md` 起草:登记上述 5 项 known backlog;Phase 61 "事务回滚"Open 标 Resolved;§完成条件验收逐项打勾(M1+M2+M3 / 测试 / DATA_MODEL diff 边界 / INVARIANTS 零改动 等)
6. `docs/concerns_backlog.md` 同步:Phase 65 新登记 backlog 行;Phase 61 "事务回滚"Open 标 Resolved
