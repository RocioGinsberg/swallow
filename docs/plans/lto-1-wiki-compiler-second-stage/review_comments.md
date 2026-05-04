---
author: claude
phase: lto-1-wiki-compiler-second-stage
slice: pr-review
status: final
depends_on:
  - docs/plans/lto-1-wiki-compiler-second-stage/plan.md
  - docs/plans/lto-1-wiki-compiler-second-stage/plan_audit.md
  - docs/plans/lto-1-wiki-compiler-second-stage/closeout.md
  - src/swallow/application/commands/knowledge.py
  - src/swallow/application/services/wiki_jobs.py
  - src/swallow/knowledge_retrieval/_internal_knowledge_store.py
  - src/swallow/knowledge_retrieval/_internal_knowledge_relations.py
  - src/swallow/knowledge_retrieval/knowledge_plane.py
  - src/swallow/truth_governance/proposal_registry.py
  - src/swallow/truth_governance/apply_canonical.py
  - src/swallow/truth_governance/truth/knowledge.py
  - src/swallow/truth_governance/store.py
  - src/swallow/adapters/http/api.py
  - src/swallow/adapters/http/schemas.py
  - src/swallow/adapters/http/static/index.html
  - tests/test_invariant_guards.py
  - tests/eval/test_wiki_compiler_second_stage_quality.py
  - tests/integration/http/test_wiki_fire_poll_routes.py
---

TL;DR: recommend-merge — 0 blockers / 1 concern / 1 nit。LTO-1 第二阶段 cleanly 落地 5 milestones,plan_audit 3 blockers + 5 concerns + 2 nits **全部吸收**,且对其中关键风险有"超出 plan 要求的强化"(`derived_from` 加类型守卫 / evidence id 单点 helper / 真正用 FastAPI BackgroundTasks)。一个 concern 是 promote command 在 application 层调用 `apply_proposal` + 创建 relation 的两步式残留,与 LTO-1 第一阶段 review C2 的 application-layer ownership 决定一致但值得固化语义。

# LTO-1 Wiki Compiler 第二阶段 PR Review

## Verdict

**recommend-merge** — 6 commits 严格按 plan §Branch / Commit / Review Gates 拆分:`88450dd`(plan absorption)/ `99833b6`(M1 supersede)/ `b7e1074`(M2 evidence)/ `df2c66c`(M3 fire-and-poll)/ `d578964`(M4 Web UX)/ `42c6b3d`(M5 guards/eval)。无单 commit 跨 milestone 边界。

这是项目自重构以来 plan_audit 唯一一次出现 BLOCKER 级别(3 blockers / 5 concerns / 2 nits),但实现质量却**比无 blocker 的过往 phase 还要高** —— Codex 不仅修复了三个硬伤,还在多处加入了**比 plan 明确要求更强的语义防护**。

Diff scale: **+3480 / −75** across 31 files。新增 4 个高价值实现文件(`wiki_jobs.py` 277 行 / `truth/knowledge.py` +130 行 / `_internal_knowledge_store.py` +187 行 / `static/index.html` +484 行)+ 4 个新测试文件(`test_wiki_fire_poll_routes.py` 193 / `test_wiki_compiler_second_stage_quality.py` 220 / `test_governance.py` 141 / `test_invariant_guards.py` +258)。

## Verification of plan_audit Absorption

逐项核实 `plan_audit.md` 的 3 blockers + 5 concerns + 2 nits:

### 3 BLOCKERS

