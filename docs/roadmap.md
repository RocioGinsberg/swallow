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
| **知识治理** | storage-abstracted, evidence-backed wiki retrieval 三层架构(Raw Material / Knowledge Truth / Retrieval & Serving),Wiki / Canonical 默认主入口,relation-aware retrieval 与 LLM 增强已落地 |
| **知识捕获** | 低摩擦入口已落地(`swl note` / clipboard / `generic_chat_json`) |
| **检索基础设施** | 神经 API embedding + LLM rerank + canonical/verified 路径对齐;向量与全文索引仅作辅助召回与 fallback,不是知识真值(P3) |
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
| **治理守卫收口** | INVARIANTS / DATA_MODEL / SELF_EVOLUTION | [已消化] Phase 63 + Phase 64 完成:§7 集中化函数 + Repository 抽象层 + §9 17 条守卫全 active(0 skip);route metadata / policy 三层外部化(fallback override config + route registry + route selection policy);剩余事务回滚(JSON 存储架构不支持)拆出候选 H | **Phase 63+64 完成**:详见 `docs/plans/phase63/closeout.md` + `docs/plans/phase64/closeout.md` |
| **NO_SKIP 守卫红灯修复** | INVARIANTS §0 / §4 | [已消化] Phase 64 完成:Path B fallback chain plan 前移 Orchestrator,Executor 通过只读 `lookup_route_by_name` 消费;Specialist internal chat-completion 穿透 `router.invoke_completion()`,§9 两条红灯对应守卫全启用;详见 `docs/plans/phase64/closeout.md` | **Phase 64 完成**:治理边界澄清 — fallback route 选择责任归位 + agent_llm 改走 Provider Router |
| **Truth Plane SQLite 一致性** | INVARIANTS P2 / DATA_MODEL §3 / SELF_EVOLUTION | route metadata / policy 当前以 JSON 文件 + 进程内 dict 存储,违背 P2 "SQLite-primary truth"。`apply_proposal` 4 步序列(`save_route_weights → apply → save_capability_profiles → apply`)缺事务保证,中途失败导致 in-memory 不一致;长期亦阻碍对象存储后端兼容(S3 / MinIO / OSS 没有文件系统原子 rename) | [已消化]:Phase 65 completed(2026-04-30,commit `64cbba7`);route metadata / policy 迁入 SQLite,`apply_proposal` 用 `BEGIN IMMEDIATE` transaction,引入 `route_change_log` / `policy_change_log` 审计表;履行 INVARIANTS P2 在治理状态上的代码层承诺。详见 `docs/plans/phase65/closeout.md` |
| **代码卫生(dead code / 硬编码 / 复用)** | 跨模块 | [已消化] Phase 66 完成:75 个 .py 文件 / 30954 LOC 全 read-only audit;46 finding(2 high / 36 med / 8 low)+ 5 跨块共识主题 + 7 quick-win + 9 design-needed;`docs/concerns_backlog.md` 增量已沉淀 | **Phase 66 完成**(2026-04-30,commit `596b54b`)详见 `docs/plans/phase66/audit_index.md` + `closeout.md` |
| **代码卫生债清理(Phase 66 audit 衍生)** | concerns_backlog | [已消化] Phase 67 完成 L+M+N:7 项 quick-win、JSON/JSONL helper ownership、read-only CLI artifact/report dispatch tightening;Candidate P add-on 同轮完成模块重组 | **Phase 67 完成**:详见 `docs/plans/phase67/closeout.md` |
| **模块组织 / 文件聚类** | 跨模块 | [已消化] Phase 67 Candidate P 将 runtime code 按 audit 5 块迁入 `truth_governance/`、`orchestration/`、`provider_router/`、`knowledge_retrieval/`、`surface_tools/`;root Python surface 收敛为 `__init__.py` + `_io_helpers.py` | **Phase 67 完成**:为 R 阶段 debug 与 Phase 68 raw-material 分层提供清晰目录边界 |
| **知识层 storage-abstracted raw material** | KNOWLEDGE / DATA_MODEL | [已消化] Phase 68 Candidate O 实装 `RawMaterialStore` protocol、URI parser、filesystem backend、content hashing;ingestion source refs 切到 `file://workspace/...` / absolute `file://`,artifact evidence 支持 `artifact://...` 并兼容 legacy refs | **Phase 68 完成**:不引入对象存储后端本身;future MinIO/OSS/S3-compatible backend 仍为后续真实需求驱动 |
| **能力画像自动学习** | PROVIDER_ROUTER / SELF_EVOLUTION | 已被路由消费;自动学习质量与 guard 可观测性仍需提升 | **后续方向** |
| **Runtime v1** | HARNESS | harness bridge 为 v0 约束 | 低优先级 |
| **远期方向** | 多处 | — | 跨设备同步(基于 git / 同步盘)、团队协作扩展(基于 INVARIANTS §7 埋点)、IDE 集成、Remote Worker、Hosted Control Plane、object storage backend(MinIO / OSS / S3-compatible,基于 Phase 68 `RawMaterialStore` 边界扩展) |

