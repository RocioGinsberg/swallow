---
author: claude
phase: 61
slice: pr-review
status: draft
depends_on:
  - docs/plans/phase61/design_decision.md
  - docs/plans/phase61/risk_assessment.md
  - docs/plans/phase61/design_audit.md
  - docs/plans/phase61/consistency_report.md
  - docs/design/INVARIANTS.md
---

## TL;DR

Phase 61 (apply_proposal 入口落地) 实现与 design_decision §A–§G 完全对齐,§E 表 9 处主写入 caller 全部收敛、7 处派生写入按设计豁免;§G 高风险 save+apply 配对(R8)实测保留;3 条 INVARIANTS §9 守卫测试落地、AST 扫描精度足够;`tests` 543 passed + Meta-Optimizer eval pass。整体可放行。共 6 项 [CONCERN]、0 项 [BLOCK];主要遗留是 closeout 期文档增量与提交粒度卫生问题,均不阻塞合并。

# Phase 61 Review Comments

## 一、Review 范围与方法

- **被 review 提交**:
  - `c2d4abb feat(governance): add apply_proposal canonical boundary` (M1)
  - `e54f7a3 feat(governance): route metadata apply_proposal boundary` (M2)
  - `b7f0ecf test(orchestration): relax subtask timeout timing assertion` (M3 测试 + 子任务 timing 杂项)
  - `e48bf9b feat(governance): policy apply_proposal boundary` (M3 src)
  - `3dc9d93 docs(governance): policy and concern` (active_context + concerns_backlog 同步)
- **设计基线**:`design_decision.md (revised-after-audit)` §A–§G、`kickoff.md`、`risk_assessment.md (revised-after-audit)` R1–R9、`design_audit.md`、`docs/design/INVARIANTS.md` §0 #4 / §5 / §9
- **辅助**:`consistency_report.md`(本轮 consistency-checker subagent 产出,见 docs/plans/phase61/consistency_report.md)
- **测试**:`.venv/bin/python -m pytest tests/test_governance.py tests/test_invariant_guards.py` 8 passed;`.venv/bin/python -m pytest tests/eval/test_eval_meta_optimizer_proposals.py -m eval` 1 passed;`.venv/bin/python -m pytest` 543 passed, 8 deselected

---

## 二、Checklist

### 1. 与 design_decision §A 函数签名一致性

- [PASS] `apply_proposal(proposal_id: str, operator_token: OperatorToken, target: ProposalTarget) -> ApplyResult` 与 SELF_EVOLUTION §3.1 三参数版本一致(`src/swallow/governance.py:174-199`)
- [PASS] 内部三步流程 load → validate → dispatch 完整,`_emit_event` 在 dispatch 后调用

### 2. 与 design_decision §B `OperatorToken` 字段定义一致性

- [PASS] `OperatorToken` dataclass(frozen=True)只包含 `source` + `reason: str | None = None`,**未**新增 design_audit 中提到的 `actor` 字段(`src/swallow/governance.py:36-50`)
- [PASS] `source` Literal 三值精确匹配:`"cli"` / `"system_auto"` / `"librarian_side_effect"`
- [PASS] `__post_init__` 在 source 非法时抛 `ValueError`,`tests/test_governance.py::test_operator_token_rejects_invalid_source` 验证
- [PASS] Librarian 侧效路径(`orchestrator.py:506`)使用 `OperatorToken(source="librarian_side_effect")`,Orchestrator 内部 task knowledge-promote 路径(`orchestrator.py:2966`)使用 `OperatorToken(source="cli")`,符合 §B 决策

### 3. 与 design_decision §E 表收敛清单一致性(R5 缓解)

§E 表共列 16 个写入位点,标 YES 者必须收敛、标 NO 者必须保留原状。逐项核对:

| # | 文件:函数 | §E 标记 | 实际状态 | 状态 |
|---|----------|---------|---------|------|
| 1-2 | `cli.py` stage-promote (persist_wiki / append_canonical) | YES, source="cli" | `cli.py:2333-2340` register + apply | [PASS] |
| 3-4 | `cli.py` stage-promote 派生 | NO(豁免) | 由 governance `_refresh_canonical_derivatives` 内部刷新 | [PASS] |
| 5 | `cli.py:2493 → 2504` route weights apply | YES | `register_route_metadata_proposal` + apply | [PASS] |
| 6 | `cli.py:2560 → 2575` route capabilities update | YES | 同上 | [PASS] |
| 7 | `cli.py:2465 → 2471` audit policy set | YES | `register_policy_proposal` + apply | [PASS] |
| 8-9 | `orchestrator.py:498-499 → 498-506` Librarian 侧效 | YES, source="librarian_side_effect" | register + apply | [PASS] |
| 10-11 | `orchestrator.py:2664-2667 → 2666/2669` 任务启动派生 | NO(豁免,§E BLOCKER 1 解决方案) | 仍直接调 `save_canonical_registry_index` / `save_canonical_reuse_policy` | [PASS] |
| 12 | `orchestrator.py:2956 → 2966` task knowledge-promote 主写入 | YES, source="cli" | register + apply | [PASS] |
| 13-14 | `orchestrator.py:2963-2965 → 2973/2975` 同流派生 | NO(豁免) | 仍直接调,符合设计 | [PASS] |
| 15-16 | `meta_optimizer.py:1380/1387 → 1164/1169` save_route_weights / save_route_capability_profiles | YES | `apply_reviewed_optimization_proposals()` 内部改 register + apply | [PASS] |

**绑定证据**:`grep -n "apply_proposal\|register_*_proposal" src/` 输出与上表一致;`tests/test_invariant_guards.py` 全 PASS,无 caller 残留。

### 4. 与 design_decision §F 批量 apply schema 适配一致性(BLOCKER 2 解决方案)

- [PASS] `apply_reviewed_optimization_proposals(base_dir, review_path)` 公开签名保留(`meta_optimizer.py:1158`),向后兼容
- [PASS] 函数内部退化为 governance wrapper:`register_route_metadata_proposal(review_path=...) → apply_proposal(target=ROUTE_METADATA, source="cli")`,避免循环 N 次 apply 引入的事务性陷阱(R7)
- [PASS] CLI `swl proposal apply`(`cli.py:2427-2441`)自行构造 review record proposal 并 apply,**不**经 `apply_reviewed_optimization_proposals()`,与 §F 设计意图一致(governance 层是唯一真实入口,`apply_reviewed_optimization_proposals` 只是兼容 wrapper)
- [PASS] `_load_proposal_artifact` 通过 `_PENDING_PROPOSALS` 模块级 dict 完成 schema 适配(register-then-apply 模式),设计 §F "governance 层做适配,不强制 Meta-Optimizer 改造为单条 proposal" 落地

### 5. 与 design_decision §G save+apply 配对一致性(R8 高风险项)

R8 是 Phase 61 唯一高风险项(等价性破坏点)。

- [PASS] `_apply_route_review_metadata`(`governance.py:517-525`)严格保留四步顺序:`save_route_weights → apply_route_weights → save_route_capability_profiles → apply_route_capability_profiles`
- [PASS] `_apply_route_metadata` 直接路径(`governance.py:274-281`)在 route_weights 注册时也保持 save+apply 配对;capability_profiles 同样
- [PASS] `tests/test_governance.py::test_apply_route_metadata_proposal_saves_and_refreshes_registry` 通过断言 `route.quality_weight == 0.42` / `route.task_family_scores["execution"] == 0.81` 验证内存确实被刷新——这是 R8 的关键 sentinel 检验
- [PASS] Meta-Optimizer eval(`tests/eval/test_eval_meta_optimizer_proposals.py`)实测通过(R2 残余风险闭环)

### 6. 与 INVARIANTS §9 三条守卫测试一致性

