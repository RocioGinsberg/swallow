# ai_workflow

中文 | [English](./README.md)

**一个面向真实项目工作的有状态 AI 工作流系统，以编排、执行壳、可复用能力与持久化任务记忆为核心。**

- **围绕真实项目任务进行编排**，而不是停留在一次性聊天
- **通过 Harness Runtime 执行任务**，把模型、工具、权限、hooks 与输出稳定接起来
- **以 Capabilities 复用能力**，统一 tools、skills、profiles、workflows 与 validators
- **沉淀状态、记忆与工件**，覆盖代码、笔记、检索与执行全过程

## 为什么会有这个项目

真实项目中的上下文通常分散在很多地方：

- 代码仓库与 Git 历史
- Obsidian / Markdown 笔记
- 文档、阶段总结、handoff note 与历史任务成果
- diff、patch、测试日志和中间产物

问题往往不是“信息不存在”，而是**在真正需要时，无法及时取回、联动执行并沉淀为后续可复用的成果**。与此同时，传统 AI 工具往往更擅长单次响应，却不擅长持续推进任务、联动本地项目，以及整理长期成果。

本项目希望把以下能力统一起来：

- 面向真实任务的编排
- 被 harness 约束的本地与云端执行
- 面向整个工作空间的检索
- 状态、事件与工件持久化
- 可复用的能力包与工作流包

## 它要解决什么问题

这个系统主要针对一组彼此关联的痛点：

- **上下文碎片化**：有用信息散落在代码、笔记、文档和历史记录中
- **AI 交互一次性**：很多 AI 工具单次回答不错，但难以长期推进多步任务
- **代码工作与知识工作割裂**：实现、笔记、总结通常分散在不同工具里
- **过程不可追踪**：AI 执行缺乏可恢复的状态、事件历史和工件记录
- **历史成果难复用**：做过的事情难以转化为后续任务可检索的记忆资产
- **能力组织混乱**：tools、skills、workflow 常常零散堆积，难以复用和演化

本项目的目标，是让 AI 不只是“回答”，而是能够围绕真实项目进行编排、检索、执行、校验、追踪与沉淀。

## 为什么不直接用 Codex、Claude Code 或 Gemini CLI？

Codex、Claude Code、Gemini CLI 这类工具本身都很强，尤其擅长：

- 阅读仓库
- 修改代码
- 执行命令
- 辅助完成单次开发任务

但本项目并不是为了替代它们，而是为了解决**它们单独使用时不擅长的那一层问题**。

这些工具更像是**执行器**。
而这个项目想提供的是围绕执行器之外的**编排层、执行壳、记忆层与组织层**。

具体来说，这个系统更关心的是：

- 一个任务能否跨多个步骤、多个阶段持续推进
- 上下文能否从整个工作空间而不仅是当前 prompt 中取回
- 代码工作和笔记、研究、总结能否被放进同一个任务流中
- 过程能否记录为状态、事件与工件
- 结果能否沉淀为以后可复用的资产
- 能力能否以结构化形式复用，而不是每次都重新拼 prompt
- 执行器能否保持可替换，而不是被某个平台绑定

所以两者的关系更适合这样理解：

- **Codex / Claude Code / Gemini CLI**：强执行能力的 agent / executor
- **本项目**：围绕真实项目组织编排、执行、检索、记忆和成果沉淀的有状态系统

## 系统定位

从架构上看，这个项目围绕五个核心层组织：

- **Orchestrator**：决定做什么、按什么顺序做、调用哪个 profile 或 workflow
- **Harness Runtime**：驱动任务循环、装配上下文、执行工具、应用权限与 hooks，并把结果回写到状态中
- **Capabilities**：可复用的 tools、skills、profiles、workflows 与 validators
- **State / Memory / Artifacts**：任务、事件、工件、Git 真相层、检索记忆与 handoff 输出
- **Provider Router**：模型、执行器、provider 与鉴权路径的路由层

因此，它不是单纯的 chatbot，不只是一个 RAG 项目，也不只是“多个 agent 分工”的 demo。

它更接近一个**面向真实项目工作的 AI 工作台 / AI 工作流操作系统**。

## 核心原则

这个系统围绕五个核心能力构建：

- **可检索**：从整个工作空间取回与当前任务最相关的上下文
- **可约束执行**：通过显式 Harness Runtime 推进任务，而不是依赖松散 prompt 循环
- **可组合**：把 tools、skills、profiles、workflows 与 validators 作为能力包复用
- **可持续**：围绕任务状态持续推进，而不是停留在单轮对话
- **可追踪**：把事件、工件、总结和演化过程保留下来

