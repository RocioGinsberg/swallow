# Active Context

> **Document discipline**
> Owner: Human
> Updater: Codex
> Trigger: 当前 slice / branch / 下一步 / 阻塞项 / 产出物变化
> Anti-scope: 不维护长期协作规则、不维护历史 phase 总表、不复制 roadmap 或 closeout 正文

## 当前轮次

- latest_completed_track: `LTO-2 Retrieval Quality / Evidence Serving`
- latest_completed_phase: `lto-2-retrieval-source-scoping`
- latest_completed_slice: `merged to main at d4288a1`
- active_track: `R-entry Real Usage`
- active_phase: `r-entry-v1.9-real-usage`
- active_slice: `r19-008 knowledge-policy terminal status / handoff guidance fix`
- active_branch: `fix/r19-008-knowledge-policy-handoff`
- status: `r19_008_knowledge_policy_handoff_fix_verified`

## 当前状态说明

当前 git 分支为 `fix/r19-008-knowledge-policy-handoff`。`v1.9.0` release docs 已提交为 `d598e58 docs(release): sync v1.9.0 release docs`,tag `v1.9.0` 已打在该 commit。Human 已 merge R19-001 narrow fix 到 `main` at `7516bc5 R19-001 fixed`,merge R19-003 truth reuse visibility fix 到 `main` at `ed08d8f R19-003 fixed`,merge R19-004 Wiki dry-run artifact visibility fix 到 `main` at `b4ed07e R19-004 fixed`,merge R19-002 note-only offline status semantics fix 到 `main` at `45a2f87 R19-002 fixed`,merge R19-007 runbook command drift fix 到 `main` at `b2dc17f R19-007 fixed`,并已提交 after-fixes smoke findings at `b92ef86 docs(test): record after-fixes r-entry smoke`。Codex 已完成 R19-008 narrow fix:retrieval-eligible `candidate/source_only` task knowledge 仍被 knowledge policy 阻断,但 executor 已完成且其他 policy/validation 通过时,terminal state now becomes `waiting_human` with `handoff_status: knowledge_policy_review` instead of `failed` executor recovery.

LTO-2 source scoping 实现内容:task-declared `document_paths` 现在进入 `RetrievalRequest.declared_document_paths`;`build_task_retrieval_request` 是唯一注入点并把路径规范为 workspace-relative;retrieval 在 rerank 前应用 declared-document priority 与 generated/archive/build-cache noise downgrade;`score_breakdown` 暴露 `declared_document_priority` / `source_noise_penalty`;`retrieval_report.md` 新增 `Truth Reuse Visibility`;task memory/summary 也记录 truth reuse visibility 状态。非目标仍保持:Graph RAG、schema migration、vector index overhaul、chunk 大改、provider/rerank 新集成。

本轮另外按 Human direction 取消 model_review gate 层:删除 `.agents/workflows/model_review.md`,并从 `claude/rules` `claude/role` `codex/rules` `codex/role` `shared/rules` `feature.md` `AGENTS.md` `.codex/session_bootstrap.md` 中移除所有 model_review 引用;plan gate 前不再要求第二模型审查,plan_audit 直接进入 Human Plan Gate。

LTO-4 已完成 M1-M4:CLI command-family split、shared builders/assertions、AST guard helper extraction、global builder fixture entry。最终 `collect-only` 为 `806/825 tests collected (19 deselected)`,比 LTO-4 起始 baseline `802/821` 增加 4 个 helper self-tests,没有测试数量减少。最终全量 pytest `806 passed, 19 deselected in 131.76s`,real `2m12.909s`,处于 LTO-4 允许耗时区间内。LTO-4 完成后没有 cut tag,随后进入 R-entry 并触发本次 LTO-2 source scoping phase。

最近稳定 checkpoint:

- LTO-2 Retrieval Quality / Evidence Serving 已 merge 到 `main` at `03744f0`;post-merge state sync 已提交为 `a3c1844`。
- LTO-4 Test Architecture 已 merge / synced 到 `main` at `ac2d3ff`;历史 phase 文档已归档到 `docs/archive_phases/`。
- R-entry Real Usage 不是开发 phase;R-entry runbook 与 findings 保留为 LTO-2 source scoping 的 evidence input。
- LTO-2 Retrieval Source Scoping And Truth Reuse Visibility 已 merge 到 `main` at `d4288a1`。

## 当前关键文档

1. `docs/active_context.md`(本文)
2. `current_state.md`
3. `docs/roadmap.md`
4. `docs/plans/r-entry-v1.9-real-usage/plan.md`
5. `docs/plans/r-entry-v1.9-real-usage/findings.md`
6. `docs/plans/r-entry-real-usage/plan.md`
7. `docs/design/INVARIANTS.md`
8. `docs/design/KNOWLEDGE.md`
9. `docs/design/DATA_MODEL.md`
10. `docs/engineering/TEST_ARCHITECTURE.md`
11. `docs/engineering/ADAPTER_DISCIPLINE.md`
12. `docs/engineering/CODE_ORGANIZATION.md`
13. `docs/concerns_backlog.md`

## 当前推进

已完成:

