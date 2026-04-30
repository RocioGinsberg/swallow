# CLI Reference

`swl` is the operator-facing CLI for the swallow stateful AI workflow system.

## Global Usage

```bash
swl [--base-dir <path>] <command> ...
```

- `--base-dir`: root directory containing `.swl/`; defaults to the current directory
- Use `swl <command> --help` or `swl <command> <subcommand> --help` for argument-level detail

Top-level commands:

- `audit` — consistency audit policy commands
- `synthesis` — multi-perspective synthesis policy, run, and staging commands
- `route` — route registry, weight, and capability commands
- `task` — task lifecycle, inspection, recovery, and artifact access
- `knowledge` — staged knowledge review, file ingest, and explicit relation management
- `doctor` — environment and storage diagnostics
- `migrate` — file task state backfill into SQLite
- `meta-optimize` — read-only telemetry scan and proposal generation
- `proposal` — operator review/apply for structured proposals
- `note` — capture one operator note directly into staged knowledge
- `ingest` — external session ingestion into staged knowledge
- `serve` — read-only control center API server

## Common Examples

```bash
# Create and run a task
swl task create --title "Design orchestrator" --goal "Tighten harness boundary" --workspace-root .
swl task run <task-id>

# Inspect task state and artifacts
swl task inspect <task-id>
swl task artifacts <task-id>
swl task review <task-id>

# Work the staged knowledge queue
swl knowledge stage-list
swl knowledge stage-inspect <candidate-id>
swl knowledge stage-promote <candidate-id>

# Ingest one local file into staged knowledge
swl knowledge ingest-file docs/notes.md --task-id <task-id>

# Manage explicit knowledge relations
swl knowledge link <source-object-id> <target-object-id> --type related_to
swl knowledge links <object-id>

# Inspect routing and policy surfaces
swl route registry show
swl route policy show
swl route weights show
swl route capabilities show
swl audit policy show

# Review and apply structured proposals
swl proposal review <proposal-bundle> --decision approved
swl proposal apply <review-record>

# Run multi-perspective synthesis
swl synthesis run --task <task-id> --config <config.json>
swl synthesis stage --task <task-id>

# Capture one operator note into staged knowledge
swl note "Remember to keep route overrides explicit" --tag routing

# Run diagnostics
swl doctor
swl doctor sqlite

# Start the read-only dashboard
swl serve --host 127.0.0.1 --port 8000
```

## `swl task`

Primary workbench for task lifecycle, recovery, inspection, and artifact access.

### Lifecycle And Recovery

- `swl task create`
- `swl task planning-handoff`
- `swl task knowledge-capture`
- `swl task run`
- `swl task retry`
- `swl task resume`
- `swl task rerun`
- `swl task acknowledge`

### Queue And Control Views

- `swl task list`
- `swl task queue`
- `swl task attempts`
- `swl task compare-attempts`
- `swl task control`
- `swl task intake`
- `swl task staged`
- `swl task inspect`
- `swl task review`
- `swl task checkpoint`
- `swl task policy`

### Knowledge And Reuse Views

- `swl task knowledge-objects`
- `swl task knowledge-partition`
- `swl task knowledge-index`
- `swl task knowledge-policy`
- `swl task knowledge-review-queue`
- `swl task knowledge-promote`
- `swl task knowledge-reject`
- `swl task knowledge-decisions`
- `swl task canonical-registry`
- `swl task canonical-registry-index`
- `swl task canonical-reuse`
- `swl task canonical-reuse-regression`
- `swl task canonical-reuse-eval`
- `swl task canonical-reuse-evaluate`

### Execution, Retrieval, And Routing Reports

- `swl task semantics`
- `swl task capabilities`
- `swl task consistency-audit`
- `swl task artifacts`
- `swl task summarize`
- `swl task resume-note`
- `swl task validation`
- `swl task compatibility`
- `swl task grounding`
- `swl task retrieval`
- `swl task topology`
- `swl task execution-site`
- `swl task dispatch`
- `swl task handoff`
- `swl task remote-handoff`
- `swl task execution-fit`
- `swl task retry-policy`
- `swl task execution-budget-policy`
- `swl task stop-policy`
- `swl task memory`
- `swl task route`

### JSON Record Views

- `swl task compatibility-json`
- `swl task route-json`
- `swl task topology-json`
- `swl task execution-site-json`
- `swl task dispatch-json`
- `swl task handoff-json`
- `swl task remote-handoff-json`
- `swl task execution-fit-json`
- `swl task retry-policy-json`
- `swl task execution-budget-policy-json`
- `swl task stop-policy-json`
- `swl task checkpoint-json`
- `swl task capabilities-json`
- `swl task semantics-json`
- `swl task knowledge-objects-json`
- `swl task knowledge-partition-json`
- `swl task knowledge-index-json`
- `swl task knowledge-policy-json`
- `swl task knowledge-decisions-json`
- `swl task canonical-registry-json`
- `swl task canonical-registry-index-json`
- `swl task canonical-reuse-json`
- `swl task canonical-reuse-eval-json`
- `swl task canonical-reuse-regression-json`
- `swl task retrieval-json`

