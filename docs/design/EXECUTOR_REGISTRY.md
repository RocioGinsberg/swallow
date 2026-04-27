# Executor Registry

> **Design Statement**
> 本文档是 Swallow 中**所有具体 executor 绑定的唯一权威**。任何品牌名、CLI 名、API 提供商名只在本文档中出现。其他设计文档讨论角色、路径、权限,不持有任何品牌信息。
>
> 加入新 executor 的 PR **只能改这一份文档** + 对应实现代码。如果发现还需要改其他设计文档,说明那个文档里有该迁出的内容。

> 项目不变量见 → `INVARIANTS.md`(权威)。五元组与角色定义见 → `AGENT_TAXONOMY.md`。

---

## 1. 当前注册的 executor

按 role 分类。每个条目使用 AGENT_TAXONOMY §2 定义的五元组结构。

### 1.1 General Executors

#### Claude Code

```
role               = general_executor
advancement_right  = advance_via_orchestrator
truth_writes       = {task_artifacts, event_log}
llm_call_path      = agent_internal
runtime_site       = local_process
```

| 字段 | 说明 |
|---|---|
| 强项 | 长链路推理、架构级任务、复杂重构、跨多文件的全局理解 |
| 编排集成度 | 中(stdout 解析 + 文件 artifact) |
| 指令注入机制 | `CLAUDE.md`(项目根)+ 命令行参数 |
| 默认沙箱 | 工具白名单 + workspace 边界 |
| 适合承担 | 高复杂度主执行、最终收口、需要长上下文积累的探索任务 |
| 不适合 | 大量重复机械实现、批量脚本化任务 |

#### Codex CLI

```
role               = general_executor
advancement_right  = advance_via_orchestrator
truth_writes       = {task_artifacts, event_log}
llm_call_path      = agent_internal
runtime_site       = local_process
```

| 字段 | 说明 |
|---|---|
| 强项 | 非交互模式与脚本化集成,`codex exec --json` 输出 NDJSON 事件流;OS 级沙箱默认无网络 |
| 编排集成度 | **高**(NDJSON 事件流可直接解析为 event_log entries) |
| 指令注入机制 | `AGENTS.md`(支持嵌套目录优先级)+ `~/.codex/config.toml` |
| 默认沙箱 | OS 级强制 + 默认无网络访问 |
| 适合承担 | CI 场景、批量 fan-out、可重放的实现任务、需要严格沙箱的任务 |
| 不适合 | 需要长会话上下文积累的探索任务 |
| 实现备注 | `CodexCLIExecutor` 优先走 `codex exec --json`,把 NDJSON 解析为 telemetry 事件,而不是只抓最终 stdout |

#### Aider

```
role               = general_executor
advancement_right  = advance_via_orchestrator
truth_writes       = {task_artifacts, event_log}
llm_call_path      = agent_internal
runtime_site       = local_process
```

| 字段 | 说明 |
|---|---|
| 强项 | 高频小修改、紧凑 edit loop、文件粒度精确、git commit 集成 |
| 编排集成度 | 中(命令行参数 + chat 历史) |
| 指令注入机制 | 命令行参数 + `.aider.conf.yml` |
| 默认沙箱 | 无特殊沙箱(依赖 workspace 边界) |
| 适合承担 | 边界清晰的 daily 实现、小到中等复杂度 edit loop |
| 不适合 | 模糊需求、跨架构边界的改动 |

#### HTTP Executor(无品牌,Path A 的执行器封装)

```
role               = general_executor
advancement_right  = advance_via_orchestrator
truth_writes       = {task_artifacts, event_log}
llm_call_path      = controlled_http
runtime_site       = hybrid
```

