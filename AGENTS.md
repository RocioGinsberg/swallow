# AGENTS.md

> **本文件是 swallow 仓库自身的协作约定**,不是 swallow 系统在运行时生成的 task instruction(后者位于 `.swl/instructions/<task_id>/AGENTS.md`)。两者文件名相同,语义不同——本文件描述"我们如何协作开发 swallow",task instruction 描述"swallow 给 Codex executor 的本次 task 指令"。
>
> **Document discipline**
> Owner: Human
> Updater: Human / Claude / Codex（按各自可写边界）
> Trigger: 协作规则、读取顺序、workflow、Git 节奏发生变化
> Anti-scope: 不维护 phase 高频状态、不维护 tag-level release 快照、不复制设计文档正文

---

## 仓库定位

本仓库构建一个**面向真实项目工作的有状态 AI workflow 系统**。

系统设计哲学、架构边界、能力定义见**项目设计文档**(`docs/design/INVARIANTS.md` / `docs/design/ARCHITECTURE.md` / 等)。

本仓库不是通用聊天机器人仓库,也不是纯 RAG 仓库。

---

## 项目宪法

任何设计或实现讨论必须遵守 [`docs/design/INVARIANTS.md`](./docs/design/INVARIANTS.md) 中定义的不变量,包括:

- Control 只在 Orchestrator 和 Operator 手里
- Execution 永远不直接写 Truth
- LLM 调用只有三条路径(Path A / B / C)
- `apply_proposal` 是 canonical / route / policy 的唯一写入入口

新会话第一件事:读 `docs/design/INVARIANTS.md`。所有其他文档与宪法冲突时,以宪法为准。

---

## 当前项目状态

**当前 tag 与高频状态不在本文件维护**,请查阅:

- `docs/active_context.md` — 当前 phase / slice 状态
- `docs/roadmap.md` — 跨 phase 演进路线
- README.md — 与最新 tag 对齐的产品描述

理由:本文件是入口控制面,不是状态板。Phase / tag 进度散落在多处会造成漂移。

---

## 协作模式

本项目采用两 agent + 人工协作开发:

| 角色 | 职责 | 控制文件 |
|------|------|----------|
| **Claude** | 方案拆解、风险评估、PR 评审、分支建议、tag 评估、roadmap 优先级维护 | `CLAUDE.md` → `.agents/claude/` |
| **Codex** | 代码实现、测试、状态同步、slice 验证记录、milestone 级 commit 建议、PR 文案整理 | `.codex/session_bootstrap.md` → `.agents/codex/` |
| **Human** | 设计审批、git 提交执行、PR 创建、合并决策 | — |

Claude subagent(`.claude/agents/`)承接的辅助职责:

| Subagent | 模型 | 职责 |
|----------|------|------|
| `context-analyst` | Sonnet | phase 启动时产出 context_brief |
| `roadmap-updater` | Sonnet | phase closeout 后增量更新 roadmap |
| `design-auditor` | Sonnet | design gate 前从实现者视角审计设计产物 |
| `consistency-checker` | Sonnet | 实现后对比设计文档产出 consistency_report |

协作流程定义见 `.agents/workflows/feature.md`。
共享规则见 `.agents/shared/`。
状态同步规则见 `.agents/shared/state_sync_rules.md`。
跨 phase 蓝图对齐见 `docs/roadmap.md`。

---

## 文档结构(全仓库视角)

仓库文档分五层。**第 1 / 2 / 5 层与 README 的"产品设计文档体系"对齐**;**第 3 / 4 层是开发协作专属**,不进 README 的设计文档章节。

### 1. 宪法层(产品设计 - 不变量)
- `docs/design/INVARIANTS.md` — 项目宪法
- `docs/design/DATA_MODEL.md` — 实现层不变量(SQLite namespace / Repository 写权限)
- `docs/design/EXECUTOR_REGISTRY.md` — 实体到品牌的具体绑定