---

## 四、推荐 Phase 队列

### 队列总览

| 优先级 | Phase 候选 | 名称 | Primary Track | 状态 |
|--------|-----------|------|---------------|------|
| ~~当前 active~~ | ~~候选 G~~ | ~~治理守卫收口(Governance Closure)~~ | ~~Governance~~ | ~~✅ Phase 63 已完成~~ → 已 merge,详见 `docs/plans/phase63/closeout.md` |
| ~~推荐次序 1~~ | ~~候选 F~~ | ~~`apply_proposal()` 入口函数化(Architectural fix)~~ | ~~Design / Governance~~ | ~~✅ Phase 61 已完成~~ |
| ~~推荐次序 1~~ | ~~候选 E~~ | ~~完整 Multi-Perspective Synthesis~~ | ~~Orchestration~~ | ~~✅ Phase 62 已完成~~ |
| ~~当前 active~~ | ~~候选 G.5 / Phase 64~~ | ~~NO_SKIP 守卫红灯修复~~ | ~~Governance~~ | ~~Direction = 候选 G.5(Phase 64);2 条红灯由 Phase 63 M0 audit 精确定位;fallback_route 边界澄清 + agent_llm 改走 Provider Router~~ → 已 merge(Phase 64,2026-04-29,详见 `docs/plans/phase64/closeout.md`) |
| 推荐次序 2 | 候选 H | Truth Plane SQLite 一致性 | Truth / Storage | ✅ Phase 65 已完成(2026-04-30,commit `64cbba7`;closeout: `docs/plans/phase65/closeout.md`) |
| ~~推荐次序 3~~ | ~~候选 K~~ | ~~代码卫生 audit(dead code / 硬编码 / 复用)~~ | ~~Refactor / Hygiene~~ | ✅ Phase 66 已完成(2026-04-30,commit `596b54b`;46 finding;closeout: `docs/plans/phase66/closeout.md`) |
| ~~推荐次序 4~~ | ~~候选 L~~ | ~~Small hygiene cleanup(audit quick-win 7 项消化)~~ | ~~Refactor / Hygiene~~ | ✅ Phase 67 完成 |
| ~~推荐次序 4~~ | ~~候选 M~~ | ~~IO + artifact ownership design~~ | ~~Design / Refactor~~ | ✅ Phase 67 完成 |
| ~~推荐次序 4~~ | ~~候选 N~~ | ~~CLI dispatch tightening~~ | ~~Refactor / Surface~~ | ✅ Phase 67 完成 |
| ~~推荐次序 5~~ | ~~候选 P~~ | ~~模块重组(5 主目录对齐 audit 块 + KNOWLEDGE 三层)~~ | ~~Refactor / Architecture~~ | ✅ Phase 67 完成 |
| ~~推荐次序 6~~ | ~~候选 O~~ | ~~Storage Backend Independence(`RawMaterialStore` 接口 + filesystem 后端)~~ | ~~Knowledge / Storage~~ | ✅ Phase 68 完成 |
| 推荐次序 1 | 候选 R | 真实使用反馈观察期 | Operations | 治理三段闭合 + 代码债盘点 + 模块重组 + raw-material storage boundary 后,观察 P1 / P2 在生产负载下的有效性 |
| 推荐次序 2 | 候选 D | 编排增强(Planner / DAG / Strategy Router) | Orchestration | 无真实瓶颈推动 |

