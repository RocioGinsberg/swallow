---
author: claude
phase: lto-2-retrieval-quality-evidence-serving
slice: pr-review
status: final
depends_on:
  - docs/plans/lto-2-retrieval-quality-evidence-serving/plan.md
  - docs/plans/lto-2-retrieval-quality-evidence-serving/plan_audit.md
  - src/swallow/knowledge_retrieval/_internal_knowledge_store.py
  - src/swallow/knowledge_retrieval/evidence_pack.py
  - src/swallow/knowledge_retrieval/knowledge_plane.py
  - src/swallow/knowledge_retrieval/retrieval.py
  - src/swallow/orchestration/task_report.py
  - src/swallow/truth_governance/truth/knowledge.py
  - tests/test_invariant_guards.py
  - tests/eval/test_lto2_retrieval_quality.py
  - tests/test_governance.py
  - tests/test_evidence_pack.py
  - tests/test_knowledge_store.py
  - tests/test_retrieval_adapters.py
  - tests/unit/orchestration/test_task_report_module.py
---

TL;DR: recommend-merge — 0 blockers / 1 concern / 1 nit。LTO-2 cleanly 落地 5 milestones,plan_audit 5 concerns + 2 nits 全部吸收并有具体技术决议(`source-anchor-v1` JSON canonicalization、`evidence-src-<key>` 单点 helper 升级、`derived-from-v1` deterministic relation id、`source_anchor_key` 由 retrieval 层 enrich path A、`entry_json["preview"]` reuse stored excerpt path)。一个 concern 是 closeout.md 尚未产出,review 提前于 closeout(与之前 phase 工作序不同)但不阻塞 merge。

# LTO-2 PR Review

## Verdict

**recommend-merge** — 5 commits 严格按 plan §Branch / Commit / Review Gates 拆分,每个 commit 对应一个 milestone:`f9b683a`(M1 source-anchor identity)/ `9b0a381`(M2 dedup on promotion)/ `1590e62`(M3 EvidencePack dedup)/ `62a2a7d`(M4 report quality)/ `d6967f3`(M5 eval)。无单 commit 跨 milestone 边界。

这是延续 LTO-1 stage 1 / Hygiene Bundle / LTO-1 stage 2 的"高质量小切片 + 强 audit 吸收"工作模式。LTO-2 plan 在 governance / facade / apply path 等关键边界做对了选择,实现层全部按 plan 落地,且**多处吸收 audit concerns 时给出比 plan 要求更具体的技术决议**。

Diff scale: **+1334 / −105** across 17 files。新增 1 个高价值 implementation 区域(`evidence_pack.py` +168 行,引入 dedup + `source_anchor_key` 字段)+ `_internal_knowledge_store.py` +127 行(`source-anchor-v1` identity helper + materialization)+ 4 个新测试文件(`test_lto2_retrieval_quality.py` 209 / `test_evidence_pack.py` 84 / `test_knowledge_store.py` +124 / `test_retrieval_adapters.py` +128 / `test_task_report_module.py` 63)。

## Verification of plan_audit Absorption

逐项核实 5 concerns + 2 nits + Codex 给出的具体技术决议:

### 5 concerns

