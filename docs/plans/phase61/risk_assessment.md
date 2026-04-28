---
author: claude
phase: 61
slice: risk_assessment
status: revised-after-audit
depends_on:
  - docs/plans/phase61/kickoff.md
  - docs/plans/phase61/design_decision.md
  - docs/plans/phase61/design_audit.md
  - docs/plans/phase61/context_brief.md
---

## TL;DR

Phase 61 的核心风险集中在三处:(1)Librarian 侧效路径 OperatorToken 设计是否污染 SELF_EVOLUTION §3.1 语义;(2)Meta-Optimizer eval 在 caller 替换后是否等价;(3)守卫测试的静态扫描粒度与测试代码豁免边界。整体风险中等。**本稿已根据 design audit 反馈修订**,补充 R7(批量 apply 事务性)/ R8(内存刷新配对)两个原稿遗漏的实施风险,并重排 R5 / R6。

# Phase 61 Risk Assessment

## 一、风险清单(按严重度)

### R1: Librarian 侧效 OperatorToken 设计污染 SELF_EVOLUTION 语义 — **中**

**描述**:design_decision §B 提出扩展 `OperatorToken.source` 第三种值 `"librarian_side_effect"`,处理 `orchestrator.py:498-499` 的 Librarian agent 在 task 执行中产生的 canonical 写入。如果设计不当,这个值会被滥用为"任何非 CLI 写入的兜底",侵蚀 OperatorToken 的核心语义"operator-authorized write"。

**影响**:
- 短期:Phase 61 完成后,审计中 `librarian_side_effect` 来源的 canonical 写入语义清晰,可与 CLI / system_auto 区分
- 长期:若未来其他 agent 也产生类似 side effect 路径,可能继续扩展 source enum,失去枚举的边界意义

**缓解**:
1. 在 `governance.py` 中以 docstring + Literal type 严格限定 `OperatorToken.source` 为三个具名值,新增需经 design phase 审批
2. 守卫测试 `test_canonical_write_only_via_apply_proposal` 同步断言:Librarian 侧效路径的 caller 必须在调用 `apply_proposal` 之前显式构造 `OperatorToken(source="librarian_side_effect")`,不允许 Librarian agent 直接传 `source="cli"`
3. 在 closeout 中将 `OperatorToken.source` 三值的语义边界作为文档增量,提示在 SELF_EVOLUTION.md §3.1 增加该 source 的描述

**残余风险**:design audit 阶段 `design-auditor` 可能挑战该设计,要求 Librarian 走完整 staged review 流程。如果挑战成立,Phase 61 范围扩大;最坏情况 Librarian 路径无法在本 phase 收敛,需要单独后置 phase 处理。

---

### R2: Meta-Optimizer eval 在 caller 替换后行为漂移 — **中**

**描述**:`apply_reviewed_optimization_proposals()`(`meta_optimizer.py:1380-1387`)是 route weight / capability profile 应用的核心函数。S3 把它内部的 `save_route_weights` / `save_route_capability_profiles` 调用替换为 `apply_proposal()`,虽然语义等价,但可能引入序列化时机 / 错误处理顺序 / 副作用顺序 / 事件 emit 时机的微妙差异,在 `tests/eval/test_eval_meta_optimizer_proposals.py` 中暴露为 eval output 不等价。

**影响**:
- 该 eval 是 Meta-Optimizer proposal 应用正确性的高层保证;若不等价,意味着 governance 层引入了非透明语义,phase 不可声明完成
- proposal 应用是 SELF_EVOLUTION 的主链路,任何漂移都会直接影响系统自我进化能力

**缓解**:
1. **S3 实施前打 baseline**:在 S3 开始前,运行一次 `tests/eval/test_eval_meta_optimizer_proposals.py` 并保存输出快照(JSON 或 stdout)
2. **S3 完成后对比 baseline**:用 `git stash` + 重跑或 fixture 对比的方式,确保输出完全一致
3. **`_apply_route_metadata()` 内部实现要求等价**:
   - 调用顺序与原 `apply_reviewed_optimization_proposals()` 内部一致(先权重,后能力画像)
   - 错误抛出位置一致
   - 事件 emit 与状态更新顺序一致
