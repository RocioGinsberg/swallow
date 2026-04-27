---
author: claude
status: living-document
---

> **Document discipline**
> Owner: Claude
> Updater: `roadmap-updater` subagent (after phase closeout)
> Trigger: phase 收口 OR 新设计文档引入重大方向
> Anti-scope: 不维护已完成 phase 历史(→ git log + `docs/plans/<phase>/closeout.md`);不维护 tag / release docs 状态(→ `docs/concerns_backlog.md`);不存储设计原则(→ `INVARIANTS.md`)
> 长度上限:300 行;超过说明放进了不该放的东西

# 演进路线图 (Roadmap)

> 最近更新:见 git log。本文件不在文档内维护"最近更新时间",由 git 提供权威时间线。

---

## 一、当前实现基线(摘要)

详细当前能力描述见 `README.md` 与 `EXECUTOR_REGISTRY.md`。本节只提供一句话锚点,帮助决策"下一步走向哪里"。

| 维度 | 现状摘要 |
|------|---------|
| **知识治理** | truth-first 双层架构完整,relation-aware retrieval 与 LLM 增强已落地 |
| **知识捕获** | 低摩擦入口已落地(`swl note` / clipboard / `generic_chat_json`) |
| **检索基础设施** | 神经 API embedding + LLM rerank + canonical/verified 路径对齐 |
| **Agent 体系** | 7 个 Specialist Agent 独立生命周期 |
| **CLI 生态** | aider + claude-code + codex 三足鼎立(详见 EXECUTOR_REGISTRY) |
| **执行编排** | fan-out + timeout + subtask summary 已落地;独立 Planner / DAG / Strategy Router 仍未一等化 |
| **自我进化** | Librarian 知识沉淀 + Meta-Optimizer 提案应用闭环 |

---

## 二、Era 演进锚点

> 一句话 Era 摘要,帮助新协作者快速建立 context。具体 phase 细节通过 `git log` 与 `docs/plans/<phase>/closeout.md` 追溯,本文件不维护 phase 历史。

| Era | Phase 范围 | 一句话摘要 |
|-----|------------|------------|
| **Foundation Era** | Phase 47-54 | 6 个能力代际依次落地(Consensus → Async → Knowledge → Policy → Parallel → Specialist),架构债务清零,7 个 Specialist Agent 独立生命周期成型 |
| **Knowledge Loop Era** | Phase 55+ | 演进逻辑从"消化蓝图差距"转为"从可展示的知识闭环出发,逐步扩展系统能力";每个 phase 是前一个的自然延伸 |

---

## 三、前瞻性差距表

| 差距 | 相关设计文档 | 当前状态 | 演进方向 |
|------|-------------|---------|---------| 
| **路径感知的 Retrieval Policy** | KNOWLEDGE / ARCHITECTURE / AGENT_TAXONOMY | retrieval 默认 source 与执行路径无关;Path B coding route 可能被重复灌入 repo chunk,Path A 也容易被误塑造成代码库 Q&A 的 repo RAG 辅助链路 | **候选 C / 当前 active**:按 route capability + execution family + task_family 分流 retrieval request,repo source 显式化 |
| **编排显式化(Planner / DAG)** | ORCHESTRATION | Planner 部分构造已抽出,DAG / Strategy Router 仍未一等化 | **候选 D**:Planner 独立组件、DAG subtask 依赖、Strategy Router 显式化 |
| **完整 Multi-Perspective Synthesis** | ORCHESTRATION | A-lite 已落地低摩擦捕获;受控 multi-route synthesis 编排仍未实现 | **候选 E**:基于 artifact pointer 的多视角并行+仲裁,依赖 A-lite 真实使用反馈 |
| **能力画像自动学习** | PROVIDER_ROUTER / SELF_EVOLUTION | 已被路由消费;自动学习质量与 guard 可观测性仍需提升 | **后续方向** |
| **Runtime v1** | HARNESS | harness bridge 为 v0 约束 | 低优先级 |
| **远期方向** | 多处 | — | 跨设备同步(基于 git / 同步盘)、团队协作扩展(基于 INVARIANTS §7 埋点)、IDE 集成、Remote Worker、Hosted Control Plane |

---

## 四、推荐 Phase 队列

### 队列总览

| 优先级 | Phase 候选 | 名称 | Primary Track | 状态 |
|--------|-----------|------|---------------|------|
| **当前 active** | 候选 C | 路径感知的 Retrieval Policy | Knowledge / RAG | Implementation pending |
| 中期 | 候选 E | 完整 Multi-Perspective Synthesis | Orchestration | 等候 A-lite 使用反馈 |
| 后置 | 候选 D | 编排增强(Planner / DAG / Strategy Router) | Orchestration | 等候真实瓶颈出现 |

### 候选 C:路径感知的 Retrieval Policy(执行路径分流)