| 字段 | 说明 |
|---|---|
| 强项 | Orchestrator 完全控制 prompt / dialect / fallback;telemetry 完整 |
| 编排集成度 | 完全集成(Path A 的本质就是 Orchestrator 直接驱动) |
| 适合承担 | brainstorm、review、synthesis、classification、结构化抽取、多模型 fan-out |
| 不适合 | 默认代码库阅读、代码修改、命令验证 |
| 实现备注 | 是一个能力封装而非品牌;具体调用哪个 model 由 Provider Router 解析 |

### 1.2 Specialists

下面四个 specialist 是 Swallow 的内置专项角色,不是外部品牌——但它们以独立 executor 身份出现在 registry 中。
**关于 `default_retrieval_sources`**:每个 specialist 有自己默认的 retrieval source 集合,与 KNOWLEDGE.md §3.2 的通用默认规则不同。这反映 specialist 的窄边界——它们的输入语义固定,不应像通用 executor 那样泛化召回。Operator 可通过 task_semantics 显式 override,但不建议(会模糊 specialist 的边界)。

#### Librarian

```
role               = specialist
advancement_right  = propose_only
truth_writes       = {task_artifacts, event_log, staged_knowledge}
llm_call_path      = specialist_internal
runtime_site       = hybrid
```

| 字段 | 说明 |
|---|---|
| 职责 | 知识冲突检测、去重、变更整理、staged 写入收口 |
| 输入 | task artifacts、event truth、handoffs、已有知识对象 |
| 输出 | staged candidates、conflict/supersede markers、change log entries |
| 边界 | **不写 canonical**(canonical 写入仅经 `apply_proposal`,操作主体是 Operator) |
| `default_retrieval_sources` | `["knowledge", "artifacts"]` |

理由:Librarian 需要看现有 canonical/wiki 做冲突检测,以及 task artifacts 提取候选;不需要 repo / notes。

#### Ingestion Specialist

```
role               = specialist
advancement_right  = advance_via_orchestrator
truth_writes       = {task_artifacts, event_log, staged_knowledge}
llm_call_path      = specialist_internal
runtime_site       = hybrid
```

| 字段 | 说明 |
|---|---|
| 职责 | 外部会话提纯、结构化候选对象生成 |
| 输入 | conversation exports、markdown transcripts、剪贴板片段 |
| 输出 | staged candidates(待 review) |
| `advancement_right` 选择理由 | 摄入任务本身有完成语义("这次摄入任务已完成"),与 Librarian 的"产出提案"不同;但摄入产物仍是 staged,不直接进 canonical |
| `default_retrieval_sources` | `[]`(纯 explicit input,不做泛化召回) |

理由:Ingestion 的输入是显式传入的对话/文件,不需要从知识库召回;若需要查重,应通过 Librarian 流程而非 ingestion 自身做召回。

#### Literature Specialist

```
role               = specialist
advancement_right  = advance_via_orchestrator
truth_writes       = {task_artifacts, event_log}
llm_call_path      = specialist_internal
runtime_site       = hybrid
```

| 字段 | 说明 |
|---|---|
| 职责 | 领域资料深度解析与结构化比较 |
| 输入 | document paths、PDF / markdown 文档集 |
| 输出 | 结构化比较 artifact、概念抽取报告 |
| 边界 | 不直接写知识真值,产物以 artifact 形态供后续 Librarian 消费 |
| `default_retrieval_sources` | `["artifacts"]` |

理由:Literature 的核心输入是 explicit document paths;artifacts 用于查找前序解析产出避免重复。不需要 knowledge / notes / repo。

#### Meta-Optimizer

```
role               = specialist
advancement_right  = propose_only
truth_writes       = {event_log, proposal_artifact}
llm_call_path      = specialist_internal
runtime_site       = hybrid
```

| 字段 | 说明 |
|---|---|
| 职责 | 扫描 event truth、识别模式、产出优化提案 |
| 输入 | event_log、event_telemetry、route_health 聚合 |
| 输出 | proposal artifacts(写入 `.swl/artifacts/proposals/`) |
| 边界 | **只读消费**遥测,**只写**提案文件;不直接改 route_metadata / policy / canonical(强制走 `apply_proposal`) |
| `default_retrieval_sources` | `[]`(只读 event_telemetry,不走 retrieval pipeline) |

