---
author: codex
phase: 68
slice: raw-material-store
status: final
depends_on:
  - docs/plans/phase68/kickoff.md
---

TL;DR: Phase 68 is split into three commit-gated slices: interface/backend, ingestion migration, and artifact evidence normalization.
S1 is the current active slice.

# Phase 68 Breakdown

## S1: Raw Material Interface

Objective:

- Add `swallow.knowledge_retrieval.raw_material`.
- Implement URI parsing and filesystem backend.
- Cover `file://`, `artifact://`, unsupported future schemes, traversal rejection, existence checks, and content
  hashing.

Acceptance:

- `RawMaterialStore` protocol exists.
- `FilesystemRawMaterialStore` reads local files and task artifacts.
- `content_hash(...)` returns deterministic `sha256:<hex>` for filesystem reads.
- Existing behavior remains untouched because no business caller is migrated yet.

Stop gate:

- Human review / manual commit before S2.

## S2: Ingestion Migration

Objective:

- Switch `run_ingestion_pipeline(...)` and `ingest_local_file(...)` to read through the filesystem store.
- Stop writing new absolute-path source refs.
- Keep legacy absolute `file://...` source refs readable.

Acceptance:

- Ingestion tests assert stable `file://workspace/...` or equivalent relative source refs for new writes.
- Clipboard and operator-note ingestion remain unchanged.
- Existing parser behavior is preserved.

Stop gate:

- Human review / manual commit before S3.

## S3: Artifact Evidence Normalization

Objective:

- Normalize legacy `.swl/tasks/<task>/artifacts/<name>` references to `artifact://<task>/<name>` internally.
- Route artifact existence checks through `RawMaterialStore.exists(...)`.
- Keep persisted legacy artifact refs compatible.

Acceptance:

- Librarian artifact-backed knowledge checks still accept legacy refs.
- Tests cover `artifact://...` and legacy `.swl/tasks/...` forms.
- No Knowledge Truth schema change.

Stop gate:

- Human review / manual commit before phase close.
