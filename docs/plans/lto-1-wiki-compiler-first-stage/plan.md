---
author: codex
phase: lto-1-wiki-compiler-first-stage
slice: phase-plan
status: review
depends_on:
  - docs/active_context.md
  - docs/roadmap.md
  - docs/design/INVARIANTS.md
  - docs/design/EXECUTOR_REGISTRY.md
  - docs/design/SELF_EVOLUTION.md
  - docs/design/KNOWLEDGE.md
  - docs/engineering/CODE_ORGANIZATION.md
  - docs/engineering/TEST_ARCHITECTURE.md
  - docs/engineering/ADAPTER_DISCIPLINE.md
  - docs/engineering/ARCHITECTURE_DECISIONS.md
  - docs/plans/lto-1-wiki-compiler-first-stage/plan_audit.md
---

TL;DR:
LTO-1 第一阶段落地 Wiki Compiler authoring specialist:从 raw material / artifacts / existing knowledge 起草 staged wiki/canonical 草稿,并补齐 Web Knowledge Browse 视图 1/2。
本 phase 不自动 promotion、不自动 supersede、不做项目级全图谱;canonical 写入仍只走 staged review + `apply_proposal`。
实现切成 M1-M5:起草核心、browse routes、detail+relations、Web panel、guards+closeout。

# LTO-1 Wiki Compiler 第一阶段 Plan

## Plan Gate Status

- 当前状态:`review`;`plan_audit.md` verdict = `has-concerns`,0 blockers / 5 concerns / 2 nits。本 revision 已吸收全部 concerns/nits 为 M1 约束或显式 deferred 决策。
- 当前分支:`main`。
- 推荐实现分支:`feat/lto-1-wiki-compiler-first-stage`。
- 实现开始条件:本 plan 经 `design-auditor` 产出 `plan_audit.md`,Human Plan Gate 通过,且 Human 从 `main` 切到推荐 feature branch。
- `context_brief.md`:本 phase 尚未产出。当前 factual context 来自 `docs/active_context.md`、`docs/roadmap.md`、Human 指定锚点和已 merge 的设计文档。若 Human 需要 Claude context-analyst 补 `context_brief.md`,应在 plan audit 前补齐;否则本 plan 以这些已读文件作为事实输入。

## Plan Audit Absorption

`docs/plans/lto-1-wiki-compiler-first-stage/plan_audit.md` raised 5 concerns and 2 nits. This revision resolves them as follows:

| Audit item | Resolution in this plan |
|---|---|
| `StagedCandidate` slotted dataclass metadata loss | M1 explicitly requires updating `from_dict`, `to_dict`, and `update_staged_candidate` passthrough tests so compiler metadata survives promote/reject. |
| Promotion relation owner unclear | Post-promotion relation side effects belong in `promote_stage_candidate_command` or helper below application command. CLI/HTTP handlers must not create relations. |
| `derived_from` source-ref target cannot pass `create_knowledge_relation` | `derived_from` is metadata-only in M1 unless the target is an existing knowledge/evidence object id. Raw `source_ref` values stay in `source_pack`, not `knowledge_relations`. |
| relation enum cross-milestone ambiguity | Staged `relation_metadata` is stored as raw metadata and validated by compiler-mode rules, not by `create_knowledge_relation`. Persistence enum validation only applies when application creates a relation row. |
| `source_pack` schema not pinned | This plan defines `WikiCompilerSourceAnchor`: `SourcePointer.to_dict()` compatible fields plus `content_hash`, `parser_version`, `span`, and `preview`. |
| specialist / executor test location | M1 tests extend existing root-level `tests/test_specialist_agents.py` and `tests/test_executor_protocol.py` unless implementation size justifies a new focused file. |
| event-kind ambiguity | Wiki Compiler does not call `append_event` directly in this phase. It records compiler artifacts and staged candidates via existing application/facade paths; any future direct event kind requires a guard-aware plan revision. |

## Goal

本 phase 交付 LTO-1 Wiki Compiler 第一阶段的最小可审闭环:

1. 增加独立 Wiki Compiler authoring specialist,使 Operator 可通过 CLI 从 raw material / artifacts / existing knowledge 起草 staged wiki/canonical 草稿。
2. 落实 4 种模式:`draft`、`refine --mode supersede`、`refine --mode refines`、`refresh-evidence`。
3. 让草稿携带可审元数据:`source_pack`、`rationale`、`relation_metadata`、`conflict_flag`。
4. 增加 Web Control Center 的 Knowledge Browse 读表面:wiki / canonical / staged 列表、knowledge detail、adjacent relations。
5. 增加 guard,证明 Wiki Compiler 不写 canonical,`refresh-evidence` 不绕过 parser/version/content/span 锚点,Web adapter 不承载业务 state machine。

本 phase 是 `v1.8.0` 的候选能力节点:首次 LLM-内知识编译能力(raw material -> staged wiki/canonical 草稿)进入本地 operator workflow。

## Non-Goals

- 不自动 promote canonical,不自动 apply proposal,不自动 supersede 旧 wiki。Operator review 是强制边界。
- 不把 Wiki Compiler 合并进 Librarian。Wiki Compiler 负责起草,Librarian 负责守门,两者保持上下游独立 verdict。
- 不把 Ingestion 扩成多源综合。Ingestion 仍是单源结构化;Wiki Compiler 才做多源 synthesis。
- 不做 Web 侧 LLM 触发按钮。本期 Web 只读 Knowledge Browse 视图 1/2,避免把长跑 LLM action 放进 HTTP/JS surface。CLI 是本期 Wiki Compiler 唯一触发入口。
- 不做项目级全图谱可视化(roadmap 视图 3 deferred)。
- 不引入新前端包、build step、asset pipeline 或后台 job runner。
- 不做 auth/multi-user、remote worker、cloud truth mirror、Planner/DAG。
- 不做 design-level `know_*` schema 大迁移。实现继续使用当前 SQLite/file compatibility stores,仅在 touched surface 内补足字段、relations、guards。
- 不强行处理 LTO-6 review C1 alias cleanup。若实现自然触碰 `knowledge_plane.py` 对应区域,可作为单独小 commit;否则 deferred。

## Design Anchors

- `docs/design/INVARIANTS.md §0/§4/§5`:Control 只在 Orchestrator / Operator;Execution 不直接写 Truth;Path C specialist internal LLM calls 必须穿透 Provider Router;canonical / route / policy mutation 只能由 `apply_proposal`。
- `docs/design/EXECUTOR_REGISTRY.md §1.2 Wiki Compiler`:Wiki Compiler 五元组为 `(specialist / propose_only / {task_artifacts, event_log, staged_knowledge} / specialist_internal / hybrid)`,默认 retrieval sources 为 `knowledge`, `artifacts`, `raw_material`。
- `docs/design/EXECUTOR_REGISTRY.md §1.2 4 模式表`:实现必须区分 `draft`、`refine-supersede`、`refine-refines`、`refresh-evidence`,并落实 `relation_metadata` 语义。
- `docs/design/SELF_EVOLUTION.md §4.2`:Wiki Compiler 起草侧 -> Librarian 守门侧 -> Operator 共同收口。冲突草稿只标 `contradicts(<wiki_id>)`,系统永不自动 supersede。
- `docs/design/KNOWLEDGE.md §2.2/§2.3`:Wiki / Canonical 是默认语义入口;Evidence 是 source-anchored support;relation expansion 是 retrieval 层正式步骤。
- `docs/design/KNOWLEDGE.md §A`:M5 guard 以 `Unversioned Evidence Rebuild` 为 worked example,禁止只刷新 `content_hash` 而不刷新 `parser_version` / `span` / `heading_path`。
- `docs/engineering/ADAPTER_DISCIPLINE.md`:HTTP 实现必须使用 Pydantic response models、`Depends`、集中 exception handlers;adapter 不写 state machine,不直接 import lower-layer internals。
- `docs/engineering/CODE_ORGANIZATION.md` + `ARCHITECTURE_DECISIONS.md`:Driving adapters 只调用 `application/commands` / `application/queries`;Knowledge upper layers 走 `knowledge_plane` facade。
- `docs/engineering/TEST_ARCHITECTURE.md`:新增 CLI tests 放 `tests/integration/cli/`;HTTP tests 放 `tests/integration/http/`;boundary rules 放 guard tests;质量梯度用 eval signal,不进默认 hard gate。

## Current Code Baseline