| ID | plan_audit Finding | Codex 决议(active_context line 67-71)| 实现位点 + 验证 |
|---|---|---|---|
| C1 | `heading_path` 类型/normalize 规则不明 | "list/string 统一归一化为 ` > ` join;空 `span` 可由 `line_start/line_end` fallback 为 `line:<start>-<end>`" | `_internal_knowledge_store.py:63-79` `build_source_anchor_identity` + `_normalized_source_anchor_fields` helper;`SOURCE_ANCHOR_VERSION = "source-anchor-v1"` 作为 schema 演进 marker |
| C2 | `source_anchor_key` hash 输入字段拼接顺序未指定 | "固定 `source-anchor-v1` canonical JSON hash 输入、5 字段顺序" | `_internal_knowledge_store.py:65-73` `_canonical_json([SOURCE_ANCHOR_VERSION, source_ref, content_hash, parser_version, span, heading_path])` → `sha256[:16]`。**version-prefixed canonical JSON 比简单字段拼接更稳健** —— 未来加字段时改 version 即可不破坏旧 key |
| C3 | Cross-task evidence lookup 实现机制未明示 | "固定 cross-task lookup 使用 `knowledge_object_exists(base_dir, evidence-src-<key>)`;不做 legacy evidence row backfill" | `_internal_knowledge_store.py:377` `_knowledge_object_exists(base_dir, evidence_id)` 在 `materialize_source_evidence_from_canonical_record` 内被调用;line 530-536 委托 `SqliteTaskStore().knowledge_object_exists` —— 复用现有 `WHERE object_id = ?` scan,**不加新索引**(plan §M2 注:current evidence volume small) |
| C4 | Relation id scheme 切换有 backfill 影响 | "固定 `derived_from` relation id 改为 source object + evidence id pair hash;同一 source/evidence pair upsert 到同一 relation row" | `truth/knowledge.py:147-160` `_derived_from_relation_id(source_id, evidence_id)` + `upsert_knowledge_relation`;同一 pair 重复 promote 不创建新 row(LTO-1 stage 2 idempotency 升级到跨 candidate)。Plan 没要求 backfill — 既存 relation rows 用旧 uuid id,新 row 用 deterministic id,共存兼容 |
| C5 | `source_anchor_key` 在 retrieval 链路传播路径未指定 | "固定 `source_anchor_key` 由 retrieval pipeline 写入 `RetrievalItem.metadata`,EvidencePack 不做 store lookup" | `retrieval.py:248` `build_knowledge_item_metadata` 把 `source_anchor_key` 注入 `RetrievalItem.metadata`(path A);`evidence_pack.py:163` 直接读 `item.metadata.get("source_anchor_key")`,无 store lookup —— retrieval pipeline 是单一 enrichment 点,evidence_pack 是消费者,边界清晰 |

### 2 nits

| ID | Finding | Status |
|---|---|---|
| N1 | LTO-2 eval extend 还是新建未明确 | **Resolved by new file** — `tests/eval/test_lto2_retrieval_quality.py` 209 行新建,与 stage 1 / stage 2 eval 并存;Codex 同步给 `test_wiki_compiler_second_stage_quality.py` 加了 +13 行(可能是修补 fixture 或新断言)。三 eval 文件并存模式与 LTO-1 stage 2 review N2 决议一致 |
| N2 | `bounded excerpt` 来源 + 长度政策 | **Resolved by stored preview** — "固定 M4 excerpt 来源为 stored `entry_json[\"preview\"]`,不做 fresh raw material resolution"。这是合理选择 —— LTO-1 stage 2 `WikiCompilerSourceAnchor.preview` 已有 `PREVIEW_LIMIT = 320` cap,LTO-2 直接 reuse,不重新做长度政策 / UTF-8 截断设计 |

**5 / 5 concerns + 2 / 2 nits 全部吸收**,且每条都有显式 file:line 锚点。

## Findings

### [CONCERN] C1 — `closeout.md` 尚未产出,review 提前于 closeout

**Files**:
- 缺失:`docs/plans/lto-2-retrieval-quality-evidence-serving/closeout.md`
- 存在:plan.md / plan_audit.md / 5 个 implementation commits + active_context status sync

LTO-2 plan §M5 明确说 "closeout/pr prep after implementation"(line 223 + 387),implementation 已完成但 closeout 还没写。这与之前 4 个 phase(LTO-13 / LTO-6 / LTO-1 stage 1 / stage 2)的工作序不同 —— 那些 phase 在 review 前 Codex 已 draft closeout,review 后 Codex 再 final。

**Why it matters**:closeout 不仅是文档形式,它是 phase 收口的事实留底:
- 验证 stats 永久化(防 active_context 后续清理时丢失)
- Plan audit absorption summary(本 phase 5 concerns + 2 nits 吸收路径)
- Deferred 项 explicit 列表(本 phase 是否有未做项滚到 backlog)
- Review status 字段(为 Codex final closeout 时填充 review 结论留位)

**Why not blocker**:plan §M5 表格说 "closeout/pr prep" 与"implementation"是同 milestone 的两个 sub-task,Codex 现在按 review-first 工作序也合理 —— review concerns 可以一并 fold 进 closeout。