## 当前阶段

当前优先实现一个 **CLI-first MVP**。

Phase 0 聚焦于：

- 一个最小 **Orchestrator**，负责任务接入与阶段推进
- 一个最小 **Harness Runtime**，负责 retrieve → execute → record → summarize 的闭环
- 一个最小 **Capability Registry**，先只支持内置工具
- 使用 Codex 作为主本地 code executor adapter
- 支持 Git 项目文件作为检索源
- 支持 Markdown / Obsidian 笔记作为检索源
- 采用本地优先、结构可检查的实现方式

这一阶段的目标，是先验证最核心的闭环：

**让 AI 能围绕本地项目通过“编排 + 执行壳 + 状态沉淀”的方式持续工作，而不只是给出一次性回答。**

## 长期方向

长期来看，这个系统预计会逐步演进到：

- 更丰富的工作流编排
- 多个可替换执行器
- 更完善的检索质量与长期记忆
- 更强的状态与工件管理
- 面向 coding 与 research 的可复用 capability packs
- 可选的 provider 路由与成本感知执行策略
- 更广泛的 source adapter 与更完整的工作台界面


## 运行形态

本项目当前优先面向**个人高频工作流**，采用“**本地工作台 + 可选远端重执行**”的运行形态。

默认思路如下：

* **本地工作台**负责日常交互，包括桌面端 UI、轻量 CLI、任务发起、结果查看、文件接入与小规模本地处理。
* **远端执行环境**用于承载高成本任务，例如长时间运行的工作流、重型 RAG、复杂代码分析、多步 Agent 执行与持续服务。
* 系统在设计上区分**交互层**与**执行层**，避免将 UI、调度器和执行器强耦合在同一运行环境中。

这意味着：

* 轻量任务可以直接在本地完成；
* 重任务可以在未来迁移到服务器执行；
* 当前版本即使以本地优先方式运行，也不会在架构上排斥远端扩展。

### 当前阶段目标

当前版本的重点不是构建完整多用户平台，而是验证以下能力是否真正提升个人效率：

* 工作流编排是否有价值；
* 多 Agent / 多执行器协作是否必要；
* RAG 与记忆层是否能减少资料来回切换；
* 状态、事件与工件沉淀是否能形成长期复用。

### 当前非目标

当前版本暂不优先解决以下问题：

* 多租户与复杂权限体系；
* 高并发分布式任务集群；
* 大规模云端托管；
* 完整商业化部署形态。

项目首先追求的是：**让单用户场景稳定可用，并为后续扩展保留清晰边界。**

## 当前状态

Phase 0 CLI bootstrap。

## 快速开始

当前仓库已经包含一个可运行的最小 CLI，用来验证文档里定义的 Phase 0 闭环。

可编辑安装：

```bash
python3 -m pip install -e .
```

创建任务：

```bash
swl task create \
  --title "Design orchestrator" \
  --goal "Create a minimal Phase 0 harness runtime" \
  --workspace-root .
```

运行任务：

```bash
swl task run <task-id>
```

查看产物：

```bash
swl task summarize <task-id>
swl task handoff <task-id>
```

运行测试：

```bash
python3 -m unittest discover -s tests
```

## 工作约定

为了在终端意外中断后快速恢复，仓库级实现状态记录在这里：

- [current_state.md](./current_state.md)

## 当前 CLI 形态

Phase 0 CLI 目前提供：

- `swl task create`
- `swl task run`
- `swl task summarize`
- `swl task handoff`

任务状态与产物会写入：

```text
.swl/
  tasks/
    <task-id>/
      state.json
      events.jsonl
      retrieval.json
      artifacts/
        summary.md
        handoff.md
```

当前仍然是 bootstrap。`run` 命令已经能完成检索、状态记录、事件追加和 summary/handoff 产物写入，但执行步骤仍是占位实现。下一步应替换为真实 executor adapter。

当前实现已经包含一个收敛范围很小的 Codex executor adapter：

- 默认模式：对任务工作目录执行 `codex exec`
- 测试模式：设置 `AIWF_EXECUTOR_MODE=mock`，用于稳定的本地验证
- 超时控制：设置 `AIWF_EXECUTOR_TIMEOUT_SECONDS`，为非交互执行设置上限
- 执行产物：
  - `executor_prompt.md`
  - `executor_output.md`

## 许可证

待定
