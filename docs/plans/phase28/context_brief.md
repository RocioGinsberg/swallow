---
author: gemini
phase: 28
slice: context_brief
status: draft
depends_on: [docs/plans/phase27/closeout.md, docs/plans/phase28/design_preview.md]
---

## TL;DR
Phase 28 will establish the **Knowledge Promotion & Refinement Baseline**, enabling the transition of staged knowledge candidates to the canonical registry through an operator-driven workflow. This phase focuses on building CLI commands for managing staged knowledge, implementing the promotion logic, and ensuring knowledge refinement and conflict resolution.

---

## 1. Phase Objective

This phase aims to create a robust mechanism for promoting staged knowledge candidates into the canonical knowledge registry. By introducing operator-facing commands and automated checks, we will ensure that the system's long-term memory grows with verified, refined, and deduplicated knowledge, directly supporting the **Self-Evolution** mandate of the architecture.

## 2. Scope

### Primary Track: Track 2 (Retrieval / Memory)

-   **Knowledge Promotion Workflow:** Implement the core logic for promoting `StagedCandidate` objects to `CanonicalRecord`.
-   **Operator Control Surface:** Develop CLI commands (`task staged`, `task promote`) for listing, reviewing, and managing staged knowledge candidates.
-   **Knowledge Refinement:** Allow for basic text refinement or summarization during the promotion process.
-   **Deduplication & Supersede:** Enhance the promotion process to leverage Phase 26's audit capabilities, automatically identifying and handling potential conflicts and superseded records.

### Secondary Track: Track 5 (Workbench / UX)

-   **CLI Command Integration:** Ensure the new `task staged` and `task promote` commands are well-integrated into the CLI, providing a clear and usable interface for operators.
-   **Information Display:** Improve the visibility of staged knowledge status and promotion outcomes within the CLI.

## 3. Key Goals

-   Implement the `task staged` command to list and filter pending knowledge candidates.
-   Implement the `task promote <candidate_id>` command to initiate the promotion process.
-   Develop the backend logic to convert a `StagedCandidate` into a `CanonicalRecord`.
-   Integrate refinement capabilities during promotion, allowing for minor text adjustments.
-   Ensure `CanonicalRecord` creation respects existing deduplication and supersede rules, leveraging `canonical_registry.py` logic.
-   Update the status of promoted `StagedCandidate` objects to reflect their canonicalization.

## 4. Non-Goals

-   **Automated AI Promotion:** This phase focuses on operator-driven promotion, not automated decision-making by AI agents.
-   **Semantic Vector Deduplication:** While canonical records will be checked for key-based conflicts, advanced semantic vector deduplication is out of scope for this phase.
-   **Complex Agentic RAG Integration:** Direct integration with dynamic retrieval during task execution is not part of this phase's scope.

## 5. Dependencies

-   `docs/plans/phase27/closeout.md`: Provides the baseline of completed work from the previous phase.
-   `docs/plans/phase28/design_preview.md`: Outlines the strategic direction and goals for this phase.
-   Existing modules in `src/swallow/staged_knowledge.py`, `src/swallow/canonical_registry.py`, and `src/swallow/store.py` will be extended.
