# System Tracks

## 文档目的

本文件用于定义仓库中的**长期系统 track 地图**。

它回答的问题是：

- 这个系统长期有哪些主要方向
- 每个方向分别负责什么
- 新 phase 应该如何挂靠到这些方向上
- 规划时如何避免把多个系统问题混成一个大包

本文件不是：

- 当前 phase 的状态板
- 当前 active slice 说明
- 历史 phase 编年史
- closeout 索引页
- commit summary 入口

当前轮次信息请看：

- `AGENTS.md`
- `docs/active_context.md`

当前 phase 计划请看：

- `docs/plans/<phase>/kickoff.md`
- `docs/plans/<phase>/breakdown.md`
- `docs/plans/<phase>/closeout.md`

---

## 为什么需要 track

仓库已经明显超出“单一 MVP 阶段”的范围。  
如果没有显式 track，后续 phase 很容易把以下问题混在一起推进：

- execution topology
- retrieval / memory
- capabilities
- workbench / UX
- evaluation / policy
- core loop

这样会带来几个问题：

- phase 边界不清晰
- Git 提交难以对齐真正语义
- closeout 难以判断“这轮到底完成了什么”
- agent 容易把当前 phase 扩张成混合目标包

track 的作用，就是把：

- **长期系统方向**
- **当前 phase**
- **当前 slice**

分开。

---

## Track Map

---

## 1. Core Loop

### 负责范围

- orchestrator 生命周期
- harness runtime 主循环
- task intake
- phase / step progression
- state truth
- event truth
- artifact 写入时机
- resume / retry / rerun / recovery 的流程边界

### 这个 track 关注的核心问题

- 任务从创建到结束的生命周期是否清晰
- 当前状态与历史事件是否语义一致
- artifact 是否在正确时机写出
- 恢复、重试、重跑是否有明确边界
- 主循环是否在扩展中保持稳定

### 长期目标

- 更强的恢复与中断处理语义
- 更清晰的 operator checkpoint
- 更成熟的 stop / resume / retry 边界
- 在保持本地优先前提下支持更复杂工作流推进

---

## 2. Retrieval / Memory

### 负责范围

- source adapters
- parsing / chunking
- ranking / rerank
- grounding outputs
- retrieval artifact indexing
- retrieval-memory reuse
- retrieval evaluation
- external planning ingestion 边界
- external knowledge capture
- staged knowledge pipeline
- reusable knowledge selection
- verification / canonicalization / noise control

### 这个 track 关注的核心问题

- 系统如何获取、组织、复用外部和内部知识
- retrieval 输出是否可追踪、可引用、可复用
- task semantics 与 knowledge objects 的边界是否清晰
- staged knowledge 如何从记录走向 review / promotion / reuse readiness
- 历史知识如何在不失控的前提下进入后续任务

### 长期目标

- 更清晰的 historical context policy
- 更明确的 indexing / refresh / invalidation 策略
- 更稳定的 reusable knowledge 路径
- 更好的 retrieval evaluation 深度
- 更清晰的 staged `raw` / `candidate` / `verified` / `canonical` 语义

---

## 3. Execution Topology

### 负责范围

- executor boundaries
- route selection
- backend / executor capability fit
- execution-site boundary
- local vs remote boundary
- transport semantics
- handoff readiness
- executor family distinction
- API executor vs CLI executor routing boundary

### 这个 track 关注的核心问题

- 任务应该由谁执行、在哪执行、如何交接
- route 是否与 executor family 和 capability 对齐
- local-inline、local-detached、future remote 之间的边界是否清晰
- handoff / ownership / dispatch truth 是否可检查

### 长期目标

- 更真实的 remote execution boundary
- 跨机器 transport / job handoff 语义
- 更广的 family-aware routing
- hosted API execution 与 CLI execution 的更清晰整合规则

---

## 4. Capabilities

### 负责范围

- tools
- skills
- profiles
- workflows
- validators
- capability packs
- manifest / assembly / inspection / validation

### 这个 track 关注的核心问题