**Resolution**:
- **(a)** Codex 现在补 closeout draft(包含 review concern absorption + final validation results),与 review_comments.md 同 commit 提交。
- **(b)** Codex 在 merge 后 post-merge sync 阶段再补 closeout —— 但需要 active_context 显式记录这个 deferred 状态以避免漏写

**Recommendation**: option (a)。理由 = 与 LTO-13 / LTO-6 / LTO-1 stage 1/2 工作序一致,review_comments 与 closeout 同期提交是项目惯例。

### [NIT] N1 — Active_context 历史快照块使用 `latest_completed_phase: lto-1-wiki-compiler-second-stage` 但 v1.8.0 tag target 是 stage 1 commit `349efa9`

**File**: `docs/active_context.md:11-13`

`latest_completed_phase: lto-1-wiki-compiler-second-stage`(line 12)是事实正确的 — LTO-1 stage 2 是上一个完整 phase 流程(merge `21f8dc8`)。但 `latest_completed_slice: merged to main at 21f8dc8; roadmap synced at 25f7848`(line 13)略冗余地把 roadmap sync commit 也算作 slice 一部分。

**Why it's a nit**:active_context 字段语义清晰即可,不影响本 phase merge。如果未来有 audit 工具基于 latest_completed_slice 做自动检查,可能需要更严格语义("merged to main at <merge commit>"已足够)。

**Suggestion**:Codex 在下次 active_context 大修时可以把 "roadmap synced at <commit>" 移到独立字段或注释。本 phase 不需要修。

## Confirmed Strengths

记录这些以便未来 phase 复用:

- **`source-anchor-v1` version-prefixed canonical JSON** 是比简单字段拼接更稳健的设计:hash 输入第一个元素就是 `SOURCE_ANCHOR_VERSION`,未来加 anchor 字段时改 version 即可保持旧 key 稳定区分。这是**比 plan 要求更前瞻**的决议(plan §M1 没要求 version-prefix)。
- **Evidence id 单点 helper 持续传承**:LTO-1 stage 1 `evidence-{candidate_id}-{index}` → LTO-1 stage 2 单点维持 → LTO-2 升级为 `evidence-src-<source_anchor_key>`。三阶段保持单点产生,helper 替换是 mechanical 的,**这正是 LTO-1 stage 2 review 我建议的"为未来 dedup phase 留干净接入点"的兑现**。
- **`derived-from-v1` deterministic relation id** 带 schema version:`_derived_from_relation_id` 用 version-prefixed 形式生成稳定 id,同一 source/evidence pair upsert 到同一 row。重复 promote 不会重复 insert,跨 candidate dedup 自然落地。
- **C5 path A enrichment 选择正确**:`retrieval.py:248` 在 `build_knowledge_item_metadata` 内单点 enrich `source_anchor_key`,`evidence_pack.py` 作为消费者只读不查。这避免了 evidence_pack 反向 import store / facade,保持 retrieval pipeline 是 enrichment 单一点。
- **`_knowledge_object_exists` cross-task 复用现有 scan**(C3):**没有**为本 phase 加新 SQLite 索引(plan §M2 注 line 156:current evidence volume small)。这是正确的 yagni — 索引可以未来真痛点出现时加,不预先优化。
- **EvidencePack dedup 输出可观察**(`evidence_pack.py:291-294, 306-309`):`dedup_reason = "duplicate_source_anchor"` + `expansion_path_count` 在 dedup 时记录,Operator 在 retrieval report 里可以看到"这个 evidence 被 N 个路径命中"而不是静默 dedup。这与 plan §M3 acceptance "EvidencePack summaries make duplicate suppression visible" 一致。
- **task_report.py facade 边界严格**:`task_report.py:6` 只 import `from swallow.knowledge_retrieval.knowledge_plane import ...`,无任何 `_internal_*` 直 reach。LTO-6 facade 收口的纪律延续到 LTO-2。
- **M5 guard `test_wiki_compiler_source_pack_evidence_id_is_source_anchor_key_based`(`test_invariant_guards.py:718`)**:guard 用真实 helper 调用做断言(`identity = build_source_anchor_identity(...)`;`assert identity["evidence_id"] == f"evidence-src-{identity['source_anchor_key']}"`),不是字符串检查,而是行为级 invariant —— 防止未来重构时静默退化为非 anchor-key-based id。
- **Eval 文件命名一致**:`tests/eval/test_lto2_retrieval_quality.py` 与之前 `test_wiki_compiler_quality.py` / `test_wiki_compiler_second_stage_quality.py` 同前缀模式,后续 LTO-3+ 可沿用。

