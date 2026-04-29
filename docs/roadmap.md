---
author: claude
status: living-document
---

> **Document discipline**
> Owner: Claude
> Updater: Claude 主线(差距条目新增 / 推荐队列 / 优先级 / 风险批注 / 战略锚点)+ `roadmap-updater` subagent(phase 完成事实登记 / 已有差距条目状态同步)
> Trigger: phase 收口 OR 会话讨论中浮现新方向 OR phase 拆分 OR Human 请求方向建议
> Anti-scope: 不维护已完成 phase 历史(→ git log + `docs/plans/<phase>/closeout.md`);不维护 tag / release docs 状态(→ `docs/concerns_backlog.md`);不存储设计原则(→ `INVARIANTS.md`);不维护 phase 高频状态(→ `docs/active_context.md`)
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
| **治理守卫收口** | INVARIANTS / DATA_MODEL / SELF_EVOLUTION | Phase 61 / 62 暴露 5 条宪法-代码漂移 Open:(1) §9 剩余 14 条守卫测试缺失,(2) Repository 抽象层(`KnowledgeRepo` / `RouteRepo` / `PolicyRepo`)未实装,(3) `apply_proposal` 事务性回滚缺失,(4) `orchestrator.py:3145` stagedK 直写违反 §5 矩阵,(5) INVARIANTS §7 集中化函数不存在、§9 守卫可能 vacuous | **候选 G**(Phase 63 active):据 M0 audit 缩小范围 — `_route_knowledge_to_staged` 生产 0 触发改为删除 dead code(消化漂移 4);事务回滚拆出独立方向(候选 H);本 phase 集中做 §7 集中化 + Repository 抽象层 + §9 守卫批量(NO_SKIP 6/8 条) |
| **NO_SKIP 守卫红灯修复** | INVARIANTS §0 / §4 | Phase 63 M0 audit 发现 2 条 NO_SKIP 守卫红灯:(1) `executor.py:510` `fallback_route_for` 涉及 executor / orchestrator 的 control plane 边界;(2) `agent_llm.py:57` `httpx.post` 直连违反 §4 Path C(Specialist 内部 LLM 调用应走 Provider Router) | **候选 G.5**(Phase 63.5,紧随 G):治理边界澄清 — fallback route 选择责任归位 + agent_llm 改走 Provider Router;G.5 完成后 §9 NO_SKIP 守卫可全 8 条启用 |
| **Truth Plane SQLite 一致性** | INVARIANTS P2 / DATA_MODEL §3 / SELF_EVOLUTION | route metadata / policy 当前以 JSON 文件 + 进程内 dict 存储,违背 P2 "SQLite-primary truth"。`apply_proposal` 4 步序列(`save_route_weights → apply → save_capability_profiles → apply`)缺事务保证,中途失败导致 in-memory 不一致;长期亦阻碍对象存储后端兼容(S3 / MinIO / OSS 没有文件系统原子 rename) | **候选 H**(Phase 64,依赖 G + G.5 完成):route metadata / policy 迁入 SQLite,`apply_proposal` 用 `BEGIN IMMEDIATE` transaction,引入 `route_change_log` / `policy_change_log` 审计表;履行 INVARIANTS P2 在治理状态上的代码层承诺 |
| **能力画像自动学习** | PROVIDER_ROUTER / SELF_EVOLUTION | 已被路由消费;自动学习质量与 guard 可观测性仍需提升 | **后续方向** |
| **Runtime v1** | HARNESS | harness bridge 为 v0 约束 | 低优先级 |
| **远期方向** | 多处 | — | 跨设备同步(基于 git / 同步盘)、团队协作扩展(基于 INVARIANTS §7 埋点)、IDE 集成、Remote Worker、Hosted Control Plane |

---

## 四、推荐 Phase 队列

### 队列总览

| 优先级 | Phase 候选 | 名称 | Primary Track | 状态 |
|--------|-----------|------|---------------|------|
| **当前 active** | 候选 G | 治理守卫收口(Governance Closure) | Governance | Direction = 候选 G;M0 audit 已完成,scope 据 audit 缩小(删 dead code + 拆 G.5 + 拆 H);待 final-after-m0 三件套 + Human Design Gate |
| ~~推荐次序 1~~ | ~~候选 F~~ | ~~`apply_proposal()` 入口函数化(Architectural fix)~~ | ~~Design / Governance~~ | ~~✅ Phase 61 已完成~~ |
| ~~推荐次序 1~~ | ~~候选 E~~ | ~~完整 Multi-Perspective Synthesis~~ | ~~Orchestration~~ | ~~✅ Phase 62 已完成~~ |
| 推荐次序 1(紧随 G) | 候选 G.5 | NO_SKIP 守卫红灯修复 | Governance | M0 audit 暴露 2 条 NO_SKIP 红灯;依赖 G 完成 |
| 推荐次序 2 | 候选 H | Truth Plane SQLite 一致性 | Truth / Storage | 履行 INVARIANTS P2;依赖 G + G.5 完成 |
| 推荐次序 3 | 候选 D | 编排增强(Planner / DAG / Strategy Router) | Orchestration | 无真实瓶颈推动 |