用途:任何设计与实现的最终参照。**只增不改**,改动需 phase-level review。

### 2. 设计层(产品设计)
- `docs/design/ARCHITECTURE.md`
- `docs/design/STATE_AND_TRUTH.md`
- `docs/design/KNOWLEDGE.md`
- `docs/design/AGENT_TAXONOMY.md`
- `docs/design/ORCHESTRATION.md`
- `docs/design/HARNESS.md`
- `docs/design/PROVIDER_ROUTER.md`
- `docs/design/SELF_EVOLUTION.md`
- `docs/design/INTERACTION.md`

用途:描述系统设计的"为什么"与"如何思考"。具体 schema、品牌绑定、不变量都不持有,只引用宪法层。

### 3. 当前执行层(开发协作)
- `AGENTS.md`(本文件) — 仓库入口控制面与协作约定
- `docs/active_context.md` — 当前唯一高频状态入口
- `docs/roadmap.md` — 跨 phase 蓝图对齐活文档
- `current_state.md` — 恢复入口

### 4. 阶段计划层(开发协作)
- `docs/plans/<phase>/kickoff.md`
- `docs/plans/<phase>/breakdown.md`(可选；多 milestone / 复杂 phase 时使用)
- `docs/plans/<phase>/closeout.md`
- `docs/plans/<phase>/commit_summary.md`(可选)
- `docs/plans/<phase>/context_brief.md`(context-analyst subagent 产出)
- `docs/plans/<phase>/design_decision.md`(Claude 产出)
- `docs/plans/<phase>/risk_assessment.md`(Claude 产出)
- `docs/plans/<phase>/design_audit.md`(design-auditor subagent 产出,可选)
- `docs/plans/<phase>/review_comments.md`(Claude 产出)
- `docs/plans/<phase>/consistency_report.md`(consistency-checker subagent 产出,可选)

用途:组织当前 phase 的目标、拆解、收口、多 agent 产出物。Phase 文档以目录为边界。

### 5. 多 Agent 控制层与工具入口
- `.agents/shared/` — 共享规则、读取顺序、状态同步规则
- `.agents/codex/` — Codex 角色定义、专属规则、模板
- `.agents/claude/` — Claude 角色定义、专属规则
- `.agents/workflows/` — 多角色协作流程定义
- `.agents/templates/` — PR body 等共享模板
- `CLAUDE.md` — Claude 工具原生入口(thin pointer)
- `.codex/session_bootstrap.md` — Codex 工具原生入口(thin pointer)

用途:固定各角色分工、读取顺序、行动边界。各工具原生入口指向 `.agents/` 下的具体文件。

---

## Agent 读取与工作要求

所有 agent 新会话按以下顺序读取:

1. `.agents/shared/read_order.md`(按其中指引继续读取共享规则)
2. 各自的 `role.md` 和 `rules.md`
3. `docs/design/INVARIANTS.md`(项目宪法)
4. `AGENTS.md`(本文件)
5. `docs/active_context.md`
6. `docs/plans/<active-phase>/` 下的相关文件(按需)

详细读取顺序见各工具原生入口文件和 `.agents/shared/read_order.md`。

所有 agent 应遵守:

- 先确认 active phase / active slice
- 不把历史归档材料误当作当前工作目标
- 不擅自扩大当前 phase 范围
- 高频只更新 `docs/active_context.md`
- 每次完成 workflow step 后必须更新状态(见 `.agents/shared/state_sync_rules.md`)
- 各角色只在自己的可写范围内操作(见各 `role.md`)
- 任何与 `docs/design/INVARIANTS.md` 冲突的设计或实现讨论,以宪法为准

---

## 文档更新节奏

### 高频更新
只更新:
- `docs/active_context.md`

适用场景:
- 当前 slice 进度变化
- 当前目标、下一步、阻塞项变化
- 当前 branch / active phase 变化

### 低频更新
只在 phase 或 major slice 收口时更新:
- `current_state.md`
- `docs/plans/<phase>/closeout.md`
- 必要时更新 `AGENTS.md`(仅限协作规则变更)