### 候选 G:治理守卫收口(Governance Closure)— ✅ Phase 63 完成

- **核心价值**:消化 Phase 61 / 62 暴露的宪法-代码漂移 Open,把 §7 集中化函数 + Repository 抽象层 + §9 守卫批量一次性收敛
- **scope(据 M0 audit 缩小)**:M0 audit / M1 §7 集中化 / M2 删除 `_route_knowledge_to_staged` dead code(生产 0 触发) + Repository 抽象层骨架 / M3 §9 守卫 batch(NO_SKIP 6 条启用,2 条暂缓到 G.5)
- **完成产出**:15 active + 2 G.5 skip 占位守卫 / `identity.py` + `workspace.py` 集中化 / Repository 4 类骨架 + 2 条 bypass 守卫;§7 集中化与 Repository 架构已准备好接纳 G.5 与 H
- **已消化的漂移**:(1) §9 守卫 vacuous;(2) Repository 层缺失;(3) orchestrator stagedK 漂移;(4) §7 集中化缺失;剩余 (5a) 事务回滚 与 (5b) NO_SKIP 红灯 拆出 G.5 / H
- **验证**:574 passed / 2 skipped / 8 deselected;`docs/design/` 零 diff

### 候选 G.5:NO_SKIP 守卫红灯修复 — Phase 64 active

- **核心价值**:消化 Phase 63 M0 audit 暴露的 2 条 NO_SKIP 守卫红灯,完成 §9 全 17 条守卫严格执行
- **可能 slice**:S1 `executor.py:510` fallback_route_for 边界澄清(executor 不再独立选 fallback route,改由 orchestrator 决策后传入)/ S2 `agent_llm.py:57` 改走 Provider Router(履行 §4 Path C "Specialist 内部 LLM 调用必须穿透到 Provider Router")
- **风险**:中——两条都触及治理边界,但范围收敛(executor 单点 + agent_llm 单点)
- **优先级理由**:Phase 63 NO_SKIP 守卫只启用 6/8 条留尾巴;G.5 是 G 的自然延续,完成后宪法守卫真正可全启用
- **依赖**:Phase 63(G)完成✅,Repository 抽象层骨架已就位

### 候选 H:Truth Plane SQLite 一致性 — Phase 65 active

- **核心价值**:履行 INVARIANTS P2 "SQLite-primary truth" 在 route metadata / policy 上的代码层承诺;为对象存储后端兼容(S3 / MinIO / OSS)清除技术债;`apply_proposal` 真正可包 transaction
- **可能 slice**:M1 schema 设计(`route_metadata` / `policy` SQLite 表 + index + constraint) / M2 store 函数迁移(4 个 store 写函数从 JSON 改 SQL 写,接受 connection)/ M3 reader 改造(orchestrator / Provider Router / CLI 各处)/ M4 migration 脚本(JSON → SQLite,旧文件保留 backup)+ `apply_proposal` `BEGIN IMMEDIATE` 包装 + `route_change_log` / `policy_change_log` 审计表
- **风险**:高——schema 设计 + reader 改造跨多模块 + migration backwards compat;但**回滚成本中**(每个 milestone 边界清晰,migration 阶段可保留 JSON backup 做双写过渡)
- **优先级理由**:P2 是 INVARIANTS 中明确写出的不变量但代码层未兑现;长期不修复会阻碍对象存储后端、阻碍多 actor 扩展、让事务回滚永远没有正确实装路径
- **依赖**:Phase 63(G)✅ + G.5(Phase 64)完成。G 的 Repository 抽象层骨架是 H 的天然实装载体(Repository 私有方法切换到 SQL 写,governance 层无感)
- Phase 65 已启动 design phase(2026-04-29 Direction Gate);phase artifacts 在 docs/plans/phase65/

### ~~候选 H:Truth Plane SQLite 一致性~~ — Phase 65 已完成

✅ **Phase 65 merge 完成**(2026-04-30,commit `64cbba7`)

