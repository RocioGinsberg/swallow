---
author: codex
phase: lto-1-wiki-compiler-second-stage
slice: phase-plan
status: review
depends_on:
  - docs/active_context.md
  - docs/roadmap.md
  - docs/design/INVARIANTS.md
  - docs/design/DATA_MODEL.md
  - docs/design/EXECUTOR_REGISTRY.md
  - docs/design/SELF_EVOLUTION.md
  - docs/design/KNOWLEDGE.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/TEST_ARCHITECTURE.md
  - docs/engineering/ADAPTER_DISCIPLINE.md
  - docs/plans/lto-1-wiki-compiler-first-stage/plan.md
  - docs/plans/lto-1-wiki-compiler-first-stage/closeout.md
  - docs/plans/lto-1-wiki-compiler-first-stage/review_comments.md
---

TL;DR:
Wiki Compiler 第二阶段把第一阶段 CLI-only 起草能力接入 Web operator workflow,并补齐 supersede apply、derived_from evidence object 化和 conflict/supersede review UX。
本 phase 仍保持 Wiki Compiler propose-only:LLM 起草只写 staged/task artifacts;canonical mutation 只经 Operator-confirmed staged promote + `apply_proposal`。
实现分 M1-M5:governed supersede、source/evidence derivation、fire-and-poll Web authoring、review UX、guards/eval/closeout。

# LTO-1 Wiki Compiler 第二阶段 Plan

## Plan Gate Status

- 当前状态:`review`;`plan_audit.md` 初版 verdict = `has-blockers`,3 blockers / 5 concerns / 2 nits。本 revision 已吸收全部 blocker/concern/nit 为显式设计决策,重新提交 Human Plan Gate。
- 当前分支:`feat/lto-1-wiki-compiler-second-stage`。
- 推荐实现分支:`feat/lto-1-wiki-compiler-second-stage`。
- 实现开始条件:
  - 本 plan 经 review/audit 后无 unresolved blocker。
  - Human Plan Gate 通过。
  - Human 从 `main` 切到推荐 feature branch。
  - `docs/active_context.md` 的 `active_branch` 与实际分支一致。
- `context_brief.md`:本 phase 尚未产出。当前 factual context 来自 `docs/roadmap.md` Direction Gate 选择、第一阶段 plan/closeout/review、设计锚点和当前代码表面。若 Human 需要 Claude context-analyst 补 `context_brief.md`,应在 plan audit 前补齐;否则本 plan 以这些文件为事实输入。

## Plan Audit Absorption

`docs/plans/lto-1-wiki-compiler-second-stage/plan_audit.md` raised 3 blockers,5 concerns,and 2 nits. This revision resolves them as follows:

| Audit item | Resolution in this plan |
|---|---|
| B1: target-id supersede path unspecified | M1 now chooses `_CanonicalProposal.supersede_target_ids` as apply-time payload and a `KnowledgeRepo._promote_canonical(...)` store helper after new-record append, before derived refresh. |
| B2: evidence physical store mismatch | M2 now explicitly reuses the existing task-scoped `knowledge_evidence` implementation store and does not create `know_evidence` or a schema migration in this phase. |
| B3: evidence write boundary unspecified | Promotion-derived evidence objectization now runs inside the canonical `apply_proposal` path; `refresh-evidence` remains the separate no-LLM application command. |
| M1 preflight / CLI force concerns | M1 now requires relation-metadata supersede notices and states that CLI `--force` is the existing local Operator confirmation while Web uses structured confirmations. |
| M2 idempotency and relation type concerns | M2 now scopes idempotency to per-candidate/per-source-pack entry, extends persisted `KNOWLEDGE_RELATION_TYPES` with `derived_from`, and keeps `supersedes` out of persisted relation rows. |
| M3 job storage and background nit | M3 now chooses task artifact job records at `wiki_jobs/<job_id>.json` and defines best-effort in-process execution, not durable workers. |
| M5 guard/eval nits | M5 now forbids HTTP adapter imports of `application.services.wiki_compiler` and requires a second eval file for second-stage structural checks. |

## Goal

本 phase 交付 Wiki Compiler 第二阶段的 operator 可用闭环:

