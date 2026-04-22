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

**当前 tag: `v0.7.0`** — Knowledge Era：知识层 SQLite SSOT + Librarian Agent + sqlite-vec 可退级 RAG

本仓库已形成稳定运行基线，395 tests passed + 8 eval passed。

当前默认工作起点不是早期 MVP，而是：

- 从系统 track 出发选择下一轮工作
- 通过新的 phase slice 明确边界
- 保持已有本地任务循环、artifact 语义、恢复路径与 inspect/review 入口的稳定性

当前 phase 进度、活跃方向等实时信息不在本文件维护，请查阅：
- `docs/active_context.md` — 当前轮次状态
- `docs/roadmap.md` — 跨 phase 演进路线

---

## 当前系统能力（与 tag 对齐）

以下描述与最新 tag 对齐，仅在打新 tag 时更新。Phase 级增量变更请查阅 `docs/active_context.md`。

- 本地优先任务循环：显式 state / events / artifacts / checkpoint / resume / retry / rerun
- 显式 route / topology / dispatch / execution-site / handoff / policy 记录
- taxonomy 元数据、taxonomy-aware routing guard、operator-facing taxonomy visibility
- staged knowledge capture、review queue、promote / reject、capability-aware 写入边界
- **知识真值 SQLite SSOT**：Evidence / Wiki 知识读取已切换为 SQLite primary，文件系统仅保留 mirror / export / fallback 视图
- **知识迁移与诊断入口**：`swl knowledge migrate` 支持 dry-run / 实迁 / 幂等回填；`swl doctor sqlite` 已包含知识层健康检查
- **LibrarianAgent 边界化落地**：`LibrarianExecutor` 升级为 `LibrarianAgent` 主体，结构化 `KnowledgeChangeLog` 与 canonical 写入 authority guard 已成为稳定基线
- **本地向量 RAG 与平滑退级**：`sqlite-vec` 作为可选依赖接入，可用时走向量检索，不可用时自动回退到文本匹配并输出 WARN
- canonical registry、reuse visibility、dedupe / supersede audit、regression inspection
- grounding evidence artifact、locked grounding refs、resume-stable grounding state
- 有界 1:N TaskCard planning、DAG subtask orchestration、parent-task artifact/event aggregation
- 外部会话摄入：ChatGPT / Claude / Open WebUI / Markdown 解析、规则式过滤、`swl ingest` CLI
- 多轮 Debate Topology：结构化 `ReviewFeedback`、单任务 / 子任务 feedback-driven retry、`waiting_human` 熔断
- **异步执行主链**：`execute_async()` / `run_review_gate_async()` / `run_task_async()` 已落地，CLI 生命周期仍保留同步兼容壳
- **异步并发 ReviewGate**：N-Reviewer 审查切为 `asyncio.gather(..., return_exceptions=True)` 并发执行，支持 reviewer timeout 隔离
- **异步子任务编排**：`AsyncSubtaskOrchestrator` 提供 level-based 并发执行能力，多 card 路径统一走 async orchestration
- **SQLite 任务真值层**：`.swl/swallow.db` 以 WAL 模式持久化 `TaskState` / `EventLog`，默认 backend 已切为 sqlite primary + file mirror/fallback
- **迁移与诊断入口**：`swl migrate` 支持 legacy file task → SQLite 幂等回填；`swl doctor sqlite` 与默认 `swl doctor` 输出已包含 SQLite 健康检查
- **事件循环边界收紧**：同步 `run_task()` 在已有 event loop 中会明确拒绝并提示调用方改用 `await run_task_async(...)`
- **N-Reviewer 共识门禁**：`TaskCard.reviewer_routes` / `consensus_policy` + `majority` / `veto` 聚合，保持 `_debate_loop_core()` 外部接口不变
- **TaskCard 级真实成本护栏**：`token_cost_limit` + event log `token_cost` 聚合，预算耗尽统一进入 `waiting_human`，`checkpoint_snapshot` 可见 `human_gate_budget_exhausted`
- **只读一致性抽检**：`swl task consistency-audit <task-id> --auditor-route <route>` 对既有 artifact 发起跨模型审计，产出 `consistency_audit_*.md` 且不污染 task state
- Capability-aware Strategy Router + RouteRegistry + 四级候选匹配 + binary fallback
- Claude XML / Codex FIM dialect adapters + 共享 dialect_data prompt 数据层
- 结构化 executor event telemetry (task_family / logical_model / physical_route / latency_ms / degraded / error_code)
- 只读 Meta-Optimizer：event log 扫描 + route health / failure fingerprint / degradation trend 提案
- Meta-Optimizer 遥测修正：fallback token_cost 回计 + debate retry telemetry 隔离统计
- operator-facing inspect / review / control / intake / grounding surfaces
- LibrarianExecutor side-effect 收口：executor 只返回结构化 payload，orchestrator 接管全部持久化
- Librarian 持久化原子提交：state / knowledge / index 批量 `os.replace` + rollback
- 共享 debate loop 核心：单任务与子任务路径复用统一 `_debate_loop_core()`
- acknowledge_task route_mode 参数化 + canonical_write_guard 运行时审计 + CodexFIMDialect FIM 标记转义
- 只读 Web 控制中心（`swl serve`）：FastAPI JSON API + 单页 HTML 仪表盘 + Artifact Review 双栏视图 + Subtask Tree + artifact compare + execution timeline，零写入 `.swl/`，无前端构建工具链
- Eval-Driven Development 基础设施：`tests/eval/` + `@pytest.mark.eval` 标记隔离 + Ingestion 降噪质量基线（precision/recall）+ Meta-Optimizer 提案质量基线（scenario-based）+ 共识 majority / veto / budget exhaustion 质量基线
- ChatGPT 对话树还原：parent-child 树构建、主路径/侧枝识别、abandoned branch 语义保留
- `swl ingest --summary`：Decisions / Constraints / Rejected Alternatives / Statistics 结构化摘要
- **HTTP 执行器（HTTPExecutor）**：httpx 直连本地 new-api（OpenAI-compatible），替代 subprocess CLI 成为系统主 LLM 路径，真实多模型网络分发能力首次落地
- **CLI 执行器去品牌化（CLIAgentExecutor）**：配置驱动的 `CLIAgentConfig`，Codex / Cline 作为配置实例，消除品牌硬编码，`run_executor_inline` 对未知 executor 显式报错
- **多模型 HTTP 路由**：`http-claude`（claude_xml）/ `http-qwen`（plain_text）/ `http-glm`（plain_text）/ `http-gemini`（plain_text）/ `http-deepseek`（codex_fim）+ `local-cline` 全部注册
- **分层降级矩阵**：`http-claude → http-qwen → http-glm → local-cline → local-summary`，循环检测保护，429 rate-limit 走重试路径而非立即降级
- **自建遥测层**：HTTPExecutor 从 API 响应 `usage` 字段捕获真实 token 数据，替代静态成本估算，Meta-Optimizer 消费真实成本数据

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

