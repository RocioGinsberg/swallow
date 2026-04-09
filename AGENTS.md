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

- Phase 0 到 Phase 15 基线
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

- **Latest Completed Track**：`Evaluation / Policy`
- **Latest Completed Phase**：`Phase 15`
- **Latest Completed Slice**：`Canonical Reuse Evaluation Baseline`

Phase 15 已完成的核心内容包括：

- 建立 canonical reuse evaluation record / summary / report baseline
- 提供 `canonical-reuse-evaluate`、`canonical-reuse-eval`、`canonical-reuse-eval-json` 的 operator 入口
- 在 `inspect` / `review` 中暴露 canonical reuse evaluation 摘要
- 让 evaluation judgment 能解析 canonical citation 并追到 canonical metadata
- 在已有 `retrieval.json` 时为 evaluation 附带 retrieval provenance

当前默认不应继续无边界扩张到：

- 自动 canonical reuse policy learning
- 大范围 ranking / rerank platform 化
- queue / control 中的 evaluation workflow 扩张
- canonical freshness / invalidation workflow
- remote evaluation sync

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

## 当前文档结构

本仓库文档按四层组织：

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

用途：
- 组织当前 phase 的目标、拆解、收口
- phase 文档以目录为边界
- 未来不再新增 `post-phase-*` 命名

### 4. Codex 控制层
- `.codex/session_bootstrap.md`
- `.codex/rules.md`
- `.codex/templates/*`

用途：
- 规定 Codex 读取顺序、工作规则、模板
- 不应再复制一套完整 phase 正文或历史文档

---

## 当前 authoritative docs

开始新一轮规划或实现前，优先读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/system_tracks.md`
4. `current_state.md`
5. `docs/plans/phase15/closeout.md`

仅在需要时再读取：

- `docs/plans/phase15/kickoff.md`
- `docs/plans/phase15/breakdown.md`
- `docs/plans/phase14/kickoff.md`
- `docs/plans/phase14/breakdown.md`
- `docs/plans/phase13/kickoff.md`
- `docs/plans/phase13/breakdown.md`
- `docs/plans/phase12/kickoff.md`
- `docs/plans/phase12/breakdown.md`
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

### 合并规则

- feature branch 完成后再合并回 `main`
- `main` 只接收阶段性稳定成果
- 合并前至少确认测试与基本 CLI 入口可用
- phase 完成后建议打 tag

---

## Phase 与 Git 的对齐规则

本仓库中：

- phase 负责开发节奏
- track 负责系统方向
- slice 负责本轮语义目标
- branch 负责承载该轮开发
- commit 负责记录 slice 内的小步变更

对于已完成的 `Phase 15 / Evaluation / Policy / Canonical Reuse Evaluation Baseline`，当前收口结果包括：

1. `kickoff.md` 已完成
2. `breakdown.md` 已完成
3. feature branch 已切出并承载实现
4. canonical reuse evaluation record / report / inspect path 已完成
5. canonical citation resolution 与 retrieval provenance attachment 已完成
6. `closeout.md` 已完成

下一轮工作应重新选择 active track / phase / slice，而不是默认继续扩张 Phase 15。

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

## Codex 读取与工作要求

新会话默认按以下顺序读取：

1. `AGENTS.md`
2. `docs/active_context.md`
3. `docs/plans/phase12/kickoff.md`
4. `docs/plans/phase12/breakdown.md`

仅在需要时再读取：

- `current_state.md`
- `docs/plans/<older-phase>/closeout.md`
- `docs/archive/*`

Codex 在本仓库中做规划或实现时，应默认遵守：

- 先确认 active track、active phase、active slice
- 不把历史归档材料误当作当前工作目标
- 不擅自扩大当前 phase 范围
- 不默认更新多个状态文档
- 高频只更新 `docs/active_context.md`
- 规划时显式写明目标、非目标、验收边界
- 实现时尽量让 Git 提交与 slice 对齐

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
