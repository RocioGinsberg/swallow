---
author: codex
phase: 68
slice: closeout
status: final
created_at: 2026-04-30
depends_on:
  - docs/plans/phase68/kickoff.md
  - docs/plans/phase68/breakdown.md
  - docs/plans/phase68/codex_review_notes_s1.md
  - docs/plans/phase68/codex_review_notes_s2.md
  - docs/plans/phase68/codex_review_notes_s3.md
---

TL;DR: Phase 68 Candidate O is implemented as a narrow Raw Material Store boundary.
It adds the interface/backend, moves ingestion reads to the store, and normalizes librarian artifact evidence checks without schema changes.
Merge order remains Phase 67 first, then Phase 68.

# Phase 68 Closeout

## Result

Phase 68 implemented Candidate O: Storage Backend Independence for the Raw Material Layer.

Completed slices:

- S1: `RawMaterialStore` protocol, URI parsing, filesystem backend, content hashing, focused tests.
- S2: ingestion migration to `FilesystemRawMaterialStore` and stable `file://workspace/...` source refs.
- S3: librarian artifact evidence checks through raw material refs, accepting both legacy `.swl/tasks/...` and `artifact://...`.

## Boundary Held

No changes were made to:

- `docs/design/INVARIANTS.md`
- `docs/design/DATA_MODEL.md`
- `docs/design/KNOWLEDGE.md`
- Knowledge Truth schema
- retrieval source type semantics
- real S3 / MinIO / OSS clients

The implementation keeps object storage future-ready without pretending object storage exists today.

## Implementation Summary

Added:

- `src/swallow/knowledge_retrieval/raw_material.py`
- `tests/test_raw_material_store.py`

Changed:

- `src/swallow/knowledge_retrieval/ingestion/pipeline.py`
- `src/swallow/surface_tools/librarian_executor.py`
- `tests/test_ingestion_pipeline.py`
- `tests/test_librarian_executor.py`
- `tests/test_cli.py`

Operational behavior:

- New in-workspace ingestion source refs now use stable URI form such as `file://workspace/session.md`.
- Out-of-workspace ingestion inputs use standards-compliant absolute file URIs.
- Clipboard and operator-note ingestion refs remain unchanged.
- Legacy artifact refs remain valid.
- `artifact://<task_id>/<artifact_path>` can now back librarian promotion-ready evidence.

## Verification

Final verification:

```bash
git diff --check
# passed

git diff -- docs/design
# no output

.venv/bin/python -m compileall -q src/swallow
# passed

.venv/bin/python -m pytest -q
# 622 passed, 8 deselected, 10 subtests passed
```

Slice verification summaries:

- S1 full pytest: `620 passed, 8 deselected, 10 subtests passed`
- S2 full pytest: `621 passed, 8 deselected, 10 subtests passed`
- S3 full pytest: `622 passed, 8 deselected, 10 subtests passed`

## Merge Notes

Phase 68 is stacked on top of Phase 67 in this workspace.

Required merge order:

1. Merge Phase 67 first.
2. Rebase or retarget Phase 68 if needed.
3. Merge Phase 68 after the Phase 67 merge is visible on `main`.

Do not merge Phase 68 before Phase 67, or the Phase 68 PR will include Phase 67 commits.

## Follow-Up

Candidate O intentionally did not implement:

- object storage backends
- retrieval source collection abstraction
- artifact ref mass migration
- Knowledge Truth schema changes

Those should remain future phase decisions, not Phase 68 cleanup.
