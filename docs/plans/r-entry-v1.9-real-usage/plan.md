---
author: codex
phase: r-entry-v1.9-real-usage
slice: design-doc-flow-runbook
status: final
depends_on:
  - docs/active_context.md
  - current_state.md
  - docs/roadmap.md
  - docs/plans/r-entry-real-usage/findings.md
  - docs/plans/lto-2-retrieval-source-scoping/closeout.md
---

TL;DR:
This is a post-v1.9.0 real-usage runbook, not a development phase.
Use Swallow's own design documents to exercise retrieval source scoping, truth reuse visibility, Wiki Compiler authoring, and CLI/Web operator flows.
Record findings in `findings.md`; do not fix code inside this runbook.

# R-entry v1.9 Real Usage Runbook

## 0. Purpose

This runbook validates whether the `v1.9.0` checkpoint is useful in a realistic operator workflow.

The previous R-entry run proved that the local chain could run and exposed the source-scoping gap. `v1.9.0` fixed that gap at the product layer. This run asks a different question:

> Can an operator use Swallow's design documents as real working material and understand retrieval, truth reuse, Wiki authoring, and UI state without model memory or hidden context?

## 1. Status And Scope

This is not a formal phase:

- no feature branch required
- no `plan_audit.md`
- no PR review
- no closeout
- no release tag
- no code changes during the run

Allowed outputs:

- `docs/plans/r-entry-v1.9-real-usage/findings.md`
- optional command transcript under `$BASE/notes/`
- optional follow-up Direction Gate recommendation in `docs/active_context.md`

Non-goals:

- no Dockerfile
- no auth/multi-user/public-internet semantics
- no `swl serve` binding to `0.0.0.0` or a Tailscale IP
- no Graph RAG
- no schema migration
- no vector-index overhaul
- no chunk strategy redesign unless real output proves it is needed

## 2. Environment

Run from repository root:

```bash
export WORKSPACE="$PWD"
export BASE=/tmp/swl-r-entry-v1.9-real-usage
export SWL=".venv/bin/swl"

rm -rf "$BASE"
mkdir -p "$BASE/notes"
```

If `swl` is installed globally and preferred:

```bash
export SWL="swl"
```

Load local provider configuration only if you intend to run LLM-backed Wiki drafting, embedding, or dedicated rerank:

```bash
set -a
source .env
set +a
```

Expected provider/rerank shape for OpenRouter rerank:

```bash
export SWL_RETRIEVAL_RERANK_ENABLED=true
export SWL_RETRIEVAL_RERANK_MODEL=cohere/rerank-v3.5
export SWL_RETRIEVAL_RERANK_URL=https://openrouter.ai/api/v1/rerank
export SWL_RETRIEVAL_RERANK_API_KEY="$OPENROUTER_API_KEY"
```

Notes:

- Current implementation does not auto-load `.env`; the shell environment must contain the variables.
- Use `.venv` unless you intentionally want to test the installed CLI.
- `$BASE` is disposable and should not be inside the repo.

## 3. R0 Preflight

Commands:

```bash
git status --short --branch
git show --no-patch --decorate --oneline HEAD
git tag --points-at HEAD
$SWL doctor --skip-stack
$SWL --base-dir "$BASE" migrate --status
```

Expected:

- branch is `main`
- HEAD is at or after `d598e58 docs(release): sync v1.9.0 release docs`
- `v1.9.0` points at the release-docs commit
- CLI starts without traceback
- migration status is readable

Stop if:

- CLI cannot start
- migration status errors before any test data exists
- working tree has unexplained code changes

Record issues:

```bash
cat >> "$BASE/notes/r-entry-v1.9-issues.md" <<'EOF'
## R0 issue

- command:
- expected:
- actual:
- likely surface:
EOF
```

## 4. R1 Design Document Set

Use a small but meaningful declared source set:

```bash
export DOC_INVARIANTS="$WORKSPACE/docs/design/INVARIANTS.md"
export DOC_KNOWLEDGE="$WORKSPACE/docs/design/KNOWLEDGE.md"
export DOC_HARNESS="$WORKSPACE/docs/design/HARNESS.md"
export DOC_PROVIDER="$WORKSPACE/docs/design/PROVIDER_ROUTER.md"
export DOC_TEST_ARCH="$WORKSPACE/docs/engineering/TEST_ARCHITECTURE.md"
export DOC_ADAPTER="$WORKSPACE/docs/engineering/ADAPTER_DISCIPLINE.md"

ls -lh \
  "$DOC_INVARIANTS" \
  "$DOC_KNOWLEDGE" \
  "$DOC_HARNESS" \
  "$DOC_PROVIDER" \
  "$DOC_TEST_ARCH" \
  "$DOC_ADAPTER"
```

Use the first four docs for retrieval source-scoping tests. Use the engineering docs for Wiki Compiler and CLI/Web workflow tests.

## 5. R2 Task With Declared Source Scope

Create a task that explicitly declares the design documents retrieval should prefer:

```bash
TASK_ID=$($SWL --base-dir "$BASE" task create \
  --title "R-entry v1.9 design-doc retrieval flow" \
  --goal "Use declared design documents to explain Swallow knowledge truth and retrieval serving boundaries." \
  --workspace-root "$WORKSPACE" \
  --executor note-only \
  --route-mode offline \
  --document-paths "$DOC_INVARIANTS" \
  --document-paths "$DOC_KNOWLEDGE" \
  --document-paths "$DOC_HARNESS" \
  --document-paths "$DOC_PROVIDER" \
  --constraint "Prefer declared design documents over generated metadata or archived phase history." \
  --constraint "Do not auto-promote knowledge; canonical writes require operator review." \
  --acceptance-criterion "Retrieval report shows declared document priority and truth reuse visibility." \
  --priority-hint "Surface source-scoping and truth-reuse issues clearly.")

echo "$TASK_ID"
```

Inspect:

```bash
$SWL --base-dir "$BASE" task inspect "$TASK_ID"
$SWL --base-dir "$BASE" task intake "$TASK_ID"
$SWL --base-dir "$BASE" task control "$TASK_ID"
```

Observe:

- Does `task inspect` show document paths clearly?
- Does `task intake` make the source boundary easier to review than `inspect`?
- Does `task control` explain the next operator action?

Finding triggers:

- document paths hidden or hard to audit
- control surface too noisy
- task id output not shell-friendly

## 6. R3 Retrieval Source Scoping

Run the task enough to produce retrieval artifacts. Use the normal route for this repo. If `note-only` does not invoke retrieval in your path, use the closest retrieval-producing CLI path available in the current build.

Suggested commands:

```bash
$SWL --base-dir "$BASE" task run "$TASK_ID"
$SWL --base-dir "$BASE" task artifacts "$TASK_ID"
```

Then inspect generated artifacts:

```bash
ARTIFACT_DIR="$BASE/artifacts/$TASK_ID"
find "$ARTIFACT_DIR" -maxdepth 2 -type f | sort

sed -n '1,220p' "$ARTIFACT_DIR/retrieval_report.md"
sed -n '1,220p' "$ARTIFACT_DIR/task_summary.md" 2>/dev/null || true
sed -n '1,220p' "$ARTIFACT_DIR/memory.md" 2>/dev/null || true
```

Observe in `retrieval_report.md`:

- top hits should mostly come from declared docs
- `score_breakdown` should include `declared_document_priority` where applicable
- generated/archive/build-cache candidates should show downgrade signals when present
- `Truth Reuse Visibility` should appear
- task/canonical knowledge should be listed as considered/matched/skipped/absent where applicable

Finding triggers:

- declared docs do not dominate when they should
- generated/archive/build-cache still dominates top hits
- `declared_document_priority` is present but too strong, hiding more relevant truth
- report says `reused_knowledge_count=0` without an operator-understandable reason
- truth reuse counts are confusing or appear double-counted

## 7. R4 Task Knowledge Truth Reuse

Create task-scoped knowledge to test visibility and reuse:

```bash
$SWL --base-dir "$BASE" task knowledge-capture "$TASK_ID" \
  --knowledge-item "Truth before retrieval: Swallow defines knowledge truth objects before retrieval and does not let vector or full-text retrieval define the knowledge architecture." \
  --knowledge-stage candidate \
  --knowledge-source "operator:r-entry-v1.9" \
  --knowledge-retrieval-eligible \
  --knowledge-canonicalization-intent review

$SWL --base-dir "$BASE" task staged --status all --task "$TASK_ID"
```

Run a related task or rerun the current one:

```bash
$SWL --base-dir "$BASE" task rerun "$TASK_ID" || $SWL --base-dir "$BASE" task run "$TASK_ID"
sed -n '1,260p' "$ARTIFACT_DIR/retrieval_report.md"
```

Observe:

- task knowledge should be considered
- if it is skipped, reason should be understandable
- counts should not imply a false total if categories are signal counts

Finding triggers:

- task knowledge exists but visibility says absent
- skipped reason is not actionable
- reason counts look like a partition but are actually overlapping signals

## 8. R5 Canonical Truth Reuse

If you already have a known canonical object in this `$BASE`, use it. Otherwise promote a small staged item only if you are comfortable exercising the operator promote path.

Discovery:

```bash
$SWL --base-dir "$BASE" knowledge stage-list --all
$SWL --base-dir "$BASE" knowledge list --status active 2>/dev/null || true
```

If a relevant active canonical item exists, run a related task and inspect `Truth Reuse Visibility`.

Observe:

- canonical object considered count
- matched count
- skipped reasons
- whether policy/status/query filtering is visible

Finding triggers:

- active canonical item is silently filtered
- only `query_no_match` appears even when policy/status filtering is likely
- canonical object appears in one CLI surface but not retrieval visibility

## 9. R6 Wiki Compiler Dry Run

Start with no LLM call:

```bash
$SWL --base-dir "$BASE" wiki draft \
  --task-id "$TASK_ID" \
  --topic "Test Architecture" \
  --source-ref "file://workspace/docs/engineering/TEST_ARCHITECTURE.md" \
  --dry-run

$SWL --base-dir "$BASE" task artifacts "$TASK_ID"
find "$BASE/artifacts/$TASK_ID" -maxdepth 2 -type f | sort
```

