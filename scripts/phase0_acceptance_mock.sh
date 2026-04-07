#!/usr/bin/env bash

set -euo pipefail

cd /home/rocio/projects/swallow

. ./venv/.venv-phase0-acceptance/bin/activate 2>/dev/null || true

python3 -m unittest discover -s tests

python3 -m venv .venv-phase0-acceptance
. ./venv/.venv-phase0-acceptance/bin/activate
python -m pip install -e .

mkdir -p /tmp/swallow-phase0-acceptance
cat > /tmp/swallow-phase0-acceptance/notes.md <<'EOF'
# Phase 0 Acceptance Notes

The task should validate:
- truthful state.json lifecycle
- append-only events.jsonl history
- summary.md as run record
- resume_note.md as hand-off artifact
EOF

export AIWF_EXECUTOR_MODE=mock
unset AIWF_CODEX_BIN || true
unset AIWF_EXECUTOR_TIMEOUT_SECONDS || true
unset AIWF_EXECUTOR_FALLBACK || true

TASK_ID=$(python -m swallow.cli --base-dir /tmp/swallow-phase0-acceptance task create \
  --title "Phase 0 acceptance run" \
  --goal "Verify the CLI-first orchestrator, harness runtime, truthful state/events, and usable summary/resume artifacts" \
  --workspace-root /tmp/swallow-phase0-acceptance)

echo "TASK_ID=$TASK_ID"

python -m swallow.cli --base-dir /tmp/swallow-phase0-acceptance task run "$TASK_ID"

echo
echo "== state.json =="
cat "/tmp/swallow-phase0-acceptance/.swl/tasks/$TASK_ID/state.json"

echo
echo "== events.jsonl =="
cat "/tmp/swallow-phase0-acceptance/.swl/tasks/$TASK_ID/events.jsonl"

echo
echo "== summary.md =="
python -m swallow.cli --base-dir /tmp/swallow-phase0-acceptance task summarize "$TASK_ID"

echo
echo "== resume_note.md =="
python -m swallow.cli --base-dir /tmp/swallow-phase0-acceptance task resume-note "$TASK_ID"

echo
echo "== rerun =="
python -m swallow.cli --base-dir /tmp/swallow-phase0-acceptance task run "$TASK_ID"

echo
echo "== events.jsonl after rerun =="
cat "/tmp/swallow-phase0-acceptance/.swl/tasks/$TASK_ID/events.jsonl"
