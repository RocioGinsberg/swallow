---
author: claude
phase: phase66
slice: kickoff
status: revised-after-design-audit
depends_on:
  - docs/plans/phase66/context_brief.md
  - docs/plans/phase66/design_audit.md
  - docs/plans/phase65/closeout.md
  - docs/plans/phase64/closeout.md
  - docs/roadmap.md
  - docs/concerns_backlog.md
  - docs/design/INVARIANTS.md
  - docs/design/DATA_MODEL.md
---

TL;DR(revised-after-design-audit,2026-04-30):Phase 66 = roadmap 候选 K = **代码卫生 read-only audit phase**。Codex 按 5 块扫 src/swallow/ 全部 75 个 .py 文件(含 5 个 `__init__.py`)/ ~30994 LOC,产出 6 份文件(5 子 audit report + 1 index;单块 report > 800 行需分 part)。**严格 read-only**:不动任何代码 / 测试 / 文档(audit report 与 backlog 自身除外);typo / 1-行 dead import 也不顺手修。**4 类 finding**(dead code / 硬编码字面量 / 重复 helper / 抽象机会),dead code 用两轮 grep(src/ 先,tests/ 后);重复 helper 阈值 ≥ 9 行(原 10 行,1 行容差);分类口径见 design_decision §S1。**跳过清单 16 项**:concerns_backlog.md Open 13 项 + Phase 65 known gap 3 项(Phase 64 M2-2 已在 13 项内,不双计)。**INVARIANTS / DATA_MODEL 文字不动**;不引入新工具(vulture / pyflakes 等)。预期 finding 总量级 40-80;Claude review 分块分轮(M1 → review_comments_block1_3.md → M2 → review_comments_block4_5.md → M3 → review_comments_block2_index.md)。

## 当前轮次

- track: `Refactor / Hygiene`
- phase: `Phase 66`
- 主题: 代码卫生 audit(候选 K)
- 入口: Direction Gate 已通过(2026-04-30 Human 选定 K;Phase 65 已 merge + v1.4.0 已 tag)

## Phase 66 在 INVARIANTS / DATA_MODEL 框架中的位置

- **不触动 INVARIANTS.md**(本 phase 不评判宪法合理性,read-only audit 只盘点"该清的没清")
- **不触动 DATA_MODEL.md**(不评判物理存储设计)
- **不引入 §9 守卫新条目**(不写测试)
- 输出 finding 进 `docs/concerns_backlog.md` 后,**后续清理 phase**(Phase 67+)按重要性排队修;Phase 66 自身只盘点

## 目标(Goals)