Observe:

- source pack anchors are inspectable
- dry-run tells you what would be sent to the specialist
- no traceback when provider config is absent

Finding triggers:

- dry-run artifact is hard to locate
- source anchors lack enough preview/context
- CLI suggests real draft when LLM config is unavailable

## 10. R7 Wiki Compiler Real Draft

Only run this if provider env is loaded and you intentionally want a real LLM call:

```bash
$SWL --base-dir "$BASE" wiki draft \
  --task-id "$TASK_ID" \
  --topic "Test Architecture" \
  --source-ref "file://workspace/docs/engineering/TEST_ARCHITECTURE.md"

$SWL --base-dir "$BASE" knowledge stage-list --all
```

Then inspect staged candidate details using the current CLI-supported path.

Observe:

- staged candidate preserves `wiki_mode`
- source pack / rationale / relation metadata are visible
- candidate text is reviewable, not too large or too vague

Finding triggers:

- LLM unavailable message is unclear
- staged candidate metadata is insufficient for review
- source pack cannot be traced back to document sections

## 11. R8 Governed Supersede / Derived Evidence

Use only if R7 produced a candidate and you have a safe target. This test is about operator ergonomics, not quantity.

Suggested path:

```bash
$SWL --base-dir "$BASE" wiki refine \
  --task-id "$TASK_ID" \
  --topic "Test Architecture" \
  --source-ref "file://workspace/docs/engineering/TEST_ARCHITECTURE.md" \
  --mode supersede \
  --dry-run
```

If you run a real refine and later promote/reject, record:

- whether supersede target is explicit
- whether governed apply ownership is clear
- whether derived evidence can be traced
- whether confirmation notices are structured enough

Finding triggers:

- operator cannot tell what will be superseded
- evidence objectization is opaque
- promote/reject instructions require reading code

## 12. R9 Web Control Center Smoke

Start local server on loopback only:

```bash
$SWL --base-dir "$BASE" serve --host 127.0.0.1 --port 8765
```

In another shell:

```bash
curl -I http://127.0.0.1:8765/
```

Inspect in browser:

- task list/detail
- artifacts
- staged knowledge
- knowledge browse if populated
- action buttons and eligibility

Observe:

- Web shows same truth as CLI
- no write action bypasses governance functions
- long-running authoring action behavior is understandable

Finding triggers:

- CLI and Web disagree
- action is available when backend says ineligible
- missing artifact links
- task-scoped staged knowledge is hard to find

## 13. R10 Optional Host Nginx + Tailscale Smoke

Only if you want personal-device viewing. Keep `swl serve` on loopback.

Example nginx shape:

```nginx
server {
    listen 10080;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Validate from the host:

```bash
curl -I http://127.0.0.1:10080/
```

Validate from another Tailscale device using the host's Tailscale IP/name.

Boundaries:

- do not bind `swl serve` to `0.0.0.0`
- do not treat this as multi-user or public deployment
- do not add auth in this runbook

Finding triggers:

- static assets fail behind proxy
- links assume localhost
- WebSocket/SSE behavior breaks if used by current UI
- nginx/Tailscale steps are too fragile to document

## 14. Findings Format

Record each issue in `findings.md` with this shape:

```markdown
## R19-001 Short Title

- status: open | resolved | deferred | observation
- severity: blocker | concern | nit | observation
- surface: retrieval | truth-reuse | wiki | cli | web | nginx | config | docs
- task_id:
- command:
- expected:
- actual:
- evidence:
  - artifact:
  - report section:
  - log excerpt:
- likely next direction:
  - LTO-2 retrieval policy tuning
  - Wiki Compiler stage 3
  - D2 LTO-5 driven ports
  - docs/config hygiene
  - no phase; operator note only
- notes:
```

## 15. Direction Gate Rules

Do not open a new phase just because a finding exists.

Open `LTO-2 retrieval policy tuning` only if real output shows one of:

- declared document priority is too strong or too weak
- generated/archive/build-cache noise still dominates
- truth reuse visibility is present but not understandable
- canonical/task knowledge filtering reasons are incomplete or misleading

Open `Wiki Compiler stage 3` only if real authoring shows one of:

- supersede review is hard to trust
- source pack/evidence trace is hard to inspect
- file upload / durable runner / graph view becomes a real operator need

Open `D2 LTO-5 Driven Ports` only if real testing/adapter work shows:

- application boundaries are hard to mock
- a second adapter implementation is blocked
- injection complexity is now the main bottleneck

Otherwise continue R-entry and keep findings as observations.

## 16. Completion Criteria

This runbook is complete when:

- at least one retrieval-producing task has been run with declared design docs
- `retrieval_report.md` has been inspected for source scoping and truth reuse visibility
- at least one Wiki Compiler dry-run has been executed
- CLI/Web truth consistency has been checked, or explicitly deferred with reason
- `findings.md` has enough evidence to support either "continue real usage" or a specific next phase

