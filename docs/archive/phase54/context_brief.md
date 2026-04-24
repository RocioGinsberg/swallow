---
author: claude
phase: 54
slice: context-analysis
status: draft
depends_on: ["docs/roadmap.md", "docs/design/AGENT_TAXONOMY.md"]
---

TL;DR: Phase 53 (v1.0.0) completed the Specialist Agent ecosystem; the system now enters naming cleanup. Brand residuals exist in route names (`http-claude`, `http-gemini`), dialect key (`codex_fim`), file name (`dialect_adapters/codex_fim.py`), model default field (`AuditTriggerPolicy.auditor_route`), and CLI help text. The `[role]/[site]/[authority]/[domain]` format is fully specified in `AGENT_TAXONOMY.md §6` but not yet applied to route names. Risk is low — no functional changes are in scope.

## 变更范围

- **直接影响模块**:
  - `src/swallow/router.py` — route names `http-claude` (line 328), `http-gemini` (line 400); `dialect_hint="codex_fim"` (line 428)
  - `src/swallow/models.py` — `AuditTriggerPolicy.auditor_route` default value `"http-claude"` (lines 532, 557)
  - `src/swallow/dialect_adapters/codex_fim.py` — `DialectSpec.name = "codex_fim"` (line 13); `supported_model_hints` includes `"codex"` (line 15); backward-compat alias `CodexFIMDialect = FIMDialect` (line 59)
  - `src/swallow/dialect_adapters/__init__.py` — exports `CodexFIMDialect` (line 2, 4)
  - `src/swallow/executor.py` — `BUILTIN_DIALECTS` key `"codex_fim"` (line 421); `PlainTextDialect.supported_model_hints` includes `"gemini"` (line 279)
  - `src/swallow/cost_estimation.py` — `LEGACY_MODEL_HINT_ALIASES: {"codex": "fim"}` (line 18); `MODEL_PRICING` key `"gemini"` (line 9)
  - `src/swallow/cli.py` — help text `"http-claude"` (line 1945); `doctor codex` deprecated alias (lines 2134, 3353)

- **间接影响模块**:
  - `src/swallow/router.py` — `LEGACY_ROUTE_ALIASES: {"local-codex": "local-aider", "local-cline": "local-claude-code"}` (lines 44–45); these are already aliased and may be candidates for removal or documentation
  - Tests referencing `codex_fim`, `http-claude`, `CodexFIMDialect` by name (fixture / assertion strings)

## 近期相关变更 (git history)

| Commit | 描述 | 相关模块 |
|--------|------|---------|
| 574707b | merge: Specialist Agent Ecosystem | executor.py, models.py |
| 93481b8 | docs(phase53): absorb review concern and finalize handoff | AGENT_TAXONOMY.md |
| 509f7cd | refactor(phase53): clarify taxonomy semantics | models.py, executor.py |
| ff6a3d8 | feat(phase53): add specialist wrapper agents | executor.py (EXECUTOR_REGISTRY) |
| 5407cc1 | feat(meta-optimizer): add specialist agent lifecycle | meta_optimizer.py |
| 8445867 | feat(router): add route capability profiles | router.py |

## 关键上下文

- `BUILTIN_DIALECTS` in `executor.py` uses `"codex_fim"` as the dict key (line 421). `resolve_dialect_name()` and `resolve_dialect()` look up by this key. Renaming the key requires updating all callers that pass `dialect_hint="codex_fim"` — currently `router.py` line 428 (`http-deepseek` route) and any persisted `TaskState.route_dialect` values in existing SQLite stores.
- `FIMDialect.spec.name = "codex_fim"` is the canonical identity used for dialect resolution. The class was already renamed from `CodexFIMDialect` to `FIMDialect` in a prior phase; `CodexFIMDialect` is now a backward-compat alias at line 59 of `codex_fim.py` and re-exported from `__init__.py`. The file name `codex_fim.py` itself has not been changed.
- `AuditTriggerPolicy.auditor_route` defaults to `"http-claude"` in both the dataclass definition and `from_dict()`. This is a persisted field — existing serialized configs will contain the string `"http-claude"`. Any rename requires a migration or a legacy alias in `from_dict()`.
- `LEGACY_ROUTE_ALIASES` in `router.py` already maps `local-codex → local-aider` and `local-cline → local-claude-code`. These aliases exist for backward compat and are not themselves brand residuals to remove — they are the migration mechanism. Phase 54 should not remove them.
- `cost_estimation.py` uses `"gemini"` as a pricing key and `"codex"` as a legacy alias to `"fim"`. The `"gemini"` key is a model-hint substring match, not a route name — its scope is cost lookup only. The `"codex"` alias is already marked `LEGACY_MODEL_HINT_ALIASES`.
- `cli.py` line 2134 registers `doctor codex` as a deprecated alias for `doctor executor`. Lines 2134 and 3353 are the only two touch points; the alias is already labeled deprecated in help text.
- The `[role]/[site]/[authority]/[domain]` format is defined in `AGENT_TAXONOMY.md §6`. Current route names (`http-claude`, `http-gemini`) use `[transport]-[brand]` format. The taxonomy spec does not mandate route names follow the four-segment format — it applies to entity identity, not route registry keys. The roadmap task is to "clean up brand name residuals", not to rename all routes to four-segment form.

## 风险信号

- `AuditTriggerPolicy.auditor_route = "http-claude"` is a persisted field. Renaming the default without a `from_dict()` fallback will silently break deserialization of existing configs that contain `"http-claude"`.
- `BUILTIN_DIALECTS["codex_fim"]` is used as a lookup key by `resolve_dialect_name()`. Any `TaskState` with `route_dialect = "codex_fim"` stored in SQLite will fail dialect resolution if the key is renamed without a compatibility shim.
- `CodexFIMDialect` alias in `__init__.py` may be imported by external test fixtures or user configs outside `src/swallow/`. Removing it without a deprecation cycle is a breaking change for any downstream that imports it by name.
- `http-gemini` route references `model_hint="gemini-2.5-pro"` — the model hint string itself is not a brand residual in the taxonomy sense; it is a concrete API model identifier and should not be changed as part of this phase.
