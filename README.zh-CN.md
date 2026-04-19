# swallow

中文 | [English](./README.md)

**一个面向真实项目工作的有状态 AI 工作流系统。**

swallow 的目标不是只做单轮问答，也不是只做一个代码 agent 的外壳。  
它试图把真实项目中的这些能力放进同一套可持续推进的系统里：

- 任务编排
- 检索与上下文组织
- 执行器接入
- 状态、事件与工件沉淀
- 恢复、重试与审阅
- 可复用能力与知识对象管理

---

## 项目定位

swallow 面向的是**真实项目工作流**，而不是一次性聊天。

它更关心这些问题：

- 一个任务能否跨多个步骤、多个阶段持续推进
- 上下文能否从整个工作空间而不仅是当前 prompt 中取回
- 代码工作与知识工作能否进入同一条任务流
- 过程能否沉淀为状态、事件与工件
- 外部 planning 和外部 knowledge 能否进入系统，但不污染长期记忆
- 执行器能否保持可替换，而不是绑定某个单一平台

因此，它不是：

- 通用聊天机器人
- 纯 RAG 项目
- 只围绕某一个 executor 的薄封装
- 只展示多 agent 分工的 demo

它更接近一个**面向真实项目工作的 AI 工作台 / AI workflow 系统**。

---

## 为什么会有这个项目

真实项目中的上下文通常分散在很多地方：

- 代码仓库与 Git 历史
- Markdown / Obsidian 笔记
- 任务总结、阶段说明、恢复入口
- 检索结果、测试输出、执行产物
- 外部 AI 的规划讨论与知识整理结果

问题往往不是“信息不存在”，而是：

> **在真正需要时，信息无法被及时取回、用于执行、并沉淀为后续可复用成果。**

很多 AI 工具在单次回答上已经很强，但在下面这些方面仍然不够理想：

- 持续推进多步任务
- 跨代码与知识材料工作
- 保留可恢复的任务状态
- 把执行过程沉淀为可审查工件
- 把历史结果转化为后续可复用知识

swallow 就是为了解决这一层问题。

---

## 系统结构概览

swallow 长期围绕五层组织：

- **Orchestrator**：决定做什么、按什么顺序做
- **Harness Runtime**：执行检索、执行器调用、记录与工件产出
- **Capabilities**：tools、skills、profiles、workflows、validators 等可复用能力
- **State / Memory / Artifacts**：任务状态、事件、记忆与产物
- **Provider Routing**：route、executor family、backend 与 capability fit

在 Agent 与执行器层面，系统强制推行基于系统角色的**智能体分类学 (Agent Taxonomy)**，而不再按模型品牌区分：

- **通用执行者 (General Executor)**：承担宽泛且实质性的任务负载（如代码修改、API 规划）。
- **专项 Agent (Specialist Agent)**：聚焦于高价值、边界清晰的子系统工作（如记忆压缩、知识摄入）。
- **审查者 (Validator / Reviewer)**：对输出进行质量审计与检查，不修改主体任务状态。
- **编排器 (Orchestrator)**：严格把控流转语义，防止任何 Agent 越权成为隐藏的路由中枢。

也就是说，swallow 关心的不只是“调用哪个模型”，而是：

- 任务如何推进
- 执行如何被约束
- 结果如何被记录
- 知识如何被复用
- operator 如何审阅和恢复

---

## 当前实现概况

**当前 tag: `v0.4.0`** — 多模型网络引擎纪元：HTTP 执行器 + CLI 去品牌化 + 多模型路由 + 降级矩阵

> 本节仅在打新 tag 时更新。实时开发进度请查阅 `docs/active_context.md` 和 `docs/roadmap.md`。

当前系统已经具备：