- [PASS] `test_canonical_write_only_via_apply_proposal` 实装(`tests/test_invariant_guards.py:51-62`),AST 扫描 `append_canonical_record` / `persist_wiki_entry_from_record`
- [PASS] `test_route_metadata_writes_only_via_apply_proposal` 实装(同文件:64-73),扫描 `save_route_weights` / `save_route_capability_profiles`
- [PASS] `test_only_apply_proposal_calls_private_writers`(聚合)实装(同文件:76-101),覆盖 5 个主写入函数
- [PASS] 守卫扫描限定为 `SRC_ROOT = REPO_ROOT / "src" / "swallow"`,自动豁免 `tests/`,符合 §E 与 R3 缓解
- [PASS] AST 扫描节点限定为 `ImportFrom` + `Call`(`func.id` / `func.attr`),`mock.patch("module.fn")` 字符串形式不会误判(R3 残余风险闭环)
- [PASS] 白名单与 §E 表精确匹配:canonical 主写入 = `{governance.py, store.py, knowledge_store.py}`;route 主写入 = `{governance.py, router.py}`;policy 主写入 = `{governance.py, consistency_audit.py}`(聚合测试合并)

### 7. 与 INVARIANTS §0 第 4 条 / §5 矩阵一致性

- [PASS] §0 第 4 条要求"canonical knowledge / route metadata / policy 三类对象的写入必须经 `apply_proposal()` 唯一入口"——本 phase 实现实质性达成,§5 矩阵的三类系统级 truth 写入全部由 governance.py 出口保护
- [PASS] §5 矩阵 `route` 列:`save_route_weights` / `save_route_capability_profiles` 收敛,`apply_route_*` 内存刷新继续配对(§G);`task` 列(harness per-task)按 §C 维持原状,边界清晰
- [PASS] §5 矩阵 `policy` 列:`save_audit_trigger_policy` 收敛,harness 5 个 task-scoped derived 函数(§C)继续 task-level 治理,与系统级 `policy_records` 不混淆

### 8. 与 design_decision §C / §D 边界一致性

- [PASS] §C harness 5 函数(`save_route` / `save_knowledge_policy` / `save_retry_policy` / `save_stop_policy` / `save_execution_budget_policy`)未纳入收敛——`grep -n "from .governance" src/swallow/harness.py` 无匹配,边界保持
- [PASS] §D Repository 抽象层不实装,governance 直接调 store 函数;DATA_MODEL §4.1 描述的 `_promote_canonical` / `_apply_metadata_change` / `_apply_policy_change` 私有方法本轮不存在,守卫测试改为扫描 store 函数名(consistency_report 已记录此偏离)

### 9. Phase 49 concern 消化质量

- [PASS] `cli.py:2715` 把 `task knowledge-promote --target canonical` 的 `caller_authority` 设为 `OPERATOR_CANONICAL_WRITE_AUTHORITY`(即 `"operator-gated"`),与 stage-promote 的 Wiki 写入 authority 语义统一
- [PASS] `knowledge_review.py:9-12` 新增 `CANONICAL_PROMOTION_DECISION_AUTHORITIES` 集合,decision 层同时接受 `LIBRARIAN_MEMORY_AUTHORITY` 与 `OPERATOR_CANONICAL_WRITE_AUTHORITY` —— 既消化 concern,又保持 Librarian agent 自动 promotion 路径不破坏
- [PASS] `tests/test_cli.py:1334` 断言更新为 `"operator-gated"`,验证从端到端
- [PASS] `docs/concerns_backlog.md` Phase 49 entry 移入 Resolved 表,消化 phase 注明 "Phase 61 / M3"

### 10. 测试覆盖

- [PASS] 8 governance / guard 单元测试全 PASS
- [PASS] Meta-Optimizer eval baseline 等价(R2 闭环)
- [PASS] 全量 `pytest` 543 passed, 8 deselected
- [PASS] `test_apply_canonical_proposal_writes_registry_wiki_and_derivatives` 同时覆盖 `wiki_entry / canonical_registry / canonical_registry_index / canonical_reuse_policy` 四步写入顺序与 `applied_writes` 元组准确性
- [PASS] `test_apply_route_metadata_proposal_saves_and_refreshes_registry` 通过 `route.quality_weight` 实物断言确认 save+apply 配对(R8 sentinel)