- 系统能力如何显式声明
- capability 如何被选择、组合、检查、替换
- capability 如何服务 routing、execution、validation，而不是只增加复杂度
- domain behavior 如何进入稳定结构，而不是散落在 prompt 中

### 长期目标

- 更清晰的 capability pack 结构
- 更强的组合、版本化与装配规则
- workflow / validator / profile 的更清晰关系

---

## 5. Workbench / UX

### 负责范围

- CLI ergonomics
- artifact inspection paths
- review / handoff usability
- operator-facing control entrypoints
- future TUI / UI surfaces
- planning handoff / knowledge capture 等输入入口

### 这个 track 关注的核心问题

- operator 是否能快速看到任务状态、下一步、阻塞项
- inspect / review / control / queue 等路径是否足够清晰
- 输入、检查、恢复、对比这些工作流是否可用
- workbench 是否在扩展中保持边界清晰，而不是无止境加命令

### 长期目标

- 更强的 action-oriented browsing
- 更友好的 review / control path
- 更成熟的未来 workbench interface
- 更清晰的 imported planning / imported knowledge operator entrypoints

---

## 6. Evaluation / Policy

### 负责范围

- validation
- compatibility checks
- retrieval evaluation
- retry / stop / escalation policy
- budget / timeout policy
- future permission / operator policy controls

### 这个 track 关注的核心问题

- 系统如何判断当前执行结果是否可靠
- route、execution、knowledge、retrieval 是否满足约束
- retry / stop / budget 是否有显式判断
- policy 是否可检查、可解释、可用于 operator 决策

### 长期目标

- 更广的执行策略
- 更强的 operator safety checkpoint
- 更系统化的跨 track regression coverage

---

## Phase 与 Track 的关系

### 基本规则

每个新 phase 都应先回答三件事：

1. **Primary Track** 是什么
2. **Secondary Tracks** 是什么（如果有）
3. **明确不做什么**

也就是说：

- track 负责长期系统方向
- phase 负责阶段节奏
- slice 负责当前轮次的语义目标

---

## Phase 规划规则

新 phase 不应从“想加点什么功能”开始，而应从以下流程开始：

### 第一步
先确定当前最优先的 track。

### 第二步
在该 track 下定义最小的下一个 phase / slice。

### 第三步
显式写出：

- 当前目标
- 当前非目标
- 当前设计边界
- 当前完成条件

### 第四步
再进入：

- kickoff
- breakdown
- implementation
- closeout

---

## 推荐的 phase 命名方式

未来新增工作不再默认采用 `post-phase-*`。

推荐采用：

- 正式 phase 编号
- 明确 track
- 明确 slice

例如：

- `Phase 12`
- `Track: Retrieval / Memory`
- `Slice: Knowledge Promotion And Reuse Review`

这样可以让：

- docs 目录
- Git branch
- closeout
- tag
- Codex 读取顺序

都保持一致。

---

## 当前默认规划方式

当前默认规划应遵循：

- 先看 `docs/system_tracks.md`
- 再看 `AGENTS.md`
- 再看 `docs/active_context.md`
- 然后写当前 phase 的 `kickoff.md` 与 `breakdown.md`

不要跳过 track 选择，直接开始写新 phase。

---

## 使用本文件时的注意事项

### 适合来这里找什么
- 当前系统长期有哪些方向
- 某个新 phase 应挂在哪个方向
- 某类问题属于哪个 track
- 哪些问题不应被混成一个 phase

### 不适合来这里找什么
- 当前 phase 已做到哪一步
- 当前下一步是什么
- 当前 closeout 判断是什么
- 当前推荐 commit summary 是什么

这些内容应分别去：

- `docs/active_context.md`
- `docs/plans/<phase>/closeout.md`
- `current_state.md`

---

## 本文件的职责边界

本文件用于：

- 作为仓库长期系统地图
- 为 phase 规划提供 track 级视角
- 避免后续 phase 成为混合目标包

本文件不用于：

- 当前状态同步
- 高频上下文更新
- phase closeout 收口
- 历史 phase 编年归档