本项目采用两 agent + 人工协作开发（Gemini 已于 2026-04-23 移除）：

| 角色 | 职责 | 控制文件 |
|------|------|----------|
| **Claude** | 方案拆解、风险评估、PR 评审、分支建议、tag 评估、roadmap 优先级维护 | `CLAUDE.md` → `.agents/claude/` |
| **Codex** | 代码实现、测试、状态同步、slice 级 commit 建议、PR 文案整理 | `.codex/session_bootstrap.md` → `.agents/codex/` |
| **Human** | 设计审批、git 提交执行、PR 创建、合并决策 | — |

原 Gemini 职责由 Claude subagent 承接（`.claude/agents/`）：

| Subagent | 模型 | 职责 |
|----------|------|------|
| `context-analyst` | Sonnet | phase 启动时产出 context_brief |
| `roadmap-updater` | Sonnet | phase closeout 后增量更新 roadmap |
| `consistency-checker` | Sonnet | 实现后对比设计文档产出 consistency_report |

协作流程定义见 `.agents/workflows/feature.md`。
共享规则见 `.agents/shared/`。
状态同步规则见 `.agents/shared/state_sync_rules.md`。
跨 phase 蓝图对齐见 `docs/roadmap.md`（Claude 维护推荐队列，subagent 维护差距总表）。

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
- `docs/roadmap.md`
- `current_state.md`