- 本地优先的任务循环，以及显式 state / events / artifacts / checkpoint / resume / retry / rerun 语义
- 显式的 route、topology、dispatch、execution-site、handoff 与 policy 记录
- mock-remote dispatch gate 与 remote-handoff contract 可视化，但未扩张为真实 remote execution
- taxonomy 元数据、taxonomy-aware routing guard，以及 operator-facing taxonomy visibility
- staged knowledge capture、review queue、promote / reject 决策与 capability-aware 写入边界
- Evidence Store + Wiki Store 双层 task knowledge 结构、canonical promotion authority 校验，以及规则驱动的 `LibrarianExecutor`（side-effect 已收口：executor 只返回结构化 payload，orchestrator 接管全部持久化）
- canonical knowledge registry、reuse visibility、dedupe / supersede audit 与 regression inspection 路径
- canonical retrieval 命中的 grounding evidence artifact、锁定的 grounding refs，以及可稳定 resume 的 grounding 状态
- 有界 1:N `TaskCard` 规划、基于 DAG 的 subtask orchestration，以及父任务级 artifact / event 聚合
- 本地外部会话摄入链路：格式解析、规则式过滤、staged candidate 注册与 `swl ingest`
- 多轮 Debate Topology：结构化 `ReviewFeedback`、单任务 / 子任务 feedback-driven retry 与 `waiting_human` 熔断
- 基于能力矩阵的 Strategy Router + `RouteRegistry`，四级候选匹配（精确 → 家族+站点 → 能力 → 兜底），以及 route 级 binary fallback
- Claude XML 与 Codex FIM 方言适配器，以及共享的 `dialect_data` prompt 数据采集层（含 FIM 标记转义）
- 结构化 executor 事件遥测（`task_family`、`logical_model`、`physical_route`、`latency_ms`、`degraded`、`error_code`）
- 只读 Meta-Optimizer：扫描任务事件日志，产出 route 健康度、故障指纹与降级趋势优化提案
- Librarian 持久化原子提交：`state / knowledge / index` 批量 `os.replace` + rollback
- 共享 debate loop 核心：统一单任务与子任务 retry 控制流，不改变既有事件与 artifact 语义
- Meta-Optimizer 遥测修正：fallback token_cost 回计、debate retry 与正常执行事件隔离统计
- 只读 Web 控制中心（`swl serve`）：FastAPI JSON API + 单页 HTML 仪表盘 + Artifact Review 双栏视图、Subtask Tree、artifact compare 与 execution timeline，零写入 `.swl/`，无前端构建工具链
- Eval-Driven Development 基础设施：`tests/eval/` + `@pytest.mark.eval` 标记隔离 + Ingestion 降噪质量基线（precision/recall golden dataset）+ Meta-Optimizer 提案质量基线（scenario-based 覆盖率）
- ChatGPT 对话树还原：parent-child 树构建、主路径/侧枝识别、abandoned branch 语义保留（被否方案记录）
- `swl ingest --summary`：Decisions / Constraints / Rejected Alternatives / Statistics 结构化摄入摘要
- inspect / review / control / intake / grounding 等基于持久化任务真相的 operator 入口
- repo 文件与 Markdown / Obsidian 笔记检索，并将可复用知识保持为显式、policy-gated 结构
- **HTTP 执行器（HTTPExecutor）**：httpx 直连本地 new-api（OpenAI-compatible），替代 subprocess CLI 成为系统主 LLM 路径，系统首次具备真实多模型网络分发能力
- **CLI 执行器去品牌化（CLIAgentExecutor）**：配置驱动的 `CLIAgentConfig`，Codex / Cline 作为具名配置实例，消除品牌硬编码；未知 executor name 显式抛出 `UnknownExecutorError`
- **多模型 HTTP 路由**：`http-claude`（claude_xml）/ `http-qwen`（plain_text）/ `http-glm`（plain_text）/ `http-gemini`（plain_text）/ `http-deepseek`（codex_fim）+ `local-cline` 全部注册
- **分层降级矩阵**：`http-claude → http-qwen → http-glm → local-cline → local-summary`，循环检测保护；HTTP 429 rate-limit 走重试路径而非立即降级
- **自建遥测层**：HTTPExecutor 从 API 响应 `usage` 字段捕获真实 token 数据，替代静态成本估算；Meta-Optimizer 现在消费真实成本数据

