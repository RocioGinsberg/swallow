---
author: claude
phase: 61
slice: design_decision
status: revised-after-audit
depends_on:
  - docs/plans/phase61/kickoff.md
  - docs/plans/phase61/context_brief.md
  - docs/plans/phase61/design_audit.md
  - docs/design/INVARIANTS.md
  - docs/design/SELF_EVOLUTION.md
  - docs/design/DATA_MODEL.md
  - docs/design/INTERACTION.md
---

## TL;DR

实现 `swallow.governance.apply_proposal(proposal_id, operator_token, target) -> ApplyResult` 函数,采用 SELF_EVOLUTION.md §3.1 签名;`OperatorToken.source` 扩展为三种值(`"cli"` / `"system_auto"` / `"librarian_side_effect"`),字段保持 SELF_EVOLUTION §3.1.1 的 `source` + `reason`(无 `actor`);Repository 抽象层不实装,governance 层直接 dispatch 到现有 store 函数;守卫测试通过 AST + 文件白名单实现。本轮拆 4 个 slice,前两个合并为同一 milestone 评审。**本稿为 design audit 后的修订版**,处理 2 BLOCKER + 3 CONCERN + 2 补遗风险。

# Phase 61 Design Decision: `apply_proposal()` 入口函数化

## 一、方案总述

新建 `src/swallow/governance.py` 作为 INVARIANTS §0 第 4 条的代码具现,实现 `apply_proposal()` 函数作为 canonical knowledge / route metadata / policy 三类 truth 写入的唯一入口。函数内部按 `target` 参数 dispatch,直接调用现有 `append_canonical_record` / `save_route_weights` / `save_audit_trigger_policy` 等底层 store 函数,**不**新建完整 Repository 抽象层(DATA_MODEL §4.1 设计意图作为后续 phase 工作)。

收敛范围**严格限定**为 "proposal 应用语义"的写入路径:CLI 触发的 stage-promote / proposal apply / route 配置 / audit policy 等显式 apply 动作,以及 Librarian agent 在 task 执行中的 canonical 侧效。**不收敛**任务启动时的全量索引重建(`orchestrator.py:2664-2667`)、view-only 的索引刷新 RPC——这些是派生缓存的"读取-重建"语义,与"proposal apply"在写入时机和触发条件上不同,守卫测试通过精细的扫描目标列表区分。

详见 §二决策预决与 §三 slice 拆解。

---

## 二、关键设计决策(预决推荐 + audit 修订)

本稿在 design audit 后修订。原 §A / §B / §C / §D 保留并修正,新增 §E / §F / §G 处理 audit 暴露的真实问题。

### A. 函数签名:采用 SELF_EVOLUTION.md §3.1 版本

**分歧背景**:
- SELF_EVOLUTION.md §3.1: `apply_proposal(proposal_id: str, operator_token: OperatorToken, target: ProposalTarget) -> ApplyResult`
- DATA_MODEL.md §4.1: `apply_proposal(proposal_id: str, operator_token: OperatorToken) -> None`(无 `target`)

**预决**:**采用 SELF_EVOLUTION §3.1 版本(包含 `target`)**

**理由**:
1. **类型 dispatch 显式化**:`target` 是显式参数,caller 必须明确意图;若由 proposal 内容隐式推断,意图丢失在数据里,守卫测试无法静态验证 caller 意图
2. **Caller 可读性**:`apply_proposal(proposal_id, token, target=ProposalTarget.CANONICAL_KNOWLEDGE)` 在代码中一眼可见
3. **错误隔离**:caller 传错 target 时,governance 层可以早期校验"target 与 proposal 内容是否一致"
4. **未来扩展**:新增 target 类型只需扩展 enum,不影响现有 caller

**与 DATA_MODEL §4.1 的偏离声明**:本轮签名以 SELF_EVOLUTION §3.1 为准。DATA_MODEL §4.1 的两参数版本不予采纳。这一偏离在本 phase closeout 时作为文档同步项提示给 Human(本 phase 不直接改 DATA_MODEL.md)。

### B. `OperatorToken` 字段:严格遵循 SELF_EVOLUTION §3.1.1,扩展第三种 source

**字段定义**:严格按 SELF_EVOLUTION.md §3.1.1 权威定义,**不添加** `actor` 字段。

```python
@dataclass(frozen=True)
class OperatorToken:
    source: Literal["cli", "system_auto", "librarian_side_effect"]
    reason: str | None = None  # SELF_EVOLUTION 定义为可选,本设计沿用
```

**Source 第三种值 `"librarian_side_effect"`**:

`orchestrator.py:498-499` 的 Librarian agent 侧效路径不是 CLI 触发、不是 auto_low_risk 自动批准,而是 task 执行过程中 Librarian agent 处理 staged knowledge 时产生的 canonical 写入。

`source` 扩展为三种值的理由:
1. **语义独立**:`librarian_side_effect` 明确标识"Librarian agent 在 task 执行中产生的写入",与 `"system_auto"`(operator 配置的自动批准模式)语义分离
2. **审计可读**:`event_log` 中记录 `OperatorToken.source` 时,三种值各有明确含义
3. **守卫测试可断言**:`test_canonical_write_only_via_apply_proposal` 同步断言 "Librarian 侧效路径必须使用 `librarian_side_effect` source"

**命名收敛理由(audit §B 反馈处理)**:`"librarian_side_effect"` 暴露角色名而非触发模式。但当前只有 Librarian agent 这一条非 CLI / 非 system_auto 写路径;其他 specialist(Meta-Optimizer 等)按设计走 staged → review → apply 流程,不直接产生侧效。命名贴合现有具体路径,清晰度优于抽象的 `"agent_side_effect"`。

**未来扩展约束**:在 `governance.py` docstring 中明确写入 "新增 source 值必须经 design phase 审批,不允许在实施 phase 中临时扩展"。如果未来出现第二个 agent 需要类似侧效路径,届时通过新 phase 评估是否(a)保持 enum 形式或(b)抽象为模式名。

**`reason` 必填性**:design audit 指出原稿写"必填"与 SELF_EVOLUTION 不一致。**修订**:沿用 SELF_EVOLUTION 的 `str | None`(可选)。在守卫测试与 audit log 中,如果 `source = "system_auto"` 或 `"librarian_side_effect"`,**强烈建议**(非强制)填写 reason;但不在类型层面强制。

**closeout 文档增量**:本 phase closeout 时在 SELF_EVOLUTION.md §3.1.1 增加 `"librarian_side_effect"` 一条 source 值的描述。SELF_EVOLUTION 不在 INVARIANTS"只增不改"范围内。

**Orchestrator 内部路径的 source 语义(audit CONCERN §B 处理)**:
- `orchestrator.py:2956 / 2963-2965`(`task knowledge-promote --target canonical`):由 `swl task knowledge-promote` CLI 命令触发,Orchestrator 是 CLI 命令的同步执行者 → 使用 `source="cli"`
- `orchestrator.py:498-499`(Librarian 侧效):非 CLI 触发 → 使用 `source="librarian_side_effect"`
- 当前代码中 Orchestrator 不存在 daemon / 非 CLI 触发的 canonical 写入路径;若未来引入(例如 web API),届时新加 source 值

### C. Policy 边界:harness per-task 派生配置不纳入

**判定**:`harness.py` 中 `save_route` / `save_knowledge_policy` / `save_retry_policy` / `save_stop_policy` / `save_execution_budget_policy` 5 个函数判定为 task-scoped 派生配置,**不纳入** apply_proposal 收敛。

**理由**:
1. **物理写入位置不同**:这 5 个函数全部定义在 `store.py` 中,签名为 `(base_dir, task_id, payload)`,写入 task-scoped JSON 文件(每个文件路径包含 `task_id`)。INVARIANTS §5 矩阵的 `policy` 列对应系统级 `policy_records` 表;这 5 个函数对应 `task` 列(已由 Orchestrator 治理)
2. **caller 性质不同**:harness 函数由 task 执行时机自动调用,不是 proposal 应用动作
3. **守卫测试可清晰**:守卫测试只对 `policy_records` 写入做断言,不涉及 task-scoped 派生

**design audit 验证结果**:audit §C(line 100)代码层验证 ✅ 通过。判定站得住脚。

**实施约束**:`save_audit_trigger_policy()`(`consistency_audit.py:194`,由 `cli.py:2465` 调用)写入系统级 audit policy,**纳入** apply_proposal 收敛(归 G4)。

### D. Repository 抽象层不实装,采用最小封装

**判定**:本 phase 不实现完整 Repository 模式(`KnowledgeRepo._promote_canonical` / `RouteRepo._apply_metadata_change` / `PolicyRepo._apply_policy_change`),governance 层直接调用现有 store 函数。

**理由**:
1. **范围窄版决策**:Direction Gate 已选窄版(4-5 slice)
2. **核心目标已覆盖**:apply_proposal 作为唯一入口的目标不依赖 Repository 抽象层
3. **守卫测试粒度足够**:测试断言"除 governance.py 外无 caller 调用受保护 writer"——是否封装为 Repository 类不影响该断言
4. **Repository 层是后续 phase**:本 phase closeout 登记 backlog

