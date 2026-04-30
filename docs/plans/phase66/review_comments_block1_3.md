---
author: claude
phase: phase66
slice: review-block1-3
status: review
verdict: APPROVE_WITH_CONDITIONS
depends_on:
  - docs/plans/phase66/audit_block1_truth_governance.md
  - docs/plans/phase66/audit_block3_provider_router.md
  - docs/plans/phase66/design_decision.md
  - docs/plans/phase66/kickoff.md
  - docs/plans/phase66/risk_assessment.md
---

TL;DR(2026-04-30 M1 review):**APPROVE_WITH_CONDITIONS**。两份子 report 格式严格遵循 design_decision §S1 finding 模板,read-only 边界守住(`git diff main...HEAD -- src/ tests/ docs/design/` = 0),16 项跳过清单显式列出且遵守,7 条 finding 的代码定位经抽样核验全部准确(包括 `_load_json_lines` 跨 4 文件、`_pricing_for` 真 dead、`timeout=5.0` × 7 处、`MODEL_PRICING` 硬编码 5 模型家族、route/policy 事务包络 × 3)。Block 1 = 3 finding(预期 3-8 ✓);Block 3 = 4 finding(预期 3-6 ✓)。**1 条建议(condition)+ 2 条 NOTE,Codex 修订后 verdict 升级 APPROVE,即可进 M2**。

## 审查范围

- M1 milestone:S1(块 1 + 块 3)audit
- 输入:
  - `docs/plans/phase66/audit_block1_truth_governance.md`(124 lines,7223 bytes)
  - `docs/plans/phase66/audit_block3_provider_router.md`(130 lines,7377 bytes)
- 对照权威:
  - `design_decision.md` revised-after-design-audit §S1(finding 模板 + 4 类口径 + 16 项跳过 + dead code 两轮 grep + 重复 helper ≥9 行 + 单块 report ≤ 800 行)
  - `kickoff.md` revised §G1-G6 + §完成条件
- branch:`feat/phase66-code-hygiene-audit`(commit `6e98509 docs(phase66): add m1 code hygiene audit`)

## Read-Only 边界核验 ✓

```
$ git diff main...HEAD -- src/ tests/ docs/design/
(empty)
$ git diff main...HEAD --stat
docs/plans/phase66/audit_block1_truth_governance.md | 124 +++
docs/plans/phase66/audit_block3_provider_router.md  | 130 +++
docs/plans/phase66/{context_brief, design_audit, design_decision, kickoff, risk_assessment}.md(已存在 5 份)
```

零 src/ / tests/ / docs/design/ 改动。read-only 边界硬约束守住。

## 抽样 finding 真伪核验

我对 7 条 finding 的代码定位逐条 grep 复查,**全部准确**:

| Finding | 复查命令 | 验证结果 |
|---|---|---|
| Block 1 — `_load_json_lines` 跨文件重复 | `grep -n "def _load_json_lines"` | 命中 store.py:136 / truth/knowledge.py:59 / librarian_executor.py:57 / orchestrator.py:388 — **4 个 production 定义**,Codex 报"块 1 内 2 + 跨块 2"准确 |
| Block 1 — `timeout=5.0` × 7 处 | `grep -n "timeout=5.0\|busy_timeout = 5000"` | 7 处全部命中(line 281 / 327 / 358 / 367 / 370 / 377 / 885)|
| Block 1 — route/policy 事务包络 × 3 | `grep -nE "BEGIN IMMEDIATE\|get_connection"` | route.py:34/37 / policy.py:25/31 / policy.py:54 命中 |
| Block 3 — `_pricing_for` dead | `grep -n "_pricing_for" src/`,tests/ 单独 grep | src/cost_estimation.py 内仅 module-level def + self method def + 1 个 self.X 调用;**production 无 callsite,tests 无 callsite — 真 dead** |
| Block 3 — `MODEL_PRICING` 硬编码 | `grep -n "MODEL_PRICING\|claude\|qwen\|fim"` | 5 model family(claude/deepseek/fim/gemini/qwen)+ codex alias 嵌入代码 |
| Block 3 — chat-completion URL 默认 | 已见 `_http_helpers.py:7` `DEFAULT_NEW_API_CHAT_COMPLETIONS_URL` | URL 字面量 + 30/20 timeout magic 准确 |
| Block 3 — capability_enforcement 重复 taxonomy | (略,已见 audit 中具体行号) | 命中 |

