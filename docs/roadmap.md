---
author: claude
status: living-document
---

> **Document discipline**
> Owner: Human
> Updater: Codex 主线(长期目标、近期 ticket、优先级、风险批注)+ `roadmap-updater` subagent(phase 完成后的事实状态同步)+ Claude 主线(review / tag 相关轻量风险批注 + Human 明确要求时方向复核)
> Trigger: phase 收口 OR 会话讨论中浮现新方向 OR phase 拆分 OR Human 请求方向建议
> Anti-scope: 不维护已完成 phase 历史(→ git log + closeout);不维护 tag / release docs 状态(→ `docs/concerns_backlog.md`);不存储设计原则(→ `INVARIANTS.md`);不维护 phase 高频状态(→ `docs/active_context.md`)
> 长度上限:250 行;超过说明放进了不该放的东西

# 演进路线图 (Roadmap)

> 本文件维护:**未来可执行方向 + 触发条件 + 优先级理由**。
> 已完成 phase 详情不在此复制 —— 见 `git log` + 对应 `docs/plans/<phase>/closeout.md` 或 `docs/archive_phases/<phase>/closeout.md`。

---

## 当前位置

- **最新 tag**: `v1.9.0` at `d598e58`(Retrieval Quality + Wiki Authoring 二代 + R-entry-driven source scoping)
- **最新 main**: `d598e58`(v1.9.0 release docs;能力基线含 `d4288a1` LTO-2 Retrieval Source Scoping And Truth Reuse Visibility)
- **近期队列**: 空 —— 等 R-entry 真实使用反馈触发下一 phase

自 v1.8.0 以来累积 5 个 phase(LTO-1 stage 2 / LTO-2 retrieval quality / Hygiene Bundle / LTO-4 / LTO-2 source scoping),其中 3 个 operator-visible 增量,2 个工程纪律。详情见 git log 与 closeout。

---

## 一、当前实现基线

| 维度 | 当前状态 |
|------|---------|
| **架构身份** | Hexagonal (Ports & Adapters):driving adapters = `adapters/{cli,http}/`;application = `application/{commands,queries,services,infrastructure}/`;domain / control = `orchestration/` + `knowledge_retrieval/` + `truth_governance/` + `provider_router/`。`surface_tools/` 已删除。D1 / D4(全部 Phase A+B+C)/ D5 已落定;D2 / D3 / D6 deferred。 |
| **知识治理** | Raw Material / Knowledge Truth / Retrieval & Serving 三层成型;Wiki / Canonical 是默认语义入口;`RawMaterialStore` filesystem backend 已落地。 |
| **检索基础设施** | Retrieval U-T-Y 第一阶段(trace / dedicated rerank / source policy / EvidencePack / source pointers / summary boundary);LTO-2 retrieval quality(source-anchor evidence identity + cross-candidate dedup);LTO-2 source scoping(declared-doc priority + truth reuse visibility)均已落地。 |
| **治理边界** | `apply_proposal`、SQLite-primary truth、Path A/B/C、§9 guard suite 稳定。 |
| **Agent 体系** | 4 Specialist + 1 Authoring Specialist(Wiki Compiler stage 1+2)+ 2 Validator;品牌绑定见 `docs/design/EXECUTOR_REGISTRY.md`。 |
| **工程纪律** | 长期编码 / 重构遵循 `docs/engineering/CODE_ORGANIZATION.md` + `GOF_PATTERN_ALIGNMENT.md` + `TEST_ARCHITECTURE.md` + `ARCHITECTURE_DECISIONS.md` + `ADAPTER_DISCIPLINE.md`(LTO-13 audit 教训编纂的 6 条规则 + 16 项 worked examples)。 |

---

## 二、长期优化目标(LTO 表)

按"是否仍有未完成增量"分类,不再均等列举 12 条。

### 仍在推进 / 真实使用反馈驱动