**与 DATA_MODEL §4.1 的偏离声明(audit NIT §D 处理)**:DATA_MODEL §4.1 描述守卫测试基于 `_promote_canonical` 等私有方法名扫描;本轮守卫测试的实际扫描目标是现有 store 函数名(`append_canonical_record` / `save_route_weights` / `save_route_capability_profiles` / `save_audit_trigger_policy` / 派生写入函数,见 §F)。这一偏离在本轮代码中明确记录在守卫测试 docstring 中;DATA_MODEL.md 的描述将在 Repository 实装 phase 中更新。

**实施细节**:`apply_proposal()` 内部 dispatch 形如:
```python
def apply_proposal(proposal_id, operator_token, target):
    proposal = _load_proposal_artifact(proposal_id, target)  # target 协助路径解析
    _validate_target(proposal, target)
    if target == ProposalTarget.CANONICAL_KNOWLEDGE:
        result = _apply_canonical(proposal, operator_token)
    elif target == ProposalTarget.ROUTE_METADATA:
        result = _apply_route_metadata(proposal, operator_token)
    elif target == ProposalTarget.POLICY:
        result = _apply_policy(proposal, operator_token)
    _emit_event(operator_token, target, result)
    return result
```

`_apply_canonical()` 内部调 `append_canonical_record` / `persist_wiki_entry_from_record` + 派生写入(`save_canonical_registry_index` / `save_canonical_reuse_policy`)——这是 stage-promote 流的等价语义(§E 论证)。

`_apply_route_metadata()` 内部调 `save_route_weights` + `apply_route_weights`(内存刷新),或 `save_route_capability_profiles` + `apply_route_capability_profiles`(内存刷新)——保持 save+apply 配对(§G 处理)。

### E. 派生写入(canonical_registry_index / canonical_reuse_policy)的边界判定 — 新增

**问题背景**(audit BLOCKER 1):context_brief 列出的派生写入有两类语义:

1. **Apply 时机**:在 stage-promote / task knowledge-promote 流中,派生写入紧跟 `append_canonical_record` 发生,语义是"主写入的副作用"
   - `cli.py:2336-2346`(stage-promote):append_canonical_record 后立即 save_canonical_registry_index + save_canonical_reuse_policy ✓
   - `orchestrator.py:2956 / 2963-2965`(task knowledge-promote):同上 ✓

2. **任务启动时机**:在 `orchestrator.py:2640-2667` 的 `create_task()` 流程中,无条件调用 `save_canonical_registry_index` 和 `save_canonical_reuse_policy`,**没有任何 canonical record 新增**——是从现有 canonical_registry 读取并重建派生索引

**判定**:**只收敛 apply 时机的派生写入,不收敛任务启动时机的派生重建**

**理由**:
- 任务启动时机的派生写入语义是"派生缓存重建",不是"proposal apply"。强行经 `apply_proposal()` 会要求构造一个虚假的 OperatorToken 和虚假的 proposal_id,污染 governance 层语义
- INVARIANTS §0 第 4 条针对的是"canonical knowledge / route metadata / policy 三类对象的写入",派生缓存(index / summary)是这些 truth 的物化视图,不是 truth 本身

**守卫测试扫描目标(回答 audit BLOCKER 1 的"如何明确"问题)**:

| 函数名 | 类别 | 守卫扫描? | 白名单豁免文件 |
|--------|------|-----------|---------------|
| `append_canonical_record` | canonical 主写入 | **YES** | `governance.py` / `store.py` / `tests/` |
| `persist_wiki_entry_from_record` | canonical 主写入 | **YES** | `governance.py` / `knowledge_store.py` / `tests/` |
| `save_canonical_registry_index` | canonical 派生 | **NO**(任务启动时机合法) | 全局豁免;不进入守卫扫描 |
| `save_canonical_reuse_policy` | canonical 派生 | **NO**(同上) | 全局豁免 |
| `save_route_weights` | route 主写入 | **YES** | `governance.py` / `router.py` / `tests/` |
| `save_route_capability_profiles` | route 主写入 | **YES** | `governance.py` / `router.py` / `tests/` |
| `apply_route_weights` | route 内存刷新 | **NO**(memory-only,无持久化) | 全局豁免 |
| `apply_route_capability_profiles` | route 内存刷新 | **NO** | 全局豁免 |
| `save_audit_trigger_policy` | policy 主写入 | **YES** | `governance.py` / `consistency_audit.py` / `tests/` |

