---
author: claude
phase: phase66
slice: risk-assessment
status: revised-after-design-audit
depends_on:
  - docs/plans/phase66/kickoff.md
  - docs/plans/phase66/design_decision.md
  - docs/plans/phase66/design_audit.md
  - docs/plans/phase66/context_brief.md
  - docs/plans/phase65/closeout.md
  - docs/plans/phase64/closeout.md
---

TL;DR(revised-after-design-audit,2026-04-30):**6 条风险条目**,无变化。**0 高 / 2 中 / 4 低**。read-only audit phase 整体低风险,无事务边界 / 无 schema / 无失败注入这种重型项;两条中风险都是"过程性"风险(口径主观差 10x / Claude review 工作量爆炸),而非"代码正确性"风险。R6 跳过清单条目数从 17 项更新为 **16 项**(13 backlog Open + 3 Phase 65 known gap;Phase 64 M2-2 已在 13 项内,不双计;来自 design_audit CONCERN-2)。无风险等级 ≥ 7,**不触发 model_review**。

## 风险矩阵

| ID | 风险 | 影响范围 | 可逆性 | 依赖复杂度 | 总分 | 等级 |
|----|------|---------|--------|-----------|------|------|
| R1 | Codex 主观判定边界差 10x(finding 量级 5 vs 50) | 2 | 1 | 1 | 4 | 中 |
| R2 | Claude review 工作量爆炸(40-80 finding 单次审不可行) | 1 | 1 | 2 | 4 | 中 |
| R3 | read-only 边界被破坏(Codex 顺手改 typo / 删 dead import) | 1 | 1 | 1 | 3 | 低 |
| R4 | 后续清理 phase 排期遗忘(finding 进 backlog 后无人推进) | 2 | 1 | 1 | 4 | 低-中 |
| R5 | Phase 65 新代码信号不稳定(sqlite_store / truth/ 误报为债务) | 1 | 1 | 1 | 3 | 低 |
| R6 | 跳过清单不严密(Codex 漏读 backlog 重新报已记录条目) | 1 | 1 | 1 | 3 | 低 |

---

## 详细分析

### R1 — Codex 主观判定边界差 10x(中)

**描述**:audit phase 没有"功能正确性"标尺,只有"代码卫生"判定。Codex 主观倾向(过严 vs 过松)直接决定 finding 数量:
- **过严倾向**:仅报 100% 确定的 dead code(callsite = 0 严格);硬编码字面量仅报 ≥ 5 处重复;重复 helper 仅报 ≥ 20 行高度相似 → finding 总量 ~10
- **过松倾向**:可能 dead 也报(callsite = 1 但 self-test 唯一 caller);任意字面量都标(包括正常 enum 常量);任意 if-elif ≥ 2 处都标抽象机会 → finding 总量 ~100

**触发场景**:
- design_decision §S1 口径阈值(≥ 3 处 / ≥ 10 行 / N ≥ 3)虽锁,但具体边缘 case Codex 仍需自决(如:9 行高度相似 + 1 行细微差异算不算重复 helper)
- M1 校准阶段 Claude review 修订口径,但若修订力度不够,M2/M3 仍漂移

**缓解**:
- design_decision §S1 已给每类 finding 的具体示例(dead code 4 排除规则 / 硬编码 3 强制类 + 跨处类 + magic number 类 / 重复 helper 4 模式 / 抽象机会 3 模式)
- M1 校准是结构性安排:S1(块 1 + 块 3)是 LOC 最小 + Phase 64/65 信号最干净的两块,Claude review 时可逐条核口径,修订 design_decision §S1 后 M2/M3 重新读
- Claude review 时若发现某块 finding 量级偏离 context_brief 预估(块 1 期望 3-8;实际 < 2 或 > 15)→ 强制 Codex 重审
- closeout 阶段 audit_index.md 含 finding 量级合理性自核(单块 > 30 必须附说明 / 单块 = 0 必须附说明)

**回滚成本**:低。口径调整后 Codex 重扫单块 ~30 分钟。

---

### R2 — Claude review 工作量爆炸(中)

**描述**:context_brief 预估 finding 总量级 40-80。Claude 单次 review 上百条 finding 是难以保证质量的,容易草率核可或漏核。

**触发场景**:
- 一次性提交 5 块 + audit_index 全 6 份文件给 Claude review(原文档 ≥ 1500 行)
- review 时关注力分散到多块,某块的判定漏核

**缓解**:
- design_decision §S3 已立 review 分轮机制:M1 → review → M2 → review → M3 → review → closeout review
- 每轮 review 仅审 2 份(M1) / 2 份(M2) / 2 份(M3 含 index)
- 每轮 review 完成 Codex 才进下一 milestone,反馈先消化
- Claude 在每轮 review 时可调用 design-auditor subagent 协助核 finding(若 review 工作量超 Claude 主线 capacity)
- closeout 阶段 audit_index.md 已汇总,Claude 仅核"汇总数据是否与 5 子 report 一致"