- **完成内容**:route metadata / policy 迁入 SQLite(`route_registry` / `policy_records` / `route_change_log` / `policy_change_log` / `schema_version`),`apply_proposal` 用 `BEGIN IMMEDIATE` transaction 包装,引入审计表,legacy JSON 作 bootstrap 源
- **验证**:610 passed / 8 deselected / 10 subtests;append-only 守卫 6 表齐全;DATA_MODEL §3.4/§3.5/§4.2/§8 同步,INVARIANTS.md 零改动
- **治理三段闭合**:Phase 63(G) + Phase 64(G.5) + Phase 65(H)完整实现 = 事务回滚、NO_SKIP 红灯、SQLite 一致性三维度兑现,INVARIANTS P2 代码层履行
- **详见**:`docs/plans/phase65/closeout.md`

### ~~候选 K:代码卫生 audit(dead code / 硬编码 / 复用)~~ — Phase 66 已完成

✅ **Phase 66 merge 完成**(2026-04-30,commit `596b54b`)

- **完成内容**:75 个 .py 文件 / 30954 LOC 全 read-only audit;5 块拆扫 + audit_index 汇总;46 finding(2 high / 36 med / 8 low)→ 4 类(dead code 3 / hardcoded-literal 25 / duplicate-helper 7 / abstraction-opportunity 11);5 跨块共识主题(JSON/JSONL loader / SQLite 事务包络 / executor brand 字面量 / artifact 名 ownership / taxonomy authority);7 quick-win + 9 design-needed;`docs/concerns_backlog.md` 增量已沉淀
- **read-only 边界**:全程 `git diff main -- src/ tests/ docs/design/` = 0
- **后续 phase 推荐**(audit_index §Recommended Next Phase Seeds,authoritative):**3 类独立 phase 不应合并** — 候选 L(small hygiene cleanup)/ 候选 M(IO + artifact ownership design)/ 候选 N(CLI dispatch tightening)
- **详见**:`docs/plans/phase66/audit_index.md` + `closeout.md`

### ~~候选 L:Small Hygiene Cleanup(quick-win 7 项)~~ — Phase 67 已完成

✅ **Phase 67 M1 完成**(2026-04-30,merge `eb2c743`)

- **核心价值**:消化 Phase 66 audit_index 列出的 7 项 quick-win,把"局部、低风险、已有 behavior 测试覆盖"的清理一次做完
- **scope(authoritative,从 audit_index §Quick-Win Candidates 直接搬)**:
  - 删除或显式 wire `run_consensus_review(...)`(Block 2 finding 1,无 src / tests callsite)
  - 删除模块级 `_pricing_for(...)` 或让 `StaticCostEstimator` delegate(Block 3 finding 1)
  - `rank_documents_by_local_embedding(...)` 移到 eval/test support 或接入 production(Block 4 finding 2)
  - 命名 SQLite timeout / busy-timeout 常量(Block 1 finding 2)
  - CLI 消费 `MPS_POLICY_KINDS`(Block 5 finding 12)
  - 命名 retrieval preview / scoring limits(Block 4 finding 6)
  - 文档化或集中化 orchestration timeout / card defaults(Block 2 finding 9)
- **风险**:低——无跨模块影响,均有 behavior 测试覆盖
- **优先级理由**:scope 最清晰、回滚成本最低,适合作为 Phase 66 后第一个清理 phase 起步
- **依赖**:Phase 66 完成✅

### ~~候选 M:IO + Artifact Ownership Design~~ — Phase 67 已完成

✅ **Phase 67 M2 完成**(2026-04-30,merge `eb2c743`)

- **核心价值**:audit_index 5 跨块共识主题的两个 — JSON/JSONL loader ownership(高) + artifact name registry ownership(中)
- **可能 slice**:
  - S1 — 设计 IO helper variants(strict / missing-is-empty / malformed-is-empty)+ 各 callsite 错误策略明确
  - S2 — 设计 task artifact-name registry / owner table;决定哪些 artifact 是稳定 public surface、哪些可 retrieval、哪些 intentionally 私有
- **风险**:中——跨块影响清理 + 触动 public artifact surface;需要 design phase 决定 ownership boundary 后才能动 callsite
- **优先级理由**:Block 4 finding 1(`_load_json_lines` cross-block dup)是 audit 唯一 [high] finding;artifact name ownership 跨 orchestrator / harness / CLI / retrieval 4 处,长期不收口会随每次新报告类型加重
- **依赖**:Phase 66 完成✅;无强阻塞但建议在候选 L 之后(避免 quick-win 与 design 决策混合 review)

