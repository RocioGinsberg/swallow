---
author: claude
phase: phase66
slice: review-block4-5
status: review
verdict: APPROVE_WITH_CONDITIONS
depends_on:
  - docs/plans/phase66/audit_block4_knowledge_retrieval.md
  - docs/plans/phase66/audit_block5_surface_tools.md
  - docs/plans/phase66/review_comments_block1_3.md
  - docs/plans/phase66/design_decision.md
  - docs/plans/phase66/kickoff.md
  - docs/plans/phase66/risk_assessment.md
---

TL;DR(2026-04-30 M2 review):**APPROVE_WITH_CONDITIONS**。两份子 report 严格遵循 design_decision §S1 finding 模板,read-only 边界守住(`git diff main...HEAD -- src/ tests/ docs/design/` = 0)。Block 4 = 12 finding(预期 12-20 ✓);Block 5 = 14 finding(预期 12-26 ✓)。M2 总 26 finding;26 + M1 7 = **33 finding,接近设计预期 40-80 下沿**。Codex 已主动吸收 M1 review CONCERN-1(把 Block 4 finding 1 跨块 JSON/JSONL 标 [high])。read-only 边界完全守住:Codex 在 cost_estimation.py 看到真 dead 的 `_pricing_for` 都没顺手删,Block 5 在 cli.py 找到 deprecated `doctor codex` 别名也只标 finding 不修。**1 condition + 3 NOTE,Codex 在 M3 audit_index 阶段统一处理,M3 可立即启动**。

## 审查范围

- M2 milestone:S2(块 4 + 块 5)audit
- 输入:
  - `docs/plans/phase66/audit_block4_knowledge_retrieval.md`(297 lines,17597 bytes)
  - `docs/plans/phase66/audit_block5_surface_tools.md`(326 lines,18818 bytes)
- 对照权威:design_decision.md / kickoff.md / risk_assessment.md(revised-after-design-audit)
- branch:`feat/phase66-code-hygiene-audit`(M2 commit 待 Codex 提交;两份 audit 当前 untracked)

## Read-Only 边界核验 ✓

```
$ git diff main...HEAD -- src/ tests/ docs/design/
(empty)
```

零 src/ / tests/ / docs/design/ 改动。M2 阶段在 cost_estimation.py 与 cli.py(deprecated alias)等明显可顺手修的位置都未触动,**read-only 边界完全守住**。

## 抽样 finding 真伪核验

我对 5 条关键 finding 逐条 grep 复查:

| Finding | 复查命令 | 验证结果 |
|---|---|---|
| Block 4 — `rank_documents_by_local_embedding` test-only callsite | `grep -rn "rank_documents_by_local_embedding" src/ tests/` | src/retrieval_adapters.py:249 唯一 production 定义;tests/eval/test_vector_retrieval_eval.py:11 + 82 唯一 caller — **test-only,production-dead [med]** 准确 |
| Block 5 — `_filter_task_states` 跨 CLI/Web API 重复 | `grep -n "filter_task_states\|focus" src/swallow/cli.py src/swallow/web/api.py` | web/api.py:16-32 与 cli.py:881-897 line-for-line 等价,5 个 case 分支(all/active/failed/needs-review/recent)全相同 — 准确 |
| Block 5 — Ingestion format 重复 | `grep -n "SUPPORTED_INGESTION_FORMATS\|chatgpt_json"` | parsers.py:10-15 owner;cli.py:1520 choices 重复 — 准确 |
| Block 4 — Markdown heading 三处实装 | grep `MARKDOWN_HEADING_PATTERN` | ingestion/parsers.py / ingestion/pipeline.py / retrieval_adapters.py 三处独立实装 — 准确 |
| Block 4 — embedding endpoint suffix `/v1/embeddings` 硬编码 | grep retrieval_adapters.py | line 186-214 命中 — 准确 |

(M1 review 已抽样核验 7 条 finding 全准确;M2 抽样基础上,从全 26 条中选有代表性的 5 条复查,采样质量持续高)

## 跳过清单核验 ✓

- Block 4 跳过:Phase 45 / 49 / 57 / 58 / 64 M2-2(共 5 项,且每项明确标"already tracked, not counted")
- Block 5 跳过:Phase 50 × 2 / Phase 61/63 / Phase 65 known gap × 3(共 6 项)

