---
author: claude
phase: phase66
slice: design-decomposition
status: revised-after-design-audit
depends_on:
  - docs/plans/phase66/kickoff.md
  - docs/plans/phase66/context_brief.md
  - docs/plans/phase66/design_audit.md
  - docs/plans/phase65/closeout.md
  - docs/plans/phase64/closeout.md
  - docs/roadmap.md
  - docs/concerns_backlog.md
  - docs/design/INVARIANTS.md
  - docs/design/DATA_MODEL.md
---

TL;DR(revised-after-design-audit,2026-04-30):**3 milestone / 3 slice**(M1 块 1 + 块 3 短文件先扫 / M2 块 4 + 块 5 多代际沉淀 + 高密度发现区 / M3 块 2 最长链路 + audit_index 汇总)。统一 finding 模板:`[<severity>][<category>] <file>:<line> <title>` + 判定依据。**dead code 判定改为两轮 grep**(先 src/ 后 tests/)解决步骤自相矛盾(BLOCKER-1)。**跳过清单 16 项**(concerns_backlog.md Open 13 项 + Phase 65 closeout known gap 3 项,Phase 64 M2-2 已在 13 项内)(CONCERN-2)。**9 行边缘 case ruling**:跨 ≥2 文件 ≥9 行算重复 helper(CONCERN-3)。**块 report 上限**:单块 report ≤ 800 行(CONCERN-4)。**review handoff**:每轮 review 写 `docs/plans/phase66/review_comments_block<n>.md`(CONCERN-5)。read-only 边界由 closeout `git diff main -- src/ tests/ docs/design/` 为空验收。Claude review 按块分轮(M1 → review → M2 → review → M3 → review),不一次性吞 6 份 report。

## Revision Index(2026-04-30 design_audit 后)

本文件在原 draft 基础上吸收 `design_audit.md`(1 BLOCKER + 5 CONCERN)结论:

- **BLOCKER-1 dead code 算法自相矛盾** → §S1 dead code 判定算法改为两轮 grep(src/ 先,tests/ 后);明确 test-only callsite 算 dead 的具体判定路径
- **CONCERN-1 文件计数误** → §S1 / §S2 / §S3 各块文件清单按真实 75 .py(含 5 个 `__init__.py`)修正;块 4 = 23 文件 / 块 5 = 16 文件
- **CONCERN-2 跳过清单数双计** → §S1 跳过清单总数改为 **16 项**(13 backlog + 3 phase 65 known gap;Phase 64 M2-2 已在 13 项内不双计)
- **CONCERN-3 9 行边缘 case 无判决** → §S1 重复 helper 阈值改为 ≥9 行(原 ≥10 行),给 1-行容差
- **CONCERN-4 块 report 长度上限缺** → §S1 finding 模板段加"单块 report ≤ 800 行,超过分两份"硬约束
- **CONCERN-5 milestone review handoff 触发文件名未定义** → §S3 review 分轮机制段加 review_comments_block<n>.md 文件命名规约 + Codex 等待 trigger 的明确文件信号

修订点定位:
- §S1 关键设计决策:dead code 算法 + 跳过清单数 + 9 行 ruling + 块 report 上限
- §S3 review 分轮机制:review_comments 文件命名 + Codex handoff 信号

## 方案总述

Phase 66 是 read-only audit,**实质是把 Phase 47-65 累积的代码债做一次结构化盘点**。设计上没有事务边界 / schema 兑现 / 失败注入这种重型项,但需要**口径锁死 + 跳过清单 + review 分轮**三件事保证 audit 信号干净:

1. **口径锁死**:4 类 finding 每类的判定阈值是 design 里 authoritative 的(下方 §S1),Codex 不需自决"算不算 dead"
2. **跳过清单**:concerns_backlog Open 14 项 + Phase 65 known gap 3 项 + Phase 64 indirect chat-completion URL guard 1 项 = 18 项,Codex 显式跳过避免重复盘点
3. **review 分轮**:5 块按 M1→M2→M3 顺序,每个 milestone 完成后 Codex 提交对应 block report → Claude review 后 Codex 才进入下一 milestone(不一次性吞 6 份)

**为什么拆 3 个 slice 而非合并成 1 个**:
- M1(块 1 + 块 3):LOC 最小(总 4411)+ Phase 64/65 信号最干净 → 暖手 + 校准口径
- M2(块 4 + 块 5):多代际沉淀 + 高密度发现区(LOC ~14415)→ 验证 M1 校准的口径在大文件上是否仍可执行
- M3(块 2):最大 LOC(~12168)+ orchestrator/harness 双路径风险 → 最后做,且 audit_index 汇总顺便落地