## 跳过清单核验 ✓

两份 report 都显式列出"已跳过的 backlog 项"(audit_block1.md §Skip List Applied / audit_block3.md §Skip List Applied),与 design_decision §S1 列出的 16 项一致:

- Block 1 跳过 5 项(Phase 61/63 PendingProposalRepo / Phase 61/63 librarian_side_effect / Phase 63 M2-5 _apply_route_review_metadata / Phase 63 M3-1 events 双写 / Phase 65 known gap × 3)
- Block 3 跳过 1 项(Phase 64 M2-2 indirect chat-completion URL guard)

跳过项**不出现**在 finding 中,也未重复盘点 — 严格遵守。

## Findings(我对 Codex audit 的 finding)

### [CONCERN-1] `_load_json_lines` 严重程度可能过低

- **位置**:`audit_block1_truth_governance.md` finding 1 标 `[med]`
- **观察**:Codex 报告自己说"块 1 内 2 处 + 跨块 2 处" = **4 个 production 定义**;design_decision §S1 重复 helper 阈值是 ≥ 2 文件 + ≥ 9 行;此 finding 触发条件是 ≥ 2 文件 + ≥ 9 行,**但实际跨 4 文件 + 9 行**,远超阈值。
- **风险等级判断**:design_decision §G5 严重等级定义:
  - `[high]`:影响 INVARIANTS / DATA_MODEL 一致性 / 可读性显著下降 / **跨块影响清理**
  - `[med]`:可读性问题 / **单文件内重复** / 应外部化但低风险
- **判定**:此 finding 是"跨 4 文件 / 跨 3 块",严重等级应 `[high]`,理由是"跨块影响清理"+ "可读性显著下降(改一处忘改其他三处的回归风险随时间累加)"。Codex 标 `[med]` 偏保守。
- **建议**:Codex 在 audit_index.md 阶段重新评估,**或在本次 review 通过后,M3 写 audit_index 时把此项升级 high**;不需要在 M1 阶段重写 audit_block1。

### [NOTE-1] Block 1 finding 计数偏低,可能漏审 store.py JSON 写路径

- **位置**:`audit_block1_truth_governance.md`
- **背景**:context_brief §3 块 1 audit hotspot 明确标:**store.py(723 行)Phase 48 前 JSON 存储层:Phase 65 后 JSON 写路径是否仍有生产 callsite?dead code 高概率**。
- **观察**:audit_block1 仅报 3 finding,无一条针对 store.py 的"Phase 65 后 JSON 写路径是否仍有生产 callsite"。Codex 在 §Checked But Not Counted 段提到 "events / event_log schema coexistence was skipped because...",但这是 backlog 已记录条目;**store.py 中 task / event 之外的其他 JSON 写路径(如 staged knowledge / canonical registry / 各种 _save_* helper)是否仍有生产 callsite,未见审计结论**。
- **判定**:这可能是真的"store.py 已经在 Phase 64-65 清干净了"(合理);也可能是漏审。
- **建议**:Codex 在 M3 audit_index.md 的"已审但未列 finding"段显式声明:"store.py 内除 backlog 已记录的 events/event_log 双写外,其他 JSON 写 helper 经 grep 验证全部仍有生产 callsite,无 dead code"或类似;若发现遗漏,补 finding 进 audit_block1 part 2。**不阻塞 M1 通过**。

### [NOTE-2] Block 3 `cost_estimation.py` 双 `_pricing_for` 是 dead code 还是设计意图?

- **位置**:`audit_block3_provider_router.md` finding 1
- **观察**:Codex 报 module-level `_pricing_for` 是 dead(src/ 无 callsite,tests/ 无 callsite),建议"删除或 StaticCostEstimator delegate to it"。我手动 grep 确认无 callsite,**真 dead**。
- **疑问**:module-level def 与 method def **代码完全一致**(两次 35 行同款实现),Phase 35-50 引入 StaticCostEstimator 时可能漏删 module-level 版本。这是 Phase 35-50 的历史包袱。
- **建议**:Codex finding 文字已经合理("In a later cleanup phase, remove the module-level helper");无需修订。但 audit_index.md 阶段把此项标为"立刻可入下一清理 phase 的 quick-win"(单文件内删除,无跨模块影响,~10 行 diff)。
- **结论**:OK 如现状。