当前 `main` 应被视为与最新 tag 对齐的稳定基线。

---

## 当前文档结构

本仓库文档按五层组织：

### 1. 公开说明层
- `README.md`
- `README.zh-CN.md`

用于：
- 对外解释项目定位、结构、快速开始

### 2. 当前执行层
- `AGENTS.md`
- `docs/active_context.md`
- `current_state.md`

用于：
- `AGENTS.md`：入口控制面与长期规则
- `docs/active_context.md`：当前唯一高频状态入口
- `current_state.md`：恢复入口

### 3. 阶段计划层
- `docs/plans/<phase>/kickoff.md`
- `docs/plans/<phase>/breakdown.md`
- `docs/plans/<phase>/closeout.md`
- `docs/plans/<phase>/commit_summary.md`（可选）
- `docs/plans/<phase>/context_brief.md`
- `docs/plans/<phase>/design_decision.md`
- `docs/plans/<phase>/risk_assessment.md`
- `docs/plans/<phase>/review_comments.md`
- `docs/plans/<phase>/consistency_report.md`（可选）

用于：
- 当前 phase 的目标、拆解、收口

### 4. 多 Agent 控制层
- `.agents/shared/`
- `.agents/codex/`
- `.agents/claude/`
- `.agents/gemini/`
- `.agents/workflows/`
- `.agents/templates/`

用于：
- 共享规则、状态同步与协作流程定义
- 各角色职责、写入边界与专属规则
- 多 agent 协作模板

### 5. 工具原生入口
- `CLAUDE.md`
- `.codex/session_bootstrap.md`
- `.gemini/settings.md`

用于：
- 作为指向 `.agents/` 控制层的 thin pointer
- 提供各工具原生入口，而不是重复维护一份规则正文

---

## 当前推荐工作方式

当前仓库采用：

- **phase 负责节奏**
- **track 负责系统方向**
- **slice 负责当前语义目标**
- **feature branch 承载当前 phase**
- **小步 commit 记录 slice 级推进**

文档与 Git 的默认节奏是：

- 高频状态只更新 `docs/active_context.md`
- `current_state.md` 只在收口或恢复语义变化时更新
- `AGENTS.md` 只在入口规则或 active 方向变化时更新
- README 只在对外可见结构或工作流变化时更新

未来不再默认新增新的 `post-phase-*` 命名。  
新工作应组织为：

- 正式 phase
- 明确 track
- 明确 slice

---

## 快速开始

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

查看当前任务与工件：

```bash
swl task list
swl task queue
swl task inspect <task-id>
swl task review <task-id>
swl task control <task-id>
swl task artifacts <task-id>
swl task summarize <task-id>
swl task resume-note <task-id>
swl task route <task-id>
swl task topology <task-id>
swl task handoff <task-id>
swl task remote-handoff <task-id>
swl task grounding <task-id>
swl task policy <task-id>
swl task memory <task-id>
```

恢复与重试相关入口：

```bash
swl task checkpoint <task-id>
swl task resume <task-id>
swl task retry <task-id>
swl task rerun <task-id>
```

导入 planning 与 knowledge：

```bash
swl task planning-handoff <task-id> --planning-source chat://session-1 --constraint "保持 task semantics 显式化"
swl task knowledge-capture <task-id> --knowledge-stage candidate --knowledge-source chat://session-2 --knowledge-item "导入知识应先保持 staged 状态。"
swl task intake <task-id>
```

knowledge review 与 promote / reject：

```bash
swl task knowledge-review-queue <task-id>
swl task knowledge-promote <task-id> <object-id> --target reuse --note "提升到 retrieval reuse。"
swl task knowledge-promote <task-id> <object-id> --target canonical --note "审查后提升为 canonical。"
swl task knowledge-reject <task-id> <object-id> --target reuse --note "暂时保持 task-linked。"
swl task knowledge-decisions <task-id>
```

canonical registry 查看：

