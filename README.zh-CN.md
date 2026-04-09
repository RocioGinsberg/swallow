# swallow

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
- 文档、阶段总结、恢复说明与历史任务成果
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
- **State / Memory / Artifacts**：任务、事件、工件、Git 真相层、检索记忆与恢复说明输出
- **Provider Router**：模型、执行器、provider 与鉴权路径的路由层

因此，它不是单纯的 chatbot，不只是一个 RAG 项目，也不只是“多个 agent 分工”的 demo。

它更接近一个**面向真实项目工作的 AI 工作台 / AI 工作流操作系统**。

在这个系统形态里，executor 也不应被看成单一类别。当前架构已经区分 model、runtime backend 与 executor，而下一步规划还会继续把 executor family 细分为两类：

- **API executor**：更适合承担讨论、规划、总结、路由判断、检索后的综合、结构化输出等认知型工作
- **CLI executor**：更适合承担读仓库、改文件、跑命令、调用本地工具、在环境内执行动作等操作型工作

这两类 executor 都应被视为系统可路由的执行器。长期方向上：

- API executor 更适合与官方模型 API 或更深的托管接口集成
- CLI executor 更适合作为本地或半本地 code agent 执行壳
- 后续 routing 应优先面向 executor family 与 capability，而不只是面向某个厂商或工具名字

## 核心原则

这个系统围绕五个核心能力构建：

- **可检索**：从整个工作空间取回与当前任务最相关的上下文
- **可约束执行**：通过显式 Harness Runtime 推进任务，而不是依赖松散 prompt 循环
- **可组合**：把 tools、skills、profiles、workflows 与 validators 作为能力包复用
- **可持续**：围绕任务状态持续推进，而不是停留在单轮对话
- **可追踪**：把事件、工件、总结和演化过程保留下来

## Retrieval 与 Context 方向

在这个项目里，retrieval 是 system-level capability，而不是某个单一 executor 的附属能力。即使可以复用 Codex、Claude、Gemini 等工具内置的 retrieval / RAG，它们也只能作为 shortcut；核心知识层仍应保持外部化、可追踪、并由 orchestrator 控制。

当前默认方向是先把 enhanced retrieval 做稳，再逐步加入 light agentic retrieval。GraphRAG 不是当前默认主线，只有在多跳关系、全局结构或跨文档关系确实成为核心问题时才应考虑引入。

这也意味着 context 不能只等同于当前 prompt。系统需要持续区分 session context、workspace context、task context 与 historical context，并让检索结果能够与 state、memory、artifacts 协同，而不是在单次运行里一次性消费掉。

领域适配应优先落在 domain packs 或 capability packs 中，而不是散落在一次性 prompt 技巧里。这个原则同样适用于 retrieval 行为、工具行为与 workflow 行为。

同样的原则也适用于外部 AI 输入。外部规划、外部讨论和外部知识整理可以作为系统输入，但聊天记录本身不应直接成为 system of record。更合理的方向是把外部输入归一化为显式系统对象：

- **task objects**：承接 external planning handoff、任务意图和可执行的 task semantics
- **knowledge objects**：承接外部知识片段、研究摘录、总结、证据包，以及后续可复用的检索材料

这些对象应保持可追踪、在需要时与任务绑定，并且尽量有 artifact 或 source reference 作为依据。长期目标不是直接囤积原始对话，而是走分级蒸馏路径：

- `raw`
- `candidate`
- `verified`
- `canonical`

这样既能保留证据，也能避免把低质量或未经校验的内容直接污染长期知识层。

## 当前阶段

当前仓库正处于 **Phase 10 Resume And Recovery Loop 收口检查点**。

当前已经实现的基线包括：

- 显式的 **Orchestrator**，负责任务接入、阶段推进与 route 选择
- **Harness Runtime**，负责 retrieve → execute → record → summarize 的闭环
- 结构化的 route 与 capability 声明
- compatibility 检查与 route provenance 产物
- 明确的本地优先执行路径，以及 route、topology、dispatch、handoff、execution-fit 产物
- execution-site、attempt ownership、handoff contract、retry、stop 与 execution budget 等 policy / control 产物
- 面向 operator 的本地 workbench 控制面，包括 queue、control、checkpoint、attempts / compare-attempts、resume、retry 与 rerun 入口
- Git 项目文件与 Markdown / Obsidian 笔记检索