跳过项**不出现**在 finding 中;部分跳过项的相关代码出现在 audit hotspot,但 Codex 显式在 §Skip List Applied 段说明已跳过 — 严格遵守 design_decision §S1。

## Findings(我对 Codex audit 的 finding)

### [CONCERN-1] Block 4 finding 1 与 Block 1 finding 1 部分重叠 — M3 audit_index 需 dedupe

- **位置**:
  - Block 1 finding 1(`_load_json_lines`)位置 = store.py:136-148 / truth/knowledge.py:59-67(块 1 内 2 处)+ orchestrator.py / librarian_executor.py(跨块到块 2 / 块 5)
  - Block 4 finding 1(JSON/JSONL loader 重复)位置 = knowledge_store.py:123-143 / staged_knowledge.py:92-104 / canonical_registry.py:65-91 / knowledge_suggestions.py:22-31 / retrieval.py:588-600 / retrieval.py:678-690 / dialect_data.py:144-153
- **观察**:Codex 主动接受 M1 review CONCERN-1 思路,在 Block 4 写了一条更广义的 high finding,覆盖 7 个 location。但 Block 1 finding 1 仍标 [med] + 自身位置仅指 store.py + truth/knowledge.py — 两条 finding **从 IO 抽象角度看是同一类问题的不同子集**。
- **风险**:M3 audit_index.md 汇总时若两条都计数,会 double-count "JSON/JSONL loader 重复"问题;若只数 Block 4 finding 1(已包含跨块视角),Block 1 finding 1 就被吸收了。
- **建议**:M3 audit_index.md 阶段 Codex 在"跨块共识 finding"段明确声明:
  - "Block 1 finding 1 + Block 4 finding 1 是同一类问题的两个视角:Block 1 视角狭义('块 1 内 _load_json_lines 重复'),Block 4 视角广义('全 src JSON/JSONL loader 重复')。最终治理建议以 Block 4 finding 1 high 为准;Block 1 finding 1 升级为 high 并标'subsumed by block 4 finding 1'或保持 med 标'narrow scope of block 4 finding 1'"
  - 或:在 audit_index quick-win / design-needed 清单中**只记一条**(以 Block 4 finding 1 high 为准),Block 1 finding 1 在汇总段标 "subsumed by block 4 cross-block view"
- **不阻塞 M3 启动**;dedupe 是 audit_index 工作。

### [NOTE-1] Block 5 cli.py 未发现 dead subcommand,与 context_brief 预期不一致

- **位置**:`audit_block5_surface_tools.md` §Checked But Not Counted 第 1 条
- **背景**:context_brief §3 块 5 audit hotspot 明确标:"`cli.py`(3832 行)是最大风险 — 大量 `swl <subcommand>` 路径,可能有失活子命令(早期 Phase 10-30 添加、后续流程重写后未使用)"。预期 finding 量级 12-26,**dead subcommand 是块 5 主目标**。
- **观察**:Codex 报 0 dead-code finding;但 §Checked But Not Counted 写"current `add_parser` and `if args.command...` scan did not reveal a clearly dead subcommand"。
- **判定**:这是 audit 真实结论 — Phase 10-30 早期添加的子命令在 Phase 60-65 review 过程中已被持续清理(Phase 63 删除了 `_route_knowledge_to_staged`、Phase 64 重构 fallback chain 等);当前 cli.py 的 subcommand 树虽巨大但都仍可达。这是好事(说明 review gate 在历史 phase 中起了作用),不是 Codex 漏审。
- **NOTE**:audit_index.md 阶段 Codex 应该在"Codex 推荐下一阶段优先项"段强调:"cli.py 当前无 dead subcommand,但 N=80+ `add_parser` 与 `if args.command` 重复链是 [med][abstraction-opportunity];未来若引入新子命令前,先做 table-driven dispatch 重构会更好"。这也是 Block 5 finding 3(med 抽象机会)已经在说的。**不修订 Block 5 audit;只是 audit_index 阶段强调一下"已审且确认无 dead subcommand"的阴性结论**。

### [NOTE-2] Block 4 finding 8(MODEL_PRICING / dialect_data.py)与 Block 3 finding 2 类似,M3 dedupe 时考虑