- `src/swallow/knowledge_retrieval/knowledge_plane.py` 已是 functional facade,production 上层禁止 direct import `knowledge_retrieval.*` 子模块。
- `src/swallow/application/commands/knowledge.py` 已承接 staged promote/reject、file ingestion、relation commands;`StagedCandidate` 已由 application 层公共导出给 HTTP schemas 使用。
- `StagedCandidate` 当前字段不足以承载 `source_pack`、`rationale`、`relation_metadata`、`conflict_flag`;M1 需要 backward-compatible 扩展。
- `knowledge_relations` 当前支持 `refines` / `contradicts` / `cites` / `extends` / `related_to`;M3 需要补齐设计语义中的 `supersedes` / `refers_to` / `derived_from`,并保留 legacy 类型兼容。
- HTTP adapter 已有 `adapters/http/{api,schemas,dependencies,exceptions,server}.py` 布局,M2-M4 必须继续沿用。
- Web Control Center 目前有 task read/write 和 staged/proposal write surface,但缺 project-level knowledge browse。
- Specialist agents 当前多在 `surface_tools/*` 并注册到 `orchestration/executor.EXECUTOR_REGISTRY`。本 phase 可以为一致性新增 Wiki Compiler specialist module;不在本 phase 重命名既有 specialist home。

## Implementation Decisions

1. **CLI trigger only for LLM compiling**:`swl wiki draft/refine/refresh-evidence` 是本期唯一 Wiki Compiler trigger。Web Knowledge panel 只读,不触发 LLM,避免引入 fire-and-poll/background runner。
2. **Application command is surface wrapper,not specialist identity**:`application/commands/wiki.py` 暴露 adapter-facing command;Wiki Compiler specialist 仍是独立 execution entity,注册到 executor registry 并可被单测作为 `ExecutorProtocol` 验证。
3. **Path C through existing gateway**:LLM draft/refine 只调用 `provider_router.agent_llm.call_agent_llm()` 或其 facade path,不得直接 import/use `httpx` or provider SDK。`refresh-evidence` 不调用 LLM。
4. **Staged first**:`draft` / `refine` 只创建 staged candidate。Operator 后续仍通过已有 staged review/promote path 决策;任何 canonical mutation 仍走 `register_canonical_proposal` + `apply_proposal`。
5. **Relation-aware staged metadata**:compiler 输出 relation metadata;promotion path 只在 Operator 明确 promote 时消费这些 metadata。`supersede` 不等于系统自动覆盖,它只是候选关系和 Operator review signal。
6. **Task anchor is required**:M1 CLI 命令要求 `--task-id`,用于 staged candidate 的 `source_task_id` 与 compiler artifacts anchor。后续可做 project-level authoring task shortcut,本期不创建隐式任务。
7. **Raw material remains source,not truth**:raw material refs 进入 source pack,不成为 Knowledge Truth。source pack 持有 `source_ref` / `content_hash` / `parser_version` / `span` / `heading_path` / preview,不持有 physical backend object。
8. **Browse routes are read-only**:M2-M3 routes 只调用 `application/queries/knowledge.py`;adapter 不读 SQLite/file paths。
9. **No broad D2 ports work**:本期不引入 `KnowledgePort` 或 `TaskStorePort`。若测试需要 seam,优先 monkeypatch application command / query boundary,不做 driven ports rollout。
10. **Application owns promotion side effects**:若 staged candidate promotion 需要创建 relation row,只能由 `promote_stage_candidate_command` 或 application command 内部 helper 在 `apply_proposal` 成功后执行。CLI/HTTP adapter 不创建 relation。
11. **Supersede apply deferred in M1**:M1 支持 `refine --mode supersede` 起草和 staged review signal,但不承诺 target-id driven 的旧 wiki/canonical `superseded` 状态翻转。完整 supersede apply 需要 governance-owned extension 或 plan revision。现有 canonical-key supersede compatibility 若自然触发可保留,但不能作为 M1 验收假设。
12. **Derived-from metadata-only for raw sources**:`derived_from` 指向 raw `source_ref` 时只保存在 staged `relation_metadata` / `source_pack`;不写入 `knowledge_relations`。只有当 target 是已存在 knowledge/evidence object id 时,后续实现才可创建 relation row。