4. **Review checkpoint M2 重点审视**:由 Claude 在 review_comments 中明确列出 "Meta-Optimizer eval baseline 对比" 项,Human 在 M2 milestone 必须确认通过

**残余风险**:eval 用的是固定 fixture,真实生产 Meta-Optimizer 行为复杂度高于 fixture 覆盖;若漂移在 fixture 范围外,需要后续 phase 通过真实数据回归发现。

---

### R3: 守卫测试静态扫描粒度与测试代码豁免 — **中**

**描述**:design_decision §一/§S2/§S3 提出守卫测试基于 AST + 文件白名单实现,断言"除 governance.py / store.py 外,无文件直接调用 `append_canonical_record` 等私有 writer"。

实施挑战:
- **测试代码豁免**:`tests/` 中的单元测试经常直接调底层 store 函数构造 fixture(例如 `tests/test_canonical_registry.py` 直接调 `append_canonical_record` 来填充测试数据)。守卫测试不能简单"任何文件不允许 import private writer",否则测试代码自身违反守卫
- **mock / patch 检测**:测试用 `mock.patch("swallow.store.append_canonical_record")` 形式不构成实际调用,但 AST 扫描可能误判
- **粒度选择**:文件级白名单(governance.py + store.py + 测试目录)够粗,可能漏检 `src/` 中的违反;函数级白名单细致但实施复杂

**影响**:
- 守卫测试假阳:阻塞 PR
- 守卫测试假阴:让违反 INVARIANTS 的 caller 通过守卫——这才是真正危险的情况(invariant 名存实亡)

**缓解**:
1. **明确豁免规则**(写入守卫测试 docstring):
   - `tests/` 整目录豁免(测试代码可以构造 fixture)
   - `governance.py` 豁免(governance 是入口本身)
   - `store.py` / `knowledge_store.py` / `router.py` 等底层模块豁免(它们定义私有 writer,但 caller 不应是这些文件本身,否则形同虚设——见后)
   - 任何其他 `src/` 下文件 import / 调用受保护 writer 视为违反
2. **AST 检测精度**:用 `ast.NodeVisitor` 扫描 `Import` / `ImportFrom` / `Call` 节点;`mock.patch("module.fn")` 不会进入这三类节点,自然豁免
3. **底层模块自调豁免**:`store.py` 内部 `save_canonical_registry_index()` 调 `_write_json()` 等内部辅助函数是合法的;只断言"非底层模块" import 受保护 writer。这一点在测试 docstring 中明确
4. **守卫测试自身有测试**:在 `tests/test_invariant_guards_meta.py`(可选)中故意写一个违反样本,确认守卫能捕获;再删除样本,确认守卫不假阳

**残余风险**:AST 扫描是静态检测,无法捕获动态 import / `getattr` / `eval` 路径;但项目代码风格不使用动态 import,实际风险低。

---

### R4: harness.py per-task 派生配置边界判定被 design audit 挑战 — **中**

**描述**:design_decision §C 把 `harness.py` 中 `save_route` / `save_knowledge_policy` / `save_retry_policy` / `save_stop_policy` / `save_execution_budget_policy` 5 个函数判定为"task-scoped 派生配置",不纳入 apply_proposal 收敛。

判定理由:它们写入 `task_records` / `state` 的字段而非 `policy_records` 表。但函数命名带"policy",可能在 design audit 时被认为应纳入。

**影响**:
- 若 design-auditor 不认同,phase 范围需扩展 1 个 slice(S5),增加约 20% 工作量
- 若实施后才被认定为问题,需要在 closeout 时作为 concern 登记或直接补 slice

**缓解**:
1. **design audit 阶段主动提示**:在派给 `design-auditor` 的 prompt 中明确列出 §C 决策,要求审计员特别评估
2. **代码层面准备应急**:`apply_proposal()` 的 dispatch 设计支持后续扩展 `ProposalTarget.TASK_DERIVED_POLICY`(若需要),无需重写
3. **closeout 登记**:无论本轮是否纳入,在 closeout 中明确"harness 5 个函数的边界判定"已被讨论 + 决策结果