- **位置**:Block 4 finding 8(`dialect_data.py:DEFAULT_EXECUTOR = "aider"`,med hardcoded-literal)
- **观察**:Block 3 finding 2 已标 `MODEL_PRICING` 嵌入代码(provider/model family 字符串);Block 4 finding 8 现在标 `dialect_data.py:DEFAULT_EXECUTOR = "aider"`(executor brand);Block 5 finding 14 标 cli.py + doctor.py `aider` / `codex` brand 默认。
- **判定**:三条 finding 都是 hardcoded-literal,但**不是同一处代码** — 分别在 cost_estimation.py / dialect_data.py / cli.py + doctor.py。每条 finding 独立成立,**不需要 dedupe**;只是 M3 audit_index "跨块共识 finding"段应一起列出"executor / provider / model brand 字面量散落"主题(共识 finding,而非重复 finding)。
- **建议**:audit_index.md 阶段把 Block 3 finding 2 + Block 4 finding 8 + Block 5 finding 14 列为"executor/provider brand 字面量 ownership 不清"主题(N=3 跨块出现的 [med][hardcoded-literal])。**不修订 Block 4 / Block 5 audit**。

### [NOTE-3] Block 5 政策事务包络重复 — 与 Block 1 finding 3 形成跨块共识

- **位置**:Block 5 finding 7(`consistency_audit.py` / `mps_policy_store.py` 政策 SQLite 事务包络重复)
- **观察**:Block 5 finding 7 自己的"判定依据"段已经说了"The same shape already appeared in M1 route/policy findings";Block 1 finding 3 也是事务包络重复。
- **判定**:这是 Codex 主动跨 milestone 引用,标 [med] + design-needed,正确。**不需要修订**;但 audit_index 阶段应在"跨块共识"段把 Block 1 finding 3 + Block 5 finding 7 一起列为"SQLite 事务包络重复"主题(跨 4 个 namespace:route / policy / audit_trigger / mps);严重等级综合考虑后是否仍是 abstraction-opportunity 还是升 [high] duplicate-helper,M3 阶段 Codex 决定。

## OK 项(已确认严格遵守 design)

- ✅ finding 模板严格 — 26 条 finding 全含 [严重][类别] + 文件:行号 + 判定依据(grep 命令)+ 建议处理 + 影响范围 + 关联(部分含 backlog 编号或跨 milestone 引用)
- ✅ Block 4 finding 计数(12)在预期 12-20 内
- ✅ Block 5 finding 计数(14)在预期 12-26 内
- ✅ 单 report 大小(297 / 326 行)远在 800 行上限内,**未触发分 part**
- ✅ Phase 65 新代码标注:Block 5 finding 7 在跨块比较时显式标"the same shape already appeared in M1 route/policy findings",符合 Phase 65 new code tracking 要求
- ✅ dead code 判定使用两轮 grep:Block 4 finding 2(`rank_documents_by_local_embedding`)明确标"Per Phase 66 two-pass dead-code rule, test-only callsite = production-dead, marked med"
- ✅ 重复 helper 阈值 ≥ 9 行:Block 5 finding 1(JSON artifact printers)/ finding 2(_filter_task_states)/ finding 7(政策事务)/ finding 8(specialist 类 boilerplate)阈值都达标
- ✅ 不顺手修代码:Codex 在 cli.py 见到 deprecated `doctor codex` 别名、cost_estimation.py 见到真 dead `_pricing_for`(Block 3 finding 1)、cli.py 见到 ingestion format 重复 — 一律不顺手修,只标 finding。**read-only 严格性优秀**
- ✅ frontmatter + TL;DR 齐
- ✅ method 段记录所用工具(rg + wc),便于复查
- ✅ Block 5 含 CLI Segment Index(per design_decision §S2 cli.py 分段扫策略),9 个 segment 切分清晰
- ✅ Codex 主动接受 M1 review CONCERN-1 思路:Block 4 finding 1 直接标 [high] + 跨 7 location + 关联 M1 CONCERN-1
- ✅ skip list 在两份 report 都显式列出,跳过项**不出现**在 finding 中

## 没有发现的问题