| ID | Finding | Status | Evidence |
|---|---|---|---|
| B1 | M1 supersede apply 路径不存在 | **Resolved with extension** | `proposal_registry.py:23` `_CanonicalProposal.supersede_target_ids: tuple[str, ...] = ()`;`apply_canonical.py:62-84` 接受并归一化 `supersede_target_ids` 进 proposal 数据结构;`truth/knowledge.py:32-81` `_promote_canonical` 显式接受 `supersede_target_ids` 参数,先 `materialize_source_evidence_from_canonical_record`(line 56)再 `append_canonical_record`(line 76),然后调 `mark_canonical_records_superseded` 处理 target-id 翻转(line 81)。**Apply 路径之外**没有任何代码做 status flip,符合 INVARIANTS §0 第 4 条。 |
| B2 | M2 `know_evidence` 表不存在 / schema 不匹配 | **Resolved by reuse decision** | 按修订后 plan §M2 Schema Reuse Decision,实际复用现有 `knowledge_evidence` task-scoped 表(`task_id, object_id` 复合 PK),不创建独立 `know_evidence` 表,不做 schema migration。`_internal_knowledge_store.py:329-450` `materialize_source_evidence_from_canonical_record` 把 source_pack 写入 task-scoped `knowledge_evidence`,字段 `object_id`、`parser_version`、`content_hash`、`span`、`heading_path`、`preview` 进 `entry_json`。**已在 `concerns_backlog.md` Roadmap-Bound 登记**:DATA_MODEL §3.3 `know_evidence` 设计草案 vs 实际 schema 长期不一致,跨任务 evidence lookup 需求触发时开 schema migration phase。 |
| B3 | `derived_from` 不在 `KNOWLEDGE_RELATION_TYPES`,M2 会运行时炸 | **Resolved with stronger semantics** | `_internal_knowledge_relations.py:14` `derived_from` 加入 enum;**而且**加了类型语义守卫(line 106-114):`derived_from` source 必须是 wiki 对象,target 必须是 evidence 对象,违反 raise `ValueError`。这是**比 plan 要求更强的设计** — 不仅做到 enum 可注册,还在运行时强制 `derived_from` 边的语义合法性,与 LTO-1 第一阶段 plan_audit C4 "双枚举分层" 决议精神一致。 |

### 5 concerns

| ID | Finding | Status | Evidence |
|---|---|---|---|
| C1 | M3 fire-and-poll 存储模型未指定 | **Resolved by task artifact JSON** | `wiki_jobs.py:232` job state 写 `.swl/tasks/<task_id>/artifacts/wiki_jobs/<job_id>.json`,与 Codex 6 个回答 #5 一致。无新 SQLite 表,无新数据库 schema。`_find_wiki_job_path`(line 243)用 `glob` 找 task,生命周期与 task artifact 一致。 |
| C2 | `BackgroundTasks` 是 process-bound,server 重启 job 丢失 | **Resolved by best-effort acknowledgment** | closeout §Implementation Notes 显式声明 "best-effort UI affordance for long-running LLM work. It does not change task state orchestration or introduce durable worker semantics." 这是诚实的 best-effort 语义,符合 Wiki Compiler propose-only 边界 — job 是 task-anchored artifact,server 重启后 Operator 可重新触发,无 stuck running 风险。 |
| C3 | M5 Guard #1 forbidden-import 列表缺 `application.services.wiki_compiler` | **Resolved** | `tests/test_invariant_guards.py:496` `test_wiki_compiler_web_routes_only_call_application_boundary` 显式扫描 `adapters/http/api.py` import,覆盖 `application.services.wiki_compiler`、`provider_router.agent_llm`、`apply_proposal`、`truth_governance.store.append_canonical_record`、knowledge internals,确保 fire-and-poll 不退化为同步阻塞。 |
| C4 | Evidence 写入边界相对 INVARIANTS §0 第 4 条未明示 | **Resolved by apply-path scope** | Evidence write 实际**在 `_promote_canonical` apply path 内**(`truth/knowledge.py:56`),而非 application command 直接调用 — 这把 evidence 写入与 canonical 写入打包在 governed apply path 中,虽然 INVARIANTS §0 第 4 条只说 canonical/route/policy,但 evidence 现在通过 `apply_proposal` 间接进入,反而比预期更严格。 |
| C5 | CLI `--force` vs Web `confirmed_notice_types` 不对称是过渡期还是设计目标 | **Acknowledged as intentional asymmetry** | `application/commands/knowledge.py:204-217` 显式接受 `confirmed_notice_types` + `confirmed_supersede_target_ids` 参数;CLI 仍可用 `force=True`,Web 必须传结构化字段。closeout §Implementation Notes 明示 "CLI may still use `--force` as an existing local confirmation escape hatch. Web uses typed notice confirmations for `supersede` and `conflict`."。这是**有意的不对称**,CLI 是 single-user 终端的 explicit override,Web 是 multi-actor 表面需要 audit。 |