### Tag 级更新
仅在**已决定要打新 tag、但尚未执行 tag 命令**时更新:
- `README.md` — 与新 tag 对齐的产品描述

说明:
- README 不跟踪 phase 级进度,避免更新不及时引发上下文冲突
- phase 级实时信息由 `docs/active_context.md` 和 `docs/roadmap.md` 承载
- tag-level 文档更新应发生在最终 release commit 中,使 tag 直接指向完整对外快照
- **设计文档**(宪法层 / 设计层)的更新独立于 tag 节奏,任何宪法变更都需 phase-level review

### 可选更新
- `docs/plans/<phase>/commit_summary.md`

说明:
- commit summary 不是强制产物
- 只有当手工提交、阶段归纳或 release note 明显受益时才写

---

## Git 工作节奏

### 分支规则

不要直接在 `main` 上进行日常开发。

推荐方式:
- `main`:稳定主线
- `feat/<phase-or-slice>`
- `fix/<topic>`
- `docs/<topic>`

当前推荐分支命名方式:`feat/<phase-or-slice>`

### 切分支时机

默认规则:

1. `design_decision.md` 与 `risk_assessment.md` 通过人工审批后
2. Human 先从 `main` 切出本轮 feature branch
3. Codex 再在该 branch 上开始代码实现

补充要求:

- 设计文档产出完成但尚未通过人工 gate 时,不进入实现分支,不开始代码改动
- 一旦进入实现阶段,默认不继续把功能开发留在 `main`
- 如当前工作只是纯文档修订且不属于实现阶段,可留在当前分支,由人工决定是否另开 `docs/<topic>`

### 提交规则

提交信息统一使用:`type(scope): summary`

推荐类型:`feat` / `fix` / `refactor` / `test` / `docs` / `chore`

要求:
- 一个 commit 只表达一类变化
- 尽量避免把代码、测试、README、状态同步全部塞进一个大提交
- 高频状态变更只同步到 `docs/active_context.md`
- phase 结束时再做归档同步提交

### 提交节奏规则

每个 phase 的人工提交分两类:

1. **实现里程碑提交**:Codex 完成当前 milestone 的代码实现与测试后,人工审查并提交(包含功能代码 + 测试)
2. **审查收口提交**:Claude 完成 PR review、closeout 文档后,人工提交收口材料(review_comments + closeout + 状态同步)

实现里程碑提交与审查收口提交之间是 Claude 的评审环节。不要把实现和收口材料混在同一次提交中。

补充要求:

- design gate 通过后,应先完成 feature branch 切换,再开始第一个实现 slice
- git 提交由人工执行,Codex 只在对话中给出建议命令
- 默认 review gate 以 milestone 为单位;如未显式定义 milestone,则 `1 milestone = 1 slice`
- Codex 对每个 slice 都要给出验证结果与建议提交范围;到达 milestone 边界时,再给出最终 commit 建议命令
- 高风险 slice、schema 变更、公共 CLI/API surface 变化、跨模块重构应单独成为一个 milestone,不要与低风险改动混提
- 低风险且边界清晰的相邻 slices 可在 design_decision / breakdown 中预先分组,在同一轮 human review 中一起提交
- 禁止把整个 phase 的实现、测试和状态同步压成一次大包 commit
- 需要发起 PR 时,Codex 负责将 PR 文案整理到仓库根目录 `./pr.md`,Human 先 push branch,再据此创建 PR
- PR 创建后如 review 结论或实现内容变化,Codex 应继续更新 `./pr.md`,Human 再决定是否同步到 PR 描述

### 合并规则