### 11. Phase scope 自检

- [PASS] 4 slice 全部在 kickoff §goals G1–G5 范围内
- [PASS] 未触及 kickoff §non-goals(Repository 完整层、14 条剩余守卫、CLI 命令重命名、migration 路径、harness per-task、`orchestrator.py:2664-2667`)
- [PASS] 未引入 `[SCOPE WARNING]`
- [PASS] CLI 用户视角无变化(命令名、参数、输出格式不变)

### 12. b7f0ecf 提交粒度卫生

- [CONCERN] `b7f0ecf` 的 commit message 是 "test(orchestration): relax subtask timeout timing assertion",但实际 diff 包含 4 类改动:(a) `tests/test_run_task_subtasks.py` 子任务 timing 1.35→1.75 放宽(message 描述的);(b) `tests/test_governance.py` 新增 `test_apply_policy_proposal_saves_audit_trigger_policy`(M3 范围);(c) `tests/test_invariant_guards.py` 新增聚合守卫 `test_only_apply_proposal_calls_private_writers`(M3 范围);(d) `tests/test_cli.py:1334` 把 caller_authority 断言从 `canonical-promotion` 改为 `operator-gated`(Phase 49 concern 消化测试侧)。后三类是 M3 测试,本应进入 `e48bf9b` (M3 src) 或单独的 `test(governance)` 提交,放在一个 message 里只描述子任务 timing 的提交里会让 git history 难以反向追溯 M3 测试的来源。
  - **影响**:文档/git 历史可读性,不影响功能
  - **建议**:本轮不强制 amend(不阻塞合并);提醒 Codex 后续遵守 commit message 与 diff 范围一致的纪律(`.agents/codex/rules.md` 中的"提交粒度"项)

### 13. concerns_backlog Open 表清理不完整

- [CONCERN] `docs/concerns_backlog.md` Open 表仍保留 "Meta Docs Sync / Roadmap audit (closeout)" 那条 concern,内容是"INVARIANTS §0 第 4 条以及 ARCHITECTURE / STATE_AND_TRUTH / EXECUTOR_REGISTRY / INTERACTION 等 7+ 处把 `apply_proposal()` 定义为唯一入口...... `grep -rn "apply_proposal" src/ tests/` 零匹配......"。这正是 Phase 61 要消化的根因 concern,本 phase 已经实装 `apply_proposal()` + 3 条守卫测试,该 entry 应移入 Resolved 表。M3 docs commit `3dc9d93` 只移动了 Phase 49 那条,遗漏了 Roadmap audit 那条。
  - **建议**:closeout 时由 Codex 把 Open 表 "Meta Docs Sync / Roadmap audit (closeout)" 那行移入 Resolved,消化 phase 标 "Phase 61",消化方式标 "实装 `apply_proposal()` + 3 条 INVARIANTS §9 守卫测试,代码与 INVARIANTS §0 第 4 条对齐"
  - **影响**:concerns_backlog 完整性,review hygiene

### 14. design_decision §E 表行号偏移(closeout 文档同步)

- [CONCERN] design_decision §E 精确清单(line 163-181)援引 `orchestrator.py:2664` / `orchestrator.py:2667` 为不收敛的派生写入位置,但 M1/M2 提交后实际 `save_canonical_registry_index` 在 `orchestrator.py:2666`、`save_canonical_reuse_policy` 在 `orchestrator.py:2669`(偏移 +2)。语义完全吻合,但文档行号陈旧。
  - **建议**:closeout 时由 Codex 一次性更新 §E 表行号到当前实际值;或在 design_decision 末尾追加"行号注释"小节注明此偏移在合并后已发生
  - **影响**:文档可追溯性,不影响代码正确性

### 15. closeout 期文档增量(design 自我承诺,部分自我修正)

design_decision 在多处承诺 closeout 时同步设计文档,但 review-second-pass 发现其中两条违反"设计文档不携带实现叙事"的宪法级原则,需自我修正。

