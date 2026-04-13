# AGENTS.md

## 仓库定位

本仓库用于构建一个**面向真实项目工作的有状态 AI workflow 系统**。  
系统长期围绕以下五层组织：

- orchestrator
- harness runtime
- capabilities
- state / memory / artifacts
- provider routing

本仓库不是通用聊天机器人仓库，也不是纯 RAG 仓库。  
它的目标是让 AI 围绕真实任务进行：编排、检索、执行、记录、恢复、复用。

---

## 当前项目状态

本仓库当前已经完成：

- Phase 0 到 Phase 27 基线
- post-Phase-2 retrieval baseline
- post-Phase-5 executor / external-input slice
- post-Phase-5 retrieval / memory-next slice

这些历史阶段视为**已完成的稳定 checkpoint**，不再作为默认继续方向。

当前默认工作起点不是早期 MVP，而是：

- 从系统 track 出发选择下一轮工作
- 通过新的 phase slice 明确边界
- 保持已有本地任务循环、artifact 语义、恢复路径与 inspect/review 入口的稳定性

---

## 当前 active 方向

当前最近完成的 phase 为：

- **Latest Completed Track**：`Retrieval / Memory` (Primary) + `Workbench / UX` (Secondary)
- **Latest Completed Phase**：`Phase 27`
- **Latest Completed Slice**：`Knowledge-Driven Task Grounding Baseline`

Phase 27 已完成的核心内容包括：

- 从 canonical retrieval hits 中抽取 grounding evidence artifact
- 将 grounding refs 与 grounding_locked 落入 TaskState，保证 resume 稳定
- 在 `inspect` / `review` / `task grounding` 中暴露 grounding 状态与 artifact
- 保持 grounding 走 artifact 路径，不直接注入 prompt
- 完成 Phase 27 实现、评审、merge 与 closeout 收口

当前默认不应继续无边界扩张到：

- 真实 remote worker execution
- cross-machine transport implementation
- distributed job queue / hosted orchestration platform
- automatic remote dispatch
- remote handoff driven policy mutation or execution gating
- operator-selectable remote override policy without fresh kickoff
- dynamic taxonomy registration / discovery without fresh kickoff
- ad hoc taxonomy-aware route selection without fresh kickoff
- workbench UI expansion beyond the scoped CLI surface without fresh kickoff
- staged knowledge automatic promotion without fresh kickoff
- staged knowledge retrieval integration without fresh kickoff
- cross-task staged candidate merge / dedupe without fresh kickoff
- dynamic runtime policy engines without fresh kickoff
- manifest-level capability pruning without fresh kickoff
- semantic merge / conflict resolution without fresh kickoff
- automatic canonical promotion or conflict arbitration without fresh kickoff
- vector grounding or semantic retrieval without fresh kickoff
- prompt-level direct injection of canonical knowledge without fresh kickoff
- agentic multi-hop RAG without fresh kickoff

---

## 长期稳定原则

### 架构原则

- 优先保持 orchestrator 与 harness runtime 的边界清晰。
- capabilities 是一等对象，不应退化为零散 prompt 片段。
- state、events、artifacts 必须保持分层，而不是混成单一输出。
- retrieval 是系统层能力，不是某个单一 executor 的附属功能。
- provider、runtime backend、executor 必须区分，不要混用概念。
- 当前执行器家族应继续区分 API executor 与 CLI executor 的定位边界。

### 执行原则

- 优先做最小可闭环实现，再逐步扩展。
- 优先显式、可读、可检查的模块，不优先追求抽象花样。
- 优先本地、可恢复、可追踪的执行路径。
- 除非当前 phase 明确要求，否则不要顺手扩大范围。
- 已完成 phase 的 checkpoint 不应被模糊回退成“重新整理一下旧 MVP”。

### 检索与知识原则

- retrieval 必须保持可追踪、可引用、可复用。
- 外部 planning 应进入 task semantics，而不是散落在聊天历史中。
- 外部 knowledge 应进入 staged knowledge pipeline，而不是直接写入 canonical memory。
- knowledge promotion 必须显式 gated，不默认自动执行。
- domain behavior 应进入 domain pack / capability pack，而不是散落在临时 prompt 中。

---

## 协作模式

本项目采用三 agent + 人工协作开发：

| 角色 | 职责 | 控制文件 |
|------|------|----------|
| **Gemini** | 长上下文阅读、上下文摘要、一致性检查 | `.gemini/settings.md` → `.agents/gemini/` |
| **Claude** | 方案拆解、风险评估、PR 评审、分支建议 | `CLAUDE.md` → `.agents/claude/` |
| **Codex** | 代码实现、测试、状态同步、slice 级 commit 建议、PR 文案整理 | `.codex/session_bootstrap.md` → `.agents/codex/` |
| **Human** | 设计审批、git 提交执行、PR 创建、合并决策 | — |