- feature branch 完成后再合并回 `main`
- `main` 只接收阶段性稳定成果
- 合并前至少确认测试与基本 CLI 入口可用
- 合并前应确认 `review_comments.md` 已处理完毕,且 `./pr.md` 已反映当前实现与 review 结论
- 如 Claude review 后仍有实现修改,应先继续在同一 PR 上提交,再进入 merge 决策
- merge 后先由 Codex 同步 `current_state.md` / `docs/active_context.md`,再由 `roadmap-updater` 完成 roadmap factual update,之后再进入 tag 决策
- phase 完成后建议打 tag

### Tag 规则

- 使用语义化版本号:`v<major>.<minor>.<patch>`
- **v0.x.0**:表示预发布阶段的里程碑 tag,标记一个或多个 phase 完成后的稳定 checkpoint
- tag 可以与 phase 不同步:不要求每个 phase 都打 tag,也不要求一个 tag 只对应一个 phase
- tag 只在 `main` 分支上打,且只在测试全部通过时打
- 不补打历史 tag;历史 phase 通过 git log 和 closeout 文档追溯

**Tag 决策流程**:

1. **Claude 评估**:每次 phase merge 到 main 后,Claude 判断当前 main 是否构成一个有意义的能力里程碑,并给出 tag 建议(打 / 不打 / 等下一个 phase 再打)
2. **Human 决策**:Human 根据 Claude 建议决定是否打 tag
3. **Codex 同步文档**:若 Human 决定打 tag,Codex 先更新 `README.md` 与 `current_state.md` 中与新 tag 对齐的内容
4. **Human 审阅并提交 release docs**:将上述 tag-level 文档更新提交到 `main`
5. **Human 执行 tag**:`git tag -a v<X>.<Y>.<Z> -m "<tag message>"`
6. **Codex 同步结果**:Human 确认 tag 完成后,Codex 更新 `docs/active_context.md` 的 tag 状态

Claude 评估 tag 时应考虑:
- 自上一个 tag 以来是否有用户可感知的能力增量
- 当前 main 是否处于稳定状态(无进行中的重构或已知破坏性问题)
- 是否存在即将消化的 concern 可能改变公共 API(如是,建议等 concern 消化后再打)

---

## Phase 与 Git 的对齐规则

本仓库中:

- phase 负责开发节奏
- track 负责系统方向
- slice 负责本轮语义目标
- branch 负责承载该轮开发
- commit 负责记录 slice 内的小步变更
- tag 负责标记跨 phase 的稳定里程碑

下一轮工作应重新选择 active track / phase / slice,而不是默认继续扩张已完成的 phase。

---

## 下一轮工作的默认边界判断

如果某项改动不直接服务于当前 active phase 的 kickoff,应先判断:

- 它是否属于下一轮新 slice 的自然子任务
- 它是否应推迟到下一 phase
- 它是否只是当前实现内部的局部 refactor

不要再以 `post-phase-*` 的形式新增过渡型命名。

---

## 开发时的快速非目标提醒

完整非目标清单与理由见 README "Non-Goals" 章节。开发协作时常见的"不要顺手做"提醒:

- 不主动推进多租户、分布式 worker、云端 truth 镜像(当前 phase 非目标)
- 不绕过 `apply_proposal` 直接写 canonical / route / policy(违反宪法)
- 不把品牌名(Claude Code / Codex / Aider 等)写进设计文档主体(违反 P4)
- 不在已完成 phase 的 closeout 之后回头扩张该 phase 的范围
- 不引入"看起来应该有"的额外平台复杂度

---

## 本文件的职责边界

`AGENTS.md` 是:
- 仓库入口控制面
- 协作模式与 Git 节奏说明
- 全仓库文档结构索引
- 长期协作规则说明

`AGENTS.md` 不是:
- 项目宪法(→ `docs/design/INVARIANTS.md`)
- 系统能力清单(→ README "Core Capabilities" + `docs/design/EXECUTOR_REGISTRY.md`)
- 长期设计原则副本(→ `docs/design/INVARIANTS.md` §1)
- 完整 phase 历史总表(→ git log)
- 当前开发流水账(→ `docs/active_context.md`)
- 详细恢复日志(→ `current_state.md`)
- 第二份 README