- **[Human]** LTO-4 Test Architecture 已完成并 merge/sync 到 `main` at `ac2d3ff`;不 cut tag。
- **[Human]** 历史 phase 文档已移动到 `docs/archive_phases/` at `795aa4d docs(store): move history plans to archive`;`docs/plans/` 保留 R-entry runbook 与当前已完成的 LTO-2 source scoping phase 文档。
- **[Codex]** 已产出 `docs/plans/r-entry-real-usage/plan.md`,覆盖 CLI + knowledge chain + Wiki Compiler + Web UI + Tailscale/nginx smoke。
- **[Codex]** 已同步 `docs/roadmap.md` 到 LTO-4 complete / R-entry active 状态。
- **[Codex]** 已执行 R-entry 本机可验证部分并整理 `docs/plans/r-entry-real-usage/findings.md`,记录 retrieval source scoping / truth reuse visibility / note-only offline semantics / wiki ergonomics / nginx host smoke 等 Direction Gate 候选。
- **[Codex]** 已完成 R-entry UX 小修:Wiki CLI 捕获 `AgentLLMUnavailable` 并给出 `source .env` / `--dry-run` 提示;`task staged --task` 空 global staged 结果会提示 task-scoped knowledge surface;`plan.md` 补充 `.env` 与 OpenRouter rerank 配置示例。
- **[Human]** 已提交 R-entry UX 小修:`449ccda fix(cli): polish r-entry operator guidance`。
- **[Codex]** 已更新 `docs/roadmap.md`,将泛化的 `LTO-2 retrieval quality 后续增量` 收敛为 `LTO-2 Retrieval Source Scoping And Truth Reuse Visibility`,并明确 chunk 调整 / schema migration / Graph RAG 均不进入首个 slice。
- **[Codex]** 已产出 `docs/plans/lto-2-retrieval-source-scoping/plan.md`,拆分 M1 request context plumbing、M2 candidate source scoping、M3 truth reuse visibility、M4 R-entry regression smoke。
- **[Claude/design-auditor]** 已产出 `docs/plans/lto-2-retrieval-source-scoping/plan_audit.md`:0 blockers,5 concerns,2 nits。
- **[Codex]** 已吸收 plan audit:明确 `build_task_retrieval_request` 为 M1 唯一注入点;M2 指名 `source_policy_label_for` / `SOURCE_POLICY_NOISE_LABELS` 与 `score_breakdown` 验收;M4 使用 `pytest.mark.eval` 与显式 eval gate;移除 premature closeout 与 `harness.py` 主触点。
- **[Human]** 已切换到 `feat/lto-2-retrieval-source-scoping` 并在完成 review/closeout 后 merge 回 `main`。
- **[Codex]** 已完成 M1-M4 实现:request context plumbing、candidate source scoping、truth reuse visibility report/memory、R-entry regression eval fixture。
- **[Claude]** 已产出 `docs/plans/lto-2-retrieval-source-scoping/review_comments.md`:0 blocks,3 concerns,3 nits;独立验证 focused/eval/full pytest 与 Codex 报告一致(`812 passed, 20 deselected in 139.11s`)。
- **[Claude]** 已把 3 个 [CONCERN] 聚合为 `LTO-2 Source Scoping review follow-ups` 写入 `docs/concerns_backlog.md` Active Open。
- **[Codex]** 已产出 `docs/plans/lto-2-retrieval-source-scoping/closeout.md`,同步 review disposition / validation / deferred follow-ups / merge readiness。
- **[Codex]** 已更新 `pr.md` Review 段,记录 Claude review verdict、独立验证和 3 个 tracked concerns。
- **[Human]** 已 merge LTO-2 Retrieval Source Scoping And Truth Reuse Visibility 到 `main` at `d4288a1`。
- **[Codex]** 已同步 post-merge `docs/active_context.md` / `current_state.md` / `docs/roadmap.md`。
- **[Claude]** 已对 `main@d4288a1` 完成 tag 评估:推荐 cut **v1.9.0**(主题 Retrieval Quality 累积闭环 + R-entry-driven source scoping;v1.8.0 以来 5 个 phase / 3 个 operator-visible 增量;main 稳定;无 API drift 风险)。
- **[Claude]** 已按 Human 要求重写 `docs/roadmap.md`:压缩已完成内容(180→151 行),将 Direction Gate 候选与触发条件提到 §三,LTO 表按"仍在推进 vs 已闭合"分类,完成 phase 细节移交 git log + closeout。
- **[Human]** 已提交 `v1.9.0` release docs:`d598e58 docs(release): sync v1.9.0 release docs`。
- **[Human]** 已执行 tag:`v1.9.0` -> `d598e58`。
- **[Codex]** 已同步 `latest_executed_public_tag` / active context / roadmap tag 状态。
- **[Codex]** 已产出 `docs/plans/r-entry-v1.9-real-usage/plan.md`,作为 post-v1.9.0 设计文档真实使用 runbook。
- **[Codex]** 已产出 `docs/plans/r-entry-v1.9-real-usage/findings.md`,作为真实使用 issue log / Direction Gate evidence 模板。
- **[Codex]** 已执行 R0-R4 / R6 / R9 loopback smoke:preflight、declared-doc task、retrieval report、task knowledge capture、Wiki dry-run、Web API smoke。
- **[Codex]** 已记录 5 条 findings:R19-001 declared `document_paths` 未进入 task truth/source scoping 未应用(blocker);R19-002 note-only offline 被分类为 failed/unreachable_backend(concern);R19-003 Truth Reuse Visibility reason counts/ warning wording 复现 review concern(concern);R19-004 Wiki dry-run `prompt_artifact=-`(concern);R19-005 Web loopback smoke passed(observation)。
- **[Codex]** 已完成 R19-001 narrow fix:普通 `task create --document-paths` 现在持久化到 task `input_context`, `task intake` / `task inspect` 显示声明文档, retrieval JSON/report 暴露 `declared_document_priority`。
- **[Human]** 已提交 R19-001 narrow fix:`8891b7f fix(cli): persist declared task document paths`。
- **[Codex]** 已继续 post-fix R-entry runbook:
  - task `d0a84932a9f1` in `/tmp/swl-r-entry-v1.9-continue`
  - `task inspect` / `task intake` / Web API detail show 4 declared document paths
  - `retrieval_report.md` top hits are declared `docs/design/KNOWLEDGE.md` chunks with `declared_document_priority=1000`
  - task-scoped knowledge reuse visibility still reproduces R19-003
  - Wiki dry-run still prints `prompt_artifact=-`, but real `wiki draft` with `.env` created `staged-1d1c4524` and `wiki_compiler_prompt_pack.json` / `wiki_compiler_result.json`
  - Web loopback on 127.0.0.1:8766 returned task detail, staged knowledge detail, and artifacts; server was stopped