**保留**:
- §B 末尾:SELF_EVOLUTION §3.1.1 增加 `"librarian_side_effect"` source 条目 — design-level 增量(描述允许的 source 值集合扩展),无 phase 号 / 日期 / 实现状态描述,合规
- §F 末尾:SELF_EVOLUTION §3.1 增加"proposal_id 可指向 review record(批量 proposal 容器)"注解 — design-level 增量,合规

**撤回**(本条 review 自我修正):
- ~~§A 末尾:DATA_MODEL §4.1 两参数签名偏离声明~~ — 仅 signature 三参数化更新本身合规;**不**应在 DATA_MODEL 中加入"两参数草案不再作为实现目标"这种实现叙事
- ~~§D 末尾:DATA_MODEL §4.1 守卫扫描目标偏离声明(基于 phase-specific 物理函数名)~~ — design 文档不应引入 phase 号 / 日期 / "尚未实装"等实现状态描述;Codex 在 closeout 时已添加该段,经 Human 复核后已**整段回退**,DATA_MODEL §4.1 仅保留 signature 三参数化更新与原 CI 守卫描述

- [CONCERN][SELF-CORRECTED] 原本 review 推荐的"DATA_MODEL §4.1 偏离声明"会把实现叙事(phase 号 / 日期 / `尚未实装` / phase-specific 物理 writer 函数名)嵌入设计文档,违反"设计文档只描述设计真值,不携带实现细节"的宪法级原则。Human 已指出该问题,DATA_MODEL §4.1 已回退到只保留 signature 三参数化(2 → 3 param)。SELF_EVOLUTION 的两处增量保持(都是 design-level 语义增加)。
  - **教训**:Claude 在 review 阶段提出 closeout 文档 TODO 时,必须先核对该 TODO 是否会破坏 design / phase plan 的边界。design 文档(`docs/design/*.md`)只表达"系统的设计真值是什么";phase 实现状态、版本节点、偏离叙事一律放在 phase plan(`docs/plans/<phase>/*.md`)与 active_context
  - **closeout 实际状态**:SELF_EVOLUTION 两处增量已落地;DATA_MODEL §4.1 已回退到只更 signature(三参数化);design_decision §E 表行号刷新落在 phase plan,合规
  - **后续提示给 Codex**:closeout.md 中提及的 "Concern 15 — DATA_MODEL §4.1 Phase 61 签名与守卫扫描目标说明" 描述需同步更新,只保留 signature 三参数化部分,删除"守卫扫描目标说明"那一项(因为该项已被回退)

### 16. 14 条剩余 INVARIANTS §9 守卫测试

- [CONCERN] kickoff §non-goals 明确不实装另外 14 条 §9 守卫测试,本 phase closeout 应作为单独 Open 项登记。当前 `concerns_backlog.md` 未见此 entry。
  - **建议**:closeout 时新增 Open 条目 "INVARIANTS §9 剩余 14 条守卫测试缺失",消化时机注 "后续单独 phase";同时新增 "DATA_MODEL §4.1 完整 Repository 抽象层" Open 条目(本轮采用最小封装)与 "Meta-Optimizer 批量 apply 的事务性回滚机制"(R7 backlog 项)

### 17. `_PENDING_PROPOSALS` 模块级 dict 生命周期(consistency_report NOT_COVERED 1)

- [CONCERN] `governance.py:88` 的 `_PENDING_PROPOSALS` 模块级全局 dict 在 `apply_proposal` 调用后**不**自动清除已 register 的 proposal。设计文档未涉及清理语义。当前测试都用独立 `tmp_path`,未覆盖长 process 单例累积场景。同 `proposal_id` 第二次 register 会静默覆盖。
  - **影响**:CLI 单进程多次调用场景下内存缓慢增长(每次大约 1 个 dataclass);多线程暂无,因为 swallow CLI 走 asyncio 单线程主路径
  - **建议**:作为 Repository 实装 phase 的同类设计点(durable proposal artifact 层落地后,这个 in-memory 注册表会被替换),不在本 phase 内修复