**回滚成本**:零(过程性风险,不影响 audit 输出正确性)。

---

### R3 — read-only 边界被破坏(低)

**描述**:Codex 在 audit 过程中可能因"惯性"顺手修小问题(typo / 1-行 dead import / 注释错误)。这破坏 Phase 66 的核心约束。

**触发场景**:
- Codex 看到 cli.py 一个明显 typo,1 行就能修,顺手 commit 进 audit branch
- Codex 看到一个 dead import `from foo import bar` 没人用,顺手删
- Codex 在 audit report 之外的文件做了"格式整理"(如 ruff format / black 整段)

**缓解**:
- kickoff §non-goals + design_decision §不做的事 显式声明:**任何代码 / 测试 / docs/design/ 修改都不做,即使是 1 行 typo**
- closeout 阶段验收清单必含 `git diff main -- src/ tests/ docs/design/` 为空,任何 src 改动都触发回退
- Claude review 每个 milestone 检查 `git diff main -- src/`(应为空);若发现非空,Codex 必须 git revert + 把对应改动转为 finding
- finding 自身可以记录"建议 1-行修复"作为推荐处理,但实际修复留给后续清理 phase

**回滚成本**:低(`git revert` + 把改动转为 finding,不涉及功能回滚)。

---

### R4 — 后续清理 phase 排期遗忘(低-中)

**描述**:Phase 66 finding 进 `concerns_backlog.md` 后,若没有清晰的"下一阶段优先级",finding 仍积压不动,Phase 66 的 audit 价值打折。

**触发场景**:
- audit_index.md 仅给"finding 计数",未给"建议下一清理 phase 范围"
- backlog 增量后 50+ 条新条目,Human 在 Direction Gate 看不到优先排序
- 后续 phase 持续选 capability-bearing 工作(如候选 D / R),清理 phase 一直推迟

**缓解**:
- design_decision §S3 audit_index.md 模板含两段强制内容:
  - **Quick-win 清单**:立刻可入下一清理 phase(单文件内 dead code 删除 / typo / `[low]` 全部);Codex 给出"5-10 个 quick-win 项"的简短列表,作为下一 misc-cleanup phase 的种子
  - **Design-needed 清单**:`[high]` 跨块影响 / 抽象机会 N ≥ 5 跨块 / INVARIANTS 相关 / 需引入新 helper 模块的项 — 标记需要 design phase
- closeout 阶段 Codex 给"下一阶段推荐"(1-3 条),Human 在新 Direction Gate 决定;不替 Human 决,但提供材料
- backlog 增量行加严重程度标签(`[high]` / `[med]` / `[low]`),便于 Human 排序

**回滚成本**:零(过程性,不影响 finding 正确性)。

---

### R5 — Phase 65 新代码信号不稳定(低)

**描述**:`sqlite_store.py`(953 行)/ `truth/route.py`(115)/ `truth/policy.py`(123)是 Phase 65 新建,代码状态新,可能"是设计如此"被误报为债务。

**触发场景**:
- bootstrap 4 个 helper(`_bootstrap_route_metadata` / `_bootstrap_route_policy` / `_bootstrap_audit_trigger_policy` / `_bootstrap_mps_policy`)代码模式确实重复,但每个对应不同 truth 命名空间,抽象到一起反而破坏 Phase 65 design_decision §S1 的 namespace 隔离
- `route_change_log` / `policy_change_log` 两个 audit 表的 INSERT 模式重复,但属于 Phase 65 design 故意保持的"namespace clarity"
- sqlite_store.py 中 5 个 namespace 的 `CREATE TABLE IF NOT EXISTS` 块结构相似,可能被 Codex 标抽象机会

**缓解**:
- audit 时 Phase 65 新文件 finding **强制标注 `(Phase 65 new code)`**
- 每个此类 finding **额外说明**是否是 Phase 65 closeout 已记录的 known tradeoff(如:"Phase 65 design_decision §S1 已声明 4 个 bootstrap helper namespace 分离;不抽象 = intentional")
- Claude review 时若 finding 标 `(Phase 65 new code)` 且未附 tradeoff 说明,要求 Codex 补
- 不视为 finding 数量"漏检",而是 design 决议的 known acceptance

**回滚成本**:低(标注 + 说明文字工作量)。

---

### R6 — 跳过清单不严密(低)

**描述**:Codex 漏读 concerns_backlog.md Open 表,在 audit 中重新报已记录条目,浪费工作量 + 增加 Claude review 噪声。