## Milestones

| Milestone | Scope | Files / Areas | Acceptance | Validation | Risk | Commit Gate |
|---|---|---|---|---|---|---|
| **M1 - Wiki Compiler 起草核心** | 新增 `swl wiki draft`;`swl wiki refine --mode supersede\|refines`;`swl wiki refresh-evidence`;新增 application commands;新增 specialist;扩展 staged metadata;source pack + rationale + conflict flag;写 task artifacts 记录 prompt pack / compiler result | `src/swallow/adapters/cli.py`;`src/swallow/adapters/cli_commands/wiki.py`;`src/swallow/application/commands/wiki.py`;specialist module;`knowledge_plane.py`;staged candidate model;executor registry/tests | CLI 可用;draft/refine 用 mocked LLM 写 pending staged candidate和 task artifact;`update_staged_candidate` 保留 compiler metadata;refresh-evidence 不走 LLM且更新 evidence anchor;Wiki Compiler 注册为 specialist executor;无 canonical direct write;`derived_from` raw source refs metadata-only;`supersede` apply status flip deferred | `tests/integration/cli/test_wiki_commands.py`;existing `tests/test_specialist_agents.py`;existing `tests/test_executor_protocol.py`;facade tests;focused invariant guard | High:LLM path + staged schema + promotion semantics | 单独 milestone commit |
| **M2 - Knowledge browse 路由** | 增加 read-only list routes:`GET /api/knowledge/wiki`,`GET /api/knowledge/canonical`,`GET /api/knowledge/staged`;新建 shared query model | `src/swallow/application/queries/knowledge.py`;`src/swallow/adapters/http/api.py`;`schemas.py` | 所有 routes 走 Pydantic response envelope;adapter 只调用 query;支持 count/filter/basic summary | `tests/integration/http/test_knowledge_browse_routes.py`;`tests/unit/application/test_knowledge_queries.py`;HTTP schema tests | Medium:global knowledge list may cross task/file/sqlite compatibility | 可与 M3 同一 commit,但 M2 验证单独记录 |
| **M3 - Knowledge detail + relations 视图** | 增加 `GET /api/knowledge/{id}` + `GET /api/knowledge/{id}/relations`;补齐 relation type semantics;detail 响应包括 wiki/canonical/staged/evidence 来源与 adjacent relations | `application/queries/knowledge.py`;`knowledge_plane.py`;relation helpers;HTTP schemas/routes | detail 能解析 canonical id、wiki object id、staged id;relations response 包含 `supersedes` / `refines` / `contradicts` / `refers_to` / `derived_from` adjacency | HTTP integration;relation unit tests;facade characterization | Medium-high:当前 relation enum 与设计枚举不一致 | 可与 M2 同一 commit,若 schema/relations diff 大则单独 |
| **M4 - Web UI Knowledge panel** | 静态 UI 增加 Knowledge tab:wiki/canonical/staged 列表、详情、邻接 relations;不加 LLM trigger buttons | `src/swallow/adapters/http/static/index.html`;HTTP read models | Operator 可从浏览器查看 staged/wiki/canonical 与 relation adjacency;JS 不编码业务 state machine;无新 frontend dependency | `tests/test_web_api.py` / HTTP static smoke;Playwright 若仓库已有则补 screenshot,否则用 HTML/route smoke;manual `swl serve` optional | Medium:UI 容易扩大范围 | 单独 or M2-M3 同 milestone,由实现 diff 决定 |
| **M5 - Guard / Eval / Closeout prep** | 增加 Wiki Compiler boundary guard;Evidence rebuild parser_version guard;adapter boundary guard更新;eval signal;closeout draft/PR material prep | `tests/test_invariant_guards.py`;`tests/eval/`;plan/closeout/pr | Guard 证明 Wiki Compiler 不调用 `apply_proposal` / canonical writers;refresh-evidence helper 必须写 `parser_version` + content/span/heading path;Web adapter不越界 | invariant guard;focused CLI/HTTP/application;eval deselected/default;full pytest;compileall;diff check | High:guard 太宽会误伤现有 specialist | 单独 final validation gate |

## M1 Detailed Contract

### CLI shape