协作流程定义见 `.agents/workflows/feature.md`。
共享规则见 `.agents/shared/`。
状态同步规则见 `.agents/shared/state_sync_rules.md`。

---

## 当前文档结构

本仓库文档按五层组织：

### 1. 公开说明层
- `README.md`
- `README.zh-CN.md`

用途：
- 面向读者解释项目定位、架构概览、快速开始
- 不承担当前轮次状态板职责

### 2. 当前执行层
- `AGENTS.md`
- `docs/active_context.md`
- `current_state.md`

用途：
- `AGENTS.md`：入口控制面与长期规则
- `docs/active_context.md`：当前唯一高频状态入口
- `current_state.md`：恢复入口，不是完整开发编年史

### 3. 阶段计划层
- `docs/plans/<phase>/kickoff.md`
- `docs/plans/<phase>/breakdown.md`
- `docs/plans/<phase>/closeout.md`
- `docs/plans/<phase>/commit_summary.md`（可选）
- `docs/plans/<phase>/context_brief.md`（Gemini 产出）
- `docs/plans/<phase>/design_decision.md`（Claude 产出）
- `docs/plans/<phase>/risk_assessment.md`（Claude 产出）
- `docs/plans/<phase>/review_comments.md`（Claude 产出）
- `docs/plans/<phase>/consistency_report.md`（Gemini 产出，可选）

用途：
- 组织当前 phase 的目标、拆解、收口、多 agent 产出物
- phase 文档以目录为边界
- 未来不再新增 `post-phase-*` 命名

### 4. 多 Agent 控制层
- `.agents/shared/` — 共享规则、读取顺序、状态同步规则
- `.agents/codex/` — Codex 角色定义、专属规则、模板、skills
- `.agents/claude/` — Claude 角色定义、专属规则
- `.agents/gemini/` — Gemini 角色定义、专属规则
- `.agents/workflows/` — 多角色协作流程定义
- `.agents/templates/` — PR body 等共享模板

用途：
- 固定各角色分工、读取顺序、行动边界
- 定义协作流程和产出物格式
- 各工具原生入口（`CLAUDE.md`、`.codex/session_bootstrap.md`、`.gemini/settings.md`）指向此层

### 5. 工具原生入口（thin pointer）
- `CLAUDE.md` → `.agents/shared/` + `.agents/claude/`
- `.codex/session_bootstrap.md` → `.agents/shared/` + `.agents/codex/`
- `.gemini/settings.md` → `.agents/shared/` + `.agents/gemini/`

用途：
- 各 agent 工具的自动加载入口
- 不包含实际规则内容，只负责引导读取 `.agents/` 下的文件

---

## 当前 authoritative docs