**等价性保证**:Phase 66 完成对外可观察行为零变化(无代码 diff / 无测试 diff / 无设计文档 diff);唯一变化是 `docs/plans/phase66/*.md` 6 份新文件 + `docs/concerns_backlog.md` 增量。

## Slice 拆解

### S1 — 块 1 + 块 3 audit(M1,中-低风险:校准口径 + 暖手)

**目标**:产出 `audit_block1_truth_governance.md` + `audit_block3_provider_router.md`,完整覆盖块 1 + 块 3 的 4411 LOC。

**影响范围**:
- 仅写:`docs/plans/phase66/audit_block1_truth_governance.md` + `docs/plans/phase66/audit_block3_provider_router.md`
- 0 src/ diff / 0 tests/ diff / 0 docs/design/ diff

**关键设计决策**:

- **finding 模板(authoritative,Codex 每条 finding 严格遵循)**:
  ```markdown
  ### [high|med|low][dead-code|hardcoded-literal|duplicate-helper|abstraction-opportunity] <one-line title>

  - **位置**:`src/swallow/<file>.py:<line>` (或多行范围 `<start>-<end>`)
  - **判定依据**:
    - 例如(dead code):`grep -rn "function_name" src/swallow/ tests/` 命中数 = 1(仅自身定义)
    - 例如(硬编码):跨 4 处出现 magic string `"http-claude"` 在 router.py / synthesis.py / orchestrator.py / cli.py
    - 例如(重复 helper):router.py:120-135 与 governance.py:312-329 高度相似的 `json.loads + FileNotFoundError fallback` 16 行
    - 例如(抽象机会):capability_enforcement.py:45/72/108 出现 3 处 `if route_kind == "X": ... elif route_kind == "Y":` 结构
  - **建议处理**(Codex 给初判,Claude review 时核可):
    - dead code 高严重 → 推荐立刻删
    - 硬编码 URL / model name → 推荐外部化到 routes.default.json 或 capability_enforcement 常量
    - 重复 helper → 推荐抽到 _http_helpers.py 或 sqlite_store helper 段
    - 抽象机会 → 标记后由后续 design phase 决定(Phase 66 不做)
  - **影响范围**:single-file / cross-block / cross-module
  - **关联**(可选):若 finding 与 backlog Open 项有重叠或衍生关系,引用 backlog 编号
  ```

