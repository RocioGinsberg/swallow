# Architecture Principles

## 文档目的

本文件用于记录仓库中**长期稳定、低频变动**的架构原则。

它回答的问题是：

- 这个系统长期按什么结构组织
- 哪些边界不应在每个 phase 中反复改变
- 未来新增 phase 或新 slice 时，哪些架构前提应默认成立

本文件不是：

- 当前 phase 的状态板
- 当前实现进度记录
- 历史 phase 总表
- 当前 active 任务说明

当前轮次的工作状态请看：

- `docs/active_context.md`

当前 phase 的目标、拆解与收口请看：

- `docs/plans/<phase>/kickoff.md`
- `docs/plans/<phase>/breakdown.md`
- `docs/plans/<phase>/closeout.md`

---

## 一、系统总结构原则

本仓库长期围绕以下五层组织：

- orchestrator
- harness runtime
- capabilities
- state / memory / artifacts
- provider routing

这些层之间应保持清晰边界，不应因为某一阶段的局部实现便利而重新混合。

---

## 二、orchestrator 与 harness runtime 的边界

### orchestrator 负责什么

orchestrator 负责：

- task 生命周期推进
- phase / step 编排
- route 选择与执行准备
- retrieval 是否发生、何时发生
- handoff、retry、resume、review 等流程决策
- 让状态与 artifact 有一致的推进顺序

### harness runtime 负责什么

harness runtime 负责：

- 执行 retrieval
- 执行 executor
- 落盘 artifacts
- 执行 validation / policy / compatibility / fit 等检查
- 把执行结果组织成可检查记录

### 原则

- orchestrator 决定“做什么、按什么顺序做”
- harness runtime 决定“具体怎么执行这一步并产出记录”
- 不要把 phase 级流程判断塞进 harness
- 不要把具体执行细节散落回 orchestrator

---

## 三、capabilities 的原则

capabilities 是一等对象，不应退化为零散 prompt 片段。

capabilities 可以包括：

- tools
- skills
- profiles
- workflows
- validators

### 原则

- capability 应显式声明，而不是隐式猜测
- capability 应可检查、可组合、可替换
- capability 的存在应帮助 routing、execution、validation，而不是只增加命名复杂度
- domain-specific behavior 优先进入 capability / domain pack，而不是散落进临时实现

---

## 四、state / events / artifacts 的分层原则

系统必须长期保持以下分层：

### state
表示当前任务的当前真值，例如：

- status
- phase
- attempt
- current route / topology / ownership truth

### events
表示 append-only 的历史过程，例如：

- task.run_started
- retrieval.completed
- executor.failed
- task.completed

### artifacts
表示可供人和系统检查的产物，例如：

- summary
- resume note
- retrieval report
- handoff report
- policy report
- memory record

### 原则

- state 不应承担完整历史
- events 不应冒充当前真值
- artifacts 不应替代状态机
- 这三者即使初期存储简单，也必须在语义上分开

---

## 五、retrieval 的原则

retrieval 是系统层能力，不是某个单一 executor 的附属功能。

### retrieval 应负责

- ingestion / parsing / chunking
- metadata
- retrieval strategy
- ranking / rerank
- citation / grounding
- retrieval-facing reusable knowledge selection

### orchestrator 应负责

- 是否检索
- 检索哪个来源
- 是否重新检索
- 何时停止检索
- retrieval 结果如何进入后续执行与 artifact

### 原则

- retrieval 输出必须可追踪、可引用、可复用
- 不要把 retrieval 简化为一次 prompt helper
- 不要把 built-in vendor retrieval 当作唯一知识基底
- source-specific parsing 与 chunking 优先于“一切都一样处理”

---

## 六、外部输入与知识进入系统的原则

### planning 输入
外部 planning 应进入：

- task semantics

而不是散落在聊天历史中。

### knowledge 输入
外部 knowledge 应进入：

- staged knowledge pipeline

而不是直接写入长期 canonical memory。

### staged knowledge 的默认路径

推荐长期维持显式阶段：

- `raw`
- `candidate`
- `verified`
- `canonical`

### 原则