**任务启动时机的派生写入仍由 orchestrator.py:2666-2669 直接调用**:不收敛、不触发守卫——这是 audit BLOCKER 1 的明确解决方案。原设计审计时行号为 2664-2667,M1/M2/M3 实施后代码行号偏移为当前值。

**11 处直接写路径的精确清单(audit "11 vs 16" 计数澄清)**:

| # | 文件:行 | 函数 | 是否收敛 | 收敛 source |
|---|---------|------|---------|-------------|
| 1 | `cli.py:2336` | persist_wiki_entry_from_record | YES | "cli" |
| 2 | `cli.py:2341` | append_canonical_record | YES | "cli" |
| 3 | `cli.py:2345` | save_canonical_registry_index | **NO**(派生,豁免) | — |
| 4 | `cli.py:2346` | save_canonical_reuse_policy | **NO**(派生,豁免) | — |
| 5 | `cli.py:2493` | save_route_weights | YES | "cli" |
| 6 | `cli.py:2560` | save_route_capability_profiles | YES | "cli" |
| 7 | `cli.py:2465` | save_audit_trigger_policy | YES | "cli" |
| 8 | `orchestrator.py:498` | append_canonical_record | YES | "librarian_side_effect" |
| 9 | `orchestrator.py:499` | persist_wiki_entry_from_record | YES | "librarian_side_effect" |
| 10 | `orchestrator.py:2666` | save_canonical_registry_index | **NO**(任务启动派生,豁免) | — |
| 11 | `orchestrator.py:2669` | save_canonical_reuse_policy | **NO**(同上) | — |
| 12 | `orchestrator.py:2956` | append_canonical_record | YES | "cli" |
| 13 | `orchestrator.py:2963` | save_canonical_registry_index | **NO**(随 #12 主写入发生,但守卫整体豁免派生函数) | — |
| 14 | `orchestrator.py:2965` | save_canonical_reuse_policy | **NO**(同上) | — |
| 15 | `meta_optimizer.py:1380` | save_route_weights | YES | "cli" |
| 16 | `meta_optimizer.py:1387` | save_route_capability_profiles | YES | "cli" |

**实际收敛 9 处**(主写入)+ 7 处豁免(派生)。原"11 处"为粗略估数,本稿以精确表为准。

### F. Meta-Optimizer 批量 apply 的 schema 适配 — 新增

**问题背景**(audit BLOCKER 2):`meta_optimizer.py:apply_reviewed_optimization_proposals(review_path, ...)` 是批量函数:
- 接受 `review_path: Path`(review record 文件路径,含 N 个 ProposalReviewEntry)
- 不接受单条 `proposal_id`
- Meta-Optimizer 的 proposal artifact 是 bundle 文件(`OptimizationProposalBundle`),不是 `.swl/artifacts/proposals/<id>.json` 形式

**预决方案**:**用 review_id 作为 governance 层的 proposal_id;`apply_reviewed_optimization_proposals` 整体作为一次 `apply_proposal()` 调用**

**理由**:
1. **语义对齐**:operator 实际 review 的对象是 review record(其中包含一组提案),不是单条 proposal——CLI `swl proposal apply` 接收的也是 review record 路径。governance 层的 proposal_id 对应 operator 实际审阅与批准的最小语义单位,即 review record
2. **避免 N 次调用的事务性问题**:循环 N 次会引入"中途失败 → 部分应用 → 状态不一致"问题。整体单次 apply 让 `_apply_route_metadata()` 内部的 save+apply 配对保持原子(参考 §G)
3. **`_load_proposal_artifact(proposal_id, target)`** 接受 `target` 参数后,可以根据 target 路由到不同的 artifact 加载逻辑:
   - `target == CANONICAL_KNOWLEDGE`:proposal_id 是 staged candidate id,从 `staged_knowledge` 加载
   - `target == ROUTE_METADATA`:proposal_id 是 review record id,从 review record 路径加载 ProposalReviewEntry 列表
   - `target == POLICY`:proposal_id 是 policy proposal id,从对应路径加载

**实施约束**:
- governance 层 `_load_proposal_artifact()` 内部按 target 分支处理 schema 差异(适配层),**不**强制 Meta-Optimizer 改造为单条 proposal artifact 模式
- `apply_reviewed_optimization_proposals()` 函数本身不删除——它的核心逻辑(权重计算、profile 合并、application record 持久化)迁移到 `_apply_route_metadata()` 或保留为 `_apply_route_metadata` 的内部 helper
- `cli.py:swl proposal apply` 命令的 caller 改为:
  ```python
  apply_proposal(
      proposal_id=str(review_record_id),
      operator_token=OperatorToken(source="cli"),
      target=ProposalTarget.ROUTE_METADATA,
  )
  ```
- `_apply_route_metadata()` 内部调用迁移过来的逻辑,完成批量 apply

**与 SELF_EVOLUTION §3.1 的语义偏离**:SELF_EVOLUTION 假设"每个 proposal_id 是单条 proposal artifact 的标识"。Meta-Optimizer 的 review record 是"批量 proposal 的容器",将其作为 proposal_id 传入是适配选择。在 closeout 时同步在 SELF_EVOLUTION 中增加"proposal_id 可指向 review record(批量 proposal 容器)"的注解。

### G. `apply_route_weights` / `apply_route_capability_profiles` 内存刷新配对 — 新增

**问题背景**(audit R8):当前 `meta_optimizer.py:1380-1388` 的写入模式是:
```python
save_route_weights(base_dir, persisted_weights)
apply_route_weights(base_dir)             # 内存刷新
save_route_capability_profiles(base_dir, persisted_profiles)
apply_route_capability_profiles(base_dir) # 内存刷新
```

`apply_route_weights` 和 `apply_route_capability_profiles` 是 `router.py:656 / 713` 定义的内存刷新函数:把磁盘上的最新 route_weights / profiles 加载到内存中的 `RouteRegistry` 单例,确保 process 内后续路由决策看到最新状态。

如果 governance 层只迁移 `save_*` 调用而遗漏 `apply_*` 调用,route metadata 持久化但内存不更新——下次 router 路由决策仍用旧权重,直到 process 重启。这是等价性破坏。

**预决方案**:**`_apply_route_metadata()` 内部保持 save+apply 配对,与现有代码语义完全一致**

**实施约束**:
- `_apply_route_metadata()` 内 `save_route_weights → apply_route_weights → save_route_capability_profiles → apply_route_capability_profiles` 顺序与原 `apply_reviewed_optimization_proposals` 保持完全一致
- `apply_route_weights` / `apply_route_capability_profiles` 在守卫测试中**不**列入扫描目标(§E 表中已豁免),因为它们是内存刷新,不是持久化写入,守卫的语义是"持久化写入唯一入口"
- 但 governance 层调用它们是必须的——通过 `consistency-checker` subagent 在 M2 milestone 复核 save+apply 配对完整性

**回滚策略(audit R7 处理)**:
- `apply_reviewed_optimization_proposals` 当前已记录 `rollback_weights` / `rollback_capability_profiles` 字段,但实际不执行回滚(audit R7 指出)
- 本 phase **不**新增运行时回滚机制——这超出 phase 范围,且与 INVARIANTS 没有直接冲突
- save_route_weights → apply_route_weights → save_route_capability_profiles → apply_route_capability_profiles 四步在 governance 层视为"不可分割的批量 apply",中途失败时记录 event 并抛错;事务性增强(rollback 实际执行)登记为 backlog item

---

## 三、Slice 拆解

### S1: `governance` 模块 + 类型 + 骨架

**目标**:建立 `src/swallow/governance.py` 文件骨架,定义类型(`OperatorToken` / `ProposalTarget` / `ApplyResult`),实现 `apply_proposal()` dispatch shell + `_load_proposal_artifact` / `_validate_target` / `_emit_event` 通用辅助函数。`_apply_canonical` / `_apply_route_metadata` / `_apply_policy` 留 stub(返回 NotImplementedError),由后续 slice 填充。

**改动范围**:
- 新建 `src/swallow/governance.py`,定义:
  - `OperatorToken` dataclass(`source: Literal["cli", "system_auto", "librarian_side_effect"]`,`reason: str | None = None`)
  - `ProposalTarget` enum(`CANONICAL_KNOWLEDGE` / `ROUTE_METADATA` / `POLICY`)
  - `ApplyResult` dataclass(success / detail / 副作用记录)
  - `apply_proposal()` dispatch shell
  - `_load_proposal_artifact(proposal_id, target)` 按 target 分支适配 schema(本 slice 留 stub)
  - `_validate_target(proposal, target)` 校验
  - `_emit_event(operator_token, target, result)` 事件 emit
- 新建 `tests/test_governance.py` 包含 type 与 dispatch shell 测试
- `OperatorToken.source` 的运行时校验通过 `__post_init__` + `Literal` type hint 双保险(audit NIT §S1 处理)

**风险评级**:
- 影响范围:1(新建单文件)
- 可逆性:1
- 依赖复杂度:1
- **总分:3 / 低风险**

**依赖**:无外部依赖

**验收条件**:
- `from swallow.governance import apply_proposal, OperatorToken, ProposalTarget, ApplyResult` 可成功 import
- `OperatorToken(source="invalid")` 抛 `ValueError`(`__post_init__` 校验)
- 调用 `apply_proposal(proposal_id, token, target=CANONICAL_KNOWLEDGE)` 进入 stub,抛 `NotImplementedError`
- `tests/test_governance.py` PASS

**Review checkpoint**:与 S2 合并为同一 milestone(M1)

---

### S2: Canonical 写路径收敛 + 守卫测试 1

**目标**:实装 `_apply_canonical()` 内部逻辑,把 canonical **主写入** caller 收敛到 `apply_proposal()`(派生写入按 §E 不收敛)。实装 `test_canonical_write_only_via_apply_proposal` 守卫测试。

**改动范围(精确清单,§E 表中标 YES 的 canonical 行)**:
- `src/swallow/governance.py`: `_apply_canonical(proposal, token)` 实装。内部调 `persist_wiki_entry_from_record` + `append_canonical_record` + 派生写入(`save_canonical_registry_index` / `save_canonical_reuse_policy`)——派生写入随主写入 caller 一并迁移到 governance,但守卫不约束派生函数
- `src/swallow/cli.py:2320-2350`: `swl knowledge stage-promote` 路径,4 行 store 调用替换为单次 `apply_proposal(target=CANONICAL_KNOWLEDGE, source="cli")`
- `src/swallow/orchestrator.py:498-499`: Librarian 侧效,2 行 store 调用替换为 `apply_proposal(target=CANONICAL_KNOWLEDGE, source="librarian_side_effect")`
- `src/swallow/orchestrator.py:2956 / 2963-2965`: task knowledge-promote 路径,store 调用替换为 `apply_proposal(target=CANONICAL_KNOWLEDGE, source="cli")`
- **不动**:`orchestrator.py:2664-2667`(任务启动时机派生,§E 豁免)
- 新建 `tests/test_invariant_guards.py`,实装 `test_canonical_write_only_via_apply_proposal`(AST 扫描 `src/` 中对 `append_canonical_record` 和 `persist_wiki_entry_from_record` 的直接调用,白名单豁免 governance.py / store.py / knowledge_store.py / tests/)

**风险评级**:
- 影响范围:3(跨模块:cli + orchestrator + governance + tests)
- 可逆性:2
- 依赖复杂度:2(依赖 S1)
- **总分:7 / 高风险**

**风险缓解**:
- 按 caller 文件分组提交:先 `cli.py` → 再 `orchestrator.py:2956 / 2963-2965` → 最后 `orchestrator.py:498-499`
- 每组提交后跑 `tests/test_cli.py` / `tests/test_librarian_executor.py` / `tests/test_orchestrator.py`,regression 早发现
- 守卫测试在所有 caller 收敛后最后实装

**依赖**:S1

**验收条件**:
- 上述 5 处 caller 全部经 `apply_proposal()`
- `grep -rn "append_canonical_record\|persist_wiki_entry_from_record" src/` 输出仅在 `governance.py` / `store.py` / `knowledge_store.py` 中匹配
- `test_canonical_write_only_via_apply_proposal` PASS
- 现有 `tests/test_cli.py::test_stage_promote_*` / `tests/test_librarian_executor.py` / `tests/test_orchestrator.py::test_task_knowledge_promote_*` 全 PASS
- `orchestrator.py:2664-2667` 的派生写入保持原状不动(回归不变)

**Review checkpoint**:与 S1 合并为 M1 milestone

---

### S3: Route metadata 写路径收敛 + 守卫测试 2

**目标**:实装 `_apply_route_metadata()`,收敛 4 处 route 写 caller(主写入 + 内存刷新配对);实装 `test_route_metadata_writes_only_via_apply_proposal`。

**关键澄清**:本 slice **只**实装守卫测试 2;原稿守卫测试 3(`test_only_apply_proposal_calls_private_writers`,聚合断言)推迟到 S4 末尾,等 policy 路径也收敛后再激活——这处理 audit NIT §S3 指出的依赖问题。

**改动范围**:
- `src/swallow/governance.py`: `_apply_route_metadata(proposal, token)` 实装
  - 内部按 §G 保持 save+apply 配对:`save_route_weights → apply_route_weights → save_route_capability_profiles → apply_route_capability_profiles`
  - 处理 §F 的 schema 适配:`_load_proposal_artifact(proposal_id, target=ROUTE_METADATA)` 加载 review record(批量 proposal)
  - 迁移 `apply_reviewed_optimization_proposals()` 内部的权重计算 / profile 合并 / application record 持久化逻辑
- `src/swallow/cli.py:2493`: `swl route weights apply` 改为 `apply_proposal(target=ROUTE_METADATA, source="cli")`
- `src/swallow/cli.py:2560`: `swl route capabilities update` 改为 `apply_proposal(target=ROUTE_METADATA, source="cli")`
- `src/swallow/cli.py:swl proposal apply` 命令(对应 `apply_reviewed_optimization_proposals` 调用): `apply_proposal(proposal_id=review_record_id, target=ROUTE_METADATA, source="cli")`
- `src/swallow/meta_optimizer.py:apply_reviewed_optimization_proposals()`:函数本身保留(它是 review 编排逻辑),但其内部 `save_route_weights` / `apply_route_weights` / `save_route_capability_profiles` / `apply_route_capability_profiles` 调用迁移到 governance 层。函数返回值与签名不变(向后兼容)
- `tests/test_invariant_guards.py`: 实装 `test_route_metadata_writes_only_via_apply_proposal`(扫描 `save_route_weights` / `save_route_capability_profiles`,白名单 governance.py / router.py / tests/)

**风险评级**:
- 影响范围:3
- 可逆性:2
- 依赖复杂度:2
- **总分:7 / 高风险**

**风险缓解**:
- **S3 实施前打 Meta-Optimizer eval baseline**(risk_assessment R2):运行 `tests/eval/test_eval_meta_optimizer_proposals.py` 保存输出快照
- S3 完成后对比 baseline,确保完全等价
- governance 层 `_apply_route_metadata` 内部调用顺序必须与原 `apply_reviewed_optimization_proposals` 完全一致(权重计算 → save_route_weights → apply_route_weights → 同样顺序处理 profiles)
- 派 `consistency-checker` subagent 在 S3 末尾跑一次,对比 governance.py 实现与 SELF_EVOLUTION §3.1 + §F 适配方案

**依赖**:S1, S2(governance 骨架)

**验收条件**:
- 上述 4 处 caller 全部经 `apply_proposal()`
- `grep -rn "save_route_weights\|save_route_capability_profiles" src/` 输出仅在 `governance.py` / `router.py` 内匹配
- `apply_route_weights` / `apply_route_capability_profiles` 在 governance 层正确调用,内存刷新行为不变
- `test_route_metadata_writes_only_via_apply_proposal` PASS
- `tests/eval/test_eval_meta_optimizer_proposals.py` 输出与 baseline 完全一致

**Review checkpoint**:M2 milestone(独立,因 Meta-Optimizer eval 是关键 sentinel)

---

### S4: Policy 写路径收敛 + 守卫测试 3 + Phase 49 concern 消化

**目标**:实装 `_apply_policy()`,收敛 `swl audit policy set` 写路径;实装聚合守卫测试 3;同时统一 `task knowledge-promote --target canonical` 的 authority 语义,消化 Phase 49 concern。

**改动范围**:
- `src/swallow/governance.py`: `_apply_policy(proposal, token)` 实装,内部调 `save_audit_trigger_policy`
- `src/swallow/cli.py:2465`: `swl audit policy set` 改为 `apply_proposal(target=POLICY, source="cli")`
- 复核 `task knowledge-promote --target canonical` 路径(已在 S2 部分收敛):确认 authority 通过 OperatorToken 统一管理,Phase 49 concern 消化
- `tests/test_invariant_guards.py`: 实装 `test_only_apply_proposal_calls_private_writers`(聚合断言:扫描 §E 表中所有标 YES 的 canonical + route + policy 主写入函数,统一豁免规则)

**风险评级**:
- 影响范围:2
- 可逆性:2
- 依赖复杂度:2
- **总分:6 / 中风险**

**依赖**:S1, S2, S3(聚合守卫测试需要三类路径都收敛)

**验收条件**:
- `swl audit policy set` 经 `apply_proposal()` 写 policy_records
- `task knowledge-promote --target canonical` 的 authority 通过 `OperatorToken(source="cli")` 统一
- Phase 49 concern 在 backlog 中标记为 Resolved
- `test_only_apply_proposal_calls_private_writers` PASS
- `tests/eval/` / `tests/test_cli.py` 全 PASS

**Review checkpoint**:M3 milestone

---

## 四、Slice 依赖图

```
S1 (governance 骨架)
 │
 ├──► S2 (Canonical 主写入收敛 + 守卫 1) ──┐
 │                                          │
 ├──► S3 (Route 收敛 + 守卫 2) ─────────────┤
 │                                          │
 └──► S4 (Policy 收敛 + 守卫 3 聚合) ───────┴──► closeout
```

S2 / S3 / S4 必须串行(S4 的聚合守卫依赖 S2/S3 的收敛完成)。

---

## 五、Review Checkpoint / Milestone 分组

| Milestone | 包含 slice | 评审重点 |
|-----------|-----------|---------|
| **M1: Governance API + Canonical 收敛** | S1 + S2 | API 签名是否对齐 SELF_EVOLUTION §3.1 / §3.1.1;OperatorToken 三种 source 是否覆盖所有 canonical caller;canonical 主写入收敛后 regression 是否清零;`orchestrator.py:2664-2667` 派生写入按 §E 保留不动 |
| **M2: Route 收敛 + Meta-Optimizer eval baseline** | S3 | Meta-Optimizer eval 是否等价(关键 sentinel);§F schema 适配是否正确(review_id 作为 proposal_id);§G save+apply 配对是否完整;consistency-checker 报告 |
| **M3: Policy 收敛 + 聚合守卫测试** | S4 | policy_records 写路径清晰;Phase 49 concern 真的消化;聚合守卫测试覆盖所有 §E 表 YES 行 |

---

## 六、明确的非目标

详见 kickoff §非目标。本 design_decision 复述关键不做项 + 修订后新增:

- 不实装完整 Repository 抽象层(后续 phase)
- 不实装另外 14 条 INVARIANTS §9 守卫测试(后续 phase)
- 不修改 INVARIANTS / DATA_MODEL / SELF_EVOLUTION 等设计文档(本轮代码追文档;closeout 时提示文档增量)
- 不重命名 CLI 命令
- 不纳入 `migrate_file_knowledge_to_sqlite()` 路径(bootstrap 写入)
- 不纳入 harness.py 的 5 个 per-task 派生配置函数(§C)
- **不收敛任务启动时机的派生写入**(`orchestrator.py:2664-2667`,§E)
- **不收敛 view-only 内存刷新**(`apply_route_weights` / `apply_route_capability_profiles`,§G 中保持配对但不在守卫扫描)
- **不实施运行时事务回滚**(audit R7,登记为后续 backlog)
- **不重设计 proposal artifact schema**(§F 通过 governance 层适配 + closeout 文档增量解决)
- CLI 用户视角无变化

---

## 七、验收条件汇总

详见 kickoff §完成条件。本 design_decision 补充技术性验收:

1. `from swallow.governance import apply_proposal, OperatorToken, ProposalTarget, ApplyResult` 可 import
2. `apply_proposal()` 函数签名为 `(proposal_id: str, operator_token: OperatorToken, target: ProposalTarget) -> ApplyResult`
3. `OperatorToken` 字段为 `source: Literal["cli", "system_auto", "librarian_side_effect"]` + `reason: str | None = None`(无 `actor` 字段)
4. `OperatorToken.__post_init__` 在 source 非法时抛 `ValueError`
5. §E 表中标 YES 的 9 处主写入 caller 全部收敛
6. `orchestrator.py:2666-2669` 派生写入保持原状(§E;原设计审计行号 2664-2667 已随实现偏移)
7. `apply_route_weights` / `apply_route_capability_profiles` 配对完整(§G)
8. 3 条守卫测试 PASS
9. `tests/eval/test_eval_meta_optimizer_proposals.py` 输出与 S3 前 baseline 完全一致
10. Phase 49 concern 在 backlog 中移入 Resolved
11. closeout 中登记后续 backlog:14 条剩余守卫测试 + Repository 抽象层 + apply 事务回滚 + DATA_MODEL §4.1 文档同步 + SELF_EVOLUTION §3.1.1 文档同步("librarian_side_effect" source) + SELF_EVOLUTION §3.1 文档同步(proposal_id 可指向 review record)

---

## 八、Phase Guard 自检

按 Claude rules §五要求自检:

1. **是否越出 kickoff goals?** 否。修订后仍在 G1-G5 范围内
2. **是否触及 kickoff non-goals?** 否。明确不做完整 Repository 层、不做 14 条剩余守卫测试、不改设计文档(只在 closeout 提示)、不改 CLI 命令名;新增的 §E §F §G 都在"如何收敛 11 处写路径"的范围内
3. **slice 数量是否合理?** 4 个 slice,符合"≤5 个 slice"建议
4. **`[SCOPE WARNING]`?** 无