### 2 nits

| ID | Finding | Status |
|---|---|---|
| N1 | CLI 与 Web 长跑路由策略不对称 | **Resolved** — closeout 明示 CLI sync / Web fire-and-poll,与 LTO-13 R2-1 决议传承一致(LTO-13 task-run 路由是 accept-long-request,LTO-1 第二阶段 wiki-draft 路由是 fire-and-poll,因为 wiki LLM 调用预期更长且需要 polling) |
| N2 | Eval 文件 extend vs 新建未明确 | **Resolved by new file** — `tests/eval/test_wiki_compiler_second_stage_quality.py` 220 行新建,与第一阶段 `test_wiki_compiler_quality.py` 并存;两个文件都用 `pytest.mark.eval` deselected;`8 passed` 报 closeout |

**3 blockers + 5 concerns + 2 nits 全部吸收**。无静默回归。

## Findings

### [CONCERN] C1 — `_create_promoted_relation_records` 与 `_promote_canonical` 的 `derived_from` 路径分裂

**Files**:
- `src/swallow/application/commands/knowledge.py:272-293`(LTO-1 第一阶段已存在,处理 `refines`)
- `src/swallow/truth_governance/truth/knowledge.py:140-160`(本 phase 新增,处理 `derived_from`)

LTO-1 第一阶段建立的 application-layer relation creation pattern(`_create_promoted_relation_records` 在 `apply_proposal` 之后调用)只处理 `refines`。本 phase 新增 `derived_from` 关系**不**走这条路径,而是在 `truth/knowledge.py:140-160` 内联到 `_promote_canonical` apply path 里。结果:

```
refines    → application/commands/knowledge.py 创建(apply_proposal 之后)
derived_from → truth_governance/truth/knowledge.py 创建(apply_proposal 之内)
supersedes → 不创建 relation row,只翻 canonical_status(apply path 之内)
```

**Why it matters**:三种 relation 各走各的路径,分别在三个层(application / truth / store)创建。这本身**不是**一个 invariant 违规 —— 每条路径都有合理理由(`refines` 是 application-layer composition;`derived_from` 是 governance side-effect;`supersedes` 不持 relation row)。但:
- 未来加新 relation 类型(`refers_to` / `cites` 等)时,贡献者要在 3 处之间选:不显然是哪一处
- LTO-1 第一阶段 review C2 的"application 层 ownership"原则与本 phase 的"governance 层内联"原则没有显式对照

**Why it's not a blocker**:`derived_from` 放进 governance apply path 是**正确的**(它是 evidence write 的副产品),只是与 `refines` 的 application-layer 创建路径形成不对称。

**Recommendation options** (任一可,不阻塞 merge):

- **(a)** closeout §Implementation Notes 加一段 "Relation creation site decision matrix",说明每种 relation 类型的层归属规则(`refines` 持 application-layer composition / `derived_from` 持 governance side-effect / `supersedes` 翻 status field 不持 row)。这是文档化决议,~10 行。
- **(b)** 后续 phase 重构:把所有 relation 创建统一到 application 层 helper,truth 层只负责 status field。代价较大,留 LTO-1 第三阶段或 D2 driven ports rollout 时机。
- **(c)** Defer 到 concerns_backlog,等下次新 relation 类型加入时再决定。

**Recommendation**: option (a)。理由 = LTO-13 C1 / LTO-6 C1 / LTO-1 第一阶段 C1 都属于 "现在记录决议成本极低,未来贡献者读 review 链路就能复现思考路径" 的相同形态。

