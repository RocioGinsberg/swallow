# 自我进化与记忆沉淀设计 (Self-Evolution & Memory Consolidation)

## 0. 阅读约定

本文档描述的是 **Swallow 当前主分支的自我进化与记忆沉淀基线**。

这里最重要的不是“系统会不会自动变聪明”，而是明确：

- 记忆沉淀必须显式化
- 自我改进必须工作流化
- 知识晋升必须受治理
- 任何“自进化”都不能绕过 truth layer、review 边界与 human gate

本文档应与当前架构文档中的以下原则一起理解：

- SQLite-primary task truth / knowledge truth
- truth before retrieval
- taxonomy before brand
- Librarian-governed knowledge boundaries
- explicit separation between controlled HTTP path and black-box agent path

---

## 1. 核心理念：拒绝隐式黑盒，拥抱显式改进工作流

先进开发工具常常会在内部“记住”用户偏好、上下文与历史错误，但在 Swallow 的体系中，**隐式记忆**仍然是高风险设计。

原因并不只是“不透明”，更在于：

- 不同执行器无法共享一致的隐式状态
- 记忆污染无法被可靠审计
- 黑盒 agent 的内部缓存不等于项目长期知识
- 任何无法显式检查的“自动学习”都可能破坏稳定性

因此，Swallow 当前的基本哲学不是“让系统偷偷学会更多”，而是：

> **把记忆沉淀、自我改进与系统反思显式化、对象化、工作流化。**

这意味着：

- 编排层负责触发时机与边界控制
- 专项角色负责提炼、对齐、总结与提案
- 最终结果必须沉淀为可见的 truth objects、artifacts 或 proposal artifacts

---

## 2. 当前自我进化的正确边界

Swallow 当前不追求“黑盒自我变异系统”。

更准确的追求是：

- 从 task truth / event truth / artifacts 中提炼可复用认知
- 从 route telemetry / failure patterns 中提炼优化建议
- 通过明确的 staged → review → promote 机制管理知识晋升
- 通过 proposal → human decision 机制管理系统策略优化

因此，当前应明确拒绝以下误解：

- 不是让 orchestrator 自己偷偷学习并修改策略
- 不是让 executor 自动把自己的经验直接写进长期知识层
- 不是把向量库或聊天记录当作自然生长的记忆系统
- 不是让 Meta-Optimizer 自动改系统配置

---

## 3. 项目级记忆沉淀：Librarian 主线

当前项目级记忆沉淀的主线，不应再被理解为“生成一个更聪明的 LLM Wiki 层”，而应理解为：

> **围绕 SQLite-backed knowledge truth、staged knowledge、canonical boundary 与 review/promotion 流程展开的知识治理工作流。**

### 3.1 Librarian 的正确定位

Librarian 不是通用业务执行者，而是：

- 记忆提纯者
- 知识边界守门人
- staged/canonical 变化的受控写入收口者
- 冲突、去重、supersede、change-log 语义的执行者

当前它最重要的职责包括：

1. **降噪提炼**：从 Event Log、artifacts、handoff、已有 knowledge objects 中提取高价值结论
2. **冲突检测与合并仲裁**：发现相互矛盾或已过期的知识对象，标记而非静默覆盖
3. **结构化变更生成**：形成 `KnowledgeChangeLog` / `KnowledgeChangeEntry` 等变更痕迹
4. **受控写入 staged knowledge**：把高价值候选结果送入 staged / reusable / canonical 流程，而不是绕过治理边界直接进入长期真值

### 3.2 Librarian 的权限边界

当前最关键的一点是：

- Librarian 并不是“自动全权写长期记忆”的角色
- 它是少数拥有受控 knowledge write surface 的专项角色之一
- 但它仍然受 canonical boundary、review 与 authority guard 约束

因此，Librarian 的正确理解是：

> **knowledge governance specialist**

而不是“系统自动记忆本身”。

---

## 4. 当前记忆沉淀工作流

项目级记忆沉淀当前更适合理解为一个显式闭环，而不是任务结束后顺手做个摘要。

### 4.1 触发条件

较合理的触发条件包括：

- 复杂任务收口后
- 明显有可复用经验产生时
- 重要失败模式被识别时
- 关键任务进入 review / closeout 阶段时

不必要求所有任务都强制进入重型沉淀流程，但高价值任务应优先触发。

### 4.2 处理流程

更稳的主线是：

1. 任务执行产生 task truth、event truth、artifacts、handoff objects
2. Librarian 或相关专项流程读取这些显式材料
3. 提炼出：
   - reusable evidence
   - staged knowledge candidates
   - canonical candidate updates
   - dedupe / supersede / conflict signals
4. 生成结构化变更记录
5. 进入 review / promotion / rejection 路径
6. 最终只让通过治理边界的对象进入更正式的 knowledge truth

### 4.3 为什么不能跳过这条链

因为如果跳过 staged / review / promotion，你就会重新掉回：

- 黑盒记忆自动长出来
- 执行器把局部经验偷偷写成长久规范
- 项目级知识被低质量结论污染