| ID | 长期目标 | 下一类增量 | 触发条件 | 工程锚点 |
|----|---------|-----------|---------|---------|
| **LTO-1** | Knowledge Authoring / Wiki Compiler | (1) Wiki Compiler 第三阶段(视图 3 全图谱 / 多 worker durable runner / 文件上传 source ingestion);(2) cross-task evidence schema migration / standalone `know_evidence` 表(`concerns_backlog.md` Active Open);(3) relation creation site decision matrix(若引入新 relation 类型时复审) | R-entry 真实 operator 反馈中具体痛点 | `KNOWLEDGE.md`, `SELF_EVOLUTION.md`, `ADAPTER_DISCIPLINE.md` |
| **LTO-2** | Retrieval Quality / Evidence Serving | (1) **retrieval policy tuning** —— score magnitude 配置化 / task-knowledge reason-count 语义 partition / canonical reason coverage(`concerns_backlog.md` 中 `LTO-2 Source Scoping review follow-ups`);(2) evidence schema migration(同 LTO-1 项 2);(3) chunk 策略调整(仅在真实使用证实必要时) | R-entry 真实使用复现 declared-doc priority 过强 / report 数字误读 / canonical 静默过滤 | `KNOWLEDGE.md`, `HARNESS.md`, `docs/plans/r-entry-real-usage/findings.md` |
| **LTO-5** | Driven Ports Rollout(N phases,首推 `TaskStorePort`)| `application/ports/` 显式化 + 第一个 port 落定;之后再做 `OrchestratorPort` / `KnowledgePort` / `ProposalPort` / `ProviderRouterPort` / `HttpClientPort` 等 | 测试需要 mock application boundary、引入 second adapter、或注入复杂度上升 —— LTO-4 builders 形态会让边界更清晰 | `CODE_ORGANIZATION.md`, `INVARIANTS.md` |
| **LTO-11** | Planner / DAG / Strategy Router | Planner interface / DAG dependency / Strategy Router observability;LTO-8 `debate_loop_core` 9 callable 注入纪律边缘问题在此一并处理 | 真实编排瓶颈或新 loop control pattern 设计需求 | `ORCHESTRATION.md` |
| **LTO-12** | Long-horizon Runtime / Sync | multi-actor / sync / object storage 扩展 | 真实跨设备 / 团队 / remote worker 需求 | `INVARIANTS.md §7` |

### 已完成,保留长期目标编号(无近期增量计划)

- **LTO-3** Architecture Recomposition Program —— 已归档,执行清单由簇 C subtrack 兑现,**编号不复用**。
- **LTO-4** Test Architecture / TDD Harness —— 已闭合(`ac2d3ff`,压缩流程不 cut tag);后续仅按 touched surface 增量维护。
- **LTO-6** Knowledge Plane Facade Solidification —— 已闭合(`883e2a9`);`knowledge_plane.py` 升级为 functional facade,无后续增量。
- **LTO-7 / 8 / 9 / 10** 簇 C 子系统解耦四金刚 —— 已闭合(v1.6.0 标记 cluster closure at `0e6215a`);后续动作走新 phase / 偏离修复(D1-D6),不接续旧编号。
- **LTO-13** FastAPI Local Web UI Write Surface —— 已闭合(v1.7.0 at `2156d4a`,merge `4ea7a9d`);deferred operator UX 项见下方 §三 Deferred 队列。

详情:`git log` + `docs/archive_phases/<phase>/closeout.md`。

---

## 三、Direction Gate 候选

按真实使用触发条件 / 优先级排序。Human 在每次 phase 完成后从中选下一 phase。

### 候选 A:R-entry 真实使用(非 phase,持续进行)

- **触发条件**:LTO-2 source scoping 刚 merge,operator 还未真实任务验证。
- **期望产出**:retrieval 质量真实反馈;Truth Reuse Visibility 是否解释清楚 canonical 不复用的原因;declared-doc priority 是否过强 / 过弱;R-entry findings 中 R9(host nginx + 第二台 Tailscale 反代 smoke)/ note-only offline semantics / wiki ergonomics 等条目消化进度。
- **性质**:不开 phase,只跑任务 + 更新 `docs/plans/r-entry-real-usage/findings.md`。
- **退出条件**:出现具体反馈触发下方任一候选,或 operator 判定当前能力已稳定。

### 候选 B:LTO-2 retrieval policy tuning

- **触发条件**:R-entry 真实使用复现 source scoping 3 个 review concerns 中任一(`docs/concerns_backlog.md` `LTO-2 Source Scoping review follow-ups`)。
- **Phase 边界(初步)**:`DECLARED_DOCUMENT_PRIORITY_BONUS` / `SOURCE_POLICY_NOISE_PENALTY` 配置化或注释 / `task_knowledge.reason_counts` 改为互斥 partition 或显式标注 signal-not-partition / `canonical_registry.reason_counts` 暴露 `policy_excluded` / `status_not_active` 等。
- **非目标**:不动 schema、不引入新 source type、不做 chunk 大改。
- **性质**:产品质量 / LTO-2 增量。