- **[Human]** 已 merge R19-001 fix 回 `main` at `7516bc5 R19-001 fixed`。
- **[Codex]** 已创建并切换到 `fix/r19-003-truth-reuse-visibility`。
- **[Codex]** 已完成 R19-003 narrow fix:
  - `summarize_truth_reuse_visibility` 使用 primary skipped reason,避免一个 skipped task knowledge item 同时计入 `missing_source_pointer` / `query_no_match` / `status_not_active`
  - `summarize_source_policy_warnings` 接收 truth reuse visibility context,当 task/canonical truth exists but did not match retrieval 时使用 `fallback_hits_without_reused_truth_objects`
  - smoke task `6aa7d7ed9619` in `/tmp/swl-r19-003-truth-reuse-fix` shows `skipped_reasons: status_not_active=1` and no stale “no canonical or task knowledge item is present” warning
- **[Human]** 已 merge R19-003 fix 回 `main` at `ed08d8f R19-003 fixed`。
- **[Codex]** 已创建并切换到 `fix/r19-004-wiki-dry-run-artifacts`。
- **[Codex]** 已完成 R19-004 narrow fix:
  - dry-run path writes `wiki_compiler_prompt_pack.json`
  - CLI dry-run output includes concrete `prompt_artifact=.../wiki_compiler_prompt_pack.json`
  - `task artifacts` lists `wiki_compiler_prompt_pack` / `wiki_compiler_result`
  - smoke task `d052660f390b` in `/tmp/swl-r19-004-wiki-dry-run-2` confirms no staged candidate is written by dry-run
- **[Human]** 已 merge R19-004 fix 回 `main` at `b4ed07e R19-004 fixed`。
- **[Codex]** 已创建并切换到 `fix/r19-002-note-only-offline-status`。
- **[Codex]** 已完成 R19-002 narrow fix:
  - explicit `note-only` + `route_mode=offline` returns `ExecutorResult(status="completed", failure_kind="")`
  - `executor_output.md` uses `# Note-Only Offline Run` and records `live_executor_called: no`
  - non-offline `note-only` fallback still reports failed `unreachable_backend`, preserving existing backend recovery semantics
- **[Human]** 已 merge R19-002 fix 回 `main` at `45a2f87 R19-002 fixed`。
- **[Codex]** 已创建并切换到 `fix/r19-007-runbook-command-drift`。
- **[Codex]** 已完成 R19-007 docs/config hygiene 小修:
  - active runbook uses `knowledge canonical-audit` instead of nonexistent `knowledge list --status active`
  - `wiki refine` runbook uses required `--target "$WIKI_TARGET"` and removes unsupported `--topic`
  - dry-run artifact discovery now points to `$BASE/.swl/tasks/$TASK_ID/artifacts`
- **[Human]** 已 merge R19-007 fix 回 `main` at `b2dc17f R19-007 fixed`。
- **[Codex]** 已按 corrected runbook 完成 after-fixes smoke:
  - base_dir `/tmp/swl-r-entry-v1.9-after-fixes`,task `9efc0525e0d4`
  - declared docs persisted and retrieval top hits stayed in declared design docs
  - `set -a; source .env; set +a` made dedicated rerank active: `rerank_backend=dedicated_http`, `rerank_model=rerank-v3.5`, `rerank_applied=True`
  - explicit offline note-only run completed before task knowledge capture
  - Wiki dry-run wrote discoverable prompt pack; real draft produced `staged-3f6fcea5`; refine dry-run with `--target staged-3f6fcea5` succeeded
  - Web loopback on `127.0.0.1:8770` returned 200 for `/`, task detail, staged candidate detail, and artifacts; server stopped
  - new finding R19-008 recorded: retrieval-eligible `candidate/source_only` task knowledge makes rerun terminal status `failed` via knowledge policy despite executor completion
- **[Human]** 已提交 after-fixes smoke findings:`b92ef86 docs(test): record after-fixes r-entry smoke`。
- **[Codex]** 已创建并切换到 `fix/r19-008-knowledge-policy-handoff`。
- **[Codex]** 已完成 R19-008 narrow fix:
  - shared terminal classifier maps completed executor + failed knowledge policy + otherwise-passed checks to `status: waiting_human`, `execution_lifecycle: completed`
  - handoff uses `knowledge_policy_review` contract/status and points `next_operator_action` at `knowledge_policy_report.md`
  - checkpoint snapshot uses `checkpoint_state: knowledge_policy_review`, `recovery_semantics: knowledge_policy_review`, `recommended_path: review`
  - smoke task `4795c81e0c99` in `/tmp/swl-r19-008-knowledge-policy-handoff` confirms no live-executor recovery guidance

待执行:

- **[Human]** 审阅 R19-008 narrow fix,决定是否提交并 merge。
- **[Codex]** merge 后可继续按 corrected runbook 做下一轮 real usage。

## 当前验证

Post-merge state sync validation:

- `git diff --check` -> passed
- `git status --short --branch` -> `## main...origin/main`;modified `current_state.md`, `docs/active_context.md`, `docs/roadmap.md`
- `wc -l docs/roadmap.md` -> `180 docs/roadmap.md`(低于 300 行上限)

Pre-`v1.9.0` release docs validation:

- `git diff --check` -> passed
- `git status --short --branch` -> `## main...origin/main [ahead 1]`;modified `README.md`, `current_state.md`, `docs/active_context.md`, `docs/roadmap.md`
- `wc -l docs/roadmap.md README.md docs/active_context.md current_state.md` -> `151` / `359` / `246` / `174`

Post-`v1.9.0` tag sync validation:

- `git diff --check` -> passed
- `git status --short --branch` -> `## main...origin/main`;modified `current_state.md`, `docs/active_context.md`, `docs/roadmap.md`
- `wc -l docs/roadmap.md docs/active_context.md current_state.md` -> `150` / `248` / `169`

R-entry v1.9 runbook drafting validation:

- `git diff --check` -> passed
- `git status --short --branch` -> `## main...origin/main`;modified `current_state.md`, `docs/active_context.md`, `docs/roadmap.md`;untracked `docs/plans/r-entry-v1.9-real-usage/`
- `wc -l docs/plans/r-entry-v1.9-real-usage/plan.md docs/plans/r-entry-v1.9-real-usage/findings.md docs/active_context.md current_state.md docs/roadmap.md` -> `521` / `73` / `265` / `178` / `152`

R-entry v1.9 partial execution validation:

- R0 preflight -> `doctor --skip-stack` ok; isolated base migrate status `schema_version: 1, pending: 0`
- R2 task -> `10b2890bab71`
- R3/R4 retrieval run -> task failed due note-only offline semantics, but produced `retrieval_count=8`
- R4 task knowledge capture -> `knowledge_capture_added added=1 total=1`; review queue shows `knowledge-0001` blocked by `stage_not_verified`
- R6 Wiki dry-run -> `wiki_draft_dry_run source_count=1 prompt_artifact=-`
- R9 Web loopback smoke -> `GET /` 200; `/api/tasks` and `/api/tasks/10b2890bab71` returned task state; server stopped after smoke
- findings -> R19-001..R19-005 recorded in `docs/plans/r-entry-v1.9-real-usage/findings.md`
- final check -> `git diff --check` passed; port 8765 no longer listening; `wc -l findings/active/current` -> `161` / `276` / `179`

R19-001 document path plumbing fix validation:

- `.venv/bin/python -m pytest tests/integration/cli/test_task_commands.py tests/unit/orchestration/test_retrieval_flow_module.py tests/unit/orchestration/test_task_report_module.py -q` -> `57 passed in 24.57s`
- `.venv/bin/python -m compileall -q src/swallow tests` -> passed
- smoke base dir -> `/tmp/swl-r-entry-v1.9-document-path-fix`
- smoke task -> `7c1e8a592ae1`
- `task intake` / `task inspect` -> `document_paths_count: 2`
- `task rerun 7c1e8a592ae1 --from-phase retrieval` -> produced retrieval artifacts; still reports failed due known R19-002 note-only/offline semantics
- `retrieval.json` / `retrieval_report.md` -> `declared_document_priority=1000` visible
- `git diff --check` -> passed

Post-fix R-entry continuation validation:

- commit under test -> `8891b7f fix(cli): persist declared task document paths`
- base_dir -> `/tmp/swl-r-entry-v1.9-continue`
- task -> `d0a84932a9f1`
- R0/R1 -> `doctor --skip-stack` ok; migrate status `schema_version: 1, pending: 0`; source docs present
- R2 -> `state.json`, `task inspect`, `task intake`, and `GET /api/tasks/d0a84932a9f1` show 4 declared document paths
- R3 -> `task run` produced retrieval artifacts; `retrieval_report.md` top hits are declared `docs/design/KNOWLEDGE.md` chunks with `declared_document_priority=1000`
- R4 -> task knowledge capture added `knowledge-0001`; rerun reproduced R19-003 reason/warning issue
- R5 -> `knowledge list --status active` is not supported by current CLI; recorded R19-007
- R6 -> wiki draft dry-run still reports `prompt_artifact=-`
- R7 -> real `wiki draft` with `.env` succeeded; staged candidate `staged-1d1c4524`; artifacts `wiki_compiler_prompt_pack.json` and `wiki_compiler_result.json`
- R8 -> current `wiki refine` requires `--target` and does not accept `--topic`; corrected dry-run with `--target staged-1d1c4524` still reports `prompt_artifact=-`
- R9 -> loopback Web smoke on `127.0.0.1:8766` passed for `/`, `/api/tasks`, `/api/tasks/d0a84932a9f1`, `/api/tasks/d0a84932a9f1/knowledge`, `/api/knowledge/staged`, `/api/knowledge/staged-1d1c4524`, and `/api/tasks/d0a84932a9f1/artifacts`; server stopped and health check returned `000`

R19-003 truth reuse visibility fix validation:

- `.venv/bin/python -m pytest tests/unit/orchestration/test_task_report_module.py tests/unit/orchestration/test_retrieval_flow_module.py tests/test_retrieval_adapters.py -q` -> `44 passed in 1.39s`
- `.venv/bin/python -m compileall -q src/swallow tests` -> passed
- smoke base dir -> `/tmp/swl-r19-003-truth-reuse-fix`
- smoke task -> `6aa7d7ed9619`
- smoke flow -> create declared-doc task; run; capture candidate/source-only retrieval-eligible task knowledge; rerun from retrieval
- `retrieval_report.md` -> `fallback_hits_without_reused_truth_objects: canonical or task knowledge exists but did not match retrieval`
- `retrieval_report.md` -> `task_knowledge status: considered`, `considered_count: 1`, `skipped_count: 1`, `skipped_reasons: status_not_active=1`
- `memory.json` -> `truth_reuse_visibility.task_knowledge.reason_counts.status_not_active: 1`

R19-004 wiki dry-run artifact visibility fix validation:

- `.venv/bin/python -m pytest tests/integration/cli/test_wiki_commands.py tests/unit/orchestration/test_artifact_writer_module.py -q` -> `15 passed in 1.91s`
- `.venv/bin/python -m pytest tests/integration/cli/test_task_commands.py::LegacyCliTaskCommandTest::test_task_artifacts_groups_paths_by_operator_concern -q` -> `1 passed in 0.81s`
- `.venv/bin/python -m compileall -q src/swallow/application/services/wiki_compiler.py src/swallow/orchestration/artifact_writer.py src/swallow/adapters/cli.py tests/integration/cli/test_wiki_commands.py tests/unit/orchestration/test_artifact_writer_module.py` -> passed
- smoke base dir -> `/tmp/swl-r19-004-wiki-dry-run-2`
- smoke task -> `d052660f390b`
- `wiki draft --dry-run` -> `prompt_artifact=/tmp/swl-r19-004-wiki-dry-run-2/.swl/tasks/d052660f390b/artifacts/wiki_compiler_prompt_pack.json`
- `task artifacts d052660f390b` -> lists `wiki_compiler_prompt_pack` and `wiki_compiler_result`
- `wiki_compiler_prompt_pack.json` -> includes source pack with `resolved_path: docs/engineering/TEST_ARCHITECTURE.md`, `span: L1-L185`, `content_hash`, and preview
- `knowledge stage-list --all` -> `count: 0`

R19-002 note-only offline status semantics fix validation:

- `.venv/bin/python -m pytest tests/integration/cli/test_task_commands.py::test_note_only_offline_task_run_completes_without_backend_failure -q` -> `1 passed in 0.94s`
- `.venv/bin/python -m pytest tests/integration/cli/test_task_commands.py -q` -> `43 passed in 15.87s`
- `.venv/bin/python -m pytest tests/integration/cli/test_knowledge_commands.py::LegacyCliKnowledgeCommandTest::test_note_only_mode_skips_subprocess tests/integration/cli/test_route_commands.py::LegacyCliRouteCommandTest::test_run_task_route_mode_override_changes_selected_route -q` -> `2 passed in 0.23s`
- `.venv/bin/python -m compileall -q src/swallow/orchestration/executor.py tests/integration/cli/test_task_commands.py` -> passed
- smoke base dir -> `/tmp/swl-r19-002-note-only-status`
- smoke task -> `e3795dbb6ce5`
- `task run e3795dbb6ce5` -> `e3795dbb6ce5 completed retrieval=8 execution_phase=analysis_done`
- `task inspect e3795dbb6ce5` -> `status: completed`, `executor_status: completed`, `execution_lifecycle: completed`, `route_mode: offline`, `route_name: local-note`
- `executor_output.md` -> `# Note-Only Offline Run`, `live_executor_called: no`, no `unreachable_backend` or backend/network repair guidance

R19-007 runbook command drift fix validation:

- `.venv/bin/swl knowledge --help` -> confirms supported subcommands include `stage-list`, `stage-inspect`, `stage-promote`, `stage-reject`, and `canonical-audit`;no `knowledge list`
- `.venv/bin/swl wiki refine --help` -> confirms required `--target` and no `--topic`
- `rg -n "knowledge list|wiki refine[\\s\\S]*--topic|find \"\\$BASE/artifacts" docs/plans/r-entry-v1.9-real-usage/plan.md` -> no stale active-runbook command pattern found

After-fixes corrected runbook smoke validation:

- base_dir -> `/tmp/swl-r-entry-v1.9-after-fixes`
- task -> `9efc0525e0d4`
- R0 -> `doctor --skip-stack` ok; `migrate` scanned 0 tasks; source docs present
- R2/R3 -> `task run 9efc0525e0d4` initially returned `completed retrieval=8 execution_phase=analysis_done`; `task inspect` showed `document_paths_count: 6`, `route_mode: offline`, `route_name: local-note`, `executor_status: completed`
- `.env` rerun -> `set -a; source .env; set +a` then `task rerun --from-phase retrieval`; `retrieval_report.md` showed `rerank_backend: dedicated_http`, `rerank_model: rerank-v3.5`, `rerank_applied: True`, `final_order_basis: dedicated_rerank`
- R4 -> task knowledge capture added `knowledge-0001`; `task staged --task` correctly pointed to task-scoped knowledge review queue; `knowledge stage-list --all` stayed empty; `knowledge canonical-audit` succeeded with 0 active records
- R4 rerun -> terminal status became `failed` because `knowledge_policy_status: failed` for `candidate/source_only/retrieval_candidate`; recorded as R19-008
- R6 -> `wiki draft --dry-run` returned concrete `wiki_compiler_prompt_pack.json`; `task artifacts` listed wiki compiler artifacts; no staged candidate written by dry-run
- R7 -> real `wiki draft` with exported `.env` created `staged-3f6fcea5`; `wiki_compiler_result.json` recorded `status: completed`, `model: openai/gpt-4o-mini`, source pack `docs/engineering/TEST_ARCHITECTURE.md`
- R8 -> corrected `wiki refine --mode supersede --target staged-3f6fcea5 --dry-run` succeeded and returned concrete prompt artifact
- R9 -> Web loopback on `127.0.0.1:8770`: `GET /` -> `200 text/html`; `/api/tasks/9efc0525e0d4`, `/api/knowledge/staged-3f6fcea5`, `/api/tasks/9efc0525e0d4/artifacts` all returned 200; server stopped

R19-008 knowledge-policy handoff fix validation:

- `.venv/bin/python -m pytest tests/integration/cli/test_task_commands.py::test_retrieval_candidate_task_knowledge_requires_policy_review_not_executor_recovery -q` -> `1 passed in 1.53s`
- `.venv/bin/python -m pytest tests/unit/orchestration/test_artifact_writer_module.py::test_handoff_builder_routes_completed_executor_with_failed_knowledge_policy_to_review -q` -> `1 passed in 0.08s`
- `.venv/bin/python -m pytest tests/integration/cli/test_task_commands.py -q` -> `44 passed in 17.45s`
- `.venv/bin/python -m pytest tests/unit/orchestration/test_artifact_writer_module.py -q` -> `8 passed in 0.04s`
- `.venv/bin/python -m pytest tests/unit/orchestration/test_task_report_module.py tests/unit/orchestration/test_retrieval_flow_module.py -q` -> `16 passed in 0.23s`
- smoke base dir -> `/tmp/swl-r19-008-knowledge-policy-handoff`
- smoke task -> `4795c81e0c99`
- pre-capture `task run` -> `4795c81e0c99 completed retrieval=8 execution_phase=analysis_done`
- post-capture `task rerun --from-phase retrieval` -> `4795c81e0c99 waiting_human retrieval=8 execution_phase=analysis_done`
- `task inspect` -> `status: waiting_human`, `execution_lifecycle: completed`, `knowledge_policy_status: failed`, `handoff_status: knowledge_policy_review`, `recommended_path: review`
- `handoff_report.md` -> `contract_kind: knowledge_policy_review`, `executor_status: completed`, `failure_kind: none`, `next_operator_action: Review knowledge_policy_report.md...`
- `checkpoint_snapshot_report.md` -> `checkpoint_state: knowledge_policy_review`, `recovery_semantics: knowledge_policy_review`

本轮文档同步验证:

- `git diff --check` -> passed
- `git status --short --branch` -> `## main...origin/main`;modified `current_state.md`, `docs/active_context.md`, `docs/roadmap.md`;untracked `docs/plans/`(contains `docs/plans/r-entry-real-usage/plan.md`)

Roadmap Direction Gate 同步验证:

- `git diff --check` -> passed
- `git status --short --branch` -> `## main...origin/main [ahead 2]`;modified `docs/active_context.md`, `docs/roadmap.md`
- `wc -l docs/roadmap.md` -> `184 docs/roadmap.md`(低于 300 行上限)

LTO-2 source scoping plan drafting validation:

- `git diff --check` -> passed
- `git status --short --branch` -> `## main...origin/main [ahead 3]`;modified `docs/active_context.md`;untracked `docs/plans/lto-2-retrieval-source-scoping/`;also present unrelated agent/workflow files outside this plan absorption scope
- `wc -l docs/plans/lto-2-retrieval-source-scoping/plan.md docs/active_context.md` -> `232` / `191`

Plan audit absorption validation:

- `git diff --check` -> passed
- `rg` confirmed plan now names `build_task_retrieval_request`, `SOURCE_POLICY_NOISE_LABELS`, `score_breakdown`, and `pytest.mark.eval`

LTO-2 source scoping implementation validation:

- `.venv/bin/python -m pytest tests/unit/orchestration/test_retrieval_flow_module.py -q` -> `12 passed in 0.19s`
- `.venv/bin/python -m pytest tests/unit/orchestration/test_task_report_module.py -q` -> `3 passed in 0.04s`
- `.venv/bin/python -m pytest -m eval tests/eval/test_lto2_retrieval_source_scoping.py -q` -> `1 passed in 0.03s`
- `.venv/bin/python -m pytest tests/integration/cli/test_retrieval_commands.py -q` -> `44 passed in 7.53s`
- `.venv/bin/python -m compileall -q src/swallow tests` -> passed
- `.venv/bin/python -m pytest -q` -> `812 passed,20 deselected in 110.51s`
- `git diff --check` -> passed

LTO-2 source scoping review / closeout validation:

- Claude independent focused tests -> `59 passed in 7.70s`
- Claude eval gate -> `1 passed in 0.02s`
- Claude full pytest -> `812 passed,20 deselected in 139.11s`
- `docs/concerns_backlog.md` -> appended `LTO-2 Source Scoping review follow-ups`
- closeout / PR sync -> `git diff --check` passed
- Human merge -> `d4288a1 LTO-2 Retrieval Source Scoping And Truth Reuse Visibility`

R-entry UX fixes validation:

- `.venv/bin/python -m pytest tests/integration/cli/test_wiki_commands.py::test_wiki_draft_cli_reports_llm_unavailable_without_traceback -q` -> `1 passed in 0.29s`
- `.venv/bin/python -m pytest tests/integration/cli/test_task_commands.py::test_task_staged_points_to_task_knowledge_surface_when_no_global_candidate -q` -> `1 passed in 0.45s`
- `.venv/bin/python -m pytest tests/integration/cli/test_wiki_commands.py -q` -> `6 passed in 1.46s`
- `.venv/bin/python -m pytest tests/integration/cli/test_task_commands.py -q` -> `41 passed in 14.87s`

LTO-4 compressed-flow validation:

- Baseline before LTO-4 edits:
  - `.venv/bin/python -m pytest -q --co 2>&1 | tail -1` -> `802/821 tests collected (19 deselected) in 0.67s`
  - `time .venv/bin/python -m pytest -q 2>&1 | tail -1` -> `802 passed, 19 deselected in 116.89s`; real `1m57.852s`
- M1 CLI command-family split:
  - commits: `d63a880 refactor(tests): split test_cli.py command-family modules`;`79f6695 docs(state): record lto4 m1 test split`
  - `.venv/bin/python -m pytest -q --co 2>&1 | tail -1` -> `802/821 tests collected (19 deselected) in 0.82s`
  - `.venv/bin/python -m pytest tests/integration/cli/test_task_commands.py tests/integration/cli/test_knowledge_commands.py tests/integration/cli/test_route_commands.py tests/integration/cli/test_proposal_commands.py tests/integration/cli/test_synthesis_commands.py tests/integration/cli/test_retrieval_commands.py tests/integration/cli/test_system_commands.py -q` -> `253 passed in 78.09s`
  - test count change: `0` (baseline `802`, current `802`)
- M2 shared builders/assertions helpers:
  - commits: `d20b99d refactor(tests): extract common builders into helpers`;`28f0e8f docs(state): record lto4 m2 helpers`
  - `.venv/bin/python -m pytest tests/unit/test_helpers_builders.py tests/integration/cli/test_task_commands.py tests/integration/cli/test_knowledge_commands.py tests/integration/cli/test_wiki_commands.py -q` -> `121 passed in 49.06s`
  - `.venv/bin/python -m compileall -q tests/helpers tests/unit/test_helpers_builders.py` passed
  - `.venv/bin/python -m pytest -q --co 2>&1 | tail -1` -> `806/825 tests collected (19 deselected) in 0.71s`
  - `git diff --check` passed
  - test count change: `+4` (new helper self-tests only; no test deletion)