```text
swl wiki draft --task-id <task_id> --topic <topic> --source-ref <ref> [--source-ref <ref> ...] [--model <model>] [--dry-run]
swl wiki refine --task-id <task_id> --mode supersede|refines --target <wiki_id> --source-ref <ref> [--source-ref <ref> ...] [--model <model>] [--dry-run]
swl wiki refresh-evidence --task-id <task_id> --target <evidence_id> --source-ref <ref> --parser-version <version> --span <span> [--heading-path <path>]
```

Implementation notes:

- `--task-id` is required in first stage to keep staged candidates and compiler artifacts anchored to an existing task truth object.
- `--source-ref` accepts existing `file://...` and `artifact://...` refs supported by `RawMaterialStore`; path-to-source-ref convenience may be added if it uses existing raw material helpers and stores only stable `source_ref`.
- `draft` / `refine` write task artifacts under the supplied task id, at minimum `wiki_compiler_prompt_pack.json` and `wiki_compiler_result.json` or equivalent artifact keys. These artifacts are supporting evidence for review; they are not canonical truth.
- `draft` uses no target wiki relation except optional `derived_from`.
- `refine --mode supersede` records `relation_metadata = [{"relation_type": "supersedes", "target_object_id": <wiki_id>}]`.
- `refine --mode refines` records `relation_metadata = [{"relation_type": "refines", "target_object_id": <wiki_id>}]`.
- `refresh-evidence` is a technical update command, not a compiler LLM call and not a staged candidate draft.

### Staged candidate extension

Extend `StagedCandidate` with backward-compatible defaults:

- `wiki_mode: str = ""`
- `target_object_id: str = ""`
- `source_pack: list[dict[str, object]] = []`
- `rationale: str = ""`
- `relation_metadata: list[dict[str, object]] = []`
- `conflict_flag: str = ""`

Existing staged registry records must still load.

Required implementation detail:

- `StagedCandidate.from_dict(...)` must read the new keys with defaults.
- `StagedCandidate.to_dict()` must emit the new keys for new records.
- `update_staged_candidate(...)` must pass all compiler metadata through when reconstructing a decided candidate. Promote/reject must not zero `source_pack`, `rationale`, `relation_metadata`, or `conflict_flag`.
- M1 tests must include an old-record load fixture and a promote/reject passthrough fixture.

### Source pack schema

Define a small `WikiCompilerSourceAnchor` schema rather than ad hoc dicts. Each source pack entry is compatible with `SourcePointer.to_dict()` from `knowledge_retrieval/evidence_pack.py` and extends it with evidence anchor fields:

```json
{
  "reference": "source label used in prompt",
  "path": "display path or source key",
  "source_type": "raw_material|artifact|knowledge",
  "source_ref": "file://workspace/... or artifact://task/file.md",
  "artifact_ref": "",
  "resolved_ref": "",
  "resolved_path": "",
  "resolution_status": "resolved|unresolved",
  "resolution_reason": "",
  "line_start": 0,
  "line_end": 0,
  "heading_level": 0,
  "heading_path": "",
  "content_hash": "sha256:...",
  "parser_version": "wiki-compiler-v1",
  "span": "",
  "preview": "bounded text preview"
}
```

Rules:

- `content_hash`, `parser_version`, and at least one location anchor (`span`, `line_start/line_end`, or `heading_path`) are required for resolved raw/artifact sources.
- `resolved_path` is display/debug metadata only; Truth-facing fields must use `source_ref`, not absolute path assumptions.
- `derived_from` relationships to raw/artifact sources point to these source anchors, not to `knowledge_relations` rows.

### Specialist output contract

Mocked LLM / real LLM content is parsed into a structured draft:

```json
{
  "title": "short wiki title",
  "text": "compiled wiki body",
  "rationale": "why these sources support this draft",
  "relation_metadata": [
    {"relation_type": "derived_from", "target_ref": "file://workspace/notes/foo.md"}
  ],
  "conflict_flag": "contradicts(<wiki_id>) or empty"
}
```

The compiler must also persist/return a source pack with content anchors. If the LLM omits relation/conflict fields, the parser defaults to empty metadata; it must not invent `supersedes` or `contradicts`.

### Promotion interaction

This phase may enhance `promote_stage_candidate_command` only to preserve and apply Operator-approved relation metadata:

