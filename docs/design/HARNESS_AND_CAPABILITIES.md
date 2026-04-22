# Harness 与能力分层设计 (Harness & Capabilities)

## 0. 阅读约定

本文档描述的是 **Swallow 当前主分支的 Harness 与能力分层基线**。

这里最重要的不是把 Harness 理解成“工具箱”或“prompt 包装器”，而是把它理解为：

- 执行器的受控运行面
- 工具、skills、workflows 与 validators 的统一能力层
- 与 task truth / knowledge truth / provider routing 协同工作的运行时中枢

本文档应与当前架构文档中的以下原则一起理解：

- local-first
- truth before retrieval
- taxonomy before brand
- explicit separation between controlled HTTP path and black-box agent path

---

## 1. 核心概念：什么是 Harness？

Harness 不是简单的方法或函数集合，也不只是“给模型加工具调用”的壳。它更适合被理解为：

> **一层把任务语义、工作区约束、工具能力、执行边界和验证流程组合起来的受控运行时。**

如果说大模型或 executor 是做推理与施工的执行者，那么 Harness 是：

- 让执行者能够安全接触工作区、文件、命令与上下文的运行环境
- 把工具、skills、workflows 和 validators 组织成可复用能力体系的供应层
- 把执行结果沉淀为 artifacts、event truth 和 task truth 的中间控制面

换句话说，Harness 关心的不是“模型有多聪明”，而是：

- 执行能否被约束
- 能力能否被复用
- 结果能否被恢复、验证与审计

---

## 2. 安全执行与工作区边界

Swallow 当前坚持的首要准则是：

> **自主执行不能破坏宿主环境，也不能绕过任务边界静默修改主真值。**

因此，Harness 的安全职责主要体现在以下几层：

### 2.1 工作区边界

所有具备副作用的执行动作，都必须显式落在受控工作区和受控任务上下文之内。

这意味着 Harness 需要负责：

- 明确当前任务的 workspace root
- 控制文件读写、命令执行与 artifact 输出位置
- 将执行结果回收到 task truth / event truth / artifacts 中

### 2.2 运行环境隔离

受 Claude Code 等先进开发环境启发，Swallow 应尽量把具备副作用的操作限制在可恢复、可替换、可审计的环境中。

当前合理的方向包括：

- 项目级 Python virtualenv
- 受控 shell 执行
- 有需要时的容器化运行面
- 对危险系统级操作保持保守默认值

这层的目的不是炫技，而是确保：

- 不污染宿主环境
- 不让试错代价无限外溢
- 让执行失败后还能恢复到安全基线

### 2.3 状态快照与恢复

Harness 不应只负责“去执行”，还必须负责：

- 在关键节点保留可恢复痕迹
- 在失败、熔断或人工接管时留下 resume 入口
- 让任务能够回到可继续推进的位置

### 2.4 审查防线兜底

安全不只来自执行前的限制，也来自执行后的结构化审查。

当前 Harness 需要与以下机制协同：

- ReviewGate
- Debate Topology
- waiting_human
- consistency audit / validator 路径

也就是说，Harness 不是“做完就完了”，而是要为后续 review / retry / rerun / recovery 留下结构化支点。

> 注：像命令黑名单、超细粒度系统调用拦截等能力可以作为未来增强，但当前基线更依赖受控工作区、任务边界和事后审查链条共同兜底。

---

## 3. 通用 Executor 与 Harness 的关系

Executor 是系统的标准化执行手臂，但 Harness 不是 Executor 的同义词。

更准确地说：

- **Executor**：谁来做事
- **Harness**：在什么受控环境下做事、可调用哪些能力、结果如何回收

因此，一个任务至少会涉及：

1. **Task/Orchestration layer**：决定做什么
2. **Executor layer**：决定谁执行
3. **Harness/Capabilities layer**：决定执行时有哪些受控能力与验证机制可用

这三者必须分开。

### Executor 的核心职责

当前通用 executor 仍应承担这些职责：

1. workspace execution
2. tool invocation
3. file operations
4. context handling
5. verification trigger
6. reporting
7. handoff

### Executor 不该做什么

