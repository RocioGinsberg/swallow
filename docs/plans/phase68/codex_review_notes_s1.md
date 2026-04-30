---
author: codex
phase: 68
slice: s1-raw-material-interface
status: review
created_at: 2026-04-30
depends_on:
  - docs/plans/phase68/kickoff.md
  - docs/plans/phase68/breakdown.md
  - docs/design/KNOWLEDGE.md
---

TL;DR: S1 adds `swallow.knowledge_retrieval.raw_material` with URI parsing, a `RawMaterialStore` protocol, filesystem-backed `file://` / `artifact://` resolution, content hashing, and focused tests.
No business caller is migrated yet.

# Phase 68 S1 Codex Review Notes

## Scope

Implemented:

- `RawMaterialStore` protocol with `resolve`, `exists`, and `content_hash`.
- `RawMaterialRef` parsed representation.
- URI parsing for backend-independent `source_ref` strings.
- `FilesystemRawMaterialStore` as the only concrete backend for this phase.
- Stable source-ref helper for workspace files.
- Stable source-ref helper for task artifacts.
- Legacy `.swl/tasks/<task_id>/artifacts/<artifact_path>` to `artifact://<task_id>/<artifact_path>` conversion.
- Explicit exceptions for malformed refs and unsupported schemes.

Out of scope for S1:

- No ingestion migration.
- No librarian artifact-check migration.
- No retrieval workspace-scan migration.
- No object storage client implementation.
- No Knowledge Truth schema change.

## Implementation Notes

`file://` handling supports two forms:

- New stable workspace-relative refs, for example `file://workspace/docs/note.md`.
- Legacy absolute file URIs, for example `file:///tmp/source.md`.

`artifact://` handling maps to local task artifact storage through existing `.swl` path helpers:

- `artifact://task-abc/report.md`
- `artifact://task-abc/nested/report.md`

Traversal is rejected for relative filesystem and artifact refs. Unsupported future schemes such as `s3://`, `minio://`,
and `oss://` are parsed as URI schemes but the filesystem store raises `UnsupportedRawMaterialScheme`; this avoids
pretending object storage is implemented.

`content_hash(...)` returns deterministic `sha256:<hex>` for filesystem-backed reads.

The implementation routes path absolutization through `swallow.surface_tools.workspace.resolve_path(...)` so the
existing `test_no_absolute_path_in_truth_writes` invariant guard remains intact.

## Verification

```bash
.venv/bin/python -m pytest tests/test_raw_material_store.py -q
# 10 passed

.venv/bin/python -m pytest tests/test_raw_material_store.py tests/test_ingestion_pipeline.py \
  tests/test_librarian_executor.py -q
# 24 passed

git diff --check
# passed

git diff -- docs/design
# no output

.venv/bin/python -m pytest -q
# 620 passed, 8 deselected, 10 subtests passed
```

## Review Guidance

Recommended review order:

1. `src/swallow/knowledge_retrieval/raw_material.py`
2. `tests/test_raw_material_store.py`
3. `docs/plans/phase68/kickoff.md`
4. `docs/plans/phase68/breakdown.md`
5. `docs/active_context.md`

Suggested commit message:

```bash
feat(phase68-s1): add raw material store interface
```
