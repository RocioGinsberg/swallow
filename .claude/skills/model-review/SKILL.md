---
name: model-review
description: Run Swallow's conditional second-model design review gate after design_auditor and before Human Design Gate. Use only when the project workflow requires or the human explicitly requests a GPT/OpenAI/second-model review of roadmap, kickoff, design_decision, or risk_assessment.
argument-hint: "[phase-dir optional, e.g. docs/plans/phase61]"
---

TL;DR:
Run this after design_audit and before Human Design Gate when second-model review is required.
It writes or skips `docs/plans/<phase>/model_review.md` and updates `docs/active_context.md`.
It never implements code or embeds Codex inside Claude Code.

# Model Review Gate

Use this skill as the Claude-side workflow for `.agents/workflows/model_review.md`.

It is a gate protocol, not an implementation tool. Do not edit source code, tests, `docs/design/*.md`, or Codex-owned implementation files.

## Invocation

Run `/model-review` after `design-auditor` has produced `docs/plans/<phase>/design_audit.md` and before Human Design Gate.

If `$ARGUMENTS` is empty, infer the active phase from `docs/active_context.md`. If `$ARGUMENTS` points to a phase directory, use that directory.

If the current Claude Code session does not list `/model-review`, restart Claude Code after this skill has been committed.

## Required Reads

Read only these files unless a referenced design doc is clearly needed:

1. `.agents/workflows/model_review.md`
2. `docs/active_context.md`
3. `docs/plans/<phase>/kickoff.md`
4. `docs/plans/<phase>/design_decision.md`
5. `docs/plans/<phase>/risk_assessment.md`
6. `docs/plans/<phase>/design_audit.md`
7. `docs/design/INVARIANTS.md`

## Trigger Decision

Set model review to `required` if any condition is true:

- Roadmap direction, phase boundary, or phase priority is uncertain.
- The plan touches `INVARIANTS.md`, `DATA_MODEL.md`, `SELF_EVOLUTION.md`, schema, CLI/API surface, state transition, truth write path, or provider routing policy.
- `design_audit.md` contains `[BLOCKER]` or multiple `[CONCERN]`.
- Human explicitly requested second-model review.

If none apply, update `docs/active_context.md` with:

```markdown
model_review:
- status: skipped
- artifact: none
- reason: no high-risk trigger
```

Do not create extra files for a no-trigger skip unless the human asks for a trace file.

## External Review Rule

If a configured external GPT/OpenAI/second-model channel is available in the current Claude Code environment, use it only for a read-only review packet.

If no such channel is available:

- Do not simulate an external second-model result.
- If model review was optional, record `skipped`.
- If model review was required, record `blocked` and ask Human to either provide an external result, configure a channel, or explicitly skip.

Do not invoke Codex as an implementation plugin inside Claude Code. Codex remains the separate implementation agent after Human Design Gate.

## Review Packet

When required, prepare a compact packet with:

- Phase goal and non-goals.
- Slice/milestone plan.
- Risk assessment summary.
- Design audit findings.
- Specific questions for the external reviewer.
- Relevant invariant anchors, especially any touched truth/control/write-path rules.

Ask the external reviewer for:

- `[BLOCK]` items that must be fixed before Design Gate.
- `[CONCERN]` items that can be accepted with explicit tradeoff.
- Missing tests or acceptance criteria.
- Scope creep or invariant conflicts.

## Output

Write the official output to:

```text
docs/plans/<phase>/model_review.md
```

Use this structure:

```markdown
---
author: claude
phase: <phase-number>
slice: design-gate
status: review
depends_on:
  - docs/plans/<phase>/kickoff.md
  - docs/plans/<phase>/design_decision.md
  - docs/plans/<phase>/risk_assessment.md
  - docs/plans/<phase>/design_audit.md
reviewer: external-model | manual-external | unavailable
verdict: PASS | CONCERN | BLOCK | SKIPPED
---

TL;DR:
<max 3 lines>

# Model Review

## Scope
<what was reviewed>

## Verdict
PASS | CONCERN | BLOCK | SKIPPED

## Findings
- [PASS] ...
- [CONCERN] ...
- [BLOCK] ...

## Claude Follow-Up
<whether design_decision.md / risk_assessment.md must be revised>

## Human Gate Note
<what Human must check before approving design>
```

After writing or skipping, update `docs/active_context.md` with model review status, artifact path, reason, and next workflow step.