### ~~候选 N:CLI Dispatch Tightening~~ — Phase 67 已完成

✅ **Phase 67 M3 完成**(2026-04-30,merge `eb2c743`)

- **核心价值**:audit_block5 finding 3 + audit_index §CLI Dead Subcommand Negative Finding;cli.py 3832 行的 80+ `add_parser` 与 `if args.command` 并行命令树可 table-driven 化
- **可能 slice**:
  - S1 — 起步 read-only artifact / report command(无 governance write 风险)
  - S2 — 评估是否扩展到 governance write commands(`proposal apply` / route policy apply / migrate);**保持 explicit 是合理选项**
- **风险**:中——cli.py 是 public CLI surface,改 dispatch 必须保留 golden-output 行为;但起步 read-only 子集风险可控
- **优先级理由**:Phase 66 audit 确认 cli.py 无 dead subcommand(历史 review 把关质量好);剩下的债务是 dispatch 重复,table-driven 后未来加新 subcommand 成本下降
- **依赖**:Phase 66 完成✅;建议候选 M 后启动(IO/artifact ownership 决议会影响 artifact printer 命令族的 dispatch 表设计)

### ~~候选 P:Module Reorganization(5 主目录对齐 audit 块 + KNOWLEDGE 三层)~~ — Phase 67 已完成

✅ **Phase 67 Candidate P add-on 完成**(2026-04-30,merge `eb2c743`)

- **完成内容**:runtime code 已按 Phase 66 audit 5 块迁入 5 个主目录:
  - `src/swallow/truth_governance/`
  - `src/swallow/orchestration/`
  - `src/swallow/provider_router/`
  - `src/swallow/knowledge_retrieval/`
  - `src/swallow/surface_tools/`
- **保留根层**:`src/swallow/__init__.py` + `src/swallow/_io_helpers.py`。
- **边界保留**:未重写业务逻辑,未重组 `tests/`,未拆 KNOWLEDGE 三层内部子目录。
- **价值**:为真实使用反馈阶段的 debug 与 Phase 68 raw-material boundary 提供清晰代码入口。

### ~~候选 O:Storage Backend Independence(`RawMaterialStore` 接口)~~ — Phase 68 已完成

✅ **Phase 68 完成**(2026-04-30,merge `5cb08af`)

- **完成内容**:`RawMaterialStore` protocol、URI parser、filesystem backend、content hashing。
- **读路径迁移**:ingestion file reads 通过 `FilesystemRawMaterialStore`;workspace 内 refs 使用 `file://workspace/...`,workspace 外 refs 使用 absolute `file://`。
- **artifact evidence**:librarian artifact evidence checks 接受 `artifact://<task_id>/<artifact_path>` 并兼容 legacy `.swl/tasks/...` refs。
- **边界保留**:不引入对象存储后端本身,不修改 Knowledge Truth schema,不修改 retrieval source type semantics。
- **后续条件**:只有出现真实跨设备 / object-storage backend 需求时,再评估 MinIO / OSS / S3-compatible backend。

### 候选 R:真实使用反馈观察期 — 推荐次序 1

- **核心价值**:治理三段(G + G.5 + H)闭合 + 代码债盘点(Phase 66)+ 文档强化(KNOWLEDGE 三层)三个稳定锚点都已就位后,**不再追加 capability-bearing phase**,而是观察一轮真实使用反馈
- **观察维度**:多 agent 协作、复杂任务编排、长期知识沉淀、Wiki / Canonical 检索质量、route 自动学习有效性、INVARIANTS P1 / P2 在生产负载下的稳定性
- **可能产出**:基于真实反馈生成新差距条目,或确认稳定状态进入更后续方向(候选 D / 远期方向)
- **风险**:零(不写代码)
- **优先级理由**:架构债务已基本清空;无紧迫真实需求拉动新 phase;此时观察期价值高于继续推进 capability
- **依赖**:无

### 候选 D:编排增强(Planner / DAG / Strategy Router 显式化)— 推荐次序 2