- M3 invariant AST guard helper extraction:
  - commits: `ba5d3b1 refactor(tests): consolidate invariant guard helpers`;`97e3073 docs(state): record lto4 m3 guard helpers`
  - `.venv/bin/python -m pytest tests/test_invariant_guards.py -q` -> `41 passed in 6.49s`
  - `.venv/bin/python -m compileall -q tests/helpers/ast_guards.py tests/test_invariant_guards.py` passed
  - `.venv/bin/python -m pytest -q --co 2>&1 | tail -1` -> `806/825 tests collected (19 deselected) in 0.71s`
  - `git diff --check` passed
  - test count change: `0` (baseline after M2 `806`, current `806`)
- M4 conftest fixture entry consolidation + final gate:
  - `.venv/bin/python -m pytest tests/unit/test_helpers_builders.py tests/integration/cli/test_task_commands.py tests/integration/cli/test_knowledge_commands.py tests/integration/cli/test_wiki_commands.py -q` -> `121 passed in 33.93s`
  - `.venv/bin/python -m pytest -q --co 2>&1 | tail -1` -> `806/825 tests collected (19 deselected) in 0.66s`
  - `.venv/bin/python -m compileall -q src/swallow tests/helpers tests/conftest.py` passed
  - `time .venv/bin/python -m pytest -q 2>&1 | tail -1` -> `806 passed, 19 deselected in 131.76s`; real `2m12.909s`
  - `git diff --check` passed
  - test count change: `0` after M3;`+4` vs LTO-4 starting baseline from helper self-tests only

## 当前阻塞项

- 无 code blocker。LTO-2 source scoping 已 merge 到 `main`;3 个 review concerns 已登记为后续项。

## Tag 状态

- 最新已执行 tag: **`v1.9.0`**
- tag target: `d598e58 docs(release): sync v1.9.0 release docs`
- 标记意义: **Wiki Compiler 第二阶段 + Retrieval Quality / Evidence Serving + R-entry-driven Source Scoping / Truth Reuse Visibility 的稳定 checkpoint**。
- pending release tag: `none`

## 当前下一步

1. **[Human]** 审阅 R19-008 narrow fix。
2. **[Human]** 提交并决定是否 merge `fix/r19-008-knowledge-policy-handoff` 回 `main`。
3. **[Codex]** merge 后同步 state;然后继续用 corrected runbook 做下一轮 real usage。

```markdown
compressed_gate:
- active_phase: r-entry-v1.9-real-usage
- active_slice: r19-008 knowledge-policy terminal status / handoff guidance fix
- active_branch: fix/r19-008-knowledge-policy-handoff
- status: r19_008_knowledge_policy_handoff_fix_verified
- latest_completed_phase: lto-2-retrieval-source-scoping
- latest_completed_commit: d4288a1 LTO-2 Retrieval Source Scoping And Truth Reuse Visibility
- latest_history_archive_commit: 795aa4d docs(store): move history plans to archive
- latest_release_tag: v1.9.0 at d598e58 docs(release): sync v1.9.0 release docs
- pending_release_tag: none
- workflow: formal phase plan;plan_audit.md produced and absorbed;implementation complete;Claude review acceptable to merge;merged to main;post-merge state synced;release docs committed;tag complete
- boundary: docs/plans/lto-2-retrieval-source-scoping/plan.md is current plan
- baseline_count: 802/821 collected;19 deselected
- current_count: 806/825 collected;19 deselected
- final_full_pytest: 806 passed, 19 deselected in 131.76s; real 2m12.909s
- r_entry_plan: docs/plans/r-entry-real-usage/plan.md
- findings: docs/plans/r-entry-real-usage/findings.md
- r_entry_v1_9_plan: docs/plans/r-entry-v1.9-real-usage/plan.md
- r_entry_v1_9_findings: docs/plans/r-entry-v1.9-real-usage/findings.md
- phase_plan: docs/plans/lto-2-retrieval-source-scoping/plan.md
- plan_audit: docs/plans/lto-2-retrieval-source-scoping/plan_audit.md
- ux_fixes: wiki llm unavailable CLI hint; task staged task-knowledge hint; env/rerank runbook docs
- next_gate: Human review and commit R19-008 narrow fix
```

## 当前产出物

