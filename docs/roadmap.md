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
| **Agent 体系** | 4 个 Specialist(Librarian / Ingestion / Literature / Meta-Optimizer)+ 2 个 Validator(Quality / Consistency)独立生命周期 |
| **CLI 生态** | aider + claude-code + codex 三足鼎立(详见 EXECUTOR_REGISTRY) |
| **执行编排** | fan-out + timeout + subtask summary 已落地;独立 Planner / DAG / Strategy Router 仍未一等化 |
| **自我进化** | Librarian 知识沉淀 + Meta-Optimizer 提案应用闭环 |

---

## 二、Era 演进锚点

> 一句话 Era 摘要,帮助新协作者快速建立 context。具体 phase 细节通过 `git log` 与 `docs/plans/<phase>/closeout.md` 追溯,本文件不维护 phase 历史。

| Era | Phase 范围 | 一句话摘要 |
|-----|------------|------------|
| **Foundation Era** | Phase 47-54 | 6 个能力代际依次落地(Consensus → Async → Knowledge → Policy → Parallel → Specialist),架构债务清零,4 个 Specialist + 2 个 Validator 独立生命周期成型 |
| **Knowledge Loop Era** | Phase 55+ | 演进逻辑从"消化蓝图差距"转为"从可展示的知识闭环出发,逐步扩展系统能力";每个 phase 是前一个的自然延伸 |

---

## 三、前瞻性差距表

| 差距 | 相关设计文档 | 当前状态 | 演进方向 |
|------|-------------|---------|---------| 
| **路径感知的 Retrieval Policy** | KNOWLEDGE / ARCHITECTURE / AGENT_TAXONOMY | [已消化] autonomous CLI coding route 默认只取 knowledge,HTTP route 默认聚焦 knowledge + notes,legacy fallback 保留旧三源兼容,TaskSemantics.retrieval_source_types 支持显式 override | **Phase 60 完成**:按 route capability + executor family + task_family 分流 retrieval request,repo source 显式化 |
| **apply_proposal() 入口函数化** | INVARIANTS / ARCHITECTURE / STATE_AND_TRUTH / EXECUTOR_REGISTRY / SELF_EVOLUTION / INTERACTION | [已消化] canonical / route / policy 三类主写入收敛至 `apply_proposal()` 唯一入口,M1 canonical boundary + M2 route metadata boundary + M3 policy boundary 完整落地,3 条 INVARIANTS §9 apply_proposal 守卫测试已实装;后续仍有 14 条非 apply_proposal 守卫测试与 Repository 抽象层 durable artifact 层待完整化 | **Phase 61 完成**:apply_proposal() 三参数入口函数实装,canonical knowledge / route metadata / policy 三类主写入路径收敛,§9 三条守卫测试落地,INVARIANTS §0 第 4 条代码级合规;剩余 14 条 §9 守卫测试 + durable Repository 层 + 事务性回滚机制为后续 Open 债务 |
| **编排显式化(Planner / DAG)** | ORCHESTRATION | Planner 部分构造已抽出,DAG / Strategy Router 仍未一等化 | **候选 D**:Planner 独立组件、DAG subtask 依赖、Strategy Router 显式化 |
| **完整 Multi-Perspective Synthesis** | ORCHESTRATION | [已消化] MPS Path A route-resolved participant / arbiter 编排、policy governance、staged knowledge bridge、13 条守卫测试完整落地 | **Phase 62 完成**:基于 artifact pointer 的多视角并行+仲裁,受控 multi-route synthesis 编排与显式 staged handoff 闭合;A-lite 低摩擦捕获反馈基础已具备 |
| **治理守卫收口** | INVARIANTS / DATA_MODEL / SELF_EVOLUTION | Phase 61 / 62 暴露 5 条宪法-代码漂移 Open:(1) §9 剩余 14 条守卫测试缺失,(2) Repository 抽象层(`KnowledgeRepo` / `RouteRepo` / `PolicyRepo`)未实装,(3) `apply_proposal` 事务性回滚缺失,(4) `orchestrator.py:3145` stagedK 直写违反 §5 矩阵,(5) INVARIANTS §7 集中化函数不存在、§9 守卫可能 vacuous | **候选 G**:一次性收敛 5 条宪法漂移 Open,把 INVARIANTS §5 / §7 / §9 与代码侧拉齐 |
| **能力画像自动学习** | PROVIDER_ROUTER / SELF_EVOLUTION | 已被路由消费;自动学习质量与 guard 可观测性仍需提升 | **后续方向** |
| **Runtime v1** | HARNESS | harness bridge 为 v0 约束 | 低优先级 |
| **远期方向** | 多处 | — | 跨设备同步(基于 git / 同步盘)、团队协作扩展(基于 INVARIANTS §7 埋点)、IDE 集成、Remote Worker、Hosted Control Plane |

---

## 四、推荐 Phase 队列

### 队列总览