当前目标已经不是证明一个“最小 bootstrap 闭环”，而是在保持当前本地基线稳定的前提下，把已完成的 executor / external-input 切片、retrieval / memory 下一段切片，以及已完成的 Phase 6、Phase 7、Phase 8、Phase 9、Phase 10 都视为稳定检查点。下一条切片应从新的 kickoff note 开始，而不是默认继续扩张 Phase 10。

## 长期方向

长期来看，这个系统预计会逐步演进到：

- 更丰富的工作流编排
- 多个可替换执行器
- 更完善的检索质量与长期记忆
- 更强的状态与工件管理
- 面向 coding 与 research 的可复用 capability packs
- 可选的 provider 路由与成本感知执行策略
- 更广泛的 source adapter 与更完整的工作台界面

这个方向也包括：

- 更明确的 API executor 与 CLI executor 路由边界
- 把 external planning handoff 收敛成 task semantics，而不是散落聊天残留
- 把 external knowledge capture 收敛成分级、可引用的 knowledge objects
- 更清楚地区分短期交互历史与长期系统记录


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

### Backend 兼容性原则

这个项目未来可以允许 Harness 挂接多个 backend，但**多 backend 并不等于全兼容**。

backend 不等于模型，也不等于 executor。

系统应当区分三层：

* **模型（Model）**：底层推理来源，例如 OpenAI、Anthropic、Gemini 或经路由接入的 provider
* **运行时 backend（Runtime backend）**：Harness 内部使用的 agent / workflow 运行时
* **执行器（Executor）**：真正执行代码、命令或其他任务动作的具体执行单元

而在 executor 这一层里，下一步规划还应继续区分：

* **API executor**：偏认知型工作，负责讨论、规划、综合、结构化输出
* **CLI executor**：偏操作型工作，负责仓库、文件、命令与工具调用等环境内执行

因此，项目不应假设：

* 所有模型都支持相同的 agent 能力
* 所有 runtime backend 都支持相同的 handoff 语义
* 所有 executor 都能参与所有工作流步骤
* 所有 backend 都同等支持代码执行、tool loop、结构化 handoff 或失败后恢复
* 所有 executor family 都适合同样的任务形态

更合理的原则是：

> **Harness 可以对外提供统一接口，但每个 backend 都必须声明自己的能力等级。**

例如，一个 backend 可能支持，也可能不支持：

* 结构化 handoff packet
* tool loop
* 多步 runtime session
* 代码执行
* 失败后的恢复继续执行
* tracing 或更丰富的运行时元数据

这意味着，这套架构追求的应当是：

> **可路由的兼容性（routable compatibility）**，而不是“所有能力的全兼容”。

在实际设计中：

* **Orchestrator** 根据任务需求选择 backend 或 executor
* **Harness Runtime** 提供稳定的集成边界
* 每个 backend 明确声明自己真正支持的能力
* 工作流设计应面向“角色、executor family 与能力”，而不是写死某个模型厂商

这条原则很重要，因为这个项目并不是想成为某一个 agent framework 的薄封装。它真正的核心价值仍然在于自己的 orchestration、retrieval、state、artifact 和 execution 设计 

因此，项目的长期方向应是：

* 保持自身编排与持久化语义稳定
* 在合适的时候接入多个 backend
* 不把“支持很多模型”误解为“天然支持所有 agent 行为”

一个更实用的压缩表达是：

> **在 Harness 边界上统一接口，在边界之下按能力路由。**

## 当前状态