- `docs/plans/r-entry-real-usage/plan.md`(codex, 2026-05-04, R-entry real usage runbook for design-doc knowledge chain, CLI, UI, nginx/Tailscale smoke, and issue logging)
- `docs/plans/r-entry-real-usage/findings.md`(codex, 2026-05-04, R-entry real usage findings and Direction Gate candidates)
- `src/swallow/adapters/cli_commands/wiki.py`(codex, 2026-05-04, operator-facing LLM unavailable handling for wiki CLI)
- `src/swallow/adapters/cli.py` / `src/swallow/adapters/cli_commands/tasks.py`(codex, 2026-05-04, task staged hint for task-scoped knowledge surface)
- `tests/integration/cli/test_wiki_commands.py` / `tests/integration/cli/test_task_commands.py`(codex, 2026-05-04, regression coverage for R-entry UX fixes)
- `docs/active_context.md`(codex, 2026-05-04, current state and checkpoint cleanup)
- `docs/roadmap.md`(codex, 2026-05-04, LTO-4 complete / R-entry active roadmap sync;LTO-2 Retrieval Source Scoping And Truth Reuse Visibility Direction Gate proposal)
- `current_state.md`(codex, 2026-05-04, recovery checkpoint sync to post-LTO-2 source scoping main state)
- `docs/plans/lto-2-retrieval-source-scoping/plan.md`(codex, 2026-05-04, LTO-2 source scoping / truth reuse visibility phase plan;revised after plan_audit)
- `docs/plans/lto-2-retrieval-source-scoping/plan_audit.md`(claude:design-auditor, 2026-05-04, plan gate audit — has-concerns;0 blockers, 5 concerns, 2 nits)
- `src/swallow/orchestration/models.py` / `src/swallow/orchestration/retrieval_flow.py`(codex, 2026-05-04, declared document request plumbing)
- `src/swallow/knowledge_retrieval/retrieval.py` / `src/swallow/knowledge_retrieval/evidence_pack.py` / `src/swallow/knowledge_retrieval/knowledge_plane.py`(codex, 2026-05-04, source scoping policy and truth reuse visibility helpers)
- `src/swallow/orchestration/task_report.py` / `src/swallow/orchestration/harness.py`(codex, 2026-05-04, truth reuse visibility report and memory surfaces)
- `tests/unit/orchestration/test_retrieval_flow_module.py` / `tests/unit/orchestration/test_task_report_module.py` / `tests/eval/test_lto2_retrieval_source_scoping.py`(codex, 2026-05-04, M1-M4 regression coverage)
- `.agents/workflows/feature.md` / `.agents/workflows/model_review.md`(deleted) / `.agents/claude/rules.md` / `.agents/claude/role.md` / `.agents/codex/rules.md` / `.agents/codex/role.md` / `.agents/shared/rules.md` / `AGENTS.md` / `.codex/session_bootstrap.md`(claude, 2026-05-04, remove model_review gate layer per Human direction)
- `docs/plans/lto-2-retrieval-source-scoping/review_comments.md`(claude, 2026-05-04, PR review — acceptable to merge with 3 concerns;0 blocks)
- `docs/concerns_backlog.md`(claude, 2026-05-04, append LTO-2 Source Scoping review follow-ups Active Open row)
- `docs/roadmap.md`(claude, 2026-05-04, 全面重写 —— 压缩已完成 phase 叙事,Direction Gate 候选与触发条件提到 §三,LTO 表按状态分类;180→151 行)
- `docs/plans/lto-2-retrieval-source-scoping/closeout.md`(codex, 2026-05-04, phase closeout — acceptable to merge with tracked concerns)
- `pr.md`(codex, 2026-05-04, PR body updated with Claude review disposition)
- `docs/active_context.md` / `current_state.md` / `docs/roadmap.md`(codex, 2026-05-04, post-merge state sync for `main@d4288a1`)
- `README.md` / `current_state.md` / `docs/active_context.md` / `docs/roadmap.md`(codex, 2026-05-04, pre-`v1.9.0` release docs sync)
- `current_state.md` / `docs/active_context.md` / `docs/roadmap.md`(codex, 2026-05-04, post-`v1.9.0` tag status sync)
- `docs/plans/r-entry-v1.9-real-usage/plan.md`(codex, 2026-05-05, post-v1.9.0 design-doc real usage runbook)
- `docs/plans/r-entry-v1.9-real-usage/findings.md`(codex, 2026-05-05, findings template for post-v1.9.0 real usage)
- `src/swallow/adapters/cli.py` / `src/swallow/adapters/cli_commands/tasks.py` / `src/swallow/orchestration/task_report.py`(codex, 2026-05-05, R19-001 narrow fix: task document path persistence, operator visibility, retrieval report score breakdown)
- `tests/integration/cli/test_task_commands.py` / `tests/unit/orchestration/test_task_report_module.py`(codex, 2026-05-05, regression coverage for document path plumbing and retrieval report visibility)
- `docs/plans/r-entry-v1.9-real-usage/findings.md`(codex, 2026-05-05, post-fix R-entry continuation results: R19-006 observation and R19-007 runbook drift)
- `src/swallow/knowledge_retrieval/retrieval.py` / `src/swallow/knowledge_retrieval/knowledge_plane.py` / `src/swallow/orchestration/task_report.py`(codex, 2026-05-05, R19-003 truth reuse visibility primary skipped reasons and warning context)
- `tests/unit/orchestration/test_task_report_module.py`(codex, 2026-05-05, regression coverage for R19-003 report wording/counts)
- `src/swallow/application/services/wiki_compiler.py` / `src/swallow/orchestration/artifact_writer.py` / `src/swallow/adapters/cli.py`(codex, 2026-05-05, R19-004 wiki dry-run prompt pack artifact and task artifact index visibility)
- `tests/integration/cli/test_wiki_commands.py` / `tests/unit/orchestration/test_artifact_writer_module.py`(codex, 2026-05-05, regression coverage for wiki dry-run prompt artifact visibility)
- `src/swallow/orchestration/executor.py`(codex, 2026-05-05, R19-002 note-only offline status semantics: explicit offline note-only completes as a no-live-executor run record)
- `tests/integration/cli/test_task_commands.py`(codex, 2026-05-05, regression coverage for R19-002 offline note-only completion)
- `docs/plans/r-entry-v1.9-real-usage/plan.md`(codex, 2026-05-05, R19-007 runbook command drift fix: canonical audit, wiki refine target, and current artifact path)
- `docs/plans/r-entry-v1.9-real-usage/findings.md`(codex, 2026-05-05, after-fixes corrected runbook smoke;records R19-008 open concern and R19-009 observation)
- `src/swallow/orchestration/artifact_writer.py` / `src/swallow/orchestration/harness.py` / `src/swallow/orchestration/orchestrator.py` / `src/swallow/orchestration/checkpoint_snapshot.py`(codex, 2026-05-05, R19-008 knowledge-policy terminal status and handoff guidance)
- `tests/integration/cli/test_task_commands.py` / `tests/unit/orchestration/test_artifact_writer_module.py`(codex, 2026-05-05, regression coverage for R19-008 knowledge policy review semantics)
