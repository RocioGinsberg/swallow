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
| **apply_proposal() 入口函数化** | INVARIANTS / ARCHITECTURE / STATE_AND_TRUTH / EXECUTOR_REGISTRY / SELF_EVOLUTION / INTERACTION | canonical / route / policy 写入设计为仅通过 apply_proposal() 进行(INVARIANTS §0-4,§9 守卫测试);但实际代码零匹配,当前由 swl knowledge apply-suggestions / swl route apply-proposals 等 CLI 直接调底层 store——宪法与代码级漂移 | **后续专项**:需 phase 实现 apply_proposal() 函数、聚合现有 CLI 写路径并补齐守卫测试;或反向修订 INVARIANTS 承认 CLI 等价入口 |
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
| **当前 active** | — | 待 Direction Gate 决策 | — | Phase 60 已收口,下一方向待人工选择 |
| 推荐次序 1 | 候选 F | `apply_proposal()` 入口函数化(Architectural fix) | Design / Governance | 宪法 vs 代码漂移待修复 |
| 推荐次序 2 | 候选 E | 完整 Multi-Perspective Synthesis | Orchestration | A-lite 反馈已具备,设计已就绪 |
| 推荐次序 3 | 候选 D | 编排增强(Planner / DAG / Strategy Router) | Orchestration | 无真实瓶颈推动 |

### 候选 F:`apply_proposal()` 入口函数化(Architectural fix)

- **核心价值**:把 INVARIANTS §0 第 4 条规定的"canonical / route / policy 写入唯一入口"在代码中真正落地;补齐 §9 三条守卫测试(`test_canonical_write_only_via_apply_proposal` / `test_only_apply_proposal_calls_private_writers` / `test_route_metadata_writes_only_via_apply_proposal`);消除 7+ 设计文档与代码之间的宪法级漂移
- **可能 slice**:`apply_proposal()` 函数定义 / canonical-write 路径收敛 / route-metadata 写路径收敛 / policy-write 路径收敛 / §9 守卫测试补齐
- **风险**:中——影响所有现有 CLI 写路径(`swl knowledge apply-suggestions` / `swl route apply-proposals` 等),但属于同质重构;无新能力引入,无功能回归面;回滚清晰
- **优先级理由**:宪法漂移期待及早收敛,拖得越久新增写路径越可能继续违反;依赖关系简单,可独立交付;完成后系统不变量观测能力大幅提升
- **依赖**:无外部依赖;只依赖 INVARIANTS 现有定义

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

**F → E → D**(Phase 60 已收口,以下为下一方向候选的推荐次序)

理由:

1. **F 优先(`apply_proposal()` 入口函数化)**——是宪法漂移,7+ 设计文档基于"apply_proposal 是唯一入口"展开;不修复会持续制造新违反点。设计已写死,实现等价于"把 INVARIANTS 文字翻译成代码"。无新能力引入,回滚清晰,影响面虽广但同质,适合作为 architectural fix 单独 phase 收敛。完成后 §9 三条守卫测试落地,系统不变量观测能力上一个台阶
2. **E 中期(Multi-Perspective Synthesis)**——ORCHESTRATION §5 设计已成熟,A-lite 已落地一段时间,反馈基础具备。是 Path A 认知层的下一个大跃升,用户体验导向价值高;但复杂度也高,先稳住宪法再做更稳妥
3. **D 后置(Planner / DAG / Strategy Router)**——编排能力实际可用,无真实瓶颈推动。Planner 部分已抽出在 `orchestrator.py` / `planner.py` 中,显式化是架构债务清理而非阻塞修复。orchestrator 主链路重构回滚成本高,应在真实需求明确后再做

**取舍提示**:若 human 偏向体验向新功能而非治理向修旧账,E 与 F 顺序可对换。但 INVARIANTS §9 已列出 apply_proposal 守卫测试,治理债务无限拖延的成本会随每次 governance-adjacent 的 phase 累积

---

## 六、战略锚点分析

| 维度 | 蓝图愿景 | 当前现状 | 下一步候选 |
|------|---------|----------|-----------|
| 知识治理 | truth-first 多阶段检索 + neural retrieval | 全部实现 | 稳定期 |
| 知识捕获 | 低摩擦入口 + 外部讨论回收 + staged review | A-lite 已落地 | 稳定期 |
| CLI 生态 | aider + claude-code + codex 三足鼎立 | 三者均为独立 route | 稳定期 |
| 检索分流 | retrieval policy 感知 execution family + task intent | ✅ 已按 path / executor family / task_family 分流 | **稳定期**;后续可评估 operator-facing override CLI / 更细粒度 task-family 专用化 |
| Agent 体系 | 4 个 Specialist + 2 个 Validator 独立生命周期 | 全部落地 | 稳定期 |
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