- 不该成为顶层总调度器
- 不该越权修改长期知识真值
- 不该把关键中间产物封装成不可审查黑箱
- 不该静默接管全局路由与策略决策

Harness 的价值就在于：

> 即使执行器是黑盒，也尽量让它在一个边界明确、产物可回收、能力可审计的运行面中工作。

---

## 4. 当前默认执行器分工与 Harness 侧重点

结合当前默认工作组合，Harness 对不同执行器的支持重点并不完全相同。

### 4.1 Claude Code

当前更适合被视为：

- 高价值、高复杂度任务的主执行者
- 复杂变更的收口者

Harness 对它的支持重点是：

- 高质量 task context 组织
- 明确的 workspace / artifact 边界
- review / validator / waiting_human 链路
- 复杂任务的 handoff 与 recovery 支点

Harness 不应让 Claude Code 长期被低价值、重复性实现工作稀释。

### 4.2 Aider

当前更适合被视为：

- 高频实现默认 executor
- 小到中等复杂度施工主力

Harness 对它的支持重点是：

- 清晰的文件边界
- 高频 edit loop 支撑
- 快速验证动作（lint/test/build/check）
- 在边界扩散时及时升级到 Claude Code 的机制

### 4.3 Warp / Oz Agents

当前更适合被视为：

- terminal-native parallel worker surface
- 多终端并行与中间结果生产层

Harness 对它的支持重点是：

- 多任务/多终端边界管理
- 中间结果与 artifact 回收
- 日志、测试矩阵、环境调查等并行任务模板
- 防止其演化成 hidden orchestrator 的边界控制

因此，Harness 不只是统一提供能力，还要根据 executor 的角色定位，提供不同层级的约束与支撑。

---

## 5. 能力分层架构 (Capabilities Hierarchy)

Harness 内部的能力供应，当前更适合按四层理解：

1. **Tools**：原子操作
2. **Skills**：可复用方法模板
3. **Workflows**：更高层的多步任务闭环
4. **Validators / Policies**：校验与准入控制

旧式的“profile = persona”理解已经不够准确。Swallow 当前更强调：

- 行为边界来自 task semantics / workflow / policy / validator
- 而不是来自一个抽象的人设标签

### 5.1 工具层 (Tools)

工具是最小化、可组合的原子能力。它们应满足：

- 输入输出清晰
- 副作用边界明确
- 易于记录与审计
- 不自带任务级业务状态

典型工具包括：

- 文件系统交互：`read_file`, `write_file`, `glob_search`
- 代码理解：`ast_parse`, `find_references`
- 底层执行：`run_isolated_shell`
- 必要时的网络读取或远程获取工具

### 5.2 技能层 (Skills)

Skill 不是“更大的工具”，而是：

> **围绕一个常见问题模式，把工具组合、输入输出约束、方法提示和执行顺序打包起来的可复用方法模板。**

例如：

- `test_driven_development`
- `literature_review`
- `failure_analysis`
- `conversation_ingestion`
- `consistency_check`

Skill 的价值在于：

- 减少每次从零组织工具链
- 让黑盒 agent 也能被更稳定地引导
- 让 HTTP 受控路径中的 prompt 结构更可重复

### 5.3 工作流层 (Workflows)

Workflow 比 skill 更高一层，它通常对应完整的多步闭环。

例如：

- task loop
- planning → execution → review
- ingest → stage → review → promote
- implement → verify → audit → handoff

Workflow 的作用是：

- 把多个 skills / validators 组织成稳定流程
- 把成功标准和熔断条件前置
- 减少执行器自由发挥带来的漂移

### 5.4 Validators / Policies

Validators 与 policy controls 不是附属品，而是 Harness 的一等能力。

它们负责：

- 结果检查
- 质量断言
- schema / consistency / safety 验证
- 触发 feedback / retry / waiting_human

因此，当前更稳的理解是：

> Harness 不只是“让执行器做事”，还负责决定“什么结果算有效”。

---

## 6. Controlled HTTP Path vs Agent Black-Box Path

这是当前最容易混淆、也最需要写清的一层。

### 6.1 Swallow-controlled HTTP path

典型形态：