- **核心价值**:把已部分抽出的 planning 能力继续一等化,形成明确 Planner 接口、DAG dependency orchestration 与 Strategy Router 可观测边界
- **可能 slice**:Planner 接口抽取 / DAG-based subtask 依赖 / Strategy Router 显式化
- **风险**:高——涉及 orchestrator 主链路重构,回滚成本高
- **优先级理由**:架构债务清理,但当前编排能力实际可用,没有真实瓶颈推动
- **依赖**:无强依赖;但 H 的 Repository SQL 化对 D 的 Planner / Strategy Router 一等化有益(state.py / route registry 都是 SQL-backed)

---

## 五、Claude 推荐顺序

**G ✓ → G.5 ✓ → H ✓ → K ✓ → L/M/N/P ✓ → O ✓ → R → D**(2026-04-30,Phase 68 merge 后事实同步)

理由:

1. **候选 G 已完成✅(治理守卫收口,Phase 63)** —— Phase 61 / 62 引入两次"承认现状、登记 Open"模式,已通过 Phase 63 收口让 INVARIANTS 重获威慑力。§7 集中化 + Repository 抽象层骨架 + §9 守卫批量(15 active + 2 G.5 skip)已落地,为后续 G.5 / H / D 准备好前置
2. **候选 G.5 紧随已完成✅(NO_SKIP 红灯修复,Phase 64)** —— Phase 63 完成后 §9 守卫只启用 6/8 条会留治理尾巴;G.5 是 G 的自然延续,2 条红灯已被 M0 audit 精确定位(`executor.py:510` + `agent_llm.py:57`),scope 可控,完成后宪法守卫真正全启用
3. **候选 H 已完成✅(Truth Plane SQLite 一致性,Phase 65)** —— P2 "SQLite-primary truth" 是 INVARIANTS 已写但代码未兑现的不变量。Phase 65 通过迁入 SQLite + `BEGIN IMMEDIATE` transaction + audit log 完整闭合;治理三段(G + G.5 + H)合璧后 INVARIANTS 宪法在治理维度实现完整兑现
4. **候选 K 已完成✅(代码卫生 audit,Phase 66)** —— 75 个 .py 文件 / 30954 LOC 全 read-only audit;46 finding + 5 跨块共识主题 + 7 quick-win + 9 design-needed 已沉淀 backlog,为后续清理 phase 提供精确弹药
5. **候选 L / M / N 已完成✅(Phase 67)** —— Human 接受三合一实现,通过严格 milestone gate 缓解 audit_index 原先的合并风险:quick-win、IO helper ownership、read-only CLI dispatch tightening 分别提交与评审
6. **候选 P 已完成✅(Phase 67 add-on)** —— 5 主目录重组落地,为后续 debug / raw-material 分层提供清晰代码边界
7. **候选 O 已完成✅(Phase 68)** —— `RawMaterialStore` 接口 + filesystem backend + URI refs 落地;对象存储后端本身仍留待真实需求驱动
8. **候选 R 观察期(真实使用反馈)** —— 治理三段 + 代码债盘点 + 模块重组 + raw-material storage boundary 五个稳定锚点完成后,建议观察一轮真实使用反馈,验证 P1 / P2 代码承诺在生产负载下的有效性
9. **候选 D 后置(Planner / DAG / Strategy Router)** —— 编排能力实际可用,无真实瓶颈推动。orchestrator 主链路重构回滚成本高,等到真实需求(MPS 真实使用反馈 / 多 task 复杂依赖场景)出现后再做

---

## 六、战略锚点分析