Phase 0 已验收，Phase 1 已完成，Phase 2 baseline 已完成，post-Phase-2 retrieval baseline 已完成，Phase 3 baseline 已完成，Phase 4 baseline 已完成，Phase 5 baseline 已完成，post-Phase-5 executor / external-input slice 已完成，post-Phase-5 retrieval / memory-next slice 已完成，Phase 6 baseline 已完成，Phase 7 baseline 已完成，Phase 8 baseline 已完成，Phase 9 baseline 已完成，Phase 10 baseline 已完成。

- [current_state.md](./current_state.md)
- [docs/phase3_closeout_note.md](./docs/phase3_closeout_note.md)
- [docs/phase4_closeout_note.md](./docs/phase4_closeout_note.md)
- [docs/phase5_task_breakdown.md](./docs/phase5_task_breakdown.md)
- [docs/phase5_closeout_note.md](./docs/phase5_closeout_note.md)
- [docs/phase6_closeout_note.md](./docs/phase6_closeout_note.md)
- [docs/phase7_closeout_note.md](./docs/phase7_closeout_note.md)
- [docs/phase8_closeout_note.md](./docs/phase8_closeout_note.md)
- [docs/post_phase5_executor_and_external_input_kickoff_note.md](./docs/post_phase5_executor_and_external_input_kickoff_note.md)
- [docs/post_phase5_executor_and_external_input_task_breakdown.md](./docs/post_phase5_executor_and_external_input_task_breakdown.md)
- [docs/post_phase5_executor_and_external_input_closeout_note.md](./docs/post_phase5_executor_and_external_input_closeout_note.md)
- [docs/post_phase5_retrieval_memory_next_closeout_note.md](./docs/post_phase5_retrieval_memory_next_closeout_note.md)
- [docs/phase9_kickoff_note.md](./docs/phase9_kickoff_note.md)
- [docs/phase9_task_breakdown.md](./docs/phase9_task_breakdown.md)
- [docs/phase9_closeout_note.md](./docs/phase9_closeout_note.md)
- [docs/phase10_kickoff_note.md](./docs/phase10_kickoff_note.md)
- [docs/phase10_task_breakdown.md](./docs/phase10_task_breakdown.md)
- [docs/phase10_closeout_note.md](./docs/phase10_closeout_note.md)
- [docs/phase10_commit_summary.md](./docs/phase10_commit_summary.md)

## 术语说明

- `agent handoff`：未来的运行时委派能力，表示 orchestrator 或 harness runtime 在执行过程中把工作交给另一个 agent 或 backend
- `resume note`：当前 Phase 0 已落盘的续跑说明 / 恢复说明产物，用于一次运行结束后恢复、继续或人工接手任务

## 快速开始

当前仓库已经包含一个可运行的 CLI，用来执行当前本地优先工作流基线。

可编辑安装：

```bash
python3 -m pip install -e .
```

创建任务：

```bash
swl task create \
  --title "Design orchestrator" \
  --goal "Tighten the harness runtime boundary" \
  --workspace-root . \
  --capability profile:baseline_local \
  --capability workflow:task_loop \
  --executor local
```

运行任务：

```bash
swl task run <task-id>
swl task run <task-id> --capability validator:strict_validation
swl task run <task-id> --executor codex
```

查看产物：

```bash
swl task summarize <task-id>
swl task resume-note <task-id>
swl task compatibility <task-id>
swl task validation <task-id>
swl task grounding <task-id>
swl task topology <task-id>
swl task dispatch <task-id>
swl task handoff <task-id>
swl task execution-fit <task-id>
swl task policy <task-id>
swl task memory <task-id>
swl task route <task-id>
```

使用当前 workbench 风格的审阅流程：

```bash
swl task list
swl task list --focus needs-review
swl task queue
swl task inspect <task-id>
swl task control <task-id>
swl task attempts <task-id>
swl task compare-attempts <task-id>
swl task capabilities <task-id>
swl task review <task-id>
swl task artifacts <task-id>
```

使用当前恢复与 rerun 入口：

```bash
swl task checkpoint <task-id>
swl task resume <task-id>
swl task retry <task-id>
swl task rerun <task-id>
```

当前建议的 operator 边界是：

