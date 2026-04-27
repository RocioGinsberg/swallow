好,那我们一次把所有事情说清楚再动手。先给文件夹结构和 skill/subagent 配置建议,然后改 roadmap,最后把"5 条纪律"也落地到 AGENTS.md。

---

## 一、文件夹结构推荐

按"6 个文档类别 + 5 条纪律"的框架,目标结构是这样的:

```
swallow/                                    仓库根
│
├── README.md
├── AGENTS.md                               ─┐  协作约定(开发流程规则)
├── CLAUDE.md                               ─┘  Owner: Human                
│
├── docs/
│   ├── active_context.md                    ←  实时状态(Codex 唯一高频更新)
│   ├── current_state.md                     ←  恢复入口(low-frequency)
│   ├── roadmap.md                           ←  决策辅助(只剩 A 类)
│   ├── concerns_backlog.md                  ←  临时事务
│   ├── cli_reference.md                     ←  命令参考(单独维护)
│   ├── design
│   │   ├── INVARIANTS.md                           ─┐
│   │   ├── DATA_MODEL.md                            │
│   │   ├── EXECUTOR_REGISTRY.md                     │  设计文档(产品宪法 + 设计)
│   │   ├── ARCHITECTURE.md                          │  Owner: Human + Claude
│   │   ├── STATE_AND_TRUTH.md                       │  Trigger: 设计变更
│   │   ├── KNOWLEDGE.md                             │
│   │   ├── AGENT_TAXONOMY.md                        │
│   │   ├── ORCHESTRATION.md                         │
│   │   ├── HARNESS.md                               │
│   │   ├── PROVIDER_ROUTER.md                       │
│   │   ├── SELF_EVOLUTION.md                        │
│   │   └── INTERACTION.md                          ─┘
│   │                               
│   ├── plans/                               ←  历史记录(phase 收尾归档)
│   │   ├── phasexx/
│   │   │   ├── kickoff.md
│   │   │   ├── breakdown.md
│   │   │   ├── closeout.md
│   │   │   ├── design_decision.md
│   │   │   ├── risk_assessment.md
│   │   │   └── review_comments.md
│   │   ├── phasexy/
│   │   └── ...
│   │
│   └── archive/                             ←  老资料(deprecated 设计文档/废弃讨论)
│       └── ...
│
├── .agents/                                 ←  多 Agent 控制层
│   ├── shared/
│   │   ├── read_order.md                    各 agent 共用读取顺序
│   │   ├── rules.md                         共同规则
│   │   ├── state_sync_rules.md              状态同步规则
│   │   ├── document_discipline.md           ★ 新增:5 条文档纪律
│   │   └── reading_manifest_format.md       ★ 新增:reading manifest 格式
│   │
│   ├── claude/
│   │   ├── role.md                          Claude 角色定义
│   │   └── rules.md                         Claude 专属规则
│   │
│   ├── codex/
│   │   ├── role.md                          Codex 角色定义
│   │   ├── rules.md                         Codex 专属规则
│   │   └── templates/                       Codex 用到的模板
│   │
│   ├── workflows/
│   │   ├── feature.md                       feature 开发流程
│   │   ├── tag_release.md                   ★ 新增:tag 发布流程
│   │   └── ...
│   │
│   └── templates/
│       ├── pr_body.md                       PR body 模板
│       ├── closeout.md                      ★ 新增:closeout 模板
│       ├── design_decision.md               ★ 新增:design_decision 模板
│       └── ...
│
├── .claude/                                 ←  Claude Code 原生配置
│   ├── agents/                              Claude subagents 定义
│   │   ├── context-analyst.md               phase 启动时的 brief 生成
│   │   ├── roadmap-updater.md               phase 收口时的 roadmap 增量更新
│   │   └── consistency-checker.md           实现后对比设计文档
│   │
│   └── skills/                              ★ Claude Code 用 skills
│       ├── design-review.md                 设计文档评审 skill
│       ├── invariant-check.md               ★ 新增:宪法对齐检查 skill
│       └── risk-assessment.md               风险评估 skill
│
├── .codex/                                  ←  Codex CLI 原生配置
│   ├── session_bootstrap.md                 启动加载入口 
│   └── skills/                              Codex 用 skills
│       ├── slice-implement.md               slice 级实现 skill
│       ├── test-coverage.md                 测试覆盖 skill
│       ├── apply-proposal.md                ★ 新增:apply_proposal 调用 skill
│       └── handoff-write.md                 ★ 新增:handoff object 撰写 skill
│
├── swallow/                                 ←  代码主目录
├── tests/                                   ←  测试
│   ├── invariants/                          ★ 守卫测试单独目录
│   │   ├── test_no_executor_writes_task_directly.py
│   │   ├── test_canonical_write_only_via_apply_proposal.py
│   │   └── ...
│   └── ...
│
└── pyproject.toml / etc.
```