开始新一轮规划或实现前，优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/system_tracks.md`
4. `current_state.md`
5. `docs/plans/phase27/closeout.md`

仅在需要时再读取：

- `docs/plans/phase27/context_brief.md`
- `docs/plans/phase27/design_decision.md`
- `docs/plans/phase27/risk_assessment.md`
- `docs/plans/phase27/review_comments.md`
- `docs/plans/phase26/closeout.md`
- `current_state.md`
- `docs/plans/<older-phase>/closeout.md`
- `docs/archive/*`
- 旧的 `post-phase-*` 归档材料

不要默认回读所有历史 phase。

---

## 文档更新节奏

### 高频更新
只更新：

- `docs/active_context.md`

适用场景：
- 当前 slice 进度变化
- 当前目标、下一步、阻塞项变化
- 当前 branch / active phase 变化

### 低频更新
只在 phase 或 major slice 收口时更新：

- `current_state.md`
- `docs/plans/<phase>/closeout.md`
- 必要时更新 `AGENTS.md`
- 必要时更新 `README.md` / `README.zh-CN.md`

### 可选更新
- `docs/plans/<phase>/commit_summary.md`

说明：
- commit summary 不是强制产物
- 只有当手工提交、阶段归纳或 release note 明显受益时才写

---

## Git 工作节奏

### 分支规则

不要直接在 `main` 上进行日常开发。

推荐方式：

- `main`：稳定主线
- `feat/<phase-or-slice>`
- `fix/<topic>`
- `docs/<topic>`

当前推荐分支命名方式：

- `feat/<phase-or-slice>`

### 切分支时机

默认规则：

1. `design_decision.md` 与 `risk_assessment.md` 通过人工审批后
2. Human 先从 `main` 切出本轮 feature branch
3. Codex 再在该 branch 上开始代码实现

补充要求：

- 设计文档产出完成但尚未通过人工 gate 时，不进入实现分支，不开始代码改动
- 一旦进入实现阶段，默认不继续把功能开发留在 `main`
- 如当前工作只是纯文档修订且不属于实现阶段，可留在当前分支，由人工决定是否另开 `docs/<topic>`

### 提交规则

提交信息统一使用：

- `type(scope): summary`

推荐类型：

- `feat`
- `fix`
- `refactor`
- `test`
- `docs`
- `chore`

要求：

- 一个 commit 只表达一类变化
- 尽量避免把代码、测试、README、状态同步全部塞进一个大提交
- 高频状态变更只同步到 `docs/active_context.md`
- phase 结束时再做归档同步提交

### 提交节奏规则

每个 phase 的人工提交分两次：

1. **计划实现提交**：Codex 完成代码实现后，人工审查并提交（包含功能代码 + 测试）
2. **审查收口提交**：Claude 完成 PR review、closeout 文档后，人工提交收口材料（review_comments + closeout + 状态同步）

两次提交之间是 Claude 的评审环节。不要把实现和收口材料混在同一次提交中。

补充要求：

- design gate 通过后，应先完成 feature branch 切换，再开始第一个实现 slice
- git 提交由人工执行，Codex 只在对话中给出建议命令
- commit 应按 slice 拆分；每完成一个 slice，Codex 都应给出一次提交建议
- 每个 slice 的默认节奏为：Codex 实现并验证 → Human 审查当前 diff → Human 执行该 slice commit
- 需要发起 PR 时，Codex 负责将 PR 文案整理到仓库根目录 `./pr.md`，Human 先 push branch，再据此创建 PR
- PR 创建后如 review 结论或实现内容变化，Codex 应继续更新 `./pr.md`，Human 再决定是否同步到 PR 描述

### 合并规则

- feature branch 完成后再合并回 `main`
- `main` 只接收阶段性稳定成果
- 合并前至少确认测试与基本 CLI 入口可用
- 合并前应确认 `review_comments.md` 已处理完毕，且 `./pr.md` 已反映当前实现与 review 结论
- 如 Claude review 后仍有实现修改，应先继续在同一 PR 上提交，再进入 merge 决策
- phase 完成后建议打 tag

---

## Phase 与 Git 的对齐规则

本仓库中：

- phase 负责开发节奏
- track 负责系统方向
- slice 负责本轮语义目标
- branch 负责承载该轮开发
- commit 负责记录 slice 内的小步变更

对于已完成的 `Phase 18 / Execution Topology / Remote Handoff Contract Baseline`，当前收口结果包括：

1. `kickoff.md` 已完成
2. `breakdown.md` 已完成
3. feature branch 已切出并承载实现
4. remote handoff contract record / report baseline 已完成
5. `execution-site` / `dispatch` / `handoff` / `control` / `inspect` / `review` 的 remote handoff surface 已完成
6. `closeout.md` 已完成

下一轮工作应重新选择 active track / phase / slice，而不是默认继续扩张 Phase 18。

---

## 下一轮工作的默认边界判断

如果某项改动不直接服务于已完成的 Phase 12 closeout 之后的新 kickoff，应先判断：

- 它是否属于下一轮新 slice 的自然子任务
- 它是否应推迟到下一 phase
- 它是否只是当前实现内部的局部 refactor

不要再以 `post-phase-*` 的形式新增过渡型命名。

---

## 当前非目标

除非当前 phase 明确要求，否则不要默认推进以下方向：

- 多租户架构
- 分布式 worker 集群
- 大规模托管基础设施
- 复杂权限 / 计费系统
- 广泛插件市场
- 隐式全局记忆
- 自动 knowledge promotion
- 无边界扩张 workbench UI
- 仅因为“看起来应该有”而引入额外平台复杂度

---

## Agent 读取与工作要求

所有 agent 新会话按以下顺序读取：

1. `.agents/shared/read_order.md`（按其中指引继续读取共享规则）
2. 各自的 `role.md` 和 `rules.md`
3. `AGENTS.md`
4. `docs/active_context.md`
5. `docs/plans/<active-phase>/` 下的相关文件（按需）

详细读取顺序见各工具原生入口文件和 `.agents/shared/read_order.md`。

所有 agent 应遵守：

- 先确认 active track、active phase、active slice
- 不把历史归档材料误当作当前工作目标
- 不擅自扩大当前 phase 范围
- 高频只更新 `docs/active_context.md`
- 每次完成 workflow step 后必须更新状态（见 `.agents/shared/state_sync_rules.md`）
- 各角色只在自己的可写范围内操作（见各 `role.md`）

---

## 本文件的职责边界

`AGENTS.md` 是：

- 仓库入口控制面
- 当前 active 工作方向说明
- 长期规则说明
- phase / Git / 文档节奏说明

`AGENTS.md` 不是：

- 完整 phase 历史总表
- 当前开发流水账
- 所有 closeout 的索引页
- 详细恢复日志
- 第二份 README
