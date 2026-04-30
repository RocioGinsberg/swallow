---
author: codex
phase: 68
slice: s3-artifact-evidence-normalization
status: review
created_at: 2026-04-30
depends_on:
  - docs/plans/phase68/kickoff.md
  - docs/plans/phase68/breakdown.md
  - docs/plans/phase68/codex_review_notes_s1.md
  - docs/plans/phase68/codex_review_notes_s2.md
---

TL;DR: S3 routes librarian artifact evidence existence checks through `FilesystemRawMaterialStore`.
Legacy `.swl/tasks/...` refs and new `artifact://...` refs are both accepted without changing persisted Knowledge Truth schema.

# Phase 68 S3 Codex Review Notes

## Scope

Implemented:

- Replaced direct `(base_dir / artifact_ref).exists()` in `librarian_executor`.
- Added internal normalization from legacy `.swl/tasks/<task_id>/artifacts/<path>` to `artifact://<task_id>/<path>`.
- Accepted already-normalized `artifact://...` refs.
- Preserved `file://...` artifact refs for compatibility.
- Preserved existing persisted `artifact_ref` strings; this slice only normalizes for existence checks.
- Added a librarian test proving `artifact://<task_id>/evidence.md` can back promotion-ready evidence.

Out of scope:

- No Knowledge Truth schema changes.
- No canonical key rewrite.
- No mass migration of existing `artifact_ref` values.
- No retrieval workspace-scan refactor.

## Implementation Notes

The S3 boundary is deliberately small:

- `artifact_ref` remains the user/data-facing evidence pointer.
- The librarian only converts it to a raw material source ref at validation time.
- Legacy `.swl/tasks/...` refs continue to pass.
- New `artifact://...` refs can be used without adding another filesystem path check.

This keeps Candidate O's storage abstraction honest while avoiding a schema or data migration phase.

## Verification

```bash
.venv/bin/python -m pytest tests/test_librarian_executor.py tests/test_raw_material_store.py -q
# 16 passed

.venv/bin/python -m pytest tests/test_invariant_guards.py::test_no_absolute_path_in_truth_writes -q
# 1 passed

git diff --check
# passed

.venv/bin/python -m pytest -q
# 622 passed, 8 deselected, 10 subtests passed
```

## Review Guidance

Recommended review order:

1. `src/swallow/surface_tools/librarian_executor.py`
2. `tests/test_librarian_executor.py`
3. `docs/plans/phase68/codex_review_notes_s3.md`
4. `docs/active_context.md`
5. `current_state.md`

Suggested commit message:

```bash
refactor(phase68-s3): normalize artifact raw material refs
```