1. **Operator-confirmed supersede apply**:当 staged candidate 明确携带 `supersedes(<target_id>)` 且 Operator 确认 promote 后,在 `apply_proposal` canonical 写路径内把旧 wiki/canonical 标为 `superseded`。
2. **`derived_from` evidence object 化**:promotion 时把 resolved `source_pack` anchors 物化为 evidence support objects,让 `derived_from` 从 raw source ref metadata 进化为可查询、可审的 evidence object edge。
3. **Web 侧 Wiki Compiler trigger**:Control Center 能触发 `draft` / `refine` / `refresh-evidence`,但长跑 LLM action 采用 fire-and-poll job contract,不阻塞 HTTP request。
4. **Conflict / supersede review UX**:Web review 必须把 `conflict_flag`、`supersedes`、source anchors 和 preflight notices 展示给 Operator,并只在显式确认后 promote。
5. **Guard / eval**:新增守卫证明 Web adapter 不直接调用 LLM/governance internals,Wiki Compiler 仍 propose-only,`supersedes` canonical status flip 只发生在 `apply_proposal` 路径内,source/evidence anchors 不发生 unversioned rebuild。

本 phase 不是 LTO-2 retrieval quality 增量;它只为后续 retrieval quality 提供更完整的 wiki/evidence/relation truth。

## Non-Goals

- 不自动 promote、自动 supersede、自动解决 conflict。系统只呈现信号;Operator 做最终选择。
- 不把 Wiki Compiler 合并进 Librarian。Wiki Compiler 仍是起草侧,Librarian 仍是守门侧。
- 不做 LTO-2 bounded excerpt、rerank、retrieval eval hardening 或 report UX polish。
- 不做项目级全图谱可视化。
- 不引入新前端包、build step、SPA framework 或 asset pipeline。
- 不做 D2 / LTO-5 driven ports rollout;若测试需要 seam,优先在 application command/service boundary mock。
- 不新增 auth/multi-user、remote worker、cloud truth mirror、Planner/DAG。
- 不改变 `apply_proposal` 的 public signature,除非 plan audit 判定 M1 必须通过 governed proposal payload extension 表达 supersede target。若需要改 public signature,必须修订 plan 并重新 gate。
- 不把 raw material physical path 写入 Knowledge Truth。Truth-facing relation/evidence 只持有 source ref、content hash、parser version、span、heading path 和 object id。

## Design / Engineering Anchors

- `docs/design/INVARIANTS.md §0/§4/§5`:Control 只在 Orchestrator / Operator;Path C specialist internal LLM calls 必须穿透 Provider Router;canonical / route / policy mutation 只能由 `apply_proposal`。
- `docs/design/DATA_MODEL.md §3.3`:Knowledge Truth 已有 evidence/wiki/canonical supersede 字段与 source pointer 语义;本 phase 不新增 SQLite schema 字段,只补实现层行为。
- `docs/design/EXECUTOR_REGISTRY.md §1.2 Wiki Compiler`:五元组仍是 `(specialist / propose_only / {task_artifacts, event_log, staged_knowledge} / specialist_internal / hybrid)`;4 mode 和 Conflict 段是本 phase 的权威语义。
- `docs/design/SELF_EVOLUTION.md §4.2`:起草侧 / 守门侧 / 共同收口三段必须保留;`supersede` 和 `contradicts` 都是 Operator 决策点。
- `docs/design/KNOWLEDGE.md §2.2/§2.3/§A`:Evidence 是 source-anchored support;relation metadata 包含 `supersedes` / `refines` / `derived_from`;禁止 Unversioned Evidence Rebuild。
- `docs/engineering/ADAPTER_DISCIPLINE.md`:HTTP adapter 必须用 Pydantic request/response models、`Depends`、central exception handlers、framework background primitive;adapter 不写 state machine、不直接 import knowledge/provider/governance internals。
- `docs/engineering/CODE_ORGANIZATION.md`:driving adapters 只调用 `application/commands` / `application/queries` / application services;domain/persistence/internal modules 不进入 adapter。
- `docs/engineering/TEST_ARCHITECTURE.md`:HTTP integration tests 放 `tests/integration/http/`;CLI tests 放 `tests/integration/cli/`;boundary guard 放 `tests/test_invariant_guards.py`;质量梯度放 `tests/eval/` 且默认 deselected。

