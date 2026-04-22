# 状态与事实层设计 (State & Truth Layer)

## 0. 阅读约定

本文档描述的是 **Swallow 当前主分支的状态与事实层基线**。

这里的关键点不是“系统保存了一些状态”，而是：

- 任务推进依赖外部真值，而不是单次对话历史
- 状态、事件、工件、策略边界都必须可恢复、可审计、可解释
- 当前真值层已经进入 **SQLite-primary** 阶段，而不是单纯的 JSON / 文件式状态机阶段

---

## 1. 核心理念 (Core Philosophy)

传统 AI Agent 往往过度依赖对话历史维持上下文。随着任务复杂度提升，这种模式会迅速暴露问题：

- 对话历史线性冗长，关键事实容易被淹没
- “意图、执行过程、结果”混在一起，不利于恢复与审计
- 一旦模型上下文偏移，就容易用错误记忆继续推进任务

Swallow 的核心选择是：

> **把状态与事实托管到外部可验证存储中，让模型从“靠记忆推进流程”退回到“读取事实、做判断、产出动作建议”。**

因此，系统真正依赖的是：

- task truth
- event truth
- artifact truth
- route / policy / topology truth
- workspace / git truth

而不是聊天记录本身。

---

## 2. 当前真值层的核心组成

### 2.1 Task State

**职责**：表示任务当前推进到了哪里、系统该如何恢复、是否进入等待人工、是否已经 budget exhausted、当前 review / retry / rerun 语义是什么。

当前它不应再被简单理解为一个“任务 JSON blob”，而应理解为：

- 一个持久化任务现场
- 一个受状态迁移规则约束的运行时真值
- 一个可与 checkpoint / resume / rerun / waiting_human 联动的状态面

### 2.2 Event Log

**职责**：以 append-oriented 的方式记录系统中发生过什么。

当前事件流不仅用于“黑匣子审计”，还承载：

- executor telemetry
- route / degraded / latency / token-cost 线索
- retry / review / fallback 过程痕迹
- Meta-Optimizer 可消费的行为材料

因此，Event Log 当前应理解为：

- 审计源
- 遥测源
- 诊断源
- 后续策略优化的数据源

### 2.3 Artifacts

**职责**：保存系统显式产出的文件、报告、摘要、比较结果、grounding outputs 等。

在当前基线里，需要特别注意：

- artifact file 仍然重要
- 但 artifact file 不自动等于唯一真值
- 结构化 task truth / knowledge truth 已经更多落在 SQLite 中

因此，更准确的理解是：

- **结构化 truth**：在 SQLite 中保存
- **查看 / 比较 / 导出型产物**：以 artifact 文件形式保存

### 2.4 Route / Policy / Topology Truth

这是当前系统相比早期设计更成熟的一部分。

除了任务状态本身，系统还需要显式保存：

- 路由与执行位点
- 任务拓扑
- handoff / remote-handoff contract
- grounding refs
- policy 与 capability 边界

这些内容不能继续被视为“运行时偶然存在的附属信息”，它们已经属于当前系统的重要真值面。

### 2.5 Workspace / Git Truth

对代码与文本类材料来说，文件系统和 Git 仍然是外部真值约束的重要组成部分。

但当前更准确的说法是：

- Git / workspace 是代码与文本内容的外部真值环境
- SQLite 是任务状态与知识状态的主真值层
- 文件镜像、导出和 artifact 视图围绕两者组织，而不是替代两者

---

## 3. 当前“单一事实源”的正确理解

早期可以把 Single Source of Truth 粗略写成“Git + 数据库 + 文件系统”。

在当前基线下，更准确的理解是：

### 3.1 任务与知识真值
- 以 SQLite 为主

### 3.2 代码与工作区内容真值
- 以 workspace / Git 为主

### 3.3 导出与审阅型文件产物
- 以 artifact files / mirrors 为主

也就是说，Swallow 当前不是“只有一个物理存储”，而是：