- **G1 — 5 块覆盖完整 audit**
  - 块 1 — Truth & Governance(2671 LOC):governance.py / truth/*.py / sqlite_store.py / store.py / __init__.py
  - 块 2 — Orchestration(≈12168 LOC):orchestrator.py / executor.py / synthesis.py / dispatch_policy.py / checkpoint_snapshot.py / execution_fit.py / task_semantics.py / harness.py / subtask_orchestrator.py / planner.py / execution_budget_policy.py / retry_policy.py / stop_policy.py / review_gate.py / validator.py / validator_agent.py / models.py / runtime_config.py / compatibility.py
  - 块 3 — Provider Router & Calls(1740 LOC):router.py / agent_llm.py / _http_helpers.py / cost_estimation.py / capability_enforcement.py
  - 块 4 — Knowledge & Retrieval(≈5827 LOC):retrieval.py / retrieval_config.py / knowledge_objects.py / knowledge_partition.py / knowledge_policy.py / knowledge_review.py / knowledge_store.py / staged_knowledge.py / ingestion/*.py / dialect_adapters/*.py / dialect_data.py / canonical_*.py / knowledge_index.py / knowledge_relations.py / knowledge_suggestions.py / grounding.py / retrieval_adapters.py
  - 块 5 — Surface & Tools(≈8588 LOC):cli.py / paths.py / identity.py / workspace.py / web/*.py / meta_optimizer.py / consistency_audit.py / mps_policy_store.py / doctor.py / consistency_reviewer.py / capabilities.py / librarian_executor.py / ingestion_specialist.py / literature_specialist.py / quality_reviewer.py
  - 75 个 .py 文件**全部归入某一块**(含 5 个 `__init__.py`:`__init__.py` 归块 1 / `truth/__init__.py` 归块 1 / `web/__init__.py` 归块 5 / `ingestion/__init__.py` 归块 4 / `dialect_adapters/__init__.py` 归块 4)

- **G2 — 4 类 finding,统一判定口径**(authoritative,Codex 严格按此口径,详见 design_decision §S1):
  - **dead code**:src/ + tests/ 合并 grep callsite = 0(`@deprecated` 但仍被调用不算 dead;仅注释/docstring 命中不算 callsite;__init__.py 公开导出不算 dead)
  - **硬编码字面量**:跨 ≥3 处相同 magic string;OR 任意处 URL / model name / dialect name / provider name / route name(单次出现也算);OR 任意处 magic number 未命名为常量
  - **重复 helper**:跨 ≥2 文件 ≥10 行高度相似逻辑(差异仅变量名/类型注解/格式)
  - **抽象机会**:N≥3 处相似 if-elif / switch / dataclass init 结构 — **标记不抽**

- **G3 — 6 份产出文件**:
  - `docs/plans/phase66/audit_block1_truth_governance.md`
  - `docs/plans/phase66/audit_block2_orchestration.md`
  - `docs/plans/phase66/audit_block3_provider_router.md`
  - `docs/plans/phase66/audit_block4_knowledge_retrieval.md`
  - `docs/plans/phase66/audit_block5_surface_tools.md`
  - `docs/plans/phase66/audit_index.md`(汇总各块 finding 计数 + 严重程度分布)
  - 每个子 report 同一 frontmatter 模板(详见 design_decision §S2)

- **G4 — 跳过清单 16 项(已记录 backlog 不重复盘点,修订自 design_audit CONCERN-2)**:
  - `concerns_backlog.md` Open 13 项(详见 design_decision §S1 完整列表):Phase 45/49/50/57/58/59/61/63 M2-1/M2-5/M3-1/64 M2-2(Phase 64 M2-2 已在 13 项内,不双计)
  - Phase 65 closeout 3 项 known gap(review artifact 在 SQLite commit 后写 / audit snapshot 无 size cap / 完整 migration runner deferred)
  - 总计 16 项;audit 中若发现这些条目,**显式标注"已在 backlog 登记 (origin: <phase>)"并不计 finding 数**

- **G5 — finding 严重程度三级**:
  - `[high]`:影响 INVARIANTS / DATA_MODEL 一致性 / 可读性显著下降 / 跨块影响清理
  - `[med]`:可读性问题 / 单文件内重复 / 应外部化但低风险
  - `[low]`:typo / cosmetic / 注释错误 / 1-行 dead import
  - 严重程度由 Codex 给初判,Claude review 时核可

- **G6 — `audit_index.md` 汇总**:每块 finding 计数 × 4 类 × 3 严重级 矩阵 + 跨块共识 finding(同一类问题在多块出现)+ Codex 推荐"立刻可入下一清理 phase"的 quick-win 清单 vs "需要 design 决策"的清单

## 非目标(Non-Goals)

- **不修复任何代码 / 测试 / 文档**(typo、unused import、注释错误、cosmetic 重命名 — 一律不顺手修;归类入 backlog)
- **不修改 INVARIANTS.md / DATA_MODEL.md / SELF_EVOLUTION.md**(audit 不评判宪法 / 物理存储 / 自演化设计)
- **不评判"架构是否合理"**(那是 design phase 的活;audit 只盘点"该清的没清")
- **不引入新工具**(vulture / pyflakes / radon / mypy strict / ruff 新 rule 等 — 由后续清理 phase 在 design_decision 阶段决定;Phase 66 只用 grep + manual reading)
- **不审 tests/ 目录**(测试代码债逻辑自带 review 把关 + Phase 65 刚扩 21 个测,信号不干净)
- **不引入新 §9 守卫**(audit 不写测试)
- **不重新发现 concerns_backlog.md Open 项**(列入跳过清单)
- **不替 Codex 决定后续清理 phase 的拆分**(Phase 66 只产 finding + 严重度 + 推荐;具体拆 phase 67/68/... 由 Human 在新 Direction Gate 决定)
- **不引入 multi-actor / authn / multi-host 改动建议**(永久非目标)

## 设计边界

- read-only 严格性:Phase 66 commit 只含 `docs/plans/phase66/*.md` 与可能的 `docs/concerns_backlog.md` 增量(closeout 阶段);**`git diff src/ tests/ docs/design/` 必须为空**
- 5 块拆分锁定:Codex 按上面块边界扫,不擅自重新分块;若发现某文件不属于任何块(75 个 .py 应已全覆盖,但 audit 时若发现新文件)进 closeout 报告
- finding 数量预算:每块 finding 数 > 30 必须附说明(口径过松?);单块 finding 数 = 0 必须附说明(文件真干净 OR 漏扫?)
- audit 顺序建议(Codex 自决,但推荐顺序):块 1(LOC 小 + Phase 65 新代码 + 信号最干净 → 先暖手) → 块 3(LOC 小 + Phase 64 已清一波 → 短) → 块 5(LOC 大 + cli.py 高密度 dead subcommand → 中等耗时) → 块 4(多代际沉淀 → 长) → 块 2(LOC 最大 + orchestrator/harness 双路径 → 最长)
- review 分轮:Claude 不一次性 review 全部 6 份;按"高优块先审 → 低优块后审"分轮(详见 design_decision §S3)

## Slice 拆解(详细见 `design_decision.md`)

| Slice | 主题 | Milestone | 风险评级 |
|-------|------|-----------|---------|
| S1 | 块 1 + 块 3 audit(短文件 + 信号干净) | M1 | 低(2)|
| S2 | 块 4 + 块 5 audit(大文件 + 多代际沉淀 + 高密度发现区) | M2 | 中(4)|
| S3 | 块 2 audit(最大 LOC,双路径风险高) + audit_index.md 汇总 | M3 | 低-中(3)|

**slice 数量 3 个**,符合"≤5 slice"指引;**0 个高风险 slice**(read-only audit 整体低风险)。

## Eval 验收

不适用。Phase 66 无功能改动 / 无测试新增。验收 = audit report 完整 + 分类口径一致 + 跳过清单遵守 + read-only 边界守住。

## 风险概述(详细见 `risk_assessment.md`)

- **R1**(中) — Codex 主观判定边界差 10x:finding 量级 5 vs 50 取决于口径松紧。缓解:design_decision §S1 锁口径阈值 + 给每类示例;Claude review 按口径回归。
- **R2**(中) — Claude review 工作量爆炸:40-80 finding 单次 review 不可行。缓解:分轮 review,按块审,审完一块 Codex 即可入 closeout 局部段。
- **R3**(低-中) — read-only 边界破坏:Codex 顺手改 typo / 删 1-行 dead import。缓解:closeout 验收 `git diff src/ tests/ docs/design/` 为空;CI 守卫(若有)。
- **R4**(低) — 后续清理 phase 排期遗忘:finding 进 backlog 后无人推进。缓解:Phase 66 closeout 时按严重程度分两档:(a) 高优 进显著位置 + 推荐下一清理 phase 优先项 (b) 低优 合并到 misc-cleanup phase 集中处理。
- **R5**(低) — Phase 65 新代码信号不稳定:sqlite_store.py / truth/*.py 可能"是设计如此"被误报为债务。缓解:Phase 65 新文件 finding 标 `(Phase 65 new code)` + 额外说明是否 known tradeoff。
- **R6**(低) — 跳过清单不严密:Codex 漏读 backlog,重新报已记录条目。缓解:Codex audit 每块开始前先通读 concerns_backlog.md Open 表,显式跳过。

## Model Review Gate

**默认 skipped**(根据 `.agents/workflows/model_review.md` 触发条件):
- 不触动 INVARIANTS / DATA_MODEL / SELF_EVOLUTION
- 不涉及 schema / CLI/API surface / state transition / truth write path / provider routing policy
- 不引入 NO_SKIP 红灯
- read-only,scope 与风险都低

若 design-auditor 复检后给出 [BLOCKER] 或多个 [CONCERN],再视情况触发。

## Branch Advice

- 当前分支:`main`(Phase 65 已 merge + v1.4.0 已 tag)
- 建议 branch 名:`feat/phase66-code-hygiene-audit`
- 建议操作:Human Design Gate 通过后切出该 branch,Codex 在该分支上跑 5 块 audit;commit 节奏建议每块 1 commit + audit_index 1 commit + closeout 1 commit(共 7 commit)

## 完成条件

**audit 完整性**:
- 6 份产出文件全部存在(5 子 report + 1 index),frontmatter + TL;DR 齐
- 75 个 .py 文件全部归入 5 块之一(含 5 个 `__init__.py`)
- audit_index.md 含完整 finding 计数 × 4 类 × 3 严重级矩阵
- 每块 finding 数 > 30 或 = 0 时附说明

**分类口径一致**:
- 每条 finding 显式标注 4 类之一 + 3 严重级之一 + 文件:行号 + 判定依据(grep 结果 / LOC 计数)
- 跨块共识 finding 在 audit_index.md 汇总段单列

**跳过清单遵守**:
- concerns_backlog.md Open 13 项 + Phase 65 known gap 3 项 = 16 项**不出现**在 finding 中(若出现要标"已在 backlog 登记"并不计数)

**read-only 边界**:
- `git diff main -- src/ tests/ docs/design/` 为空
- `git diff main -- docs/concerns_backlog.md` 在 closeout 阶段允许有 backlog 增量(Phase 66 finding 入 backlog),但不允许在 audit 阶段动 src/

**文档对齐**:
- `docs/plans/phase66/closeout.md` 完成 + `docs/concerns_backlog.md` 增量 + `docs/active_context.md` 由 Codex 同步(Updater 是 Codex)
- INVARIANTS.md / DATA_MODEL.md 零 diff
- `git diff --check` 通过

## 完成后的下一步

- Phase 66 closeout 后,触发 `roadmap-updater` subagent 同步 §三 "代码卫生" 行 [已消化];§四候选 K 块 strikethrough(merge 日期 + closeout 引用 + audit_index 引用);§五推荐顺序 K ✓ → R / D
- **不打 tag**(Phase 66 是 read-only audit,不构成 release 节点;v1.5.0 等到下一个 capability-bearing phase 完成后再考虑)
- 后续阶段:候选 R(真实使用反馈观察期)或下一清理 phase(按 audit_index 推荐项),Human 在新 Direction Gate 决定

## 不做的事(详见 non-goals)

- 不修复任何代码 / 测试 / 文档
- 不修改 INVARIANTS.md / DATA_MODEL.md / SELF_EVOLUTION.md
- 不审 tests/
- 不引入新工具
- 不重新发现 backlog Open 项
- 不引入新 §9 守卫
- 不评判架构合理性
- 不替后续清理 phase 决定 scope

## 验收条件(全 phase)

详见上方 §完成条件。本 kickoff 与 design_decision 一致,无补充。