- `refines`:after Operator promote and successful `apply_proposal`, `promote_stage_candidate_command` creates the `refines` relation between the newly promoted wiki object and target wiki object. This stays in application command code; adapters do not create relations.
- `supersedes`:M1 supports staged `supersedes(<wiki_id>)` metadata and review/preflight visibility only. Target-id based status flip for old wiki/canonical objects is deferred until a governance-owned apply extension or explicit plan revision. Promotion must not silently claim the old wiki was superseded unless current canonical-key compatibility actually performed that write.
- `derived_from`:raw/artifact source refs remain metadata-only in `source_pack` / staged `relation_metadata`. Do not call `create_knowledge_relation` for raw `source_ref` targets.
- `contradicts`:promotion should require explicit Operator note/confirmation through existing CLI force path or reject with a typed preflight error. Web promote still does not expose force.

If implementation shows this promotion interaction is larger than expected, it must be split into a plan revision before code proceeds beyond M1.

Staged `relation_metadata` is raw metadata validated by Wiki Compiler mode rules. The `KNOWLEDGE_RELATION_TYPES` persistence enum is only enforced when application code creates an actual relation row. In M1, that is limited to knowledge-object relations such as `refines`; `derived_from` raw refs and `supersedes` review signals are not persisted as relation rows.

## M2/M3 HTTP Contract

All success responses use the existing envelope style:

```json
{"ok": true, "data": {...}}
```

Routes:

- `GET /api/knowledge/wiki?status=active|superseded|all&limit=<n>`
- `GET /api/knowledge/canonical?status=active|superseded|all&limit=<n>`
- `GET /api/knowledge/staged?status=pending|promoted|rejected|all&limit=<n>`
- `GET /api/knowledge/{object_id}`
- `GET /api/knowledge/{object_id}/relations`

Response model requirements:

- list responses include `count`, `items`, `filters`.
- detail response includes `object_id`, `object_kind`, `status`, `text_preview`, `source_refs`, `source_pack`, `rationale`, `relation_metadata`, `conflict_flag` where available.
- relations response groups by relation type: `supersedes`, `refines`, `contradicts`, `refers_to`, `derived_from`, plus `legacy` for older `cites` / `extends` / `related_to` relations. Groups may be assembled from both persisted `knowledge_relations` rows and staged/canonical `relation_metadata`; raw `derived_from` source refs are displayed as metadata edges, not persistence rows.
- route implementation uses `Depends(get_base_dir)` and centralized error handlers.

## M4 Web UI Contract

- Add a top-level Knowledge tab or segmented control alongside the existing task surface.
- Show three list modes:Wiki, Canonical, Staged.
- Selecting an item loads detail and adjacent relations from backend.
- UI must not infer domain eligibility from raw statuses except for simple list filters already provided by backend.
- UI must not include Wiki Compiler draft/refine buttons in this phase.
- No frontend dependency or build step.
- Keep layout stable on mobile/desktop; if existing style is touched, avoid nested cards and text overflow.

## M5 Guards

Add or extend guard coverage for:

1. `test_wiki_compiler_agent_boundary_propose_only`
   - Wiki Compiler production module must not import/call `apply_proposal`, `append_canonical_record`, `persist_wiki_entry_from_record`, route/policy writers, or `save_state`.
   - Wiki Compiler may submit staged candidates only through `knowledge_plane.submit_staged_knowledge`.
   - Wiki Compiler LLM calls go through `provider_router.agent_llm` / Provider Router path, not direct `httpx`.
   - Wiki Compiler does not call `append_event` directly in M1. If future implementation needs direct event kinds, add them through a guard-aware plan revision.

2. `test_wiki_compiler_refresh_evidence_updates_parser_version_anchor`
   - Refresh helper cannot update only `content_hash`.
   - Any refreshed evidence payload must include non-empty `parser_version`, `content_hash`, and either `span` or `heading_path`.

3. `test_http_knowledge_routes_only_call_application_queries`
   - `adapters/http/api.py` knowledge routes call `application.queries.knowledge`, not `knowledge_retrieval.*`, SQLite, or filesystem path helpers.

