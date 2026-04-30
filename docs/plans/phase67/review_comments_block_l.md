---
author: claude
phase: phase67
slice: review-block-l
status: review
verdict: APPROVE
depends_on:
  - docs/plans/phase67/codex_review_notes_block_l.md
  - docs/plans/phase67/design_decision.md
  - docs/plans/phase67/kickoff.md
  - docs/plans/phase67/risk_assessment.md
  - docs/plans/phase66/audit_index.md
---

TL;DR(2026-04-30 M1 review):**APPROVE**(无 condition,可直接进 M2)。7 项 quick-win 全部消化,实装质量高。Codex 主动透明声明 4 处偏离 design 文字的实装选择,经核验全部合理:(1) `RETRIEVAL_SCORING_TEXT_LIMIT` / `RETRIEVAL_PREVIEW_LIMIT` 改放 `retrieval_config.py` 避免循环 import;(2) `orchestrator.py` 直接 import `DEFAULT_REVIEWER_TIMEOUT_SECONDS`(选项 (a) 局部应用,因已 import review_gate 无循环风险;比 design 给的选项 (b) 字面量+注释更严格);(3) `retrieval.py:788 expand_by_relations` 顺手处理同语义 preview;(4) `ingestion/pipeline.py` 命名 `INGESTION_REPORT_PREVIEW_LIMIT` / `_SUFFIX`(audit_index 第 7 项 quick-win 但 design_decision 漏给具体常量名)。全量 pytest 610 passed,与 baseline 一致。

## 审查范围

- M1 milestone:S1(7 项 quick-win)
- 输入:
  - `docs/plans/phase67/codex_review_notes_block_l.md`(Codex 自己的 implementation notes)
  - 实装 commit `b96c132 refactor(phase67-m1): complete hygiene quick wins`(12 文件 +56/-54)
  - docs commit `fc9ebba docs(phase67-m1): complete hygiene quick wins`(active_context + concerns_backlog + codex_review_notes)
- 对照权威:design_decision.md §S1.1-§S1.6(revised-after-design-audit)
- branch:`feat/phase67-hygiene-io-cli-cleanup`

## 7 项 quick-win 逐项核验

### ✓ Quick-win 1:`run_consensus_review` dead code 删除

- **位置**:`review_gate.py:617-632` 删除 18 行
- **核验**:
  - `grep -rn "run_consensus_review\\b" src/ tests/` 0 命中(只剩 `run_consensus_review_async` 仍 production 用)
  - 删除前 grep 已 confirm 无 callsite,删除后无 import error
- **遵循 design_decision §S1.2**:✓

### ✓ Quick-win 2:`_pricing_for` module-level 删除

- **位置**:`cost_estimation.py:34-42` 删除 11 行;保留 `StaticCostEstimator._pricing_for` instance method (line 59)
- **核验**:
  - `grep -rn "_pricing_for" .` 全仓库 → 仅命中 `cost_estimation.py:48` `self._pricing_for(...)` 调用 + line 59 method 定义,无 non-self callsite
  - tests 也无 callsite
- **遵循 design_decision §S1.2 修订版(全仓库 grep)**:✓

### ✓ Quick-win 3:`rank_documents_by_local_embedding` 标 eval-only

- **位置**:`retrieval_adapters.py:259` 加注释 `# eval-only: production retrieval uses TextFallbackAdapter or VectorRetrievalAdapter.`
- **核验**:
  - 函数本体保留,无 production callsite,tests/eval/ 单点 import 不变
  - 注释清楚标 production 路径替代品
- **遵循 design_decision §S1.1 选项 (b)**:✓

### ✓ Quick-win 4:SQLite timeout 常量命名

- **位置**:`sqlite_store.py` 加 `SQLITE_CONNECT_TIMEOUT_SECONDS = 5.0` + `SQLITE_BUSY_TIMEOUT_MS = 5000`(line 18-19)
- **核验**:
  - 7 处 callsite 全部替换:lines 281/327/358/367/370/377/885 + 2 处 `PRAGMA busy_timeout` f-string 插值
  - `grep -n "timeout=5.0\\|busy_timeout = 5000" src/swallow/sqlite_store.py` 0 命中(全部清理)
  - PRAGMA 字符串使用 f-string 插值 `f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}"`
- **遵循 design_decision §S1.3(authoritative)**:✓

### ✓ Quick-win 5:CLI MPS_POLICY_KINDS import owner

- **位置**:`cli.py:77` 加 `from .mps_policy_store import MPS_POLICY_KINDS`;`cli.py:1316` 改为 `choices=sorted(MPS_POLICY_KINDS)`
- **核验**:
  - 手动重复的 `("mps_round_limit", "mps_participant_limit")` 已删除
  - `sorted()` 包裹保证 `--help` 输出确定性(per design_audit Q18a)
