---
author: codex
phase: 68
slice: s2-ingestion-raw-material-store
status: review
created_at: 2026-04-30
depends_on:
  - docs/plans/phase68/kickoff.md
  - docs/plans/phase68/breakdown.md
  - docs/plans/phase68/codex_review_notes_s1.md
---

TL;DR: S2 routes local/session ingestion reads through `FilesystemRawMaterialStore` and changes newly persisted local source refs to stable `file://workspace/...` URIs.
Clipboard and operator-note ingestion remain unchanged.

# Phase 68 S2 Codex Review Notes

## Scope

Implemented:

- `run_ingestion_pipeline(...)` now creates a stable source ref with `source_ref_for_file(...)`.
- External session bytes are read through `FilesystemRawMaterialStore`.
- `ingest_local_file(...)` now reads source bytes through `FilesystemRawMaterialStore`.
- `parse_local_file(...)` now accepts bytes plus `source_name`; it no longer opens a `Path` directly.
- New in-workspace local/session ingestion refs are `file://workspace/<relative-path>`.
- Out-of-workspace ingestion inputs keep a standards-compliant absolute file URI.

Unchanged:

- `run_ingestion_bytes_pipeline(...)` keeps caller-provided refs such as `clipboard://auto`.
- `ingest_operator_note(...)` keeps `note://operator`.
- `parse_ingestion_path(...)` remains available for compatibility, but the ingestion pipeline no longer uses it.
- Knowledge Truth schema is unchanged.

## Implementation Notes

S2 preserves filesystem compatibility while changing new persisted source refs:

- before: external session `source_ref` could be a bare absolute path
- before: local file `source_ref` was `file://<absolute-path>`
- after: in-workspace source refs are `file://workspace/<relative-path>`
- after: out-of-workspace source refs fall back to `Path.as_uri()`

The pipeline calls `resolve_raw_material(...)` instead of `raw_store.resolve(...)`. This keeps the public
`RawMaterialStore.resolve(...)` contract intact while avoiding false positives in the existing AST guard that bans
direct `Path.resolve()` calls outside `surface_tools.workspace`.

## Verification

```bash
.venv/bin/python -m pytest tests/test_ingestion_pipeline.py tests/test_raw_material_store.py -q
# 20 passed

.venv/bin/python -m pytest tests/test_raw_material_store.py tests/test_ingestion_pipeline.py \
  tests/test_invariant_guards.py::test_no_absolute_path_in_truth_writes -q
# 21 passed

.venv/bin/python -m pytest tests/test_cli.py -q
# 241 passed, 10 subtests passed

git diff --check
# passed

.venv/bin/python -m pytest -q
# 621 passed, 8 deselected, 10 subtests passed
```

## Review Guidance

Recommended review order:

1. `src/swallow/knowledge_retrieval/ingestion/pipeline.py`
2. `src/swallow/knowledge_retrieval/raw_material.py`
3. `tests/test_ingestion_pipeline.py`
4. `tests/test_cli.py`
5. `docs/active_context.md`

Suggested commit message:

```bash
refactor(phase68-s2): route ingestion through raw material store
```