`TaskState + RetrievalItems -> Router -> route_model_hint / dialect_hint -> HTTPExecutor -> HTTP API`

在这条路径里，Harness 能直接参与并控制：

- prompt 生成与格式化
- retrieval context assembly
- model route 选择
- dialect 选择
- 输出结构约束
- fallback 逻辑
- telemetry 与 eval 基线

因此，这条路径上的 Harness 更像：

> **prompt/control plane**

### 6.2 Agent black-box path

典型形态：

`TaskState -> CLIAgentExecutor / external agent -> agent internal model handling -> model/provider`

对于 Aider、Claude Code、Warp/Oz 等原生 agent/CLI 工具，如果它们内部自己决定：

- 模型选择
- prompt 拼接
- 工具调用
- 子代理行为

那么 Harness 往往无法像 HTTP path 那样精细控制底层 prompt / dialect。

这时 Harness 的重点应转向：

- task boundary
- skills / workflows / rules
- input/output contract
- escalation / fallback
- cost / logging / behavior observation

因此，这条路径上的 Harness 更像：

> **executor governance plane**

### 6.3 这意味着什么

这一区分直接决定了你的控制策略：

- 对 HTTP path，追求 prompt / dialect / fallback 的强控制
- 对黑盒 agent path，追求任务边界、skills、subagents、review 和 telemetry 的强治理

后续如果继续接入更多 agent 工具，也应默认先按“黑盒执行器”理解，除非它提供足够稳定、可控的中间协议接口。

---

## 7. Harness 与 Provider Routing 的关系

Harness 与 Provider Routing 是相邻但不同的两层。

### Harness 关心的是

- 任务在受控环境中如何执行
- 当前有哪些 tools / skills / workflows / validators 可用
- 结果如何沉淀为 artifacts / events / state truth

### Provider Routing 关心的是

- 当前模型调用走哪条物理路径
- 该用哪种方言与后端格式
- 哪条 fallback 该被触发
- route telemetry 如何回收

因此，Harness 不应被写成“包办所有模型协商逻辑”的总层。

更稳的说法是：

- Harness 提供执行环境与能力层
- Provider Routing 提供模型调用的物理路径选择与方言翻译
- 两者通过 executor/runtime 接口协作

---

## 8. 关于 Skills、Subagents 与成本治理

在当前体系下，skills / subagents 的价值尤其体现在黑盒 agent 路径中。

因为当你无法精细控制 agent 内部 prompt 时，最有效的控制手段往往变成：

- 子任务拆分
- 子代理边界
- 方法模板复用
- 输入输出格式要求
- review / retry / waiting_human 条件

也就是说：

- **Skills / workflows** 负责提升执行成功率与稳定性
- **Subagents** 负责把重复、局部、边界清晰的工作从高阶执行器下放出去
- **Telemetry / cost tracking** 负责观测代价，但不是 Harness 唯一的治理手段

因此，对黑盒 agent 不能只停留在“成本监控”，还应把 Harness 理解为：

> **通过 skills、subagents、rules、validators 和 artifacts 管理执行器行为的治理层。**

---

## 9. 当前对实现者的约束性理解

如果继续扩展 Harness 与能力层，当前应坚持：

1. 不要把 Harness 简化成“工具列表”
2. 不要把 Profiles 继续写成纯 persona 叙事
3. 不要把黑盒 agent 路径误写成与 HTTP path 同等级的 prompt 可控路径
4. 不要让任何 executor 在没有 validator / review / state 回收的情况下自由漂移
5. 不要让 Warp / Oz 之类并行 worker surface 脱离 Harness 的边界约束
6. 不要把成本监控误当作对黑盒 agent 唯一的控制方式
7. 不要把 Provider Routing 和 Harness 混成一个层

---

## 10. 一句话总结

Swallow 当前的 Harness，不应理解为：

> 一个给 Agent 随便挂工具和人设的包装层

而应理解为：

> 一个把执行环境、工具能力、skills/workflows、validators、任务边界和结果回收组织起来的受控运行时；在 HTTP 受控路径中它偏向 prompt/control plane，在黑盒 agent 路径中它偏向 executor governance plane