## Current Code Baseline

- Wiki Compiler implementation lives at `src/swallow/application/services/wiki_compiler.py`;CLI commands call `src/swallow/application/commands/wiki.py`;executor registry already registers `WikiCompilerAgent`.
- `draft` / `refine` currently require `--task-id`, write prompt/result artifacts, call `provider_router.agent_llm.call_agent_llm`, and submit staged candidates with `source_pack`, `rationale`, `relation_metadata`, `conflict_flag`.
- `refresh-evidence` is no-LLM and updates task knowledge evidence anchors through `load_task_knowledge_view` / `persist_task_knowledge_view`.
- `promote_stage_candidate_command` registers a canonical proposal and calls `apply_proposal`; it currently persists only `refines` relation rows after apply. `supersedes(<target_id>)` remains metadata/preflight signal.
- `append_canonical_record` already supersedes records that share the same `canonical_key`; it does not yet apply target-id `supersedes` metadata.
- Web Knowledge panel is read-only for Wiki Compiler authoring. HTTP routes expose browse/detail/relations and staged promote/reject, but no Web Wiki Compiler trigger and no `force`/confirmation UX.
- HTTP adapter already follows LTO-13 discipline: `api.py`, `schemas.py`, `dependencies.py`, `exceptions.py`, `static/index.html`.

## Implementation Decisions

1. **Second stage scope = Web authoring + governed relationship application**. Retrieval quality remains a separate LTO-2 phase.
2. **Fire-and-poll is mandatory for Web LLM actions**. `draft` and `refine` must return quickly with a `job_id`; the browser polls job status. Synchronous long request is not allowed for new Web Wiki Compiler LLM routes.
3. **Use framework defaults**. For FastAPI, use Pydantic request/response models, `Depends`, centralized exception handlers, and FastAPI background task or an equivalent framework primitive. Background execution is best-effort in-process execution for this local single-process server,not a durable worker. Any custom helper needs an inline reason.
4. **Job state belongs below application boundary,not JS**. Web JS may render `queued/running/completed/failed`, but job creation/execution/status serialization lives in application service code. JS must not infer task/knowledge domain state transitions.
5. **Job persistence is task-anchored artifact persistence**. Job records are stored under `.swl/tasks/<task_id>/artifacts/wiki_jobs/<job_id>.json` via existing artifact-writing helpers. This phase does not add a SQLite job table. In-memory-only job state is not acceptable as the sole status source.
6. **Supersede target-id apply happens inside canonical apply path**. Marking an old canonical/wiki object `superseded` is a canonical/wiki truth mutation. M1 extends `_CanonicalProposal` with `supersede_target_ids`;`KnowledgeRepo._promote_canonical(...)` calls a store helper after appending the new record and before `refresh_derived`. CLI/HTTP adapters and application post-apply helpers must not directly flip canonical status.
7. **Application command owns confirmation semantics**. CLI may keep `--force`; Web must use structured confirmation fields such as `confirmed_notice_types=["supersede","conflict"]`. Adapter must not expose a naked `force: true` switch.
8. **Evidence object IDs are deterministic per candidate/source-pack entry**. A resolved source pack entry promoted by Operator produces or reuses `evidence-<candidate_id>-<index>` or an equivalent deterministic id scoped to the staged candidate. This phase does not deduplicate evidence across multiple candidates with the same source_ref/content_hash.
9. **`derived_from` relation rows require evidence object targets**. Raw `target_ref` remains metadata. M2 extends persisted `KNOWLEDGE_RELATION_TYPES` with `derived_from`;a persisted `derived_from` row is allowed only when the target is an evidence object id created/resolved from a source anchor. `supersedes` remains status/metadata,not a persisted relation row.
10. **Conflict remains a review signal**. `conflict_flag = contradicts(<wiki_id>)` blocks promote until Operator confirms. Confirmation does not mean the system chooses supersede; it only allows the chosen Operator action.
11. **No new public design docs by default**. This phase can implement existing DATA_MODEL / KNOWLEDGE / SELF_EVOLUTION semantics without modifying design docs. If implementation discovers schema or invariant gaps, stop and revise plan before code.