**残余风险**:边界判定本质是设计选择,没有客观标准。若 Human 在 design gate 持不同意见,Phase 61 范围实质改变。

---

### R5: 跨 4 文件 + 11 caller 的同质重构 regression — **中**

**描述**:虽然每个 caller 的改动是同质的(构造 OperatorToken + 调 apply_proposal),但分布在 4 个核心文件(`cli.py` / `orchestrator.py` / `meta_optimizer.py` / `governance.py`)+ 11 处具体位置,改动量约 200-300 行(改动 caller + 新建 governance + 新建守卫测试)。

regression 来源:
- 错传 `target` 类型(canonical caller 误传 ROUTE_METADATA)
- 错传 `source` 值(Librarian 侧效路径误用 CLI source)
- proposal artifact 加载逻辑 bug
- event_log 写入时机错位

**影响**:中等改动面;现有功能测试覆盖 cli / orchestrator / meta_optimizer / librarian 应该可以捕获大部分 regression,但事件顺序 / 审计字段类的 regression 测试覆盖较弱。

**缓解**:
1. **slice 内部分组提交**(S2 已经规定按 caller 文件分组)
2. **每组提交后跑相关测试**:
   - `cli.py` 改动后:`tests/test_cli.py`
   - `orchestrator.py:2664-2667` 改动后:`tests/test_orchestrator.py::test_task_knowledge_promote_*`
   - `orchestrator.py:498-499` 改动后:`tests/test_librarian_executor.py`
   - `meta_optimizer.py` 改动后:`tests/test_meta_optimizer.py` + `tests/eval/test_eval_meta_optimizer_proposals.py`
3. **`consistency-checker` subagent 在 S2 / S3 完成后跑一次**:对比 governance.py 实现与 SELF_EVOLUTION §3.1 设计,确保签名 / 行为一致(consistency-checker 是高风险 slice 的标配)

**残余风险**:event_log 顺序 / 审计字段格式如果有 regression,在 fixture 测试中可能不暴露,需要 manual review 或后续真实使用发现。

---

### R6: 设计文档(SELF_EVOLUTION §3.1.1 / §3.1)需在 closeout 增量更新 — **低**

**描述**:design_decision §B 决定扩展 `OperatorToken.source` 第三种值;§F 决定 `proposal_id` 可指向 review record(批量 proposal 容器)。SELF_EVOLUTION.md §3.1.1 当前只列两种 source 值,§3.1 假设 `proposal_id` 是单条 proposal artifact 的标识。本轮代码追文档,但需要在 closeout 时同步增量更新 SELF_EVOLUTION,否则下一个读 SELF_EVOLUTION 的人会再次发现"设计 vs 代码漂移"——讽刺的是,本 phase 就是为了消除这种漂移。

DATA_MODEL.md §4.1 描述守卫测试基于 Repository 私有方法名;本轮守卫扫描 store 函数名(§D 偏离声明)。同样需在 Repository 实装 phase 文档同步。

**影响**:文档维护层面,不影响代码正确性,但若忘记更新,下一轮 design audit 会再次抓到。

**缓解**:
1. closeout 模板包含"设计文档增量更新"小节,显式列出 3 处:SELF_EVOLUTION §3.1.1(增加 librarian_side_effect)/ §3.1(proposal_id 可指向 review record)/ DATA_MODEL §4.1(Repository 实装 phase 时更新)
2. 本风险在 risk_assessment 中显式列出,作为 closeout 必检项

---

### R7: Meta-Optimizer 批量 apply 的事务性 — **中**(audit 补遗)

**描述**:`apply_reviewed_optimization_proposals()` 处理 N 个 approved entries:统一计算 `updated_weights` / `updated_profiles`,最后一次性调用 `save_route_weights → apply_route_weights → save_route_capability_profiles → apply_route_capability_profiles`。当前代码记录 `rollback_weights` / `rollback_capability_profiles` 字段,但**不执行**实际回滚。