4. `test_knowledge_relation_metadata_types_cover_design_modes`
   - Staged/compiler metadata accepts `supersedes`, `refines`, `contradicts`, `refers_to`, and `derived_from`.
   - Persistence relation helper includes only relation types that can be validated as knowledge-object to knowledge-object edges. `derived_from` raw `source_ref` targets are metadata-only unless backed by an evidence/knowledge object id.

Existing invariant guards must remain passing.

## Eval Plan

Default merge gate remains pytest/guards. Add one deselected eval signal because M1 output quality has a gradient:

- `tests/eval/test_wiki_compiler_quality.py`
- Use small golden raw-material fixtures and mocked LLM JSON responses.
- Score structural completeness, not literary quality:
  - source pack present for every source.
  - rationale cites at least one source id/ref.
  - relation metadata matches requested mode.
  - no `supersedes` emitted in `draft` mode.
  - `conflict_flag` preserved when supplied.

Live API smoke is optional and must be marked separately; it is not a merge blocker.

## Validation Plan

Focused during implementation:

```bash
.venv/bin/python -m pytest tests/integration/cli/test_wiki_commands.py -q
.venv/bin/python -m pytest tests/integration/http/test_knowledge_browse_routes.py -q
.venv/bin/python -m pytest tests/unit/application/test_knowledge_queries.py -q
.venv/bin/python -m pytest tests/test_invariant_guards.py -q
.venv/bin/python -m pytest tests/test_specialist_agents.py tests/test_executor_protocol.py -q
```

M1 specialist and executor registration tests should extend existing root-level `tests/test_specialist_agents.py` and `tests/test_executor_protocol.py` unless the implementation grows large enough to justify a new focused file. If a new file is created, add it to this validation list in the same patch.

Milestone/full gate:

```bash
.venv/bin/python -m compileall -q src/swallow
.venv/bin/python -m pytest -q
git diff --check
```

Optional quality signal:

```bash
.venv/bin/python -m pytest -m eval tests/eval/test_wiki_compiler_quality.py -q
```

## Risks And Review Focus

- **Staged schema drift**:Extending `StagedCandidate` must preserve loading old records. Tests need old-record fixture.
- **Promotion semantics**:`supersede` and `refines` metadata touches canonical/relations behavior. If this becomes larger than expected, stop and revise plan before broad mutation.
- **Boundary drift**:Wiki Compiler is tempting to implement as direct application command logic. Keep specialist identity separate and guard direct canonical writers.
- **Raw material leakage**:Do not persist absolute paths or backend-specific clients in staged/source pack. Persist source refs and anchors only.
- **HTTP adapter regression**:M2-M4 must follow `ADAPTER_DISCIPLINE.md`; no route-level try/except ladders, no direct lower-layer imports, no custom response converter.
- **Web scope creep**:No graph visualization and no Web LLM trigger in this phase.
- **Eval interpretation**:Eval is a quality signal, not a hard default gate.

## Branch / Commit / Review Gates

- Before implementation:Human creates `feat/lto-1-wiki-compiler-first-stage` from `main`.
- Recommended milestone commits:
  - `feat(wiki): add compiler draft and refine commands` for M1.
  - `feat(web): add knowledge browse read routes` for M2+M3.
  - `feat(web): add knowledge panel` for M4.
  - `test(guards): lock wiki compiler boundaries` or included with M5 final validation, depending diff shape.
  - `docs(plan): close out lto-1 wiki compiler` only after review/closeout stage.
- Review gate:M1 is high-risk and should be reviewed before combining with Web UI work. M2+M3 may be reviewed together if the diff stays read-only and well-contained.
- PR body:Codex writes `./pr.md` after implementation validation and before Human opens PR.

## Completion Criteria

LTO-1 first stage is complete when:

- `swl wiki draft/refine/refresh-evidence` contracts are implemented and tested.
- Wiki Compiler specialist is registered and tested as a propose-only specialist.
- Draft/refine writes staged candidates with source pack, rationale, relation metadata, and conflict flag.
- `refresh-evidence` updates evidence anchors without LLM and without `apply_proposal`.
- HTTP Knowledge Browse routes return typed Pydantic envelopes via application queries.
- Web Knowledge panel can browse list/detail/relations without implementing business decisions in JS.
- Guard tests prove boundary constraints.
- Focused tests, full pytest, compileall, and diff check pass.
- `closeout.md` and `./pr.md` are prepared for review.