### 候选 C:Wiki Compiler 第三阶段

- **触发条件**:R-entry 反馈中 cross-task evidence schema migration 需求 / 视图 3 全图谱可视化 / 多 worker durable job runner / 文件上传 source ingestion 任一变成实际痛点。
- **Phase 边界**:依触发的具体方向决定;视图 3 与 Graph RAG 远期方向同步,不在无 Graph RAG 共识时单独推。
- **性质**:产品向 / LTO-1 增量。

### 候选 D:D2 LTO-5 Driven Ports Rollout 第一个 port

- **触发条件**:测试需要 mock application boundary / 引入 second adapter / 注入复杂度上升到要 port 抽象。
- **Phase 边界(初步)**:`application/ports/` 目录显式化 + 第一个 port(候选 `TaskStorePort`)。D6 HTTP client port 必须在 D2 第一个 port 落定后做。
- **性质**:架构重构,大 phase。

### Deferred(已确认不在近期队列,真实需求触发再开)

- **D3 Orchestrator God Object 拆分** —— 等 D2 部分落定后做,巨大 phase。
- **LTO-8 `debate_loop_core` 9 callable 注入** —— 折叠进 LTO-11 处理,见 LTO-11 行。
- **LTO-13 deferred operator UX** —— fire-and-poll background runner / staged-knowledge `--force` Web UX / 文件上传 / route policy admin write controls;每项独立 surface,真实需求触发再开。
- **`know_evidence` schema migration** —— 跨任务 evidence lookup / 全局 evidence id 唯一性需求触发。
- **R-entry observation 边角 concern** —— Phase 45 primary path tie-break / Phase 50 false fail verdict / Phase 58 `generic_chat_json` Open WebUI flat-list auto-detect;真实样本复现再开 bugfix。详见 `concerns_backlog.md`。

---

## 四、Tag 快照

| Tag | Target | 主题 | 时间 |
|-----|--------|------|-----|
| v1.6.0 | `0e6215a` | 簇 C 四金刚 cluster closure | 2026-05-03 |
| v1.7.0 | `2156d4a` | LTO-13 FastAPI Local Web UI 写表面(首次 LLM-外可观察写表面) | 2026-05-04 |
| v1.8.0 | `d6f2442` | LTO-1 Wiki Compiler 第一阶段(首次 LLM-内编译能力) | 2026-05-04 |
| **v1.9.0** | `d598e58` | Retrieval Quality 累积闭环 + R-entry-driven source scoping | 2026-05-04 |

规则:tag 是稳定 checkpoint,不与 phase 一一对应;不补打历史 tag。决策流程见 `AGENTS.md`。

---

## 五、命名与维护规则

- 新 phase 写成"推进哪个 LTO 的哪个增量",例如 `feat/lto-2-retrieval-policy-tuning`;不复用旧编号"未完成"语义。
- LTO-3 已归档,编号不复用。
- 已完成 phase 的细节不复制到本文件;查 `git log` + active / archived `closeout.md`。
- 近期队列默认空,出现明确 Direction Gate 触发条件再加入。
- Phase closeout 时,只更新对应 LTO 的"下一类增量"与触发条件;不复读已完成内容。
- 长度上限 250 行 —— 超过说明本文件又开始变成"phase 历史叙事"。
- `docs/active_context.md` 是当前 phase 高频状态唯一入口;`docs/concerns_backlog.md` 是 review CONCERN 唯一索引;`docs/design/INVARIANTS.md` 是设计原则唯一权威。

---

## 六、本文件的职责边界

`docs/roadmap.md` 是:

- 长期优化目标索引(仍在推进 vs 已闭合)
- Direction Gate 候选与触发条件
- 跨 phase 优先级理由
- Tag 决策快照

不是:

- 当前 phase 状态板(→ `docs/active_context.md`)
- 完整 phase 历史编年(→ `git log` + active / archived `closeout.md`)
- 设计文档(→ `docs/design/`)
- 设计原则副本(→ `docs/design/INVARIANTS.md`)
- closeout 索引(→ active / archived `closeout.md`)
- Tag / Release docs 同步状态(→ `docs/concerns_backlog.md`)