```bash
swl task canonical-registry <task-id>
swl task canonical-registry-json <task-id>
swl task canonical-registry-index <task-id>
swl task canonical-reuse <task-id>
swl task canonical-reuse-json <task-id>
swl task canonical-reuse-evaluate <task-id> --citation <citation> --judgment useful
swl task canonical-reuse-eval <task-id>
swl task canonical-reuse-regression <task-id>
swl task canonical-reuse-regression-json <task-id>
```

grounding 查看：

```bash
swl task grounding <task-id>
```

Meta-optimizer（只读事件日志分析）：

```bash
swl meta-optimize
swl meta-optimize --last-n 50
```

控制中心（只读 Web 仪表盘）：

```bash
swl serve
swl serve --port 8037 --host 127.0.0.1
```

canonical registry record 是显式持久化的 canonical knowledge 输出，不等于自动全局记忆，也不会自动开启广义 retrieval reuse。

canonical reuse 仍然受显式 policy 控制。`canonical-reuse` 用来查看当前哪些 active canonical records 对 retrieval reuse 可见，superseded records 默认保持排除状态。

canonical reuse evaluation 同样保持显式、由 operator 驱动。`canonical-reuse-evaluate` 用来记录 task-local judgment，`canonical-reuse-eval` 用来查看 evaluation summary，`canonical-reuse-regression` 用来比较已保存的 regression baseline 与当前 evaluation summary，快速看出是否出现漂移或 baseline 过期。

canonical reuse regression control 同样保持 operator-facing，而不是自动化 gate。现在 queue、control、inspect、review 会显式暴露 regression mismatch attention，并把 operator 引回 `canonical-reuse-regression`，而不是自动改写 policy 或阻断任务流。

execution topology 现在也把 remote handoff contract truth 保持为显式、operator-facing 的结构。`remote-handoff` 用来查看 task-local remote handoff contract baseline，而 execution-site、dispatch、handoff、control、inspect 会复用同一套 readiness summary，让 operator 能直接看到当前 route 是否已经进入 remote-candidate boundary。

这仍然只是 contract baseline，不是已经支持真实 remote execution。当前并没有实现跨机器 transport、remote worker dispatch 或 hosted orchestration。

运行测试：

```bash
.venv/bin/python -m pytest
```

---

## 当前 CLI 形态

当前 CLI 已包含任务创建、运行、检查、控制、恢复、知识输入与各类 JSON / report inspection 路径。
更适合把它理解为：

* **任务工作台**
* **artifact 查看入口**
* **operator 控制面**
* **恢复与对比入口**

而不是一个单纯的“执行命令集合”。

详细当前工作边界请看：

* `AGENTS.md`
* `docs/active_context.md`
* `current_state.md`

---

## 非目标

除非某一 phase 明确要求，否则本项目当前不默认优先推进：

* 多租户架构
* 分布式 worker 集群
* 大规模托管基础设施
* 广泛插件市场
* 隐式全局记忆
* 自动 knowledge promotion
* 无边界 workbench UI 扩张
* 仅因为未来可能需要而提前加入的平台型复杂度

项目首先追求的是：

> **单用户场景稳定可用，并为后续扩展保留清晰边界。**

---

## 术语说明

* **task semantics**：承接任务意图、planning handoff 与执行约束的显式任务语义对象
* **knowledge objects**：承接 staged knowledge、外部知识片段、可复用证据与后续检索材料
* **resume note**：运行结束后为下一次接手提供的 hand-off 说明
* **handoff**：执行边界、ownership 与下一步 operator action 的显式记录
* **checkpoint**：恢复、重试、重跑前的紧凑恢复快照
* **通用执行者 (general executor)**：专为宽泛任务执行和状态修改设计的 Agent 角色
* **专项 Agent (specialist agent)**：专为高内聚的子系统工作设计的 Agent 角色，被严格限制掌控整体任务流转权
* **记忆权限 (memory authority)**：明确授予 Agent 的读写作用域（如无状态 stateless、任务状态 task-state、待审知识 staged-knowledge 等）

---

## 许可证

待定
