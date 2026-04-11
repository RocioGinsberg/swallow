---
name: read-repo
description: Use this skill when the task is to understand an unfamiliar repository, find the entrypoint, identify the core modules, or map the main execution path before making changes.
---

# Read Repository

## Purpose

Use this skill to build a reliable architectural map before implementation work.

## When to use

Use this skill when:
- the repository is unfamiliar
- the task asks for architecture understanding
- the task requires locating entrypoints or main flows
- broad changes are being considered and repository context is still weak

Do not use this skill when:
- the task is already narrowly scoped to a known file change
- repository architecture has already been mapped for the current session

## Workflow

1. Read high-signal project files first:
   - `README*`
   - `AGENTS.md`
   - `.codex/context/*`
   - `.codex/phases/*`
   - project manifest files such as `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `Makefile`, `Dockerfile`
2. Scan top-level directories and identify likely core modules.
3. Locate entrypoints and initialization code.
4. Trace one main flow from input to output.
5. Identify configuration, retrieval, execution, state, and artifact boundaries.
6. Distinguish confirmed findings from assumptions.

## Output shape

Prefer this structure:
- repository one-line positioning
- top-level directory roles
- critical files and why they matter
- main execution path
- confirmed findings vs assumptions
- recommended next reading order

## Constraints

- Prefer structure over exhaustive file listing.
- Do not rewrite large sections of README.
- Avoid broad implementation changes until the map is clear.