- imported knowledge 必须保留 source traceability
- evidence 边界必须显式
- promotion 不应默认自动进行
- review / promote / reject / reuse-ready 应是显式 operator path
- task objects 与 knowledge objects 必须保持分工

---

## 七、executor 与 backend 的区分原则

必须区分以下概念：

- model
- runtime backend
- executor

进一步还应区分：

- API executor
- CLI executor

### API executor 更适合

- planning
- discussion
- synthesis
- summarization
- structured reasoning
- route judgment

### CLI executor 更适合

- repository / filesystem 操作
- command execution
- tool loop
- environment-bound implementation

### 原则

- 不要把 backend、model、executor 混为一个概念
- routing 应优先面向 capability 和 executor family
- 不要假设所有 backend 都支持相同的 tool loop、handoff、resume、code execution

---

## 八、execution topology 的原则

系统应保持 local-first，但不能把 local 误写成永久限制。

### 当前默认形态

- 本地 workbench
- 可检查的 task state 与 artifacts
- 本地或本机可恢复执行路径
- remote-heavy execution 作为未来可扩展方向

### 原则

- UI 不是 executor
- 执行位置应可抽象
- state 与 artifacts 应在执行位置变化后仍然可理解
- remote-capable 是架构预留，不代表当前必须实现完整远程平台

---

## 九、operator workbench 的原则

operator-facing 路径应优先保持：

- inspectable
- compact
- explicit
- reviewable

当前工作台相关入口，例如：

- inspect
- review
- control
- queue
- checkpoint
- attempts / compare-attempts

其长期目标不是“做大 UI”，而是让 operator 对当前任务、当前边界、当前下一步有清晰视图。

### 原则

- 不把 workbench 变成无边界 UI 扩张容器
- 优先补齐 operator 决策链，而不是表面命令数量
- inspect / review / control 各自的职责应保持区分

---

## 十、phase 组织原则

未来新增工作应采用：

- phase 负责节奏
- track 负责系统方向
- slice 负责当前语义目标

不再新增新的 `post-phase-*` 作为默认命名方式。

### 原则

- phase 文档应放在 `docs/plans/<phase>/`
- 每个 phase 默认包括：
  - `kickoff.md`
  - `breakdown.md`
  - `closeout.md`
  - `commit_summary.md`（可选）
- phase 结束后应形成稳定 checkpoint，而不是无限续写

---

## 十一、Git 与架构演进的关系

Git 在本仓库中不是简单文件快照工具，而是：

- phase 节奏记录器
- slice 演进记录器
- 稳定 checkpoint 的边界工具

### 原则

- 不直接在 `main` 上开发
- 一个 phase 对应一个短生命周期 feature branch
- 一个 slice 对应一个或多个小步 commit
- 大范围方向性重构必须先判断：
  - 是当前 slice 的局部整理
  - 是当前 phase 的自然子任务
  - 还是下一 phase 的正式目标

---

## 十二、文档分层原则

本仓库文档长期按四层组织：

### 公开说明层
- `README.md`
- `README.zh-CN.md`

### 当前执行层
- `AGENTS.md`
- `docs/active_context.md`
- `current_state.md`

### 阶段计划层
- `docs/plans/<phase>/*`

### Codex 控制层
- `.codex/*`

### 原则

- 高频状态只进入 `docs/active_context.md`
- `current_state.md` 只做恢复入口
- `AGENTS.md` 只做入口控制面
- `.codex/` 只做薄控制层，不复制主文档体系
- archive 材料只按需读取，不默认装载

---

## 十三、当前默认非目标

除非某一 phase 明确要求，否则本仓库不应默认优先推进：

- 多租户架构
- 分布式 worker 集群
- 大规模托管基础设施
- 广泛插件市场
- 隐式全局记忆
- 自动 knowledge promotion
- 无边界 workbench UI 扩张
- 仅因为未来可能需要而提前加入的平台型复杂度

---

## 本文件的职责边界

本文件用于：

- 固定长期稳定架构原则
- 说明系统层边界
- 约束未来 phase 与新 slice 的默认前提

本文件不用于：

- 高频状态更新
- 当前 phase 进度记录
- closeout 判断
- 当前下一步说明
- 历史 phase 编年归档