#!/usr/bin/env bash

set -euo pipefail

cd /home/rocio/projects/swallow

if [ ! -d .venv-phase0-acceptance ]; then
  python3 -m venv .venv-phase0-acceptance
fi
. ./venv/.venv-phase0-acceptance/bin/activate
python -m pip install -e .

mkdir -p /tmp/swallow-phase0-failure
cat > /tmp/swallow-phase0-failure/notes.md <<'EOF'
# Failure Acceptance Notes

This run should validate:
- failed terminal status
- truthful summarize phase retention
- failure events and artifacts
EOF

export AIWF_EXECUTOR_MODE=codex
export AIWF_CODEX_BIN=definitely-not-a-real-codex-binary

TASK_ID=$(python -m swallow.cli --base-dir /tmp/swallow-phase0-failure task create \
  --title "Phase 0 failure acceptance run" \
  --goal "Verify failed executor semantics and persisted artifacts" \
  --workspace-root /tmp/swallow-phase0-failure)

echo "TASK_ID=$TASK_ID"

python -m swallow.cli --base-dir /tmp/swallow-phase0-failure task run "$TASK_ID"

echo
echo "== state.json =="
cat "/tmp/swallow-phase0-failure/.swl/tasks/$TASK_ID/state.json"

echo
echo "== events.jsonl =="
cat "/tmp/swallow-phase0-failure/.swl/tasks/$TASK_ID/events.jsonl"

echo
echo "== summary.md =="
python -m swallow.cli --base-dir /tmp/swallow-phase0-failure task summarize "$TASK_ID"

echo
echo "== resume_note.md =="
python -m swallow.cli --base-dir /tmp/swallow-phase0-failure task resume-note "$TASK_ID"
