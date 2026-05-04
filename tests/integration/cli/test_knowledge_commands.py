from __future__ import annotations

import json
from pathlib import Path

from swallow.knowledge_retrieval.knowledge_plane import (
    StagedCandidate,
    list_staged_knowledge as load_staged_candidates,
    submit_staged_knowledge as submit_staged_candidate,
)
from swallow.application.infrastructure.paths import canonical_registry_path
from tests.helpers.cli_runner import run_cli


def test_knowledge_stage_promote_characterization_stdout_stderr_exit_code(tmp_path: Path) -> None:
    candidate = submit_staged_candidate(
        tmp_path,
        StagedCandidate(
            candidate_id="",
            text="Promote this focused integration note.",
            source_task_id="task-stage-promote",
            source_object_id="knowledge-0001",
            submitted_by="integration-test",
            taxonomy_role="specialist",
            taxonomy_memory_authority="staged-knowledge",
        ),
    )

    result = run_cli(
        tmp_path,
        "knowledge",
        "stage-promote",
        candidate.candidate_id,
        "--note",
        "Approved by focused CLI test.",
    )

    result.assert_success()
    assert result.stderr == ""
    assert f"{candidate.candidate_id} staged_promoted canonical_id=canonical-{candidate.candidate_id}" in result.stdout
    staged = load_staged_candidates(tmp_path)
    assert staged[0].status == "promoted"
    assert staged[0].decision_note == "Approved by focused CLI test."
    canonical_records = [
        json.loads(line)
        for line in canonical_registry_path(tmp_path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert canonical_records[0]["canonical_id"] == f"canonical-{candidate.candidate_id}"


def test_knowledge_stage_reject_characterization_stdout_stderr_exit_code(tmp_path: Path) -> None:
    candidate = submit_staged_candidate(
        tmp_path,
        StagedCandidate(
            candidate_id="",
            text="Reject this focused integration note.",
            source_task_id="task-stage-reject",
            submitted_by="integration-test",
        ),
    )

    result = run_cli(
        tmp_path,
        "knowledge",
        "stage-reject",
        candidate.candidate_id,
        "--note",
        "Needs better evidence.",
    )

    result.assert_success()
    assert result.stderr == ""
    assert f"{candidate.candidate_id} staged_rejected status=rejected" in result.stdout
    staged = load_staged_candidates(tmp_path)
    assert staged[0].status == "rejected"
    assert staged[0].decision_note == "Needs better evidence."


def test_knowledge_ingest_file_characterization_stdout_stderr_exit_code(tmp_path: Path) -> None:
    source = tmp_path / "operator-note.md"
    source.write_text("# Operator Note\n\nUse focused CLI tests for migration baselines.\n", encoding="utf-8")

    result = run_cli(tmp_path, "knowledge", "ingest-file", str(source), "--summary")

    result.assert_success()
    assert result.stderr == ""
    assert "# Ingestion Report" in result.stdout
    assert "staged_candidates:" in result.stdout