### 候选 G:治理守卫收口(Governance Closure)— Phase 63 active

- **核心价值**:消化 Phase 61 / 62 暴露的宪法-代码漂移 Open,把 §7 集中化函数 + Repository 抽象层 + §9 守卫批量一次性收敛
- **scope(据 M0 audit 缩小)**:M0 audit / M1 §7 集中化 / M2 删除 `_route_knowledge_to_staged` dead code(生产 0 触发) + Repository 抽象层骨架 / M3 §9 守卫 batch(NO_SKIP 6 条启用,2 条暂缓到 G.5)
- **拆出**:`apply_proposal` 事务回滚原计划在本 phase 做(S5),M0 audit 发现现有 store 是 JSON + in-memory 不是 SQLite,正确实装路径需要 storage migration → 拆出独立 phase H
- **风险**:中——Repository 抽象层重塑 governance 依赖图(高风险 slice 已是 phase 内唯一 7 分),其余治理表面收敛回滚成本低
- **优先级理由**:宪法层债务继续累积会让 INVARIANTS 失去威慑力;Phase 61/62 已经引入两次"承认现状、登记 Open"模式,再不收口会成习惯
- **依赖**:无;与 G.5 / H / D 不冲突(Repository 抽象层骨架是 H 与 D 的有用前置)

### 候选 G.5:NO_SKIP 守卫红灯修复

- **核心价值**:消化 Phase 63 M0 audit 暴露的 2 条 NO_SKIP 守卫红灯,完成 §9 全 17 条守卫严格执行
- **可能 slice**:S1 `executor.py:510` fallback_route_for 边界澄清(executor 不再独立选 fallback route,改由 orchestrator 决策后传入)/ S2 `agent_llm.py:57` 改走 Provider Router(履行 §4 Path C "Specialist 内部 LLM 调用必须穿透到 Provider Router")
- **风险**:中——两条都触及治理边界,但范围收敛(executor 单点 + agent_llm 单点)
- **优先级理由**:Phase 63 NO_SKIP 守卫只启用 6/8 条留尾巴;G.5 是 G 的自然延续,完成后宪法守卫真正可全启用
- **依赖**:Phase 63(G)完成,Repository 抽象层骨架已就位

### 候选 H:Truth Plane SQLite 一致性 — INVARIANTS P2 兑现

- **核心价值**:履行 INVARIANTS P2 "SQLite-primary truth" 在 route metadata / policy 上的代码层承诺;为对象存储后端兼容(S3 / MinIO / OSS)清除技术债;`apply_proposal` 真正可包 transaction
- **可能 slice**:M1 schema 设计(`route_metadata` / `policy` SQLite 表 + index + constraint) / M2 store 函数迁移(4 个 store 写函数从 JSON 改 SQL 写,接受 connection)/ M3 reader 改造(orchestrator / Provider Router / CLI 各处)/ M4 migration 脚本(JSON → SQLite,旧文件保留 backup)+ `apply_proposal` `BEGIN IMMEDIATE` 包装 + `route_change_log` / `policy_change_log` 审计表
- **风险**:高——schema 设计 + reader 改造跨多模块 + migration backwards compat;但**回滚成本中**(每个 milestone 边界清晰,migration 阶段可保留 JSON backup 做双写过渡)
- **优先级理由**:P2 是 INVARIANTS 中明确写出的不变量但代码层未兑现;长期不修复会阻碍对象存储后端、阻碍多 actor 扩展、让事务回滚永远没有正确实装路径
- **依赖**:Phase 63(G)+ G.5 完成。G 的 Repository 抽象层骨架是 H 的天然实装载体(Repository 私有方法切换到 SQL 写,governance 层无感)

### 候选 D:编排增强(Planner / DAG / Strategy Router 显式化)

- **核心价值**:把已部分抽出的 planning 能力继续一等化,形成明确 Planner 接口、DAG dependency orchestration 与 Strategy Router 可观测边界
- **可能 slice**:Planner 接口抽取 / DAG-based subtask 依赖 / Strategy Router 显式化
- **风险**:高——涉及 orchestrator 主链路重构,回滚成本高
- **优先级理由**:架构债务清理,但当前编排能力实际可用,没有真实瓶颈推动
- **依赖**:无强依赖;但 H 的 Repository SQL 化对 D 的 Planner / Strategy Router 一等化有益(state.py / route registry 都是 SQL-backed)

---

## 五、Claude 推荐顺序

**G → G.5 → H → D**(2026-04-29,M0 audit 后修订)

理由:

1. **候选 G 优先(治理守卫收口,Phase 63 active)** —— Phase 61 / 62 引入两次"承认现状、登记 Open"模式,再不收口会让 INVARIANTS 失去威慑力。M0 audit 缩小后 scope 收敛(治理表面 + 删 dead code),Repository 抽象层骨架是后续 G.5 / H / D 的有用前置
2. **候选 G.5 紧随(NO_SKIP 红灯修复)** —— G 完成后 §9 守卫只启用 6/8 条会留治理尾巴;G.5 是 G 的自然延续,2 条红灯都已被 M0 audit 精确定位,scope 可控,完成后宪法守卫真正全启用
3. **候选 H 优先于 D(Truth Plane SQLite 一致性)** —— P2 "SQLite-primary truth" 是 INVARIANTS 已写但代码未兑现的不变量。从 Phase 61 留下的"事务回滚"Open 视角,H 是这条 Open 的**唯一正确实装路径**(filesystem 层 staging 治标不治本);从长期视角,H 是对象存储后端兼容的前提。G 的 Repository 抽象层骨架已为 H 准备实装载体
4. **候选 D 后置(Planner / DAG / Strategy Router)** —— 编排能力实际可用,无真实瓶颈推动。orchestrator 主链路重构回滚成本高,等到真实需求(MPS 真实使用反馈 / 多 task 复杂依赖场景 / H 的 SQL-backed state 形成稳定基础)出现后再做

---

## 六、战略锚点分析

| 维度 | 蓝图愿景 | 当前现状 | 下一步候选 |
|------|---------|----------|-----------|
| 知识治理 | truth-first 多阶段检索 + neural retrieval | 全部实现 | 稳定期 |
| 知识捕获 | 低摩擦入口 + 外部讨论回收 + staged review | A-lite 已落地 | 稳定期 |
| CLI 生态 | aider + claude-code + codex 三足鼎立 | 三者均为独立 route | 稳定期 |
| 检索分流 | retrieval policy 感知 execution family + task intent | ✅ 已按 path / executor family / task_family 分流 | **稳定期**;后续可评估 operator-facing override CLI / 更细粒度 task-family 专用化 |
| Agent 体系 | 4 个 Specialist + 2 个 Validator 独立生命周期 | 全部落地 | 稳定期 |
| 写入治理 | INVARIANTS §0.4 canonical / route / policy 唯一入口 + §9 守卫测试 | Phase 61 apply_proposal() 三类主写入收敛,3 条守卫测试落地;§7 集中化 / Repository 抽象层 / §9 守卫 / stagedK 漂移 5 条 Open 在 Phase 63(候选 G)收口;事务回滚拆出 H | **候选 G**(Phase 63 active)+ **候选 G.5**(NO_SKIP 红灯)+ **候选 H**(Truth Plane SQLite,事务回滚) |
| 治理边界 LLM 路径 | INVARIANTS §0.3 + §4 三条 LLM 路径(A 受控 HTTP / B agent 黑盒 / C Specialist 内部穿透 Provider Router) | M0 audit 暴露 `agent_llm.call_agent_llm` 直连 chat completions endpoint,Specialist 内部 LLM 调用未经 Provider Router(违反 Path C);`executor.py:510` `fallback_route_for` 在 executor 内部选 fallback route(模糊 control plane 边界) | **候选 G.5**(Phase 63.5,紧随 G) |
| Truth 物理存储 | INVARIANTS P2 SQLite-primary truth + 对象存储后端兼容性 | task / event / knowledge / evidence / relations 已迁 SQLite;route metadata / policy / MPS policy 仍为 JSON 文件 + 进程内 dict;阻碍事务保证 + 对象存储后端 + multi-actor 扩展 | **候选 H**(Phase 64,依赖 G + G.5) |
| 执行编排 | 高并发多路 + DAG | fan-out 已落地 | **候选 D**(后置) |
| 思考-讨论-沉淀(完整) | 受控多视角综合 + multi-route synthesis | MPS 受控多视角综合 + 仲裁已落地(Phase 62) | **稳定期** |
| 自我进化 | Librarian + Meta-Optimizer 提案应用闭环 | 已基本完成 | 远期 |

---

## 七、本文件的职责边界

`docs/roadmap.md` 是:
- 跨 phase 蓝图对齐活文档
- 前瞻性差距表(Claude 主线维护差距条目;`roadmap-updater` subagent 同步已有条目的 phase 完成状态)
- 推荐 phase 队列(Claude 维护候选块、优先级排序与风险批注)
- 战略锚点分析(能力维度 × 现状 × 下一步;Claude 主线维护)

`docs/roadmap.md` 不是:
- 当前 phase 状态板(→ `docs/active_context.md`)
- 完整 phase 历史编年(→ git log + `docs/plans/<phase>/closeout.md`)
- 设计文档(→ 仓库根设计文档体系)
- 设计原则副本(→ `INVARIANTS.md`)
- closeout 索引(→ `docs/plans/<phase>/closeout.md`)
- Tag / Release docs 同步状态(→ `docs/concerns_backlog.md`)