## OK 项(已确认严格遵守 design)

- ✅ finding 模板严格 — 所有 finding 含 [严重][类别] + 文件:行号 + 判定依据(grep 命令) + 建议处理 + 影响范围;部分含 关联 backlog 编号
- ✅ Block 1 finding 计数(3)在预期 3-8 内
- ✅ Block 3 finding 计数(4)在预期 3-6 内
- ✅ 单 report 大小(124 / 130 行)远在 800 行上限内
- ✅ Phase 65 新代码标注:Block 1 finding 2 / 3 标 `(Phase 65 new code)`,符合 risk_assessment R5 要求
- ✅ dead code 判定使用两轮 grep(audit method 段明确写 "two-pass grep per design")
- ✅ 重复 helper 阈值 ≥ 9 行(Block 1 finding 1 写 "9+ similar lines",符合 design 修订后阈值)
- ✅ 不顺手修代码:Codex 在 src/ 中发现 dead `_pricing_for` 但**没**顺手删,严守 read-only
- ✅ frontmatter + TL;DR 齐(都通过 format-validator 标准)
- ✅ method 段记录所用工具(rg + wc),便于 review 复查

## 没有发现的问题

- 没有 BLOCKER
- 没有 dead code 误报(_pricing_for 经核验是真 dead)
- 没有硬编码字面量误报(MODEL_PRICING / timeout / URL 经核验是真硬编码)
- 没有破坏 read-only 边界(`git diff src/` = 0)
- 没有重复发现 backlog Open 项(跳过清单遵守)
- 没有越过 phase scope(没建议改 INVARIANTS / DATA_MODEL / 引入新工具 / 评判架构合理性)

## 给 Codex 的 follow-up 清单(M1 → M2 进入前完成)

合并前需要 Codex 处理的:

1. **(可选,不阻塞 M2)** 在 M3 audit_index.md 时:把 Block 1 finding 1(`_load_json_lines`)严重程度升级到 `[high]`,理由"跨 4 文件 / 跨 3 块,触发 G5 high 标准"。或者在本次 review 通过后,Codex 自决是否在 audit_block1 内修订严重等级 — 我留 Codex 判断。
2. **(可选,不阻塞 M2)** 在 M3 audit_index.md 时:补一段"已审但未列 finding"声明 store.py 中其他 JSON 写 helper 经 grep 验证全部仍有 production callsite(或补 finding 若发现遗漏)。
3. **(必须)** Codex 把当前 audit_block1 / audit_block3 status 从 `review` 改为 `final`(若 verdict 为 APPROVE_WITH_CONDITIONS,Codex 在消化 condition 后改为 final)。

## Verdict

**APPROVE_WITH_CONDITIONS**

理由:
- read-only 边界 ✓
- 16 项跳过清单遵守 ✓
- 7 条 finding 全部经核验代码定位准确 ✓
- 格式严格符合 design_decision §S1 模板 ✓
- 仅 1 条 condition(_load_json_lines 严重等级建议升级)+ 2 条 NOTE(store.py 漏审验证 + dead helper quick-win 标注),都不阻塞 M2 启动

**Codex 可立即进 M2**(块 4 + 块 5 audit),CONCERN-1 可在 M3 audit_index 阶段消化;不需要回头修订 audit_block1。

## 给 Codex 的工作流提醒

- M2 阶段 Codex 等待此 review_comments_block1_3.md 出现 + verdict 字段为 APPROVE / APPROVE_WITH_CONDITIONS 后才进 M2(per design_decision §S3 review 分轮机制)— 当前 verdict = APPROVE_WITH_CONDITIONS,**M2 可启动**
- M2 输出 = `audit_block4_knowledge_retrieval.md` + `audit_block5_surface_tools.md`(若任一 > 800 行需分 part1/part2,见 design_decision §S1)
- M2 完成后 Claude 出 `review_comments_block4_5.md`,流程同款
- M2 高密度发现区:context_brief 预估 12-26 finding,audit 时仍按 design_decision §S1 严格口径,不放宽