| 优先级 | Phase 候选 | 名称 | Primary Track | 状态 |
|--------|-----------|------|---------------|------|
| **当前 active** | 候选 G | 治理守卫收口(Governance Closure) | Governance | Direction = 候选 G(治理守卫收口);5 条宪法漂移 Open 待消化 |
| ~~推荐次序 1~~ | ~~候选 F~~ | ~~`apply_proposal()` 入口函数化(Architectural fix)~~ | ~~Design / Governance~~ | ~~✅ Phase 61 已完成~~ |
| ~~推荐次序 1~~ | ~~候选 E~~ | ~~完整 Multi-Perspective Synthesis~~ | ~~Orchestration~~ | ~~✅ Phase 62 已完成~~ |
| 推荐次序 2 | 候选 D | 编排增强(Planner / DAG / Strategy Router) | Orchestration | 无真实瓶颈推动 |

### 候选 G:治理守卫收口(Governance Closure)

- **核心价值**:消化 Phase 61 / 62 暴露的 5 条宪法-代码漂移 Open,构建合规的 governance 守卫完整性
- **可能 slice**:M1 §7 集中化函数 + 守卫真实化 / M2 stagedK 治理通道 + Repository 抽象层骨架 / M3 §9 剩余守卫批量实装 / M4 事务回滚 staged 应用
- **风险**:中——多在治理表面收敛,回滚成本低;但 Repository 抽象层涉及现有 store 函数封装,需谨慎设计接口
- **优先级理由**:宪法层债务继续累积会让 INVARIANTS 失去威慑力;Phase 61/62 已经引入两次"承认现状、登记 Open"模式,再不收口会成习惯
- **依赖**:无,且与未来 D 不冲突(Repository 抽象层是 D 的有用前置)

### 候选 D:编排增强(Planner / DAG / Strategy Router 显式化)

- **核心价值**:把已部分抽出的 planning 能力继续一等化,形成明确 Planner 接口、DAG dependency orchestration 与 Strategy Router 可观测边界
- **可能 slice**:Planner 接口抽取 / DAG-based subtask 依赖 / Strategy Router 显式化
- **风险**:高——涉及 orchestrator 主链路重构,回滚成本高
- **优先级理由**:架构债务清理,但当前编排能力实际可用,没有真实瓶颈推动

---

## 五、Claude 推荐顺序

**G → D**(2026-04-29 Direction Gate 选定 G 为 Phase 63;以下为剩余候选的相对优先级)

理由:

1. **候选 G 优先(治理守卫收口)** —— Phase 61 / 62 已经引入两次"承认现状、登记 Open"模式(librarian-side-effect / orchestrator stagedK 直写 / §7 集中化函数缺失 / §9 14 条守卫缺失),再不收口会让 INVARIANTS 失去威慑力。范围相对收敛(全是 §5 / §7 / §9 治理表面),回滚成本低,且 Repository 抽象层骨架是未来 D 的有用前置。
2. **候选 D 后置(Planner / DAG / Strategy Router)** —— 编排能力实际可用,无真实瓶颈推动。Planner 部分已抽出在 `orchestrator.py` / `planner.py` 中,显式化是架构债务清理而非阻塞修复;orchestrator 主链路重构回滚成本高。建议等到真实需求(MPS 真实使用反馈 / 多 task 复杂依赖场景)出现后再做。

---

## 六、战略锚点分析

| 维度 | 蓝图愿景 | 当前现状 | 下一步候选 |
|------|---------|----------|-----------|
| 知识治理 | truth-first 多阶段检索 + neural retrieval | 全部实现 | 稳定期 |
| 知识捕获 | 低摩擦入口 + 外部讨论回收 + staged review | A-lite 已落地 | 稳定期 |
| CLI 生态 | aider + claude-code + codex 三足鼎立 | 三者均为独立 route | 稳定期 |
| 检索分流 | retrieval policy 感知 execution family + task intent | ✅ 已按 path / executor family / task_family 分流 | **稳定期**;后续可评估 operator-facing override CLI / 更细粒度 task-family 专用化 |
| Agent 体系 | 4 个 Specialist + 2 个 Validator 独立生命周期 | 全部落地 | 稳定期 |
| 写入治理 | INVARIANTS §0.4 canonical / route / policy 唯一入口 + §9 守卫测试 | Phase 61 apply_proposal() 三类主写入收敛,3 条守卫测试落地;§9 剩余 14 条守卫 / Repository 抽象层 / 事务回滚 / orchestrator stagedK 直写 / §7 集中化函数 5 条 Open 待消化 | **候选 G**(Phase 63 active) |
| 执行编排 | 高并发多路 + DAG | fan-out 已落地 | **候选 D**(后置) |
| 思考-讨论-沉淀(完整) | 受控多视角综合 + multi-route synthesis | MPS 受控多视角综合 + 仲裁已落地(Phase 62) | **稳定期** |
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