- `resume`：沿当前失败上下文做 checkpoint-backed recovery
- `retry`：沿当前 accepted run path，受 retry / stop policy 约束
- `rerun`：显式人工 override，重新开启一轮 run
- `checkpoint`：在选择上述路径前先查看的紧凑恢复快照

运行测试：

```bash
python3 -m unittest discover -s tests
```

## 工作约定

为了在终端意外中断后快速恢复，仓库级实现状态记录在这里：

- [current_state.md](./current_state.md)
- [docs/post_phase5_executor_and_external_input_closeout_note.md](./docs/post_phase5_executor_and_external_input_closeout_note.md)
- [docs/post_phase5_retrieval_memory_next_kickoff_note.md](./docs/post_phase5_retrieval_memory_next_kickoff_note.md)
- [docs/post_phase5_retrieval_memory_next_task_breakdown.md](./docs/post_phase5_retrieval_memory_next_task_breakdown.md)
- [docs/post_phase5_retrieval_memory_next_closeout_note.md](./docs/post_phase5_retrieval_memory_next_closeout_note.md)
- [docs/phase6_closeout_note.md](./docs/phase6_closeout_note.md)
- [docs/phase7_closeout_note.md](./docs/phase7_closeout_note.md)
- [docs/phase8_closeout_note.md](./docs/phase8_closeout_note.md)
- [docs/phase9_kickoff_note.md](./docs/phase9_kickoff_note.md)
- [docs/phase9_task_breakdown.md](./docs/phase9_task_breakdown.md)
- [docs/phase9_closeout_note.md](./docs/phase9_closeout_note.md)
- [docs/phase10_kickoff_note.md](./docs/phase10_kickoff_note.md)
- [docs/phase10_task_breakdown.md](./docs/phase10_task_breakdown.md)
- [docs/phase10_closeout_note.md](./docs/phase10_closeout_note.md)

## 当前 CLI 形态

当前 CLI 提供：

- `swl task create`
- `swl task run`
- `swl task list`
- `swl task queue`
- `swl task control`
- `swl task checkpoint`
- `swl task attempts`
- `swl task compare-attempts`
- `swl task resume`
- `swl task retry`
- `swl task rerun`
- `swl task inspect`
- `swl task semantics`
- `swl task capabilities`
- `swl task knowledge-objects`
- `swl task knowledge-policy`
- `swl task review`
- `swl task policy`
- `swl task artifacts`
- `swl task summarize`
- `swl task resume-note`
- `swl task compatibility`
- `swl task validation`
- `swl task grounding`
- `swl task retrieval`
- `swl task topology`
- `swl task execution-site`
- `swl task dispatch`
- `swl task handoff`
- `swl task execution-fit`
- `swl task retry-policy`
- `swl task execution-budget-policy`
- `swl task stop-policy`
- `swl task memory`
- `swl task compatibility-json`
- `swl task route`
- `swl task route-json`
- `swl task topology-json`
- `swl task execution-site-json`
- `swl task dispatch-json`
- `swl task handoff-json`
- `swl task execution-fit-json`
- `swl task retry-policy-json`
- `swl task execution-budget-policy-json`
- `swl task stop-policy-json`
- `swl task checkpoint-json`
- `swl task capabilities-json`
- `swl task semantics-json`
- `swl task knowledge-objects-json`
- `swl task knowledge-policy-json`
- `swl task retrieval-json`
- `swl doctor codex`

任务状态与产物会写入：

```text
.swl/
  tasks/
    <task-id>/
      state.json
      events.jsonl
      retrieval.json
      task_semantics.json
      knowledge_objects.json
      knowledge_partition.json
      knowledge_index.json
      knowledge_policy.json
      retry_policy.json
      execution_budget_policy.json
      stop_policy.json
      compatibility.json
      execution_fit.json
      validation.json
      route.json
      topology.json
      execution_site.json
      dispatch.json
      handoff.json
      memory.json
      artifacts/
        summary.md
        task_semantics_report.md
        knowledge_objects_report.md
        knowledge_partition_report.md
        knowledge_index_report.md
        knowledge_policy_report.md
        resume_note.md
        retry_policy_report.md
        execution_budget_policy_report.md
        stop_policy_report.md
        compatibility_report.md
        execution_fit_report.md
        route_report.md
        topology_report.md
        execution_site_report.md
        dispatch_report.md
        handoff_report.md
        retrieval_report.md
        source_grounding.md
        validation_report.md
        executor_stdout.txt
        executor_stderr.txt
```