## Milestones

| Milestone | Scope | Files / Areas | Acceptance | Validation | Risk | Commit Gate |
|---|---|---|---|---|---|---|
| **M1 - Governed supersede apply** | Promote of a staged `supersedes(<target_id>)` candidate marks target canonical/wiki superseded only inside `apply_proposal` canonical path; structured confirmation replaces Web `force`; result reports superseded records | `application/commands/knowledge.py`;`truth_governance/{proposal_registry.py,apply_canonical.py,truth/knowledge.py,store.py}` as needed;`knowledge_plane.py`;CLI/HTTP schemas | `supersedes` target-id works after Operator confirmation; no target flip before `apply_proposal`; old object is append-only superseded,not deleted; same-key supersede compatibility still passes | CLI promote tests; unit tests for apply path; invariant guard for supersede mutation ownership; existing canonical registry tests | High:canonical truth write boundary | Single milestone commit |
| **M2 - Derived-from evidence objectization** | Operator promotion turns resolved source_pack anchors into evidence support objects; promoted wiki/canonical references source_evidence_ids; persisted `derived_from` relation rows only target evidence object ids | `application/commands/knowledge.py`;`application/queries/knowledge.py`;`knowledge_retrieval/knowledge_plane.py`;knowledge store helpers/tests | Source anchors become stable evidence objects with parser_version/content_hash/span/heading_path; `derived_from` raw refs remain metadata-only; detail/relations show evidence edges | knowledge store/facade tests; HTTP detail/relations tests; eval structural checks | High:truth/reference semantics | Single milestone commit or paired with M1 only if diff stays small |
| **M3 - Web Wiki Compiler fire-and-poll API** | Add POST routes for `draft` / `refine`; add job create/status/result routes; add sync or job-backed `refresh-evidence` route; all use Pydantic envelopes and application service boundary | `adapters/http/{api.py,schemas.py,dependencies.py,exceptions.py}`;`application/services/wiki_jobs.py` or equivalent;`application/commands/wiki.py`;tests | `POST /api/wiki/draft` and `/refine` return accepted job id quickly; `GET /api/wiki/jobs/{job_id}` reports queued/running/completed/failed; completed job links candidate/artifacts; adapter never imports provider router or wiki compiler internals directly | HTTP integration tests with mocked command/service; schema response_model tests; no live LLM | High:background execution + adapter boundary | Single milestone commit |
| **M4 - Web authoring and review UX** | Add Control Center forms/actions for draft/refine/refresh-evidence, job polling tray, source anchor display, conflict/supersede confirmation before promote | `adapters/http/static/index.html`;HTTP schemas/routes from M3;knowledge query payloads if needed | Operator can trigger draft/refine from Web, watch job status, inspect candidate source_pack/conflict/relation metadata, and confirm/reject staged candidate without hidden force | `tests/test_web_api.py`;HTTP smoke; optional manual `swl serve` smoke; no frontend dependency | Medium-high:UI scope creep | Single milestone commit |
| **M5 - Guards, eval, closeout prep** | Lock propose-only, Web adapter boundary, supersede apply ownership, derived_from evidence target rule, evidence version anchors; add deterministic eval signal; prepare closeout/pr | `tests/test_invariant_guards.py`;`tests/eval/`;`docs/plans/.../closeout.md`;`./pr.md` | Guard suite fails for direct adapter LLM/governance reach, direct supersede mutation outside apply path, unversioned evidence rebuild, raw-ref persisted derived_from relation | invariant guards; focused CLI/HTTP/application tests; eval; compileall; full pytest; diff check | Medium:guard breadth | Final validation gate |

## M1 Contract: Supersede Apply

### Operator confirmation

CLI and Web may present confirmation differently, but application semantics must converge:

- `promote_stage_candidate_command(..., force=True)` remains the CLI escape hatch for existing workflows.
- Web should call a structured route such as `POST /api/knowledge/staged/{candidate_id}/promote` with `confirmed_notice_types`, not `force`.
- Application code must compute preflight notices, compare them to confirmation, and reject missing confirmation with a typed `StagePromotePreflightError`.
- `build_stage_promote_preflight_notices(...)` must scan both same-key canonical collisions and staged `relation_metadata` entries with `relation_type == "supersedes"` / `target_object_id`.
- CLI `--force` is treated as explicit local Operator confirmation for all preflight notices,including target-id supersede and conflict. Web must not expose this raw bypass;it supplies structured confirmations instead.

Required notices:

- `supersede`: candidate will mark a target old object superseded.
- `conflict`: candidate has `conflict_flag` or `contradicts` metadata.

### Truth mutation boundary

Target-id supersede requires these properties:

- The staged candidate carries `relation_metadata = [{"relation_type":"supersedes","target_object_id":"..."}]`.
- Application command passes target ids into `register_canonical_proposal(..., supersede_target_ids=[...])`;the canonical record may still persist `relation_metadata` for audit/display,but the apply-time ownership signal is the proposal dataclass field.
- Only `apply_proposal(target=canonical_knowledge)` may apply the old-object status flip.
- `KnowledgeRepo._promote_canonical(...)` appends the new canonical record,then calls a store helper to update target old records before any `refresh_derived` rebuild.
- Store/write code updates old record fields: `canonical_status/state = "superseded"`, `superseded_by = <new_id>`, `superseded_at = <promoted_at>`.
- No code path may delete the old object.

`apply_proposal(proposal_id, operator_token, target)` public signature remains unchanged. `_CanonicalProposal` gets the new `supersede_target_ids` field,cleared with the pending proposal after apply like the rest of the in-memory proposal payload.

## M2 Contract: Source Anchors To Evidence

Promotion of Wiki Compiler candidates should make source support inspectable as evidence objects:

1. For each resolved `source_pack` entry, build a normalized evidence payload:
   - stable object id
   - `source_ref`
   - `content_hash`
   - `parser_version`
   - `span` or `heading_path`
   - bounded preview/content
   - source type and display path as metadata
2. Persist evidence through Knowledge Plane/store helper from inside the canonical `apply_proposal` path, not by adapter code and not by application post-apply direct mutation.
3. Add the evidence ids to promoted wiki/canonical `source_evidence_ids`.
4. Persist a `derived_from` relation only from promoted wiki/canonical object id to evidence object id.
5. Keep raw `target_ref` entries in metadata for display, but do not write raw refs into relation rows.

Idempotency requirement:

- Re-running the evidence/relation helper for the same candidate id and source-pack index must not duplicate evidence or relation rows.
- Existing staged candidates without source_pack still promote as before.

### M2 Schema Reuse Decision

This phase reuses the existing task-scoped `knowledge_evidence` implementation store (`knowledge_evidence` SQLite table plus mirrored `.swl/knowledge/evidence/<task_id>/<object_id>.json` entries) as the physical target for evidence support objects. It does **not** create the standalone `know_evidence` table described in `DATA_MODEL.md §3.3`,and therefore does not require a schema migration in this phase.

Mapping for this phase:

- DATA_MODEL `evidence_id` maps to the task-scoped evidence entry `object_id`.
- DATA_MODEL `source_pointer` maps to the entry JSON fields `source_ref`, `content_hash`, `parser_version`, `span`, and `heading_path`.
- `source_evidence_ids` on promoted wiki/canonical records point to these task-scoped evidence object ids.
- `derived_from` persisted relation rows may target only these evidence object ids,not raw `file://` / `artifact://` refs.

Deferred risk: this compatibility reuse keeps LTO-1 Stage 2 small, but it leaves the longer-term `know_evidence` vs `knowledge_evidence` physical schema reconciliation unresolved. Before any phase introduces global evidence ids, object-storage-backed evidence truth,or a schema migration touching evidence tables,that phase must revisit this decision and update DATA_MODEL / migration strategy explicitly.

### M2 Idempotency Scope

This phase guarantees idempotency only per staged candidate and source-pack entry. The deterministic evidence id should be derived from `(candidate_id, source_pack_index)` or an equivalent candidate-scoped key,so rerunning the same helper for the same candidate does not duplicate evidence objects or `derived_from` relation rows.