**触发场景**:
- backlog 14 项分散在多个 phase 的 closeout 段,Codex 仅扫顶部表格漏掉详细段
- Phase 65 known gap 3 项在 phase65/closeout.md 内,不在 backlog,Codex 误以为不在跳过清单
- Phase 64 M2-2 indirect chat-completion URL guard 在 phase64/review_comments.md,不在 backlog 主表

**缓解**:
- design_decision §S1 显式列出 16 项跳过清单全集(13 backlog + 3 phase 65 known gap;Phase 64 M2-2 已在 13 项内不双计;修订自 design_audit CONCERN-2)
- Codex 在每块 audit 开始前**显式列出"本块跳过的 backlog 编号"**,即使该项与 finding 区域重叠
- Claude review 时核对:子 report 跳过清单 + 实际 finding 是否有重复(若重复 → 标 "duplicate-of-backlog,不计 finding 数")
- audit_index.md 含"跳过清单核可"段,Codex 显式断言"已遵守 16 项跳过"

**回滚成本**:低(发现重复 → 从 finding 移除,不影响其他 audit 结果)。

---

## 总体策略

1. **3 milestone 顺序**(M1 → M2 → M3),无并行,每 milestone Claude review 通过才进下一
2. **M1 校准 = 关键节点**:S1 是块 1 + 块 3(LOC 最小 + 信号最干净),用来校准 4 类 finding 口径;Claude review 后修订 design_decision §S1 口径(如需),M2/M3 据修订后口径执行
3. **finding 模板严格统一**:authoritative 模板在 design_decision §S1,每条 finding 必含 [严重][类别] + 文件:行号 + 判定依据 + 建议处理 + 影响范围
4. **18 项跳过清单严格遵守**:每块 audit 开始前 Codex 显式列出"本块跳过条目"
5. **read-only 边界硬约束**:`git diff main -- src/ tests/ docs/design/` 在每个 milestone commit 必须为空
6. **review 分轮**:Claude 不一次性吞 6 份 report,每个 milestone 独立 review;closeout 阶段汇总
7. **Phase 65 新代码标注**:sqlite_store / truth/ 的 finding 强制标 `(Phase 65 new code)` + tradeoff 说明
8. **后续 phase 衔接**:audit_index.md 含 quick-win + design-needed + Codex 下一阶段推荐;Human 在新 Direction Gate 决定后续清理 phase 的 scope

## 与既有 risk 模式的对照

- **类似 Phase 60 的"调研性"phase**:Phase 60 retrieval policy 改动是"先盘点 retrieval 现状再设计",Phase 66 同款"先盘点代码现状再清理"。但 Phase 60 改了 retrieval 逻辑(中风险),Phase 66 read-only(低风险),整体更轻
- **不像 Phase 61-65 的实装 phase**:无事务边界 / 无 schema / 无失败注入 / 无 §9 守卫扩展;只产文档 finding
- **新模式**:Phase 66 是首个 audit-only phase。后续若再有此类 phase(如 Phase 70+ 的"性能 hotspot audit" / "security 配置 audit"),可复用 Phase 66 的 5 块拆 + 4 类 finding + 跳过清单 + review 分轮模式

## 与 INVARIANTS 的对照(本 phase 不触动)

| INVARIANTS 条目 | Phase 66 触动方式 |
|----------------|----------------|
| P1(Control)/ P2(SQLite-primary truth)/ §0 第 4 条(apply_proposal 入口)/ §4 LLM 调用契约 / §5 写权限矩阵 / §7 集中化函数 / §8 单用户基线 / §9 不变量守卫 | **零触动**。audit 只盘点不修;若 finding 涉及 INVARIANTS 一致性问题(如某硬编码字面量违反 §7 集中化),标 `[high]` 进 backlog,但 Phase 66 不修;后续清理 phase 处理 |

## 与 DATA_MODEL.md 的对照(本 phase 不触动)

| DATA_MODEL 条目 | Phase 66 触动方式 |
|----------------|-----------------|
| §3 Schema / §4 写入入口 + 白名单 / §5 跨命名空间引用 / §6 文件系统约束 / §7 ID + Actor / §8 Migration / §9 文档接口 | **零触动**。audit 不评判物理存储设计;若 finding 涉及 DATA_MODEL 一致性,同上策略 |

## Model Review Gate

**默认 skipped**(per kickoff + design_decision):
- 不触动 INVARIANTS / DATA_MODEL / SELF_EVOLUTION
- 不涉及 schema / CLI/API surface / state transition / truth write path / provider routing policy
- 风险矩阵无 ≥ 7 项
- read-only,scope 与风险都低

`docs/active_context.md` 的 model_review 段记录:
```markdown
model_review:
- status: skipped
- artifact: none
- reason: read-only audit phase, no high-risk trigger (no INVARIANTS/DATA_MODEL/schema/state-transition impact, max risk score = 4)
```