当前 `run` 命令已经能完成检索、执行器调用、route compatibility 检查、execution-fit 检查、knowledge policy 检查、validation、状态记录、事件追加、task memory 持久化，以及 executor、summary、resume note、task semantics、knowledge objects、grounding、route、topology、dispatch、handoff、execution-fit、compatibility、knowledge policy、validation 产物写入。

当前任务状态语义保持为最小且明确的形式：

- `status` 表示任务生命周期结果：`created`、`running`、`completed`、`failed`
- `phase` 表示当前或最后一个真实执行到的步骤：`intake`、`retrieval`、`executing`、`summarize`
- 只有在真实进入某一步时才会切换 `phase`
- 只有在 `summary.md` 与 `resume_note.md` 写完之后，任务才会进入最终 `completed` 或 `failed`

`events.jsonl` 是 append-only 的执行历史，并且会明确记录每次 run attempt 的开始。一次正常成功运行的顺序现在是：

```text
task.created
task.run_started
task.phase        # retrieval
retrieval.completed
task.phase        # executing
executor.completed
task.phase        # summarize
compatibility.completed
execution_fit.completed
knowledge_policy.completed
validation.completed
artifacts.written
task.completed
```

如果对同一个任务再次执行 `swl task run`，新的 run attempt 会继续追加一段新的事件序列，而不是覆盖已有历史。

当前实现已经有了一个显式的 executor 选择缝，并内置了一个很小的 executor 集合：

- 任务级选择：在 `swl task create` 或 `swl task run` 上使用 `--executor`
- `codex`：对任务工作目录执行 `codex exec`
- `local`：生成一个确定性的本地执行更新，用于在无 live backend 时验证 executor 可替换性
- `mock`：用于本地验证的确定性测试 executor
- `note-only`：跳过 live execution，直接写入结构化 continuation note
- 兼容旧方式：当任务仍使用默认 `codex` 时，`AIWF_EXECUTOR_MODE` 仍可作为后备选择
- 超时控制：设置 `AIWF_EXECUTOR_TIMEOUT_SECONDS`，为非交互执行设置上限
- fallback 控制：默认 `AIWF_EXECUTOR_FALLBACK=structured-note`，可设置为 `off` 关闭 fallback note
- 执行产物：
  - `executor_prompt.md`
  - `executor_output.md`
  - `executor_stdout.txt`
  - `executor_stderr.txt`

当前产物职责也做了明确区分：

- `summary.md` 负责记录本次运行实际发生了什么：任务信息、最终状态、检索结果、执行结果、执行输出
- `resume_note.md` 负责为下一次接手提供 hand-off 信息：ready state、最新 executor message、建议的下一步动作
- `route_report.md` 负责记录可读的 route provenance：选中的 route、声明的 backend、执行位置元数据和 route reason
- `route.json` 负责保存结构化 route 记录，便于后续自动化或检查
- `compatibility_report.md` 负责记录本次运行的可读 route-policy compatibility 结果
- `compatibility.json` 负责保存结构化 compatibility 记录，便于后续自动化或检查
- `source_grounding.md` 负责记录本次运行的 retrieval grounding：citation、score、matched terms 与 preview
- `validation_report.md` 负责记录本次运行的可读 validation 结果
- `validation.json` 负责保存结构化 validation 记录，便于后续自动化复用
- `memory.json` 负责保存紧凑的 task-memory packet，供后续 rerun 与 review 复用
- `executor_output.md` 保留原始执行结果或 fallback note，`executor_stdout.txt` 与 `executor_stderr.txt` 保留诊断流输出

## 许可证

待定