This phase deliberately does **not** deduplicate evidence across different staged candidates that cite the same `source_ref`, `content_hash`, `parser_version`, and `span`. Cross-candidate source-anchor deduplication is deferred to a future retrieval/evidence quality phase,where source-level identity,global evidence ids,and relation expansion behavior can be designed together.

## M3 HTTP Contract

All success responses use the existing envelope style:

```json
{"ok": true, "data": {...}}
```

Proposed routes:

- `POST /api/wiki/draft`
- `POST /api/wiki/refine`
- `POST /api/wiki/refresh-evidence`
- `GET /api/wiki/jobs/{job_id}`
- `GET /api/wiki/jobs/{job_id}/result`

Request schema sketch:

```json
{
  "task_id": "task_...",
  "topic": "Wiki topic",
  "source_refs": ["file://workspace/docs/note.md"],
  "model": ""
}
```

Refine adds:

```json
{
  "mode": "supersede|refines",
  "target_object_id": "wiki-old"
}
```

Job response sketch:

```json
{
  "ok": true,
  "data": {
    "job": {
      "job_id": "wiki-job-...",
      "task_id": "task_...",
      "action": "draft",
      "status": "queued|running|completed|failed",
      "candidate_id": "",
      "prompt_artifact": "",
      "result_artifact": "",
      "error": "",
      "created_at": "",
      "updated_at": ""
    }
  }
}
```

Constraints:

- `draft` / `refine` routes must not call `WikiCompilerAgent.compile()` inline before returning.
- `draft` / `refine` routes write a queued job record at `wiki_jobs/<job_id>.json` before returning,then background execution updates the same artifact record to `running`, `completed`, or `failed`.
- `refresh-evidence` may be synchronous because it has no LLM call, but it must still return a typed envelope.
- Adapter imports stop at application command/service/query boundary.
- Fire-and-poll is best-effort local background execution. Server restart may leave `queued` / `running` jobs stale;status readers may mark stale jobs failed, but this phase does not implement durable resume or retry.
- Tests should mock application job execution so no live LLM is needed.

## M4 Web UX Contract

Web UI should extend the existing Knowledge surface without becoming a new app architecture:

- Keep the current static HTML/JS model.
- Add an authoring panel with mode selector: `draft`, `refine/supersede`, `refine/refines`, `refresh-evidence`.
- Source refs are explicit text inputs; no file upload in this phase.
- Selected Knowledge detail can prefill `target_object_id` for refine.
- Job tray shows queued/running/completed/failed and links to created staged candidate.
- Candidate detail shows `source_pack`, `derived_from` evidence links, `supersedes/refines`, and `conflict_flag`.
- Promote confirmation is explicit:
  - supersede notice requires confirming old object id.
  - conflict notice requires confirming conflict flag.
- Web still does not expose raw `force`.

No visual graph, no frontend package, no build step.

## M5 Guard / Eval Plan

Add or extend guard coverage for:

1. `test_wiki_compiler_web_routes_only_call_application_boundary`
   - reject direct imports/calls to `provider_router.agent_llm`, `WikiCompilerAgent`, `application.services.wiki_compiler`, `apply_proposal`, `truth_governance.store.append_canonical_record`, knowledge internals from HTTP adapter.
2. `test_wiki_compiler_supersede_status_flip_only_in_apply_proposal_path`
   - reject application/adapter direct writes of `canonical_status = "superseded"` or `superseded_by` outside governance/store apply path.
3. `test_wiki_compiler_derived_from_relation_targets_evidence_only`
   - persisted `derived_from` rows must target evidence object ids; raw `file://` / `artifact://` refs remain metadata.
4. `test_wiki_compiler_web_llm_actions_are_fire_and_poll`
   - new Web draft/refine routes must create jobs and return accepted response; they cannot call compile inline.
5. `test_wiki_compiler_evidence_objectization_preserves_parser_version_anchor`
   - evidence generated from source_pack includes parser_version/content_hash/span or heading_path.

Eval signal:

- Add `tests/eval/test_wiki_compiler_second_stage_quality.py` for deterministic structural checks:
  - source_pack -> evidence object count matches resolved sources.
  - `supersedes` requires target id and does not appear in draft mode.
  - conflict payload remains visible to review response.
  - Web/job payload shape carries source anchors and candidate id without live LLM.