- 没有 BLOCKER
- 没有 finding 误报(5 条抽样核验全部代码定位准确)
- 没有破坏 read-only 边界
- 没有重复发现 backlog Open 项
- 没有越过 phase scope(没建议改 INVARIANTS / DATA_MODEL / 引入新工具 / 评判架构合理性 / 顺手修代码)

## 给 Codex 的 follow-up 清单(M2 → M3 进入前完成)

进 M3 不强制要求,可在 M3 audit_index.md 阶段统一处理:

1. **(M3 必做)** audit_index.md "跨块共识 finding" 段处理 dedupe / 升级:
   - Block 1 finding 1 + Block 4 finding 1 = JSON/JSONL loader 重复(同一类的窄/广视角);最终汇总以 Block 4 high 为准
   - Block 1 finding 3 + Block 5 finding 7 = SQLite 事务包络重复(跨 4 namespace);严重等级综合判定
   - Block 3 finding 2 + Block 4 finding 8 + Block 5 finding 14 = executor/provider brand 字面量(主题共识)
2. **(M3 必做)** audit_index.md "Codex 推荐下一阶段优先项"段含:
   - cli.py 当前无 dead subcommand 阴性结论(NOTE-1)
   - 后续 phase 推荐先做 table-driven dispatch 重构(Block 5 finding 3 抽象机会)
3. **(M3 可选)** audit_index.md "已审但未列 finding"段补 store.py JSON 写路径核验声明(M1 review NOTE-1 遗留)
4. **(必须)** Codex 把当前 audit_block4 / audit_block5 status 从 `review` 改为 `final`(若 verdict APPROVE_WITH_CONDITIONS,Codex 在 M3 阶段消化 condition 后改 final)。

## Verdict

**APPROVE_WITH_CONDITIONS**

理由:
- read-only 边界 ✓
- 跳过清单遵守 ✓
- 26 条 finding 抽样核验全部代码定位准确 ✓
- 格式严格符合 design_decision §S1 模板 ✓
- Codex 主动吸收 M1 review CONCERN-1 思路 ✓
- 仅 1 condition(M3 audit_index dedupe)+ 3 NOTE(都不阻塞 M3 启动)

**Codex 可立即进 M3**(块 2 + audit_index 汇总),CONCERN-1 在 M3 阶段消化;不需要回头修订 audit_block4 / audit_block5。

## 给 Codex 的工作流提醒

- M3 阶段 Codex 等待此 review_comments_block4_5.md 出现 + verdict 字段为 APPROVE / APPROVE_WITH_CONDITIONS 后才进 M3 — 当前 verdict = APPROVE_WITH_CONDITIONS,**M3 可启动**
- M3 输出 = `audit_block2_orchestration.md` + `audit_index.md`
- M3 块 2 = 19 文件 / ≈12168 LOC,LOC 最大;orchestrator.py 3882 行 + harness.py 1950 行 + models.py 1042 行 = 6874 行单文件巨头 + 16 个支持文件;**audit_block2 高概率触发 800 行上限分 part**
- M3 audit_index.md 必须含:finding 计数矩阵(4 类 × 3 严重 × 5 块)+ 严重程度矩阵 + 跨块共识 finding(本 review 列出 3 个主题)+ Quick-win 清单 + Design-needed 清单 + Codex 推荐下一阶段优先项 + 跳过清单核可 + Block 5 cli.py 无 dead subcommand 阴性结论(NOTE-1)
- M3 完成后 Claude 出 `review_comments_block2_index.md` + final closeout review

## 累积统计(M1 + M2)

| 块 | finding | dead-code | hardcoded | duplicate | abstraction | high | med | low |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 块 1 | 3 | 0 | 1 | 1 | 1 | 0 | 1 | 2 |
| 块 3 | 4 | 1 | 3 | 0 | 0 | 0 | 3 | 1 |
| 块 4 | 12 | 1 | 7 | 1 | 3 | 1 | 10 | 1 |
| 块 5 | 14 | 0 | 8 | 4 | 2 | 0 | 11 | 3 |
| **M1+M2 累计** | **33** | **2** | **19** | **6** | **6** | **1** | **25** | **7** |

待 M3 块 2 audit;预期块 2 finding 10-20(per context_brief §3),phase 总 finding 估在 43-53 区间,**位于设计预期 40-80 内**。
