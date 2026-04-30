---
author: codex
phase: 68
slice: raw-material-store
status: final
depends_on:
  - docs/roadmap.md
  - docs/design/KNOWLEDGE.md
  - docs/plans/phase67/closeout.md
---

TL;DR: Phase 68 implements Candidate O as a narrow Raw Material Store boundary.
It introduces URI parsing and a filesystem-backed `RawMaterialStore`, then migrates ingestion and artifact evidence checks without changing Knowledge Truth schema.
Object storage clients remain out of scope.

# Phase 68 Kickoff: Raw Material Store Boundary

## Goal

Implement Candidate O from `docs/roadmap.md`: Storage Backend Independence for Raw Material Layer.

The phase turns the storage-abstraction contract already described in `docs/design/KNOWLEDGE.md` into code:

- `RawMaterialStore.resolve(source_ref) -> bytes`
- `RawMaterialStore.exists(source_ref) -> bool`
- `RawMaterialStore.content_hash(source_ref) -> str`
- URI parsing for `file://` and `artifact://`
- filesystem backend as the only real backend in this phase

## Non-Goals

- Do not add real S3 / MinIO / OSS clients.
- Do not change Knowledge Truth schema.
- Do not add retrieval source types for storage backends.
- Do not migrate every filesystem read in the repository.
- Do not move `.swl` truth layout helpers into the raw material abstraction.

## Implementation Boundary

Candidate O is about raw bytes / source material access, not general local file IO.

In scope:

- source URI parsing
- local file raw material reads
- task artifact raw material reads
- content hashing
- ingestion source refs
- artifact evidence existence checks

Out of scope:

- task state / event / SQLite truth storage
- CLI report printing
- web static file reads
- provider route JSON files
- test fixture reads
- workspace scan enumeration for retrieval

## Slice Plan

- S1: Add raw material interface, URI parser, filesystem backend, and tests.
- S2: Route ingestion local-file/session reads through `RawMaterialStore`; new source refs become stable URI strings.
- S3: Normalize artifact evidence references and use `RawMaterialStore.exists(...)` for artifact-backed knowledge
  checks.

## Commit Gates

Each slice should stop at a Human review / manual commit gate.

Recommended branch:

- `feat/phase68-raw-material-store`

Recommended commit messages:

- `feat(phase68-s1): add raw material store interface`
- `refactor(phase68-s2): route ingestion through raw material store`
- `refactor(phase68-s3): normalize artifact raw material refs`

## Verification

Minimum verification per slice:

- focused tests for changed modules
- `git diff --check`
- full pytest at phase close