### [NIT] N1 — `_create_promoted_relation_records` 仍在 `apply_proposal` 之后调用,违反 LTO-1 第一阶段 plan_audit C2 的 governance-layer 建议?

**File**: `src/swallow/application/commands/knowledge.py:213` `_create_promoted_relation_records(base_dir, updated)` 在 `apply_proposal(...)` 之后调用。

LTO-1 第一阶段 plan_audit C2 当时建议过 "promotion-with-relation-metadata 应在 governance 层处理"。第二阶段实现部分采纳了这个建议(`derived_from` 进 governance / `supersedes` 进 governance 的 status flip),但 `refines` 仍留在 application 层(`_create_promoted_relation_records:272-293`)。

**Why it's a nit not a concern**:
- `apply_proposal` 已成功完成 canonical 写入;之后 application 层创建 `refines` relation 是 best-effort 的 composition,失败不破坏 canonical truth
- 未来如果 `refines` 创建失败,relation 表与 canonical 表脱节,但**这是有意的弱耦合**(canonical 是真值,relation 是邻接索引,可重建)
- 与 LTO-13 R2-6 处理 `TaskAcknowledgeCommandResult` 不对称的取舍同精神 —— "完美一致性 vs 实施成本" 选择实施成本

**Suggestion**:留 deferred 不阻塞;若 C1 option (a) 落地,这个 nit 就被 decision matrix 覆盖。

## Confirmed Strengths

记录这些以便未来 phase 复用:

- **Wiki Compiler propose-only 边界 100% 保留**:5 个新 guard tests 强制(`tests/test_invariant_guards.py:496-705`);Wiki Compiler service 模块零 `apply_proposal` / `append_canonical_record` / 直接 governance writer 引用。
- **`apply_proposal` ownership 实际更严格**:本 phase 让 evidence write **走 governance apply path**(`truth/knowledge.py:56`),虽然 INVARIANTS §0 第 4 条只硬性管 canonical/route/policy,但 evidence 现在间接走 `apply_proposal` 进入,这是**主动加严**而非维持现状。
- **`derived_from` 类型语义守卫强于 plan**:`_internal_knowledge_relations.py:106-114` 不仅检查 enum 注册,还检查 source/target 的对象类型(wiki / evidence),防止 LLM 生成"derived_from(canonical, raw_ref)" 这类错误形态混入持久层。**Plan 没要求,这是 Codex 主动加强**。
- **Evidence id 命名严格单点**:`_internal_knowledge_store.py:416` `evidence-{candidate_id}-{index}` 是唯一生成位点,通过 `materialize_source_evidence_from_canonical_record` facade 暴露,所有调用方走同一 helper。这与我之前讨论中提到的 "future dedup phase 触发时只改 1 处" 一致(我没主动建议 plan 加这点,Codex 自然就实现成单点了 — 好的设计直觉)。
- **Fire-and-poll 真用 FastAPI BackgroundTasks**:`adapters/http/api.py:341, 351` `background_tasks: BackgroundTasks` + `background_tasks.add_task(run_wiki_job, ...)` 是教科书 FastAPI fire-and-poll 模式。**严格遵循 ADAPTER_DISCIPLINE.md §1 Framework-Default Principle** — 没有自写 thread pool / asyncio worker / queue。
- **Structured confirmation 替代 raw force**:`confirmed_notice_types: list[str]` + `confirmed_supersede_target_ids: list[str]` 让 Web operator 必须显式确认 `["supersede", "conflict"]` 中的哪些类型 + 哪些 target id。比 binary `force` 安全且 audit-friendly。CLI 保留 `--force` 作 escape hatch。
- **Job state 持久化是 task-anchored,而非 in-memory only**:`.swl/tasks/<task_id>/artifacts/wiki_jobs/<job_id>.json` 文件;server 重启 background task 丢失但 job record 仍在,Operator 可看到 stuck running 状态并重新触发。这是诚实的 best-effort 语义而非空洞承诺 durable。
- **设计文档与实现的偏离已显式登记**:concerns_backlog 已加 DATA_MODEL §3.3 `know_evidence` schema 不一致 + cross-candidate evidence dedup 两条 deferred,符合"deferred 不丢失"的项目纪律。