S3 把这一系列调用迁移到 `_apply_route_metadata()` 内部,理论上保持相同的写入顺序与失败行为。但有两个潜在问题:
1. 第一次 `save_route_weights` 成功并调用 `apply_route_weights`(内存刷新)后,第二步 `save_route_capability_profiles` 失败 → 系统进入"权重已更新但 profile 未更新,内存权重已生效但 profile 内存未刷新"的不一致状态
2. governance 层 `_emit_event()` 在 `_apply_route_metadata()` 完成后调用,如果中途失败 event 不会写入,审计层缺失记录

**影响**:本身不是 phase61 引入的新风险——当前代码也有这个问题。但本 phase 的"governance 唯一入口"语义会让人误以为 governance 提供了原子保证,实际并未提供。

**缓解**:
1. **不在 phase61 范围内修复事务性**:design_decision §G 已声明"不实施运行时事务回滚",登记为后续 backlog
2. **保持现状等价**:`_apply_route_metadata()` 内部失败行为与原 `apply_reviewed_optimization_proposals()` 完全一致(同样不回滚,同样抛错)——等价性是验收条件
3. **在 governance.py docstring 中明确警示**:`apply_proposal()` 不提供事务性保证;批量 proposal 的部分应用失败需要 operator 手动处理
4. **closeout backlog 登记**:"apply 事务回滚机制"作为新 Open 项,描述其与 INVARIANTS 的关系("INVARIANTS §5 矩阵约束的是写入边界,事务性是次级要求")

**残余风险**:operator 在 review 后 apply,中途失败时需要手动恢复。当前 fixture 测试覆盖度不足以发现此类边界。

---

### R8: `apply_route_weights` / `apply_route_capability_profiles` 内存刷新配对遗漏 — **高**(audit 补遗)

**描述**:`apply_reviewed_optimization_proposals()` 当前的写入模式是 `save_*` + `apply_*` 配对(后者是内存刷新,确保 process 内 RouteRegistry 单例看到最新状态)。原 design_decision 完全没提 `apply_route_weights` / `apply_route_capability_profiles`——只提 `save_*` 收敛。如果 Codex 仅迁移 `save_*` 而遗漏 `apply_*`,route metadata 持久化但内存不更新,直到下次 process 重启。**这是会让代码"看起来等价但运行不等价"的等价性破坏点**。

**影响**:本 phase 完成条件第 4 条要求"现有功能测试无 regression";但 fixture 测试可能在每个测试用例都重启 RouteRegistry,不会暴露这个 bug。生产环境长 process 才会触发——属于"测试通过但生产坏"的高危场景。

**缓解**:
1. **design_decision §G 已显式处理**:`_apply_route_metadata()` 内部保持完整 save+apply 配对,顺序与原代码一致
2. **consistency-checker subagent 在 M2 milestone 必检**:派 prompt 中明确要求核验 save+apply 配对的存在 + 顺序
3. **手工 review 检查项**:M2 review_comments 中明确列"`_apply_route_metadata()` 是否完整迁移了 save+apply 4 步"作为单独 PASS/CONCERN/BLOCK 项
4. **Meta-Optimizer eval baseline**(R2)是间接信号:如果配对遗漏,eval 中后续路由决策可能基于陈旧权重——但 fixture 单进程内是否暴露不确定

**残余风险**:即使流程性 review 检查到位,代码 review 可能漏掉一行 `apply_route_weights()`——只有运行时 long-process 路由才暴露。**M2 milestone 必须是 BLOCKER,不允许"软通过"**。

---

### R9: 守卫测试的边界判定与底层模块自调豁免 — **低**(audit 反馈细化)

**描述**:audit 指出 `router.py` 同时是 `save_route_weights` 的定义文件和某些操作(如 `apply_route_weights` 内部调 `load_route_weights`)的 caller。守卫测试白名单需要明确"底层 store 文件"的精确列表。

design_decision §E 已给出精确白名单:
- canonical 主写入:`governance.py` / `store.py` / `knowledge_store.py` / `tests/`
- route 主写入:`governance.py` / `router.py` / `tests/`
- policy 主写入:`governance.py` / `consistency_audit.py` / `tests/`

**缓解**:
1. 白名单写入守卫测试 docstring,与 design_decision §E 表保持一致
2. S2 / S3 / S4 实施时,如果发现某个底层文件需要新增到白名单,在 review_comments 中明确报告