| 维度 | 蓝图愿景 | 当前现状 | 下一步候选 |
|------|---------|----------|-----------|
| 知识治理 | storage-abstracted, evidence-backed wiki retrieval 三层架构 + neural retrieval | ✅ **Phase 68 完成**:`RawMaterialStore` 实装层抽象已落地;三层架构(Raw Material / Knowledge Truth / Retrieval & Serving)+ Wiki / Canonical 默认主入口 + EvidencePack 定义保持稳定 | **稳定期**;观察真实使用后再评估 object-storage backend |
| 知识捕获 | 低摩擦入口 + 外部讨论回收 + staged review | A-lite 已落地 | 稳定期 |
| CLI 生态 | aider + claude-code + codex 三足鼎立 | 三者均为独立 route | 稳定期 |
| 检索分流 | retrieval policy 感知 execution family + task intent | ✅ 已按 path / executor family / task_family 分流 | **稳定期**;后续可评估 operator-facing override CLI / 更细粒度 task-family 专用化 |
| Agent 体系 | 4 个 Specialist + 2 个 Validator 独立生命周期 | 全部落地 | 稳定期 |
| 写入治理 | INVARIANTS §0.4 canonical / route / policy 唯一入口 + §9 守卫测试 | ✅ **Phase 61+63+64+65 完成**:apply_proposal() 三类主写入收敛;§7 集中化 + Repository 抽象层 + §9 17 条守卫全 active;route metadata 三层外部化(fallback override + registry + policy);事务回滚通过 Phase 65 SQLite `BEGIN IMMEDIATE` transaction 完整实装 | **完整闭合**;观察稳定后进后续编排增强 |
| 治理边界 LLM 路径 | INVARIANTS §0.3 + §4 三条 LLM 路径(A 受控 HTTP / B agent 黑盒 / C Specialist 内部穿透 Provider Router) | ✅ **Phase 64 + 65 完成**:Path B fallback chain plan 前移 Orchestrator(不再违反 control plane 边界),Specialist internal chat-completion 穿透 `router.invoke_completion()`(履行 Path C),§9 17 条守卫全 active | **稳定期**;观察真实使用反馈后推进多 agent 协作扩展 |
| Truth 物理存储 | INVARIANTS P2 SQLite-primary truth + 对象存储后端兼容性 | ✅ **Phase 65 + 68 完成**:task / event / knowledge / evidence / relations / route metadata / policy 全迁 SQLite;raw material 读路径通过 `RawMaterialStore` 边界与 filesystem backend 收口 | **稳定期**;真实 object-storage backend 后置 |
| Raw material storage | filesystem 当前唯一后端,future object storage(MinIO / OSS / S3-compatible)留接口适配 | ✅ **Phase 68 完成**:`file://workspace/...`、absolute `file://`、`artifact://...` refs + filesystem backend 已落地;不引入对象存储后端本身 | **稳定期**;后续仅在真实跨设备 / object-storage 需求出现时扩展 backend |
| 代码卫生 | dead code / 硬编码字面量 / 重复 helper / 抽象机会系统盘点 | ✅ **Phase 66 + 67 完成**:audit 完成后,quick-win / IO helper ownership / read-only CLI dispatch tightening 已消化;剩余 design-needed 项继续留在 concerns_backlog | **稳定期** |
| 代码组织 | 75 文件按 audit 5 块 + KNOWLEDGE 三层对齐到目录结构 | ✅ **Phase 67 Candidate P 完成**:runtime code 已按 5 个语义目录重组,root Python surface 收敛为 `__init__.py` + `_io_helpers.py` | **稳定期**;R 阶段以新目录结构观察真实维护摩擦 |
| 执行编排 | 高并发多路 + DAG | fan-out 已落地 | **候选 D**(后置) |
| 思考-讨论-沉淀(完整) | 受控多视角综合 + multi-route synthesis | MPS 受控多视角综合 + 仲裁已落地(Phase 62) | **稳定期** |
| 自我进化 | Librarian + Meta-Optimizer 提案应用闭环 | 已基本完成 | 远期 |

---

## 七、Tag / Release 决策追踪

| Release | Trigger Phase(s) | 决议 | 决议日期 |
|---------|-----------------|------|---------|
| v1.3.1 | Phase 62 | Phase 62(Multi-Perspective Synthesis)merge 后,单独打 tag 标记检索 / 编排稳定基线 | 2026-04-29 |
| v1.4.0 | Phase 63 + Phase 64 + Phase 65 | ✅ Tag 已发(2026-04-30,annotated tag,points to commit `5ec637f`)。治理三段(G + G.5 + H)完整闭合 — INVARIANTS P2 代码层兑现 | 2026-04-29(决议)/ 2026-04-30(打 tag)|
| 不打 | Phase 66 | Phase 66 是 read-only audit-only phase,不构成 release 节点 | 2026-04-30 |
| v1.5.0 | Phase 67 + Phase 68 | 待 Human 执行 tag。Phase 67 完成 cleanup/module reorganization,Phase 68 实装 `RawMaterialStore` raw-material boundary,构成 storage-abstracted knowledge plane checkpoint | 2026-04-30 |

---

## 八、本文件的职责边界

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