理由:Meta-Optimizer 的输入是结构化遥测数据,不是文本检索召回。它的"召回"是直接 SQL 查询 event_telemetry / route_health 等表。

### 1.3 Validators

#### Quality Validator

```
role               = validator
advancement_right  = none
truth_writes       = {event_log}
llm_call_path      = controlled_http
runtime_site       = hybrid
```

| 字段 | 说明 |
|---|---|
| 职责 | 关键节点的独立 verdict 产出 |
| 输入 | artifact reference、result reference、acceptance criteria |
| 输出 | `VerdictReport {pass\|fail\|uncertain, reasons[], severity, evidence_refs[]}` |
| 边界 | 不替 executor 施工,不修正主产物 |

#### Consistency Validator

```
role               = validator
advancement_right  = none
truth_writes       = {event_log}
llm_call_path      = controlled_http
runtime_site       = hybrid
```

| 字段 | 说明 |
|---|---|
| 职责 | 架构偏离、知识冗余、文档实现不一致识别 |
| 输入 | 跨文档 / 跨 artifact 的引用集合 |
| 输出 | `VerdictReport` + 不一致点列表 |
| 边界 | 不替 executor 施工,不修正主产物 |

---

## 2. 当前默认绑定

| 系统职责 | 默认 executor | 适用场景 |
|---|---|---|
| 高复杂度主执行 / 最终收口 | Claude Code | 架构改动、复杂重构、需要长链路推理 |
| 脚本化 / 批量实现 / CI | Codex CLI | 非交互模式、JSON 事件流、严格沙箱 |
| 高频 daily 实现 | Aider | 边界清晰的小步编辑循环 |
| 受控认知任务(无 tool-loop) | HTTP Executor | brainstorm、review、synthesis、抽取 |
| 知识沉淀主线 | Librarian | staged → review 收口 |
| 外部会话摄入 | Ingestion Specialist | ChatGPT / Claude Web 等导出物 |
| 领域资料深度解析 | Literature Specialist | PDF / 论文 / 长文档比较 |
| 系统优化提案 | Meta-Optimizer | event truth 扫描 → proposal |
| 关键节点 verdict | Quality Validator | review gate 输入 |
| 跨文档一致性检查 | Consistency Validator | 文档与实现一致性审计 |

**并行不在表中**——并行能力由 Orchestrator 的 Subtask Orchestrator 提供(详见 ORCHESTRATION.md §2.3),通过 fan-out 多个上面的 executor 实例实现。Warp 多 pane、Codex subagents、Claude Code subagents 等 executor 内部并行能力不暴露为平台级能力(见 INVARIANTS §6 接入边界规则)。

---

## 3. 升级 / 降级判据

| 方向 | 触发条件 |
|---|---|
| Aider → Claude Code | 改动扩散、需求模糊、两轮不收敛、涉及架构边界 |
| Aider → Codex CLI | 任务可批量化、需要严格沙箱、需要 NDJSON 遥测 |
| Codex CLI → Claude Code | 单任务复杂度上升、需要长上下文探索 |
| Claude Code → Aider | 方案定型、后续为机械实现、可拆为低风险子修改 |
| Claude Code → Codex CLI | 任务变成可重复脚本化执行 |
| HTTP Executor → CLI(任意) | 任务发现需要读 repo / 跑命令验证 |
| CLI → HTTP Executor | 任务退化为纯认知判断 / 抽取 |

升降级决策归 Strategy Router(在 Orchestrator 内,见 ORCHESTRATION.md §2.1),不归 Provider Router。

---

## 4. 项目级指令注入(Skills / AGENTS / 配置文件)