## Validation Replay

未重跑测试,closeout 记录:

```text
M5 eval: 8 passed (deselected by default)
M5 invariant guards: 40 passed
Focused phase gates:
  - tests/integration/cli/test_wiki_commands.py + test_knowledge_commands.py: 9 passed
  - tests/integration/http/test_knowledge_browse_routes.py + test_web_write_routes.py + test_web_api.py: 24 passed
  - tests/unit/application/test_knowledge_queries.py + test_staged_knowledge.py + test_knowledge_relations.py: 22 passed
Full pytest: 793 passed, 16 deselected
compileall: passed
git diff --check: passed
```

预期 +20 net new tests(793 - 773 of LTO-1 stage 1)与 diff stat 中 `tests/` 新增量基本一致(`tests/integration/http/test_wiki_fire_poll_routes.py` 193 行 + `tests/eval/test_wiki_compiler_second_stage_quality.py` 220 行 + `tests/test_governance.py` 141 行 + invariant guards / staged_knowledge / knowledge_relations / web_api 等增量)。

## Recommendation

**recommend-merge** as-is。C1 `relation creation site decision matrix` 文档化:

1. **Folded into LTO-1 stage 2 merge** 如果 Codex 想保持单一干净记录 — closeout §Implementation Notes 加 ~10 行决议表
2. **Deferred to a tiny follow-up commit on `main`** — 与 LTO-13 C1 / LTO-6 C1 / LTO-1 stage 1 C1 处理方式一致
3. **Logged 到 concerns_backlog.md** 等下次新 relation 类型加入时一并决议

我的偏好是 (1) — 这是文档变化,与 closeout 同 commit 最干净。

## Deferred Items Confirmed

closeout 列出的 deferred 全部一致:

- **跨 candidate evidence dedup**(本 phase 已在 concerns_backlog 登记)— 等真实 Operator 使用反馈或 LTO-2 retrieval quality 触发
- **DATA_MODEL §3.3 vs 实际 `knowledge_evidence` schema mismatch**(本 phase 已在 concerns_backlog 登记)— 等跨任务 evidence lookup 需求触发独立 schema migration phase
- **Retrieval quality / ranking** — LTO-2 增量,不在 LTO-1 范围
- **Graph visualization** — Wiki Compiler 视图 3 仍 deferred(`KNOWLEDGE.md §9` Graph RAG 远期方向)
- **Durable worker semantics for fire-and-poll** — `BackgroundTasks` 是 best-effort,真实多 worker / 重启自动恢复需求触发再做
- **`refines` 持 application-layer / `derived_from` 持 governance / `supersedes` 翻 status** 三路径不对称 — C1 决议覆盖

所有 deferral 都在 closeout / plan / concerns_backlog 中显式记录,无静默吸收。

## Tag 节点判断

**不建议为 LTO-1 第二阶段单独 cut tag**。

理由:
- v1.7.0(LTO-13)= "首次 LLM-外可观察写表面" — 用户可观察的能力跃迁
- v1.8.0(LTO-1 第一阶段)= "首次 LLM-内编译能力" — 用户可观察的能力跃迁
- LTO-1 第二阶段 = 第一阶段能力的 Web 化 + governed supersede + evidence objectization — **质量提升 + 可观察面拓宽**,不是新能力

可累积更多产品向 phase(Wiki Compiler 第三阶段 / LTO-2 retrieval quality 增量 / Wiki Compiler real workflow 形成的反馈)后再 cut v1.9.0,把"知识 authoring 闭环成熟"作为节点意义,比"第二阶段独立 tag" 更有 release 语义。

最终 Tag 决策由 Human 决定。
