# Current Agent State

## Purpose

This file tracks the implementation status of the repository itself so work can resume quickly if the terminal session is interrupted.

## Current Status

- phase: Phase 0 CLI bootstrap
- overall state: runnable, naming-consistent, and using a narrow Codex executor adapter
- last checked: 2026-04-05
- verification:
  - `python3 -m unittest discover -s tests`
  - `PYTHONPATH=src python3 -m ai_workflow.cli --help`
  - `AIWF_EXECUTOR_TIMEOUT_SECONDS=10 PYTHONPATH=src python3 -m ai_workflow.cli --base-dir /tmp/aiwf-exec-real task run <task-id>`

## Completed

- Added a Python package under `src/ai_workflow/`.
- Added a minimal CLI with:
  - `swl task create`
  - `swl task run`
  - `swl task summarize`
  - `swl task resume-note`
- Added explicit modules for:
  - orchestrator
  - harness runtime
  - retrieval
  - state/event/artifact storage
- Updated the main README files with quickstart and CLI shape.
- Unified the repo and package references around `ai_workflow`.
- Switched the documented test command to `unittest` so it matches the current dependency-light setup.
- Added a narrow `codex exec` adapter with:
  - mock mode for tests
  - timeout handling
  - executor prompt/output artifacts
  - terminal failure recording when executor runs stall or fail

## Current Behavior

- Tasks are stored under `.swl/tasks/<task-id>/`.
- The run loop performs:
  - retrieval
  - executor prompt construction
  - `codex exec` or mock execution
  - summary artifact generation
  - resume note artifact generation
- Failed executor runs now end in `status=failed` instead of leaving the task stuck in `running`.

## Known Issues

- A real `codex exec` run can still time out in this environment, so the adapter is structurally correct but not yet operationally reliable.
- The package metadata and CLI help text still describe the project as a Phase 0 bootstrap, which is correct for now but should be revised once the first real executor is integrated.

## Next Resume Step

1. Re-run the test suite.
2. Verify the editable install exposes the `swl` entrypoint correctly.
3. Improve live `codex exec` reliability or add a resumable execution strategy.
4. Update this file after each substantial code change.

## Resume Command

Use this first after reopening the terminal:

```bash
cd /home/rocio/projects/ai-workflow
sed -n '1,220p' current_state.md
```