- **遵循 design_decision §S1.5(authoritative)**:✓

### ✓ Quick-win 6:retrieval preview / scoring limits 命名

- **位置**:`retrieval_config.py:7-8` 加 `RETRIEVAL_SCORING_TEXT_LIMIT = 4000` + `RETRIEVAL_PREVIEW_LIMIT = 220`
- **核验**:
  - `retrieval.py` 5 处替换:lines 425/647/788/877/885
  - `retrieval_adapters.py` 3 处替换:lines 269/314/454(全部 [:4000] 三处一致)
  - `grep -rn "\\[:4000\\]\\|\\[:220\\]" src/swallow/` 仅 1 处残留(`quality_reviewer.py:159 preview = preview[:4000]`,Codex 显式 out-of-scope,见下文 NOTE-1)
- **遵循 design_decision §S1.4 修订版**:✓ 含 1 处主动 out-of-scope

### ✓ Quick-win 7:orchestration timeout / card defaults

- **位置**:多文件
  - `executor.py:34` 加 `DEFAULT_EXECUTOR_TIMEOUT_SECONDS = 20`,4 处 callsite(lines 1167/1290/1432/1561)替换 ✓
  - `models.py:641` 字面量 60 + 注释引用(选项 (b)) ✓
  - `planner.py:93` 字面量 60 + 注释引用(选项 (b)) ✓
  - `orchestrator.py:135 + 2549/2595/2596` 直接 import + 用 `DEFAULT_REVIEWER_TIMEOUT_SECONDS`(见下方 design 漂移 #2)
  - `ingestion/pipeline.py:31-32` 加 `INGESTION_REPORT_PREVIEW_LIMIT = 80` + `INGESTION_REPORT_PREVIEW_SUFFIX = "..."`(见下方 scope 漂移)
- **遵循 design_decision §S1.6 修订版**:✓(选项 (b) + orchestrator 局部更优解 + ingestion 顺手命名)

## Design 漂移 / Scope 漂移核验(全部合理)

### 漂移 #1:`RETRIEVAL_SCORING_TEXT_LIMIT` 改放 `retrieval_config.py`

- **design_decision §S1.4 文字**:`# retrieval.py - module top` 加 constants
- **Codex 实装**:加在 `retrieval_config.py:7-8`,`retrieval.py` + `retrieval_adapters.py` 各自 import
- **理由**(Codex notes #1):`retrieval.py` 已 import `retrieval_adapters.py`(line 16);若反向 `retrieval_adapters.py` 从 `retrieval.py` import,会循环 import
- **核验**:
  - `grep "^from\\|^import" retrieval.py | head` 确认 line 16 `from .retrieval_adapters import (...)`
  - `retrieval_config.py` 已是 retrieval tunables 的现有 owner(已有 `KNOWLEDGE_PRIORITY_BONUS = 50` 等),`retrieval.py` + `retrieval_adapters.py` 都从此 import 无循环
- **判定**:✓ **漂移合理且更优**,与 KNOWLEDGE.md §3.3 "Replaceable Components" 中的 retrieval tunables 应在 config 模块的精神一致
- **影响**:design_decision §S1.4 文字应在后续修订时改为 `# retrieval_config.py - module top`(closeout 阶段或下次 phase 修订)

### 漂移 #2:`orchestrator.py` 直接 import `DEFAULT_REVIEWER_TIMEOUT_SECONDS`(选项 (a) 局部应用)

- **design_decision §S1.6 文字**:reviewer_timeout owner 全局采纳选项 (b)(字面量 + 注释)以避免循环 import
- **Codex 实装**:`orchestrator.py:135 + 2549/2595/2596` 直接 `from .review_gate import DEFAULT_REVIEWER_TIMEOUT_SECONDS`
- **理由**(Codex notes #4):`orchestrator.py` 已 import 多个 review_gate 对象(`ReviewFeedback` / `run_review_gate_async` 等),无循环 import 风险;直接 import constant 比字面量+注释更干净,消除 2 处 60 字面量
- **核验**:
  - `grep "from .review_gate" src/swallow/orchestrator.py` 确认 import 链已存在
  - `grep "60" src/swallow/orchestrator.py` 现在 0 处 `60` 字面量(原有 2 处都被 `DEFAULT_REVIEWER_TIMEOUT_SECONDS` 取代)
  - `models.py` + `planner.py` 仍是字面量 60 + 注释(因为这两个文件不能 import review_gate,会循环)
- **判定**:✓ **漂移更严格,不是降格**;选项 (a) 不能全局应用(models.py / planner.py 受循环约束),但 orchestrator 局部应用是逻辑必然
- **影响**:design_decision §S1.6 应在后续修订时增加注解 "orchestrator.py 局部采纳选项 (a) 因已有 review_gate import 链;models.py / planner.py 仍用选项 (b)"

### 漂移 #3:`retrieval.py:788 expand_by_relations` 顺手处理

- **design_decision §S1.4 文字**:retrieval.py 列了 lines 423/645/875/883 共 4 处
- **Codex 实装**:同时处理 line 788(在 `expand_by_relations` 函数内)
- **理由**(Codex notes #2):grep 时发现 `expand_by_relations` 中也有同语义 preview truncation;否则会留同语义 magic number,后续 audit 仍会标 finding
- **核验**:`retrieval.py:788` 改动是 `preview = " ".join(document.text.split())[:RETRIEVAL_PREVIEW_LIMIT]`,与 425/647 完全同款
- **判定**:✓ **scope 漂移合理**,符合 audit-spirit("第 7 项 quick-win 是 retrieval preview/scoring limits"的全集),不是 over-reach

### 漂移 #4:`ingestion/pipeline.py` 顺手命名 `INGESTION_REPORT_PREVIEW_LIMIT`

- **design_decision §S1.4 文字**:仅指明"`ingestion/pipeline.py:292` 按上下文判断属于 preview 还是 scoring 限制",未给具体常量名
- **Codex 实装**:加 `INGESTION_REPORT_PREVIEW_LIMIT = 80` + `INGESTION_REPORT_PREVIEW_SUFFIX = "..."` 两个常量;callsite 改 + 修复 truncation 计算逻辑(原 `[:77]` 是 hardcoded `len(suffix)` 减算)
- **理由**:audit_index quick-win 第 7 项明确是 "ingestion preview / scoring limits";design 漏给具体常量名是 design_decision 不完整,Codex 命名补全
- **核验**:
  - 常量名 `INGESTION_REPORT_PREVIEW_LIMIT` 与 `RETRIEVAL_*` 命名风格一致
  - `INGESTION_REPORT_PREVIEW_SUFFIX = "..."` 抽出 suffix 字面量是额外整理,使 `INGESTION_REPORT_PREVIEW_LIMIT - len(SUFFIX)` 算法正确
  - 不与现有常量冲突(命名 unique)
- **判定**:✓ **漂移合理**;design 不完整,Codex 补全是必要工作

## OK 项(已严格遵守)

- ✅ M1 commit 单 commit + 独立 docs commit(`b96c132` + `fc9ebba`)— 符合 Branch Advice
- ✅ 不动 docs/design/ 任何文件(`git diff main -- docs/design/` = 0)
- ✅ Codex 主动透明 — 4 处漂移全部在 codex_review_notes_block_l.md 中显式声明,review 时无意外
- ✅ 全量 pytest 610 passed(与 Phase 65 baseline 一致;Phase 67 M1 不引入 regression)
- ✅ `grep --check`(per Codex notes 验证清单)全部清理:`run_consensus_review` / `def _pricing_for` 模块级 / `[:4000]` 在 retrieval_adapters.py / `[:220]` / `timeout=5.0` / `busy_timeout = 5000` / `choices=("mps_round_limit"...)` / `AIWF_EXECUTOR_TIMEOUT_SECONDS", "20"` 全部 0 命中
- ✅ `quality_reviewer.py:159 preview[:4000]` Codex 主动 out-of-scope(见 NOTE-1)
- ✅ M1 不引入新工具(无 vulture / pyflakes 等);仅 grep + manual reading
- ✅ 无 INVARIANTS / DATA_MODEL / KNOWLEDGE 改动

## 没有发现的问题

- 没有 BLOCKER
- 没有 design 漂移(4 处都是显式声明 + 合理理由)
- 没有 scope 漂移到 quick-win 之外(retrieval.py:788 + ingestion 命名都在 quick-win 第 7 项的合理范围内)
- 没有破坏 read-only invariant(M1 是 implementation phase,但限定在 design 锁定范围)
- 没有引入新工具
- 没有 INVARIANTS / DATA_MODEL / KNOWLEDGE 改动

## NOTES(信息性,不阻塞)

### NOTE-1:`quality_reviewer.py:159 preview = preview[:4000]` Codex 主动 out-of-scope

- **位置**:`src/swallow/quality_reviewer.py:159`
- **观察**:全仓库唯一残留 `[:4000]` 字面量;Codex notes #3 显式说明 "this is operator-facing quality-review preview, not retrieval scoring; pulling it into M1's retrieval scoring constant would broaden the scope beyond the Phase 67 M1 quick-win"
- **判定**:✓ 合理 out-of-scope。这是 quality-review 显示场景,与 retrieval scoring 不同语义;**不应**复用 `RETRIEVAL_SCORING_TEXT_LIMIT`
- **建议**:Phase 67 closeout 阶段把"`quality_reviewer.py:159` preview[:4000] 是 quality-review 语义,与 retrieval scoring 不同"显式登记到 `concerns_backlog.md`(per Phase 66 audit_block5 finding 严重等级 [low]);未来某 cleanup phase 命名 `QUALITY_REVIEW_PREVIEW_LIMIT` 或类似

### NOTE-2:design_decision 文字 vs 实装 4 处漂移建议在 closeout 阶段同步

- **背景**:M1 实装时 4 处偏离 design 文字(漂移 #1-#4),但所有偏离都被 codex_review_notes_block_l.md 透明记录
- **建议**:Phase 67 closeout 阶段(全 phase 完成后)在 closeout.md 中加"Design vs Implementation Drift" 段,把这 4 处漂移整理 + 标"已被 M1 review APPROVE"。**不修订 design_decision.md**(已 final 不动),只在 closeout 透明声明
- **影响**:零(closeout 文档透明性提升,不影响 M2/M3 实装)

### NOTE-3:M2 启动前 Codex 应注意 reviewer_timeout import 模式

- **背景**:M1 中 orchestrator 选了选项 (a) 局部应用,models.py / planner.py 选了选项 (b)
- **M2 影响**:M2 是 IO helper + artifact ownership,与 reviewer_timeout 无关;**M2 不需要再处理**这一决议
- **建议**:仅作 awareness 提示;若 M3 触动 cli.py 的 reviewer_timeout 引用(可能性低),Codex 应优先选 (a)(若已 import review_gate)

## 给 Codex 的 follow-up 清单(M1 → M2 进入前)

进 M2 不强制要求,可在 M2 实装时统一处理:

1. **(可选,M2 阶段处理)** Codex 在 M2 PR body 中标 `quality_reviewer.py:159` 是 quality-review 语义而非 retrieval scoring,留给后续 cleanup phase 单独命名(NOTE-1)
2. **(必做,但不阻塞 M2)** Codex 把当前 `codex_review_notes_block_l.md` status 从 `review` 改为 `final`(若本 review verdict APPROVE,Codex 可立即改)
3. **(建议)** 进 M2 前,Codex grep 当前 `_io_helpers.py` 不存在(确认是真新建)+ grep §S2.2 表中 11 个 callsite 现行行为,准备 M2 实装

## Verdict

**APPROVE**(无 condition)

理由:
- 7 项 quick-win 全部消化 + 全量 pytest 绿灯
- 4 处偏离 design 文字的实装选择全部合理(避免循环 import / 选项 (a) 局部更优解 / 同语义 preview 全集化 / design 漏给常量名补全)
- Codex 主动透明声明,review 无意外
- 无 BLOCKER,无 CONCERN
- 仅 3 NOTE(其中 2 个是 closeout 阶段透明性建议,1 个是 M2 起点 awareness)

**Codex 可立即进 M2**(verdict APPROVE 满足 trigger)。

## 给 Codex 的工作流提醒

- M2 阶段 Codex 等本 `review_comments_block_l.md` 出现 + frontmatter `verdict` = APPROVE 后才进 M2 — 当前 verdict = APPROVE,**M2 可启动**
- M2 输出 = `src/swallow/_io_helpers.py`(新建)+ 11 callsite 显式 variant + cli.py 私有 helpers 删除 + 跨模块 import 改动
- M2 严格按 design_decision §S2.2 authoritative 对照规则匹配 variant;**3 个 grep-pending 行**(canonical_registry / staged_knowledge / dialect_data)Codex 实装前先 grep 现行行为再按规则匹配
- M2 完成后 Claude 出 `review_comments_block_m.md`;若发现 M1 defect 需要 fixup,触发 design_decision §Review 分轮 §M1 fixup commit 协议(命名 `fixup(phase67-m1): <description>` + Claude 显式 directive)

## 累积统计(M1)

| 类别 | 完成项 |
|---|---|
| Dead code 删除 | 2 项(run_consensus_review / `_pricing_for` 模块级)|
| Eval-only 标注 | 1 项(rank_documents_by_local_embedding)|
| 常量命名 | 4 项(SQLite timeout × 2 / RETRIEVAL × 2 / EXECUTOR / INGESTION 系列)|
| Import owner | 1 项(MPS_POLICY_KINDS)|
| Owner 注释引用 | 2 项(models.py / planner.py 字面量 60 + 注释)|
| 直接 import 优化 | 1 项(orchestrator.py DEFAULT_REVIEWER_TIMEOUT_SECONDS)|

src/swallow/ +56/-54 行;1 个新文件(无,因 retrieval_config 已存在);全量 pytest 0 regression。