**残余风险**:测试代码自身违反守卫的边界——测试代码豁免规则需要清晰,否则单元测试 fixture 构造时会被守卫错误捕获。design_decision §E 已明确 `tests/` 整目录豁免,这一点写入守卫 docstring 即可。

---

## 二、风险等级汇总

| 风险 | 严重度 | 概率 | 综合 |
|------|--------|-----|------|
| R1 Librarian 侧效 source 设计 | 中 | 中 | **中** |
| R2 Meta-Optimizer eval 漂移 | 高 | 低 | **中** |
| R3 守卫测试粒度 | 中 | 低 | **低-中** |
| R4 harness 边界争议 | 中 | 低 | **低-中**(audit §C 已验证站得住) |
| R5 跨文件 regression | 中 | 中 | **中** |
| R6 设计文档增量 | 低 | 中 | **低** |
| R7 批量 apply 事务性(audit 补遗) | 中 | 低 | **中** |
| R8 内存刷新配对(audit 补遗) | **高** | **中** | **高** |
| R9 守卫测试边界(audit 细化) | 低 | 低 | **低** |

**Phase 整体风险等级**:**中-高**(因 R8 提升)。R8 是单点高风险,M2 milestone 必须设置 BLOCKER 级 review。其余风险面广但可控,需要 milestone 评审 + consistency-checker 多次协助。

---

## 三、Eval 必要性评估

按 phase60 模式,本 phase 不需要新建 eval(架构修复,不引入新功能),但 R2 决定了 **`tests/eval/test_eval_meta_optimizer_proposals.py` 是关键回归 sentinel**,在 S3 milestone 必须强制核验。

| Slice | Eval / 回归核验需求 |
|-------|--------------------|
| S1 | 无;纯类型与骨架,unit test 即可 |
| S2 | `tests/test_cli.py` / `tests/test_librarian_executor.py` / `tests/test_orchestrator.py` 全 PASS |
| S3 | **`tests/eval/test_eval_meta_optimizer_proposals.py` baseline 对比通过(强制)** |
| S4 | `tests/test_cli.py::test_audit_*` / `task knowledge-promote` 相关测试全 PASS |

---

## 四、subagent 协助建议

按 phase 风险与 `.agents/workflows/feature.md` 协作流程:

| 时机 | subagent | 目的 |
|------|---------|------|
| **design gate 前**(本轮即将到来) | `design-auditor` | 从实施者视角审计 design_decision,重点评估 §B Librarian 侧效 / §C harness 边界 / §D Repository 不实装 三个决策点 |
| **M1 完成后** | `consistency-checker` | 对比 governance.py 实现与 SELF_EVOLUTION §3.1 设计,确保签名一致 |
| **M2 完成后** | `consistency-checker` | 重点核验 Meta-Optimizer eval baseline + 11 处 caller 收敛完整性 |
| **closeout 前** | `roadmap-updater` | Phase 61 完成登记 + 候选 F 下线 + 候选 E / D 重新评估 |

---

## 五、回滚策略

每个 slice 独立回滚成本:

- **S1 回滚**:删除 `governance.py` + `tests/test_governance.py`,无副作用
- **S2 回滚**:每个 caller 文件改动独立 commit,逐个 revert 即可恢复
- **S3 回滚**:同上;特别是 `meta_optimizer.py` 改动需要先 revert 再确认 eval baseline
- **S4 回滚**:同上

最坏情况(整个 phase 回滚):4 个 slice 的 commits 一并 revert;由于改动同质 + 现有 store 函数未改,回滚后系统回到 phase 开始时的等价状态。

---

## 六、blocker 触发条件

以下任何一条出现,phase 立即停止并升级:

1. design audit 否决 §B Librarian 侧效 source 设计 → 重新设计或后置 Librarian 收敛
2. S3 完成后 Meta-Optimizer eval baseline 不等价 → 暂停,review_comments 标 BLOCK,排查 governance 实现差异
3. 守卫测试假阴(故意构造的违反样本未被捕获) → 守卫测试粒度不足,需要重新设计扫描方案
4. R4 harness 边界争议升级到必须纳入 → phase 范围扩大,重新评估是否拆 phase61a / 61b