### 18. `_apply_route_review_metadata` 验证-写入循环分离(consistency_report NOT_COVERED 2)

- [NOTE] `governance.py:326-348` 先做一次"仅校验,不写值"的 approved_entries 循环,第二次循环 `governance.py:355-510` 才执行实际写入。这是从原 `apply_reviewed_optimization_proposals` 迁移过来的逻辑结构,设计 §F 没有要求改造,本 phase 维持等价
  - **影响**:逻辑可读性轻微下降;不影响正确性
  - **建议**:不在本 phase 处理,后续 Repository 层重构时可以合并这两个循环

---

## 三、Branch Advice

- 当前分支:`feat/phase61-apply-proposal`
- 建议操作:**进入 closeout** —— 在 Codex 完成下列 closeout 任务后开 PR
- 理由:实现已通过 design 一致性检查与全量回归;唯一未达成的合并条件是 closeout 文档增量(条目 13–16),不属于实现范畴
- closeout 必做(经 review-second-pass 修订):
  1. concerns_backlog Open 表移除"Meta Docs Sync / Roadmap audit"那行,移入 Resolved(条目 13)
  2. concerns_backlog 新增 3 条 Open 条目:14 条剩余 §9 守卫、Repository 完整层、apply 事务性回滚(条目 16)
  3. SELF_EVOLUTION §3.1.1 增补 `"librarian_side_effect"` source(条目 15,design-level 合规)
  4. SELF_EVOLUTION §3.1 增补"proposal_id 可指向 review record(批量 proposal 容器)"注解(条目 15,design-level 合规)
  5. DATA_MODEL §4.1 仅做 signature 三参数化更新(2 → 3 param);**不**加入 phase-specific 偏离声明 / 实施说明(条目 15 自我修正)
  6. design_decision §E 表行号刷新到当前实际值(条目 14,phase plan 范围,合规)
- 建议 PR 范围:整个 `feat/phase61-apply-proposal` 分支单 PR 合入 `main`,4 个 slice 均为 architectural fix,拆 PR 反而增加 review 难度(与 kickoff Branch Advice 一致)

---

## 四、CONCERN 汇总(供 backlog 同步)

| # | 类型 | 描述 | 消化时机 |
|---|------|------|---------|
| 12 | 提交粒度卫生 | `b7f0ecf` commit message 与 diff 范围不一致(M3 测试被混入子任务 timing 提交) | 提醒 Codex 后续遵守 commit message 纪律,本轮不强制 amend |
| 13 | concerns_backlog 不完整 | "Meta Docs Sync / Roadmap audit" Open 条目未移入 Resolved | Phase 61 closeout |
| 14 | design 行号陈旧 | §E 表行号 2664/2667 实际为 2666/2669 | Phase 61 closeout |
| 15 | 设计文档增量(部分自我修正) | SELF_EVOLUTION §3.1.1 / §3.1 增量 → 已落地(design-level,合规);DATA_MODEL §4.1 仅保留 signature 三参数化,"偏离声明 / Phase 61 实施说明" 已回退(原 review 推荐违反"设计文档不携带实现叙事"原则,自我修正) | 已在 review-second-pass 处理 |
| 16 | 后续 backlog 未登记 | 14 条 §9 守卫 / Repository 完整层 / apply 事务性回滚 未进 Open 表 | Phase 61 closeout |
| 17 | governance in-memory 注册表生命周期 | `_PENDING_PROPOSALS` 不清理,长 process 内存累积 | Repository 实装 phase 顺带消化 |

---

## 五、最终结论

**[ACCEPT WITH CLOSEOUT TODO]**

实现质量高,与 design_decision §A–§G 完全对齐;高风险项(R8 save+apply 配对、R2 Meta-Optimizer eval 等价)实测通过;3 条守卫测试落地。共 6 条 [CONCERN] 全部为 closeout / 文档卫生层,**0 [BLOCK]**,可批准合并。closeout 阶段必须完成上文 "Branch Advice / closeout 必做" 6 项,否则不应进入 phase merge gate。