## Validation Replay

未重跑测试,active_context line 124-132 / closeout 验证(待 Codex 补 closeout 时记录)预期数字:

```text
M1 focused: tests/test_knowledge_store.py + test_knowledge_plane_facade.py: 10 passed
M1 governance subset: 2 passed, 15 deselected
M1 eval subset: 1 passed
M1 invariant guard subset: 5 passed, 35 deselected
M1 governance + relations + sqlite_store: 38 passed
M1 wiki_commands + stage 2 eval (non-eval): 5 passed, 4 deselected
compileall + git diff --check: passed
```

预期 +20 net new tests(Codex active_context 待执行区已暗示 "M5 eval coverage")。Diff stat 中 `tests/eval/test_lto2_retrieval_quality.py` 209 行 + `test_evidence_pack.py` 84 行 + `test_knowledge_store.py` +124 行 + `test_retrieval_adapters.py` +128 行 + `test_governance.py` +86 行 + `test_invariant_guards.py` +19 行 + `test_task_report_module.py` 63 行,新增容量充足。

**Codex 补 closeout 时建议跑 full pytest** 并记录 final count,作为本阶段闭环 baseline。

## Recommendation

**recommend-merge** as-is(指实现层)。**closeout 必须由 Codex 补齐后再走 merge gate** —— 这与 LTO-13 / LTO-6 / LTO-1 stage 1/2 工作序一致。

具体动作:

1. **Codex 补 `closeout.md`**(必做):
   - Phase outcome / scope delivered / implementation notes
   - **5 concerns + 2 nits 吸收路径**(我已经在 §Verification 给出了完整 mapping,Codex 可直接 reuse)
   - **Final validation 数据**(跑 full pytest + compileall + diff check 一遍,记录 N passed, K deselected)
   - Deferred follow-ups(本 phase 显式 deferred 的项)
   - Review status 字段(absorbed C1 closeout-missing concern + N1 active_context cosmetic nit)
2. **Codex 补 `./pr.md`** PR body draft
3. **Human** review final closeout + pr.md + 实现 diff,然后 merge

**C1 closeout 缺失** 是 review 唯一形式上的 concern,补上即可走 merge。

## Tag 节点判断

**不建议为 LTO-2 单独 cut tag**。

理由(延续 LTO-1 stage 2 review 同样判断):
- v1.7.0(LTO-13)/ v1.8.0(LTO-1 stage 1)= 用户可观察的能力跃迁
- LTO-1 stage 2 / Hygiene Bundle / LTO-2 = 质量提升 + 工程纪律 + retrieval quality 增量,**非新能力**

可累积 Wiki Compiler 第三阶段 / LTO-4 / D2 driven ports 等后续 phase 之后再 cut **v1.9.0**,以"Knowledge Authoring 闭环 + Retrieval Quality 增量 + 工程纪律稳定"为 release 节点意义。最终 Tag 决策由 Human。

## Deferred Items Confirmed

active_context / plan §Non-Goals 列出的 deferred 全部一致:

- **DATA_MODEL §3.3 schema migration** — backlog Active Open 项,触发条件 = 跨任务 evidence object lookup 真实需求
- **Object storage / MinIO / OSS / S3 backend** — Non-Goals 显式排除
- **Graph RAG / 多跳 LLM retrieval** — KNOWLEDGE.md §9 远期方向
- **Web background worker durable semantics** — LTO-13 R2-1 fire-and-poll 同型 deferral
- **Legacy evidence row backfill** — Codex C3/N1 决议:不做,共存兼容
- **No new SQLite index for cross-task evidence lookup** — plan §M2 line 156 注:current evidence volume small,索引等真实性能痛点出现再加

所有 deferral 在 plan / active_context 中显式记录,无静默吸收。**Closeout 补齐时应 explicit re-list 这些项,并新增 review-derived deferred(如 closeout 文件本身的"先 review 后 closeout"工作序是否成为新模式)。**