## `swl knowledge`

Global staged knowledge and graph-management commands.

- `swl knowledge stage-list`
- `swl knowledge stage-inspect`
- `swl knowledge stage-promote`
- `swl knowledge stage-reject`
- `swl knowledge canonical-audit`
- `swl knowledge ingest-file`
- `swl knowledge link`
- `swl knowledge unlink`
- `swl knowledge links`
- `swl knowledge apply-suggestions`
- `swl knowledge migrate`

Typical uses:

- review staged candidates outside a task run
- ingest markdown/text files into staged knowledge
- create and inspect explicit graph relations
- apply relation suggestions recorded by a completed task
- backfill file-based knowledge into SQLite

## `swl synthesis`

Multi-perspective synthesis policy, execution, and staging commands.

- `swl synthesis policy set`
- `swl synthesis run`
- `swl synthesis stage`

Typical uses:

- update MPS policy values through `apply_proposal`
- run multi-perspective synthesis for an existing task
- stage a synthesis arbitration artifact as a knowledge candidate

## `swl route`

Route policy and dry-run routing tools.

- `swl route registry show`
- `swl route registry apply`
- `swl route policy show`
- `swl route policy apply`
- `swl route weights show`
- `swl route weights apply`
- `swl route capabilities show`
- `swl route capabilities update`
- `swl route select`

Typical uses:

- inspect or apply full route registry metadata
- inspect or apply route selection policy metadata
- inspect current route quality weights
- apply approved route-weight proposals
- inspect or patch capability profiles
- dry-run route selection for an existing task

## `swl audit`

Automatic consistency-audit trigger policy.

- `swl audit policy show`
- `swl audit policy set`

Typical uses:

- inspect whether background consistency audits are enabled
- update degraded-run / token-cost trigger conditions
- change the auditor route

## `swl doctor`

Diagnostics for executor access, storage health, and local stack dependencies.

- `swl doctor`
- `swl doctor executor`
- `swl doctor codex`
- `swl doctor sqlite`
- `swl doctor stack`

Options:

- `--skip-stack` — skip local Docker / WireGuard / proxy health checks

Notes:

- `swl doctor codex` is a deprecated alias for `swl doctor executor`
- plain `swl doctor` runs the default diagnostic flow

## `swl migrate`

Backfill legacy file-based task state into the SQLite store.

Typical usage:

```bash
swl migrate --dry-run
swl migrate --status
swl migrate
```

Use this after upgrading older `.swl/` directories that still rely on file-primary task state.

## `swl meta-optimize`

Read-only telemetry scan that emits optimization proposal bundles from recent task history.

Typical usage:

```bash
swl meta-optimize
swl meta-optimize --last-n 50
```

Use this to generate route-weight or route-capability proposals for operator review.

## `swl proposal`

Structured proposal review/apply flow.

- `swl proposal review`
- `swl proposal apply`

Typical usage:

```bash
swl proposal review <proposal-bundle> --decision approved
swl proposal review <proposal-bundle> --decision rejected --proposal-id <proposal-id> --note "Needs more evidence"
swl proposal apply <review-record>
```

Use this to keep route and policy changes gated, auditable, and reversible.

## `swl ingest`

Ingest external session exports into staged knowledge.

Typical usage:

```bash
swl ingest <export-file>
swl ingest <export-file> --format markdown --dry-run
swl ingest <export-file> --summary
swl ingest --from-clipboard --format chatgpt_json
```

Supported pipelines include ChatGPT, Claude, Open WebUI, and Markdown ingestion surfaces already wired in the repo.

## `swl note`

Capture one operator note directly into staged knowledge.

Typical usage:

```bash
swl note "Keep provider-router defaults owned by provider_router." --tag routing
```

Use this for small operator-authored facts or reminders that should enter the staged knowledge review flow.

## `swl serve`

Run the read-only control center API server and HTML dashboard.

Typical usage:

```bash
swl serve
swl serve --host 127.0.0.1 --port 8000
```

This surface is operator-facing and should not mutate `.swl/`.

## Keeping This Current

This document is a command map, not a replacement for built-in help. When CLI structure changes:

1. update this file in the same slice as the CLI change
2. verify `swl --help`
3. verify the affected `swl <command> --help` output
4. keep argument-level detail in built-in help unless a workflow example benefits from showing the option