这和 Swallow 当前的 truth-first 设计是冲突的。

---

## 5. 记忆沉淀的结果形态

当前“记忆”的结果不应被理解成一个抽象大脑，而应理解成一组明确的对象。

这些对象可以包括：

- Evidence
- WikiEntry
- staged knowledge candidates
- canonical records / canonical updates
- change logs
- conflict / supersede markers
- task closeout summaries
- operator-facing reusable insights

其中最关键的一点是：

> **记忆结果必须以可见对象存在，而不是藏在某个 agent 的上下文缓存里。**

---

## 6. 系统级自我进化：Meta-Optimizer 主线

除了项目级知识沉淀，Swallow 还需要对自己的工作流与路由行为进行系统级反思。

当前这条线的核心不是“让系统自动改自己”，而是：

> **从 event truth、route telemetry、failure patterns 中读取信号，生成供人类或后续 phase 消费的优化提案。**

### 6.1 Meta-Optimizer 的正确定位

Meta-Optimizer 当前应继续保持：

- **只读**
- **提案型**
- **不直接改系统配置**
- **不直接改 task truth / knowledge truth**

它不是第二个 orchestrator，也不是自动化的系统改写器。

### 6.2 当前核心职责

Meta-Optimizer 适合承担：

1. 识别反复出现的任务模式，提议新的 workflow / slice 模板
2. 识别频繁失败的环节，提议 skills / validators / review strategy 优化
3. 识别路由表现退化模式，提议 route preference / fallback / capability floor 调整
4. 识别人工介入高频点，提议更明确的 handoff、control surface 或 audit 入口

### 6.3 输出形态

Meta-Optimizer 的输出应继续保持为：

- proposal artifacts
- routing optimization proposal
- workflow optimization proposal
- concern / risk / hotspot summaries

这些输出应进入：

- operator review
- backlog / roadmap / future phase planning

而不应直接进入运行时配置主线。

---

## 7. 路由遥测与系统反思的数据接口

Meta-Optimizer 的有效性，建立在可消费的结构化遥测之上。

当前最重要的最小字段集仍包括：

| 字段 | 类型 | 说明 |
|---|---|---|
| `task_family` | string | 任务族标签 |
| `logical_model` | string | 编排层选定的逻辑模型标识 |
| `physical_route` | string | 实际使用的物理通道标识 |
| `latency_ms` | int | 端到端延迟 |
| `token_cost` | float | 本次调用成本数据 |
| `degraded` | bool | 是否经历执行级降级 |
| `error_code` | string? | 错误码 |

当前最关键的约束是：

- 这些数据属于 event truth / telemetry truth
- Meta-Optimizer 只读消费
- 不直接改写原始日志与 route config

---

## 8. Self-Evolution 的正确实现方式：Proposal, Not Mutation

Swallow 当前应明确采用：

> **proposal-driven self-evolution**

而不是：

> **mutation-driven self-evolution**

也就是说：

- 系统可以自我观察
- 系统可以自我总结
- 系统可以生成建议
- 系统可以准备知识候选对象

但系统不应在没有 review / authority / human gate 的情况下，自行突变：

- 路由策略
- 验证阈值
- canonical knowledge truth
- 执行规则
- 工作流主线

这条边界非常关键，因为它决定了 Swallow 是“可靠的可演进系统”，还是“不可预测的黑盒自变系统”。

---

## 9. 与黑盒 agent 的关系

对于 Aider、Claude Code、Warp/Oz 等黑盒执行器，当前尤其需要明确：

- 它们的内部记忆不等于 Swallow 的长期记忆
- 它们的内部反思不等于系统级自我进化
- 它们的局部上下文总结，只有进入显式 artifact / staged knowledge / proposal 流程后，才属于系统可复用资产

因此，当前应把这类 agent 看作：

- 可贡献中间结果
- 可贡献候选经验
- 可贡献 artifacts / handoffs / reviewable outputs

但不能直接成为系统长期记忆的最终写入者。

---

## 10. 当前对实现者的约束性理解

如果继续扩展 Self-Evolution & Memory 层，当前应坚持：

1. 不要把自我进化理解成隐式自动学习
2. 不要把聊天记录、上下文缓存或向量召回误当成长久记忆本体
3. 不要让 Librarian 越权成为自动 canonical writer
4. 不要让 Meta-Optimizer 从 proposal 角色滑向自动 mutation 角色
5. 不要让黑盒 agent 的内部经验直接等同于项目长期知识
6. 不要把“系统会提出建议”误写成“系统会自动改自己”

---

## 11. 一句话总结

Swallow 当前的自我进化与记忆沉淀，不应理解为：

> 一个会在黑盒内部自动累积经验并自动改写自身行为的自学习系统

而应理解为：

> 一个通过 Librarian 主线沉淀项目级知识、通过 Meta-Optimizer 主线生成系统级优化提案，并通过 staged/review/promotion 与 proposal/human-gate 两套显式流程来实现可审计演进的 truth-first workbench system
