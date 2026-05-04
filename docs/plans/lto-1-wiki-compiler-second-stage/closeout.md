---
author: codex
phase: lto-1-wiki-compiler-second-stage
slice: phase-closeout
status: final
depends_on:
  - docs/plans/lto-1-wiki-compiler-second-stage/plan.md
  - docs/plans/lto-1-wiki-compiler-second-stage/plan_audit.md
  - docs/active_context.md
  - docs/concerns_backlog.md
  - src/swallow/application/commands/knowledge.py
  - src/swallow/application/services/wiki_jobs.py
  - src/swallow/knowledge_retrieval/_internal_knowledge_store.py
  - src/swallow/knowledge_retrieval/_internal_knowledge_relations.py
  - src/swallow/truth_governance/apply_canonical.py
  - src/swallow/truth_governance/truth/knowledge.py
  - src/swallow/adapters/http/api.py
  - src/swallow/adapters/http/schemas.py
  - src/swallow/adapters/http/static/index.html
  - tests/test_invariant_guards.py
  - tests/eval/test_wiki_compiler_quality.py
  - tests/eval/test_wiki_compiler_second_stage_quality.py
---

TL;DR:
LTO-1 Wiki Compiler 第二阶段实现已完成，当前分支已通过 focused guard/eval/full validation，等待 Human 对 M5 closeout 材料审阅并提交。
This phase extends the first-stage propose-only Wiki Compiler into a Web authoring / review workflow, keeps canonical mutation behind governed promotion, materializes resolved source anchors into evidence objects, and adds phase-specific guard/eval coverage for the long-term risk surfaces documented in the plan.

# LTO-1 Closeout: Wiki Compiler Second Stage

## Outcome

LTO-1 第二阶段把 first-stage 的 CLI specialist loop 接到 Web authoring / review surface 上，并补齐 governed supersede apply、source evidence objectization、structured confirmation UX、guards 和 deterministic eval signal。

Delivered:

- Web Control Center now has an authoring panel for `draft`, `refine/supersede`, `refine/refines`, and `refresh-evidence`.
- Draft/refine are fire-and-poll job actions backed by task-anchored job artifacts.
- Candidate review now exposes `source_pack`, `derived_from` evidence links, `supersedes` / `refines` metadata, and `conflict_flag`.
- Promote confirmation is structured and explicit; Web still does not expose raw `force`.
- Promotion of explicit supersede targets still happens inside the canonical `apply_proposal` path.
- Resolved source_pack anchors are materialized as evidence objects and linked through persisted `derived_from` relations.
- M5 adds guards for the phase's truth-write boundaries and a second-stage eval file for deterministic structural checks.

Canonical mutation ownership did not change. Wiki Compiler remains propose-only; the Web adapter stays inside the application boundary; evidence and supersede handling remain governed by the existing knowledge and truth store layers.

## Scope Delivered

| Plan area | Result |
|---|---|
| M1 Governed supersede apply | Delivered: explicit target-id supersede confirmation and canonical status flip inside the apply path. |
| M2 Derived-from evidence objectization | Delivered: resolved source_pack anchors become evidence objects and persisted `derived_from` relations target evidence ids only. |
| M3 Web fire-and-poll API | Delivered: draft/refine job routes, job status/result routes, and refresh-evidence route. |
| M4 Web authoring/review UX | Delivered: static authoring form, job tray, candidate review, and structured confirmations. |
| M5 guards/eval/closeout prep | Delivered: invariant guards, eval file, closeout draft, PR body draft, and state sync. |

## Implementation Notes

The Web authoring flow remains intentionally simple:

- static HTML/JS only
- no frontend package
- no build step
- no graph visualization

The job tray is a local, best-effort UI affordance for long-running LLM work. It does not change task state orchestration or introduce durable worker semantics.

The promotion-side structured confirmation path is application-owned, not adapter-owned:

- CLI may still use `--force` as an existing local confirmation escape hatch.
- Web uses typed notice confirmations for `supersede` and `conflict`.
- Missing confirmation returns a typed preflight conflict instead of silently forcing the promote.

Evidence objectization stays bounded to the stage-2 decision:

- resolve source_pack anchors
- materialize task-scoped evidence objects
- persist `derived_from` edges only to evidence object ids
- keep raw source refs as metadata for review/display

## Guard Behavior

M5 adds executable guard coverage for the phase boundary:

- `test_wiki_compiler_web_routes_only_call_application_boundary`
  - rejects direct adapter reach into `application.services.wiki_compiler`, provider clients, truth-governance writers, and knowledge internals
  - proves wiki HTTP routes stay within the application boundary
- `test_wiki_compiler_web_llm_actions_are_fire_and_poll`
  - proves draft/refine routes create queued jobs and schedule background work instead of compiling inline
- `test_wiki_compiler_supersede_status_flip_only_in_apply_proposal_path`
  - rejects direct truth-layer supersede status flips outside the canonical apply path
  - verifies `apply_canonical` passes `supersede_target_ids` and the repository owns the store helper call
- `test_wiki_compiler_derived_from_relation_targets_evidence_only`
  - verifies persisted `derived_from` validation rejects non-evidence targets
  - verifies the stage-2 promotion helper persists `derived_from` to evidence ids, not raw refs
- `test_wiki_compiler_evidence_objectization_preserves_parser_version_anchor`
  - verifies source-pack evidence objects keep parser_version/content_hash/span/heading_path anchors
  - verifies evidence materialization occurs before canonical append and relation persistence

## Eval Signal

`tests/eval/test_wiki_compiler_quality.py` and `tests/eval/test_wiki_compiler_second_stage_quality.py` are marked `pytest.mark.eval`, so they are deselected by default.

They provide deterministic structural checks without live LLM calls:

- source_pack generation keeps one anchor per resolved source ref
- draft/refine payloads preserve reviewable relation metadata shape
- stage-2 promotion materializes resolved source anchors into evidence objects
- supersede review paths require explicit target ids
- conflict signals remain visible to review callers
- Web job payloads carry candidate ids and source anchors

## Validation

Final implementation validation:

```text
M5 eval:
- .venv/bin/python -m pytest -m eval tests/eval/test_wiki_compiler_quality.py tests/eval/test_wiki_compiler_second_stage_quality.py -q
- 8 passed

M5 invariant guards:
- .venv/bin/python -m pytest tests/test_invariant_guards.py -q
- 40 passed

Focused phase gates:
- .venv/bin/python -m pytest tests/integration/cli/test_wiki_commands.py tests/integration/cli/test_knowledge_commands.py -q
- 9 passed
- .venv/bin/python -m pytest tests/integration/http/test_knowledge_browse_routes.py tests/integration/http/test_web_write_routes.py tests/test_web_api.py -q
- 24 passed
- .venv/bin/python -m pytest tests/unit/application/test_knowledge_queries.py tests/test_staged_knowledge.py tests/test_knowledge_relations.py -q
- 22 passed

Milestone/full gate:
- .venv/bin/python -m compileall -q src/swallow
- passed
- .venv/bin/python -m pytest -q
- 793 passed, 16 deselected
- git diff --check
- passed
```

## Plan Audit Absorption

`plan_audit.md` had 3 blockers / 5 concerns / 2 nits. The implementation absorbed them as follows:

- target-id supersede now has an explicit apply-time payload field and repository-side helper call path.
- evidence support objects reuse the task-scoped knowledge evidence store instead of introducing a new schema migration.
- evidence objectization and relation persistence stay inside the canonical apply path.
- structured Web confirmation replaces a raw force bypass in the browser surface.
- job persistence is task-anchored artifact storage and background execution is best-effort local work.
- the relation and evidence guards now prove the expected target discipline.

## Deferred Follow-Ups

Intentionally deferred:

- cross-candidate evidence deduplication for identical source anchors.
- a future global evidence schema reconciliation beyond the task-scoped store reuse decision.
- broader retrieval quality and ranking work.
- any graph visualization or richer Web workbench beyond the current Knowledge surface.
- PR review and merge gate, which remain a Human decision after this phase closeout prep.

## Review Status

This closeout is prepared for Human review/commit.

Current next steps:

- Human reviews the final M5 diff and commits the implementation / guard / closeout state.
- Human updates or creates `./pr.md` from the phase summary.
- Human decides merge readiness after the review pass.