Eval remains deselected by default and does not require API keys.

## Validation Plan

Minimum focused validation after implementation:

```bash
.venv/bin/python -m pytest tests/integration/cli/test_wiki_commands.py tests/integration/cli/test_knowledge_commands.py -q
.venv/bin/python -m pytest tests/integration/http/test_knowledge_browse_routes.py tests/integration/http/test_web_write_routes.py tests/test_web_api.py -q
.venv/bin/python -m pytest tests/unit/application/test_knowledge_queries.py tests/test_staged_knowledge.py tests/test_knowledge_relations.py -q
.venv/bin/python -m pytest tests/test_invariant_guards.py -q
.venv/bin/python -m pytest -m eval tests/eval/test_wiki_compiler_quality.py tests/eval/test_wiki_compiler_second_stage_quality.py -q
.venv/bin/python -m compileall -q src/swallow
git diff --check
```

Full gate before PR/merge:

```bash
.venv/bin/python -m pytest -q
```

Optional manual smoke after M3/M4:

```bash
.venv/bin/swl serve
```

Only run live LLM Web smoke if local Provider Router credentials are intentionally configured; normal tests must use mocks.

## Branch / Commit / Review Gates

- Recommended branch:`feat/lto-1-wiki-compiler-second-stage`.
- Plan/audit docs should be committed separately from implementation.
- M1 and M2 are high-risk truth semantics; each should be its own milestone commit unless implementation proves one is only a tiny helper follow-up to the other.
- M3 and M4 are Web/API surface; keep API/job implementation and static UI either separate or clearly grouped by commit.
- M5 is final guard/eval/closeout prep and should not be mixed into feature commits unless only test edits are needed to validate a small fix.
- Suggested plan commit after audit/Human approval:

```bash
git add docs/plans/lto-1-wiki-compiler-second-stage/plan.md docs/active_context.md
git commit -m "docs(plan): add wiki compiler second stage plan"
```

## Risks And Fallbacks

| Risk | Impact | Mitigation / Fallback |
|---|---|---|
| Supersede target-id mutation violates `apply_proposal` ownership | Architecture blocker | Keep status flip inside KnowledgeRepo/store path reached by `apply_proposal`; add guard before implementation continues |
| Derived evidence objectization turns into schema migration | Phase expands too much | Use existing task-scoped `knowledge_evidence` store and source pointer fields; standalone `know_evidence` is deferred and logged in concerns backlog |
| Per-candidate evidence idempotency creates duplicate evidence across candidates | Retrieval quality debt | Accept per-candidate idempotency for this phase; defer cross-candidate source-anchor/content-hash dedup to LTO-2 evidence quality |
| Fire-and-poll runner becomes generic orchestration platform | Scope creep / Control Plane drift | Keep it as local task-anchored Web action job for Operator-triggered Wiki Compiler only; no scheduler, fan-out, retry policy, or task state advancement |
| Web confirmation UX accidentally exposes raw force | Safety regression | Use structured confirmation fields; schema `extra="forbid"`; guard/static smoke checks route/request strings |
| UI grows into graph/workbench | Scope creep | Keep form + job tray + candidate review; no project graph, no new package |
| Tests need live LLM | Non-deterministic CI | Mock application service/job execution in HTTP tests; eval uses deterministic payloads |

## Completion Criteria

This phase is complete when:

- `supersedes(<target_id>)` staged candidates can be promoted by Operator confirmation and old objects become `superseded` through the canonical apply path.
- Resolved source_pack anchors become evidence support objects on promotion, with parser version/content hash/location anchors preserved.
- Web Control Center can trigger Wiki Compiler draft/refine through fire-and-poll jobs and can refresh evidence without an LLM call.
- Web review displays conflict/supersede/source evidence signals and requires explicit confirmation before promote.
- Guards prove propose-only, adapter boundary, apply ownership, derived_from target discipline, and evidence anchor versioning.
- Focused tests, eval signal, compileall, `git diff --check`, and full pytest pass.
- `docs/plans/lto-1-wiki-compiler-second-stage/closeout.md`, `docs/active_context.md`, and `./pr.md` are prepared at closeout.