- **核心价值**:retrieval 按 execution path、route capability 和 task_family 分流,并落实 KNOWLEDGE 中 source type 语义。Path B(自主 CLI coding)默认减少 repo chunk,代码库上下文由 CLI tool-loop 主动读取;Path A(HTTP)默认聚焦 knowledge / notes;Specialist Agent 依赖 explicit input_context 与专属 artifacts;repo source 降级为 explicit override 或 legacy fallback 辅助源
- **实施 slice**:
  1. route capability + executor family 判定接入 retrieval request 构造
  2. Path B 默认 source 收紧为 knowledge,并保护非自主 local fallback / deterministic route 兼容
  3. Path A planning/review/execution/extraction/retrieval 默认聚焦 knowledge / notes,不因 task_family 自动启用 repo
  4. `task_semantics.retrieval_source_types` 显式 override,并测试 Specialist / explicit input_context 不被通用 HTTP/CLI policy 误伤
- **风险**:中——涉及 retrieval 默认行为变化,需配套测试
- **依赖**:已落地的 retrieval 基线 + 知识捕获入口
- **优先级理由**:架构正确性提升;已落地的低摩擦捕获之后,retrieval 是下一个最有价值的分流点

### 候选 D:编排增强(Planner / DAG / Strategy Router 显式化)

- **核心价值**:把已部分抽出的 planning 能力继续一等化,形成明确 Planner 接口、DAG dependency orchestration 与 Strategy Router 可观测边界
- **可能 slice**:Planner 接口抽取 / DAG-based subtask 依赖 / Strategy Router 显式化
- **风险**:高——涉及 orchestrator 主链路重构,回滚成本高
- **优先级理由**:架构债务清理,但当前编排能力实际可用,没有真实瓶颈推动

### 候选 E:完整 Multi-Perspective Synthesis(受控多视角综合)

- **核心价值**:基于 ORCHESTRATION 中 Multi-Perspective Synthesis 设计,落地基于 artifact pointer 的多视角并行 + 仲裁,产出结构化 artifact 进入 staged knowledge
- **可能 slice**:`SynthesisConfig` + topology 定义 / multi-route synthesis orchestration / synthesis artifact → staged knowledge 自动候选通道
- **风险**:中到高——涉及新编排组件,需在低摩擦捕获的真实使用反馈基础上再做
- **优先级理由**:使用价值高但复杂度也高;建议在低摩擦捕获入口被证明有效后再做

---

## 五、Claude 推荐顺序

**C → E → D**

理由:

1. **C 优先**——已落地的 retrieval 基线之后,retrieval 分流是下一个最直接有价值的优化。需要收紧的是 Path B 与 Path A 默认源;Path B 的 local fallback 路径可作为 legacy 兼容暂保留旧三源。代码库问答应优先走 Path B 的 tool-loop,repo chunk 不应继续作为 Path A 默认辅助链路;Specialist Agent 不应被误归类成第三种通用 executor family
2. **E 中期**——Multi-Perspective Synthesis 是 Path A 认知层的自然主场,使用体验层面的下一个大跃升。但复杂度高,且需要低摩擦捕获入口的真实使用反馈来校准 topology 设计
3. **D 后置**——编排能力实际可用,没有真实瓶颈。Planner / DAG 重构回滚成本高,应在真实需求明确后再做

---

## 六、战略锚点分析

| 维度 | 蓝图愿景 | 当前现状 | 下一步候选 |
|------|---------|----------|-----------|
| 知识治理 | truth-first 多阶段检索 + neural retrieval | 全部实现 | 稳定期 |
| 知识捕获 | 低摩擦入口 + 外部讨论回收 + staged review | A-lite 已落地 | 稳定期 |
| CLI 生态 | aider + claude-code + codex 三足鼎立 | 三者均为独立 route | 稳定期 |
| 检索分流 | retrieval policy 感知 execution family + task intent | 默认 source 不分流 | **候选 C** |
| Agent 体系 | 7 个专项角色独立生命周期 | 全部落地 | 稳定期 |
| 执行编排 | 高并发多路 + DAG | fan-out 已落地 | **候选 D**(后置) |
| 思考-讨论-沉淀(完整) | 受控多视角综合 + multi-route synthesis | A-lite 已落地低摩擦捕获 | **候选 E**(中期) |
| 自我进化 | Librarian + Meta-Optimizer 提案应用闭环 | 已基本完成 | 远期 |

---

## 七、本文件的职责边界

`docs/roadmap.md` 是:
- 跨 phase 蓝图对齐活文档
- 推荐 phase 队列(Claude 维护优先级与风险批注)
- 战略锚点分析(能力维度 × 现状 × 下一步)

`docs/roadmap.md` 不是:
- 当前 phase 状态板(→ `docs/active_context.md`)
- 完整 phase 历史编年(→ git log + `docs/plans/<phase>/closeout.md`)
- 设计文档(→ 仓库根设计文档体系)
- 设计原则副本(→ `INVARIANTS.md`)
- closeout 索引(→ `docs/plans/<phase>/closeout.md`)
- Tag / Release docs 同步状态(→ `docs/concerns_backlog.md`)