- **dead code 判定算法**(authoritative,**两轮 grep**,修订自 design_audit BLOCKER-1):

  **轮 1 — src/ 生产 callsite 检查**:
  1. Codex 跑 `grep -rn "<symbol>" src/swallow/`(**仅 src/,不含 tests/**)
  2. 命中数(排除自身定义行 + 排除注释/docstring 命中)
  3. 若 src/ 命中 = 0 → **进入轮 2 判定** dead code 候选
  4. 若 src/ 命中 ≥ 1 → **不是 dead**,跳过

  **轮 2 — tests/ 测试 callsite 检查(轮 1 通过后才执行)**:
  1. Codex 跑 `grep -rn "<symbol>" tests/`
  2. 命中数(排除注释/docstring)
  3. 若 tests/ 命中 = 0 → **完全 dead**(标 `[high][dead-code]`)
  4. 若 tests/ 命中 ≥ 1 → **test-only callsite,算 dead**(生产路径不可达,标 `[med][dead-code]` 并附"被 N 个测试调用但生产路径无引用")

  **共同排除规则**(两轮都适用):
  - `@deprecated` 标注且仍被调用 → 不算 dead(明确 deprecated tracking)
  - `__init__.py` 的 `__all__` 公开导出 → 不算 dead
  - `__version__` / dunder 元数据 → 不算 dead
  - 仅在注释 / docstring 中出现 → 不算 callsite
  - import 语句 `from .X import Y` 的 Y 命中 → 算 callsite(被外部模块用)

- **硬编码字面量判定算法**:
  1. **强制外部化类**(单次出现也算):URL(`http://` / `https://` 字符串)/ model name(`claude-` / `gpt-` / `qwen-` / `local-` 前缀字符串)/ dialect name / provider name / route name(`http-X` / `local-X` 形式)
  2. **跨处重复类**(≥3 次):任意相同字符串字面量在 src/swallow/ 内 grep 命中 ≥ 3 次,且不在测试 / fixture / docstring 内
  3. **magic number 类**(任意未命名):port / timeout 秒数 / chunk size / retry count / threshold 值
  4. 排除:Python 标准库常量、单元测试 fixture、注释 / docstring、`__version__` 等元数据

- **重复 helper 判定算法**(阈值 ≥ 9 行,修订自 design_audit CONCERN-3):
  1. Codex 在每块内主动找以下高频模式:`json.loads(path.read_text())` + `except FileNotFoundError` + `return {}` 块;SQLite connection + cursor 样板;LLM response 错误处理 / retry wrapper;manual ULID 生成而非 `identity.new_id`
  2. 跨 **≥ 2 文件** + **≥ 9 行**高度相似 → finding(原 ≥ 10 行,1 行容差解决 9 行边缘 case)
  3. "高度相似"定义:差异仅为变量名、类型注解、轻微格式;若有实质性逻辑差异(如多了 1 个 if 分支)→ 不算重复 helper,可标 `[abstraction-opportunity]`
  4. 接口同名但实现不同(多态)不算

- **抽象机会判定算法**(标记不抽):
  1. N ≥ 3 处 if-elif / switch 结构,处理同一组类型/常量,差异仅在 case 标签
  2. N ≥ 3 处相同 dataclass init 模式
  3. 标 `[abstraction-opportunity]`,**不实际抽**(Phase 66 不重构;由后续 design phase 决定是否抽);若有现成抽象点(如 `dispatch_policy`),建议关联

- **finding 模板单块上限**(修订自 design_audit CONCERN-4):**单块 audit report ≤ 800 行**。超过则 Codex 按 finding 严重程度分两档:`audit_block<n>_<name>_part1.md`(高 + 中)+ `audit_block<n>_<name>_part2.md`(低)。其中块 5(cli.py 3832 行)和块 2(orchestrator 3882 行)预期最可能触发分档。每个 part 独立 frontmatter + 独立 TL;DR,但用同一 slice 名(`audit-block<n>`)。

- **跳过清单(M1 实施前 Codex 必读,16 项,修订自 design_audit CONCERN-2)**:

  **A. concerns_backlog.md Open 表(13 项)**:
  - Phase 45:`_select_chatgpt_primary_path()` 多叶节点主路径启发式偏差
  - Phase 49:`_sqlite_vec_warning_emitted` 多线程竞态
  - Phase 50:`extract_route_weight_proposals_from_report()` 依赖文本格式
  - Phase 50:`_FAIL_SIGNAL_PATTERNS` false fail verdict
  - Phase 57:`VECTOR_EMBEDDING_DIMENSIONS` import 时固化
  - Phase 58:`_is_open_webui_export` auto-detect 语义变更
  - Phase 59:`v1.2.0` release docs 未同步
  - Phase 61/63:`PendingProposalRepo` 仍 in-memory(durable proposal artifact 未实装)
  - Phase 61/63:`librarian_side_effect` INVARIANTS §5 矩阵漂移
  - Phase 63 M2-1:`staged_candidate_count` 永远为 0 的 vestigial payload 字段
  - Phase 63 M2-5:`_apply_route_review_metadata` 约 250 行 reconciliation 逻辑可读性
  - Phase 63 M3-1:`events` / `event_log` 双写历史行不 backfill
  - Phase 64 M2-2:chat-completion guard 不做跨语句 def-use 间接 URL binding 分析

  **B. Phase 65 closeout known gap(3 项)**:
  - Phase 65:review record application artifact 在 SQLite commit 后写文件系统(warning-only)
  - Phase 65:audit snapshot(before/after payload)无 size cap / truncation policy
  - Phase 65:full schema migration runner deferred

  Codex 在每块 audit 开始前**显式列出"本块跳过的 backlog 编号"**,即使该项与 finding 区域重叠;Claude review 时核可。


- **块 1 audit hotspot(per context_brief §3)**:
  - `store.py`(723 行)Phase 48 前 JSON 存储层:Phase 65 后 JSON 写路径是否仍有生产 callsite?dead code 高概率
  - `sqlite_store.py`(953 行)Phase 65 新建:bootstrap helper 是否有重复 JSON 解析(`_bootstrap_route_metadata_from_legacy_json` / `_bootstrap_policy_from_legacy_json` / `consistency_audit.py:_bootstrap_audit_trigger_policy_from_legacy_json` / `mps_policy_store.py:_bootstrap_mps_policy_from_legacy_json` 4 个 bootstrap 共享重复模式?)
  - `governance.py`(638 行)Phase 64/65 重写:`_apply_route_review_metadata` 250 行业务逻辑可读性已在 backlog Phase 63 M2-5 → **跳过**
  - 期望 finding 量级:**3-8**

- **块 3 audit hotspot**:
  - `router.py`(1422 行)Phase 64 重写:三层外部化已清一波,但仍可能有 model hint / dialect name 字面量未外部化
  - `capability_enforcement.py`(106 行)的 capability 名称列表是否硬编码
  - `_http_helpers.py`(91 行)Phase 64 抽出:与 retrieval_adapters.py 中 HTTP helper 是否仍有重复模式
  - 期望 finding 量级:**3-6**

**验收条件**:
- 2 份子 report 文件存在 + 同一 frontmatter 模板 + TL;DR 齐
- 块 1 + 块 3 全文件覆盖(块 1:8 文件 / 块 3:5 文件 = 13 文件)
- finding 总数 6-14(粗略 6-15 区间);若 < 3 或 > 20 必须附说明
- 跳过清单显式列出
- `git diff main -- src/ tests/ docs/design/` 为空

**风险评级**:影响范围 1 / 可逆性 1 / 依赖 0 = 2(低)。read-only,文件小,信号干净。

---

### S2 — 块 4 + 块 5 audit(M2,中风险:大文件 + 多代际沉淀)

**目标**:产出 `audit_block4_knowledge_retrieval.md` + `audit_block5_surface_tools.md`,覆盖 14415 LOC。

**关键设计决策**:

- 沿用 S1 的 finding 模板 + 4 类口径,**不重新校准**(M1 已做校准,M2 直接套用)
- 若 M1 review 阶段 Claude 修订口径(如某类阈值过严/过松),M2 实施前 Codex 重新读 design_decision §S1 修订后的口径
- 块 4 audit hotspot:
  - `canonical_reuse_eval.py`(377 行)Phase 47-55 沉淀:dead code 高概率
  - `knowledge_review.py`(243 行)+ `ingestion/parsers.py`(542 行):多代际重复 JSON read/write helper 高产区
  - `retrieval_adapters.py`(767 行):embedding HTTP calls 已声明排除 chat-completion 守卫(Phase 64 closeout),audit 时**不**视为 indirect URL binding finding;但仍可能有 dead adapter method
  - `dialect_adapters/`:仅剩 claude_xml + fim_dialect;旧 codex_fim 已 Phase 54 rename(context_brief 已确认 file 不存在),**不审 codex_fim**
  - 期望 finding 量级:**12-20**(最高产)

- 块 5 audit hotspot:
  - `cli.py`(3832 行)是最大风险 — 早期 Phase 10-30 添加的 subcommand(remote handoff / dispatch acknowledge / canonical reuse report 等)是否仍挂载?**dead subcommand 是块 5 主目标**
  - `meta_optimizer.py`(1320 行)Phase 62-63 工具化沉淀:report 解析 + proposal 生成可能有重复模式
  - `librarian_executor.py` / `literature_specialist.py` / `quality_reviewer.py` 三个 Specialist 实现间可能有 boilerplate
  - 期望 finding 量级:**12-26**

**Codex 实施提醒**:
- 块 5 cli.py 单文件 3832 行,Codex 应**分段扫**(按 subcommand 分组),audit_block5 内含分段索引(line ranges 对应每个 subcommand 处理段)
- 块 4 跨 18 个文件,Codex 按"主题"分段:knowledge canonical / knowledge retrieval / ingestion / dialect adapters 四大主题各开一节

**验收条件**:
- 2 份子 report 文件存在
- 块 4 + 块 5 全文件覆盖(块 4:18 文件 / 块 5:14 文件)
- finding 总数 24-46(粗略);单块 > 30 必须附说明
- 跳过清单显式列出
- `git diff main -- src/ tests/ docs/design/` 为空

**风险评级**:影响范围 2 / 可逆性 1 / 依赖 1 = 4(中)。LOC 大,Codex 扫的时间长 + 主观判定空间大,Claude review 时审压力增加。

---

### S3 — 块 2 audit + audit_index 汇总(M3,中风险:LOC 最大 + 跨块汇总)

**目标**:产出 `audit_block2_orchestration.md` + `audit_index.md`。

**块 2 audit hotspot**:
- `orchestrator.py`(3882 行,churn 79):Planner 部分构造已抽到 `planner.py`,orchestrator 内可能残留被 planner.py 替代的同等逻辑 → dead code 高概率
- `harness.py`(1950 行):跨越多代际,async/sync 双路径可能有死分支
- `models.py`(1042 行):event type 字符串常量是否全被消费?`staged_candidate_count` 永远为 0 已在 backlog Phase 63 M2-1 → **跳过**
- `executor.py`:Phase 64 改过 fallback chain,可能仍有过渡期 helper
- `subtask_orchestrator.py`(460)/ `review_gate.py`(649)/ `validator*.py`:跨文件可能有 boilerplate
- 期望 finding 量级:**10-20**

**audit_index.md 设计**:

```markdown
---
author: codex
phase: phase66
slice: audit-index
status: final
depends_on:
  - docs/plans/phase66/audit_block1_truth_governance.md
  - docs/plans/phase66/audit_block2_orchestration.md
  - docs/plans/phase66/audit_block3_provider_router.md
  - docs/plans/phase66/audit_block4_knowledge_retrieval.md
  - docs/plans/phase66/audit_block5_surface_tools.md
---

TL;DR: <total finding count> findings across 5 blocks; <high> high / <med> med / <low> low; <quick-win> quick-win + <design-needed> design-needed.

## Finding 计数矩阵(4 类 × 3 严重 × 5 块)

| 块 | dead-code | hardcoded-literal | duplicate-helper | abstraction-opportunity | 块小计 | LOC |
|---|---|---|---|---|---|---|
| 块 1 (Truth & Governance) | x | x | x | x | xx | 2671 |
| 块 2 (Orchestration) | x | x | x | x | xx | 12168 |
| 块 3 (Provider Router) | x | x | x | x | xx | 1740 |
| 块 4 (Knowledge & Retrieval) | x | x | x | x | xx | 5827 |
| 块 5 (Surface & Tools) | x | x | x | x | xx | 8588 |
| **总计** | xx | xx | xx | xx | **xxx** | 30994 |

## 严重程度矩阵

| 块 | high | med | low |
|---|---|---|---|
| ... | ... | ... | ... |

## 跨块共识 finding(同一类问题在 ≥ 2 块出现)

- 例:`json.loads + FileNotFoundError fallback` 在块 1 + 块 4 + 块 5 共出现 X 次 → 推荐统一抽到 `swallow/_io_helpers.py`(若不存在)

## Quick-win 清单(立刻可入下一清理 phase)

- 单文件内 dead code 删除(无跨模块影响)
- typo / cosmetic / dead import
- `[low]` 严重级所有项

## Design-needed 清单(需要 design phase 决定)

- `[high]` 跨块影响
- 抽象机会 N ≥ 5 跨块出现(需引入新 helper 模块)
- INVARIANTS 相关 finding(若有,本不应出现 — audit 不评判宪法,但若 Codex 误报则在此 flagged 给 Claude review 修订)

## Codex 推荐下一阶段优先项

- (Codex 据 audit 全貌给 1-3 条建议,Human 在新 Direction Gate 决定;Codex 不替决)

## 跳过清单核可

- concerns_backlog.md Open 14 项 + Phase 65 known gap 3 项 + Phase 64 M2-2 = 18 项跳过 ✓
```

**验收条件**:
- `audit_block2_orchestration.md` + `audit_index.md` 存在
- 块 2 全 19 文件覆盖
- audit_index.md 含完整矩阵 + 跨块共识 + quick-win + design-needed + 跳过清单核可
- 5 块总 finding 量级 40-80(若 < 25 或 > 100 必须附说明)
- `git diff main -- src/ tests/ docs/design/` 为空

**风险评级**:影响范围 2 / 可逆性 1 / 依赖 0 = 3(低-中)。块 2 单 slice 内 LOC 最大,但 audit_index 汇总是机械工作。

---

## 依赖与顺序

```
S1 (M1, 块 1 + 块 3, 暖手 + 校准口径)
       ↓ Claude review S1 → 修订口径(如需) → 校准 design_decision §S1
S2 (M2, 块 4 + 块 5, 高密度发现区)
       ↓ Claude review S2
S3 (M3, 块 2 + audit_index 汇总)
       ↓ Claude review S3 + 全 phase closeout
```

**不允许并行**:Codex 必须按 M1→M2→M3 顺序,Claude review 通过一个 milestone 才进下一个。理由:M1 校准的口径是 M2/M3 的 input,提前并行会导致口径漂移。

## Milestone 与 review checkpoint

| Milestone | 包含 slice | review 重点 | 提交节奏 |
|-----------|-----------|------------|---------|
| **M1** | S1(块 1 + 块 3) | 口径校准:dead code 阈值 / 硬编码字面量边界 / 重复 helper 判定 / 抽象机会粒度;跳过清单遵守 | 单独 milestone commit;Claude review 后修订 design_decision §S1 口径(若需) |
| **M2** | S2(块 4 + 块 5) | 大文件 audit 是否仍能保持 M1 校准的口径 + 块 4 多代际沉淀的 finding 是否被合理分类 + 块 5 cli.py 失活子命令检测完整性 | 单独 milestone commit;Claude review 重点关注重复 helper 跨块共识 |
| **M3** | S3(块 2 + audit_index) | 块 2 orchestrator/harness 双路径 dead 检查 + audit_index 矩阵完整 + Codex 下一阶段推荐合理性 | 单独 milestone commit;Claude review 后进入 closeout |

## Review 分轮机制

- Claude **不一次性 review 全部 6 份**;按 M1→M2→M3 分轮
- 每轮 review 产出**单独的 review_comments 文件**(修订自 design_audit CONCERN-5,文件名 authoritative):
  - M1 review:`docs/plans/phase66/review_comments_block1_3.md`(块 1 + 块 3 合并 review)
  - M2 review:`docs/plans/phase66/review_comments_block4_5.md`(块 4 + 块 5 合并 review)
  - M3 review:`docs/plans/phase66/review_comments_block2_index.md`(块 2 + audit_index 合并 review)
  - closeout final review(可选,若 M1-M3 review 已无遗留):`docs/plans/phase66/review_comments.md`(总 review)
- **Codex handoff 信号**:Codex 等待对应 `review_comments_blockX_Y.md` 文件出现 + frontmatter `verdict` 字段为 `APPROVE` 或 `APPROVE_WITH_CONDITIONS` 后,才进入下一 milestone。若 verdict = `NEEDS_REVISION`,Codex 修订当前块 audit report 直至 verdict 升级
- 每轮 review 后 Codex 才进入下一 milestone(避免 review 反馈未消化前后续 audit 已 baked in 错口径)
- 全 phase closeout 时,Claude 一次性出 final `review_comments.md` + closeout 评估
- review_comments 文件 frontmatter 模板:
  ```yaml
  ---
  author: claude
  phase: phase66
  slice: review-block<n>
  status: review
  verdict: APPROVE | APPROVE_WITH_CONDITIONS | NEEDS_REVISION
  depends_on:
    - docs/plans/phase66/audit_block<n>_<name>.md
    - docs/plans/phase66/design_decision.md
  ---
  ```

## phase-guard 检查

- ✅ 当前方案不越出 kickoff goals(G1-G6 与 S1-S3 一一对应)
- ✅ kickoff non-goals 严守:**不修复任何代码**;不动 INVARIANTS / DATA_MODEL;不审 tests/;不引入新工具;不重新发现 backlog Open 项
- ✅ 5 块拆分锁定 70 个 .py 文件全覆盖(per context_brief §1)
- ✅ slice 数量 3 个,符合"≤5 slice"指引
- ✅ 0 个高风险 slice(整体低风险 read-only audit)
- ✅ Phase 64/65 已落地内容保持(audit 不动 src/)

## Branch Advice

- 当前分支:`main`(Phase 65 已 merge + v1.4.0 已 tag)
- 建议 branch 名:`feat/phase66-code-hygiene-audit`
- 建议 commit 节奏:M1 (1) → M2 (1) → M3 + audit_index (2 commits) → closeout (1) = 5 commits 上 PR

## Model Review Gate

**默认 skipped**(详见 kickoff §Model Review Gate):read-only audit + 不触动宪法 + 风险低,无触发条件。

## 不做的事(详见 kickoff non-goals)

- 不修复任何代码
- 不动 INVARIANTS / DATA_MODEL / SELF_EVOLUTION
- 不审 tests/
- 不引入新工具(vulture / pyflakes / radon 等留给后续 design phase 决定)
- 不重新发现 backlog Open 项
- 不引入新 §9 守卫
- 不评判架构合理性
- 不替后续清理 phase 决定 scope

## 验收条件(全 phase)

详见 `kickoff.md §完成条件`。本 design_decision 与 kickoff 一致,无补充。