以下三种品牌都支持"项目级指令注入"——这是 Swallow Harness 治理黑盒 agent(Path B)的主要手段:

| Executor | 指令注入文件 | 作用域 |
|---|---|---|
| Claude Code | `CLAUDE.md` | 项目根 |
| Codex CLI | `AGENTS.md` | 项目根 + 嵌套子目录(优先级链) |
| Aider | `.aider.conf.yml` + 命令行 | 项目根 |

**Swallow 的 Harness 层**(见 HARNESS.md)负责:

- 在 task 启动时根据 task semantics 动态生成 / 更新这些文件
- 注入本次 task 的 constraints、acceptance criteria、可调用 skills 列表
- 在 task 结束时清理或归档(避免污染下一个 task)

具体实现是每个 executor 一个 adapter,但**对外抽象统一**:`InstructionInjector.inject(executor_id, task_semantics) -> None`。

---

## 5. 加入新 executor 的 checklist

加 executor 时,**先写完下面所有项再开 PR**:

- [ ] 确认它**不**满足 INVARIANTS §6 的接入边界排除条件(不是 sub-orchestrator、不维护平行 truth、不假设 multi-tenant)
- [ ] 在 §1 对应 role 小节添加完整五元组
- [ ] 在 §1 条目下补充强项 / 弱项 / 集成度 / 指令注入 / 沙箱 / 适合 / 不适合 字段
- [ ] 在 §2 默认绑定表中评估是否替换或新增一行
- [ ] 在 §3 升降级判据表中补充涉及该 executor 的迁移条件
- [ ] 在 §4 指令注入表中说明该 executor 的注入机制(若不支持,说明用其他什么手段做行为治理)
- [ ] 在代码层添加 `<NewExecutor>Adapter`,实现 `Executor` 接口
- [ ] 在 `tests/test_executor_registry.py` 添加五元组守卫测试
- [ ] 不允许同时修改 INVARIANTS / ARCHITECTURE / AGENT_TAXONOMY 等文档(若发现需要,说明那些文档里有该迁出的内容)

---

## 6. 与其他文档的接口

| 对接文档 | 接口关系 |
|---|---|
| `INVARIANTS.md` | 提供五元组定义、写权限矩阵、接入边界规则 |
| `AGENT_TAXONOMY.md` | 提供 role / advancement_right / llm_call_path 的语义定义 |
| `ORCHESTRATION.md` | Strategy Router 依据本注册表选择 executor |
| `HARNESS.md` | 指令注入、skills 配置、artifact 回收的统一接口由 Harness 提供 |
| `PROVIDER_ROUTER.md` | Path A / Path C 的物理 route 选择由 Provider Router 完成,与 executor 选择正交 |
| `SELF_EVOLUTION.md` | Librarian / Meta-Optimizer 的工作流细节 |

---

## 附录 A:不接入清单

以下系统**已评估,不接入**。记录在此避免重复讨论。

| 系统 | 不接入理由 |
|---|---|
| **Oz Cloud Platform** | 自身是 orchestration platform(违反 INVARIANTS §6 第 1 条),维护云端 task store 与 Swallow Truth Plane 平行(违反第 2 条),默认假设团队协作语义(违反第 3 条)。在 Warp 终端中使用 Codex / Claude Code 不受影响——那是 user environment,不是 Swallow executor。 |
| **Devin / Manus / Lindy / Replit Agent** 等"AI 工作流平台" | 同 Oz,自带 orchestration / scheduling / cloud truth,接入会让 Swallow Orchestrator 退化为薄壳。 |
| **Warp Local Agent**(Warp 内嵌的 agentic 模式) | 已评估为低优先级:Codex CLI / Claude Code / Aider 已覆盖 general_executor 需求,引入 Warp Local Agent 没有增量价值,反而增加维护面。 |

加入这个清单的标准:**已被认真评估并明确决定不接入**。"还没评估"或"将来可能加"不进这个清单。
