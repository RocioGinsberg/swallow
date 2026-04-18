from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.ingestion.pipeline import (
    EXTERNAL_SESSION_SOURCE_KIND,
    build_ingestion_report,
    run_ingestion_pipeline,
)
from swallow.staged_knowledge import load_staged_candidates


class IngestionPipelineTest(unittest.TestCase):
    def test_run_ingestion_pipeline_persists_staged_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "notes.md"
            source.write_text("# Decisions\nKeep staged review manual.\n\n# Constraints\nNo realtime sync.", encoding="utf-8")

            result = run_ingestion_pipeline(tmp_path, source)
            staged_candidates = load_staged_candidates(tmp_path)

        self.assertEqual(len(result.fragments), 2)
        self.assertEqual(len(result.staged_candidates), 2)
        self.assertEqual(len(staged_candidates), 2)
        self.assertEqual(staged_candidates[0].source_kind, EXTERNAL_SESSION_SOURCE_KIND)
        self.assertEqual(staged_candidates[0].source_ref, str(source.resolve()))
        self.assertTrue(staged_candidates[0].source_task_id.startswith("ingest-notes"))

    def test_run_ingestion_pipeline_dry_run_does_not_persist_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "session.md"
            source.write_text("# Constraints\nNo realtime sync.", encoding="utf-8")

            result = run_ingestion_pipeline(tmp_path, source, dry_run=True)
            staged_candidates = load_staged_candidates(tmp_path)

        self.assertTrue(result.dry_run)
        self.assertEqual(len(result.staged_candidates), 1)
        self.assertEqual(staged_candidates, [])

    def test_build_ingestion_report_includes_candidate_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "session.md"
            source.write_text("# Decisions\nDecision: keep staged review manual.", encoding="utf-8")

            result = run_ingestion_pipeline(tmp_path, source, dry_run=True)

        report = build_ingestion_report(result)
        self.assertIn("# Ingestion Report", report)
        self.assertIn("source_kind: external_session_ingestion", report)
        self.assertIn("dry_run: yes", report)


if __name__ == "__main__":
    unittest.main()