> **不同真值域各自有明确 authoritative store，并由 orchestrator/runtime 统一解释。**

这比“所有东西都放一个 JSON 或一个文件夹里”更符合当前实现。

---

## 4. 当前状态迁移的意义

Swallow 不是把任务当作“单轮请求”，而是把任务当作一个具有生命周期的运行实体。

因此，状态流转的意义不只是 UI 展示，而是直接影响：

- 是否允许运行下一步
- 是否需要人类介入
- 是否允许 retry / rerun / resume
- 是否触发 review gate
- 是否应停止自动推进

当前状态设计最重要的价值是：

- 提高任务可预测性
- 支持中断与恢复
- 把“无法自动裁决”的情况显式送入 `waiting_human`
- 防止模型在事实不完整时继续假装推进

---

## 5. 数据流示例（按当前语义重写）

**场景：修复一个具体 Bug 并留下可恢复轨迹**

1. **任务创建**
   - Task truth 中创建任务记录
   - Event Log 记录 `task_created`

2. **任务运行**
   - Task truth 进入 `running`
   - route / executor / topology 元数据被记录

3. **分析与计划**
   - 检索当前 workspace、知识对象与已有 artifacts
   - 生成计划或分析产物，写入 artifact surface
   - 如需人工批准，则状态转为 `waiting_human`

4. **人工确认后恢复执行**
   - Task truth 切回 `running`
   - Event Log 记录恢复行为

5. **代码或文档修改**
   - workspace / Git 成为内容层真值约束
   - 相关产出记录为 artifacts
   - 相关过程继续写入 event log

6. **验证 / 审查 / 降级 / fallback**
   - review gate 与 executor telemetry 共同写入事件流
   - 若 route degraded、budget exhausted 或质量不过关，则显式进入对应状态或 attention surface

7. **完成或失败**
   - Task truth 更新为 `completed` 或 `failed`
   - Event Log 完整保留推进轨迹
   - Artifacts 成为 inspect / compare / recovery 的后续入口

这个过程说明：

> Swallow 当前依赖的是“结构化 truth + artifact surfaces + external workspace truth”的组合，而不是“靠模型记住前面干了什么”。

---

## 6. 当前与模型方言 / 执行后端的关系

状态与事实层必须继续与底层模型品牌和协议保持解耦。

这意味着：

- 状态层不应硬编码某个厂商的 prompt 协议
- route、dialect、executor family 应作为显式元数据存在
- 具体方言适配应下沉到 provider routing / execution backend 层

因此，状态层记录的是：

- 任务意图
- route truth
- policy boundary
- execution context

而不是某一家的原生协议格式本身。

---

## 7. 当前安全兜底语义

当系统发生以下情况时，状态与事实层承担最终安全兜底：

- 模型输出不可靠
- route degraded
- review 不通过
- fallback 触发
- 参数不符 schema
- 自动推进不再可信

这时系统不应“继续猜”，而应通过显式状态与策略边界处理，例如：

- 拦截非法状态突变
- 记录 degraded / failure 事件
- 停止推进并转入 `waiting_human`
- 保留可恢复检查点和轨迹

这也是为什么真值层比“让模型自己修正自己”更重要。

---

## 8. 当前对实现者的约束性理解

如果继续扩展状态与事实层，当前应坚持：

1. 不要把状态层重新退化成 prompt memory 的附属品
2. 不要把 artifact file 误写成所有真值的唯一来源
3. 不要忽略 route / policy / topology truth 这类较新的真值面
4. 不要让模型方言渗透进状态层 schema
5. 不要把 SQLite-primary current baseline 又退回成纯 JSON 文件式理解

---

## 9. 一句话总结

Swallow 当前的状态与事实层，不应理解为：

> 一个给 Agent 存聊天上下文和几个 JSON 文件的地方

而应理解为：

> 一个以 SQLite 为主、联合 workspace / Git / artifact surfaces 共同构成的多真值域运行时底座，用来支撑任务推进、恢复、审计、策略边界与执行可解释性