用途：
- `AGENTS.md`：入口控制面与长期规则
- `docs/active_context.md`：当前唯一高频状态入口
- `docs/roadmap.md`：跨 phase 蓝图对齐活文档，新 phase 启动时从此选方向
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
3. `docs/roadmap.md`
4. `docs/system_tracks.md`
5. `current_state.md`

`docs/active_context.md` 会指向当前活跃 phase 的具体文档（kickoff / closeout 等）。
不要默认回读所有历史 phase；历史 phase 通过 `docs/plans/<phase>/closeout.md` 按需追溯。

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
- 必要时更新 `AGENTS.md`（仅限长期规则变更，不含 phase 进度）

### Tag 级更新
仅在打新 tag 时更新：

- `README.md` / `README.zh-CN.md` — "当前实现概况"章节与 tag 对齐
- `AGENTS.md` — "当前系统能力"章节与 tag 对齐

说明：
- README 和 AGENTS.md 不跟踪 phase 级进度，避免更新不及时引发上下文冲突
- phase 级实时信息由 `docs/active_context.md` 和 `docs/roadmap.md` 承载

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
- 如某轮 phase 已明确拆为多个 slices，则必须逐 slice 提交；禁止将多个 slices 的实现、测试和状态同步压成一次大包 commit
- 如某个 slice 尚未完成独立验证，则不得提前合并进下一个 slice 的提交范围
- 需要发起 PR 时，Codex 负责将 PR 文案整理到仓库根目录 `./pr.md`，Human 先 push branch，再据此创建 PR
- PR 创建后如 review 结论或实现内容变化，Codex 应继续更新 `./pr.md`，Human 再决定是否同步到 PR 描述

### 合并规则

- feature branch 完成后再合并回 `main`
- `main` 只接收阶段性稳定成果
- 合并前至少确认测试与基本 CLI 入口可用
- 合并前应确认 `review_comments.md` 已处理完毕，且 `./pr.md` 已反映当前实现与 review 结论
- 如 Claude review 后仍有实现修改，应先继续在同一 PR 上提交，再进入 merge 决策
- phase 完成后建议打 tag

### Tag 规则

- 使用语义化版本号：`v<major>.<minor>.<patch>`
- **v0.x.0**：表示预发布阶段的里程碑 tag，标记一个或多个 phase 完成后的稳定 checkpoint
- tag 可以与 phase 不同步：不要求每个 phase 都打 tag，也不要求一个 tag 只对应一个 phase
- tag 只在 `main` 分支上打，且只在测试全部通过时打
- 不补打历史 tag；历史 phase 通过 git log 和 closeout 文档追溯

**Tag 决策流程**：

1. **Claude 评估**：每次 phase merge 到 main 后，Claude 判断当前 main 是否构成一个有意义的能力里程碑，并给出 tag 建议（打 / 不打 / 等下一个 phase 再打）
2. **Human 决策**：Human 根据 Claude 建议决定是否打 tag
3. **Human 执行**：`git tag -a v0.x.0 -m "<tag message>"`
4. **Codex 同步**：打 tag 后，Codex 更新 README 和 AGENTS.md 中的 tag 引用与系统能力描述

Claude 评估 tag 时应考虑：
- 自上一个 tag 以来是否有用户可感知的能力增量
- 当前 main 是否处于稳定状态（无进行中的重构或已知破坏性问题）
- 是否存在即将消化的 concern 可能改变公共 API（如是，建议等 concern 消化后再打）

---

## Phase 与 Git 的对齐规则

本仓库中：

- phase 负责开发节奏
- track 负责系统方向
- slice 负责本轮语义目标
- branch 负责承载该轮开发
- commit 负责记录 slice 内的小步变更
- tag 负责标记跨 phase 的稳定里程碑

下一轮工作应重新选择 active track / phase / slice，而不是默认继续扩张已完成的 phase。

---

## 下一轮工作的默认边界判断

如果某项改动不直接服务于当前 active phase 的 kickoff，应先判断：

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