---

## 二、Skills 与 Subagents 的配置建议

### 2.1 Skills 是什么、Subagents 是什么、两者区别

简单说:

| 维度    | Skill                             | Subagent                                           |
| ----- | --------------------------------- | -------------------------------------------------- |
| 本质    | **方法模板**——告诉 agent "做这类事的标准流程是什么" | **独立 agent 实例**——可以被主 agent 调用,有自己的 context window |
| 触发    | 主 agent 在执行时按需引入                  | 主 agent 显式 spawn / invoke                          |
| 上下文   | 共享主 agent 的 context               | 独立 context(隔离)                                     |
| 持久化产物 | 不一定有                              | 通常产出 artifact 文件                                   |
| 适合场景  | 重复性方法(写测试、审查 diff)                | 隔离上下文的并行工作(深度分析、跨文档对比)                             |

你已经有的:

* **Subagents**:`context-analyst` / `roadmap-updater` / `consistency-checker`(都是"产出一份文档"的隔离任务)
* **Skills**:你现有的 `.codex/skills/`(我没看到具体内容,但你 README 提过有 skill 配置)

### 2.2 推荐为这个项目添加的 Skill

**对 Claude(评审视角)**:

| Skill                    | 用途                             | 触发条件                         |
| ------------------------ | ------------------------------ | ---------------------------- |
| `design-review.md`(已有)   | 评审 design_decision.md 与设计文档的对齐 | 评审任务时引入                      |
| `risk-assessment.md`(已有) | 产出 risk_assessment.md          | phase kickoff 阶段             |
| **`invariant-check.md`** | 检查任何 PR / 设计变更是否违反 INVARIANTS  | 每次 design review 与 PR review |

`invariant-check.md` 的内容大致是:

```markdown
# Skill: Invariant Check

Read INVARIANTS.md, then verify the proposed change against:
1. Three architectural planes (no entity crosses planes)
2. Three LLM call paths (no path B calls Provider Router)
3. Truth write permission matrix (§5)
4. apply_proposal as sole entry for canonical/route/policy

Output a verdict report:
  - violations: [...]
  - concerns: [...]
  - clean: bool
```

**对 Codex(实现视角)**:

| Skill                      | 用途                                                   | 触发条件           |
| -------------------------- | ---------------------------------------------------- | -------------- |
| `slice-implement.md`(已有)   | slice 级实现的标准流程                                       | 每个 slice 开始时   |
| `test-coverage.md`(已有)     | 测试覆盖检查                                               | 实现完成时          |
| **`apply-proposal.md`**    | 涉及 canonical / route / policy 写入时,确保走 apply_proposal | 实现包含这三类写入时     |
| **`handoff-write.md`**     | 撰写结构化 handoff object                                 | task 间交接时      |
| **`invariant-respect.md`** | 实现侧的宪法检查清单(对应 Claude 的 invariant-check)              | 每个 slice 完成自检时 |

### 2.3 推荐增加的 Subagent

我看你已有 3 个 subagent。再追加 1-2 个能覆盖更多场景:

| Subagent                      | 模型           | 触发                | 产出                                              |
| ----------------------------- | ------------ | ----------------- | ----------------------------------------------- |
| `context-analyst`(已有)         | Sonnet       | phase 启动          | `context_brief.md`                              |
| `roadmap-updater`(已有)         | Sonnet       | phase 收口          | roadmap.md 增量更新                                 |
| `consistency-checker`(已有)     | Sonnet       | 实现完成              | `consistency_report.md`                         |
| **`invariant-auditor`**       | Sonnet       | 设计 PR + 实现 PR(每次) | `invariant_audit.md` —— 对照 INVARIANTS 检查并产出违规清单 |
| **`closeout-summarizer`**(可选) | Sonnet/Haiku | phase 收口          | closeout 文档草稿                                   |

`invariant-auditor` 是我特别推荐的——它和 `consistency-checker` 不同:

* `consistency-checker`:对比"实现 vs 设计文档"
* `invariant-auditor`:对比"任何变更 vs INVARIANTS"

后者是结构更深的检查,因为 INVARIANTS 是宪法。

`closeout-summarizer` 是可选的便利,可以让 phase 收口阶段自动化一部分,但人工 review 不能少。

### 2.4 文件层结构落地

每个 subagent 文件的标准结构(用 `.claude/agents/invariant-auditor.md` 举例):

```markdown
---
name: invariant-auditor
model: sonnet
trigger: design_pr | implementation_pr
output_path: docs/plans/<phase>/invariant_audit.md
---

# Invariant Auditor

## Reading manifest
1. INVARIANTS.md
2. The proposed change (PR diff or design document)
3. DATA_MODEL.md (for permission matrix verification)

## Process
1. List all proposed changes that touch:
   - Truth tables (task / event / knowledge / route / policy)
   - apply_proposal call sites
   - State machine transitions
   - LLM call paths
2. For each, verify against INVARIANTS §0-§9
3. Output verdict: clean | concerns | violations

## Output format
... (与 VerdictReport 类似的结构化输出)
```

每个 skill 文件的标准结构(用 `.codex/skills/apply-proposal.md` 举例):

```markdown
---
name: apply-proposal
applies_to: codex
trigger_keywords: [canonical, route_metadata, policy, apply_proposal]
---

# Skill: Apply Proposal

When the task involves writing to canonical knowledge / route metadata / policy:

1. Confirm the change is structured as a proposal artifact first
2. Operator review must precede apply_proposal call
3. Use the single entry: apply_proposal(proposal_id, operator_token, target)
4. Never call Repository._promote_canonical / _apply_metadata_change / _apply_policy_change directly
5. Append a know_change_log / route_health entry after successful apply

## Verification checklist
- [ ] Proposal artifact created in .swl/artifacts/proposals/
- [ ] event_log entry kind="proposal_applied"
- [ ] Guard test test_canonical_write_only_via_apply_proposal still passes
```

这样的格式 agent 看到关键词就触发,触发后照流程走。

---

## 三、要先确认的几件事

在开始改 roadmap 之前,我想确认:

**问题 1**:你现在仓库里 `.claude/agents/` 与 `.codex/skills/` 是不是已经存在?如果是,具体内容我没看过。我上面建议的"新增 skill / subagent"是否要等你 review 现有内容后再决定?

**问题 2**:`docs/concerns_backlog.md` 你已经在用了(我从 AGENTS.md 注释看到),它的当前定位是什么?是"按 phase 累积的 concern"还是"全局 TODO 清单"?

**问题 3**:文件夹结构里我列了 `tests/invariants/` 单独目录。这是按"守卫测试是宪法的代码副本"原则建议的——和普通 unit test 分开。你认可吗?

---

这三个问题确认后,我直接把 roadmap.md 改造完,然后再给你两个补充文件:

* `.agents/shared/document_discipline.md`(5 条纪律)
* `.agents/shared/reading_manifest_format.md`(manifest 模板)

这样这一轮就把"协作模式"这件事一次性收拢。
