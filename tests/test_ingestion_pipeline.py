from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.knowledge_retrieval.ingestion.pipeline import (
    EXTERNAL_SESSION_SOURCE_KIND,
    build_ingestion_report,
    build_ingestion_summary,
    ingest_operator_note,
    ingest_local_file,
    run_ingestion_bytes_pipeline,
    run_ingestion_pipeline,
)
from swallow.knowledge_retrieval.staged_knowledge import load_staged_candidates


class IngestionPipelineTest(unittest.TestCase):
    def test_ingest_local_markdown_creates_staged_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "notes.md"
            source.write_text(
                "# Decisions\nKeep staged review manual.\n\n## Constraints\nNo realtime sync.",
                encoding="utf-8",
            )

            result = ingest_local_file(tmp_path, source)
            staged_candidates = load_staged_candidates(tmp_path)

        self.assertEqual(result.detected_format, "local_markdown")
        self.assertEqual(len(result.staged_candidates), 2)
        self.assertEqual(len(staged_candidates), 2)
        self.assertEqual(staged_candidates[0].source_kind, "local_file_capture")
        self.assertEqual(staged_candidates[0].source_ref, "file://workspace/notes.md")
        self.assertEqual(result.source_path, "file://workspace/notes.md")
        self.assertTrue(staged_candidates[0].source_task_id.startswith("ingest-notes"))
        self.assertIn("Decisions", staged_candidates[0].text)
        self.assertIn("Constraints", staged_candidates[1].text)

    def test_ingest_local_text_creates_single_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "notes.txt"
            source.write_text("Keep the operator gate explicit.", encoding="utf-8")

            result = ingest_local_file(tmp_path, source, dry_run=True)

        self.assertEqual(result.detected_format, "local_text")
        self.assertEqual(len(result.staged_candidates), 1)
        self.assertEqual(result.staged_candidates[0].source_kind, "local_file_capture")
        self.assertEqual(result.staged_candidates[0].source_ref, "file://workspace/notes.txt")
        self.assertEqual(result.staged_candidates[0].text, "Keep the operator gate explicit.")

    def test_ingest_local_file_dry_run_does_not_persist_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "notes.md"
            source.write_text("# Summary\nKeep local ingest separate.", encoding="utf-8")

            result = ingest_local_file(tmp_path, source, dry_run=True)
            staged_candidates = load_staged_candidates(tmp_path)

        self.assertTrue(result.dry_run)
        self.assertEqual(len(result.staged_candidates), 1)
        self.assertEqual(staged_candidates, [])

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
        self.assertEqual(staged_candidates[0].source_ref, "file://workspace/notes.md")
        self.assertEqual(result.source_path, "file://workspace/notes.md")
        self.assertTrue(staged_candidates[0].source_task_id.startswith("ingest-notes"))

    def test_run_ingestion_pipeline_supports_out_of_workspace_file_uri(self) -> None:
        with tempfile.TemporaryDirectory() as base_tmp, tempfile.TemporaryDirectory() as source_tmp:
            base_dir = Path(base_tmp)
            source = Path(source_tmp) / "external-session.md"
            source.write_text("# Decisions\nDecision: keep external export readable.", encoding="utf-8")

            result = run_ingestion_pipeline(base_dir, source, dry_run=True)

        self.assertEqual(result.source_path, source.resolve().as_uri())
        self.assertEqual(result.staged_candidates[0].source_ref, source.resolve().as_uri())

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

    def test_ingest_operator_note_persists_topic_and_source_kind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            result = ingest_operator_note(tmp_path, "Use explicit route guards.", topic="routing")
            staged_candidates = load_staged_candidates(tmp_path)

        self.assertEqual(result.detected_format, "operator_note")
        self.assertEqual(len(result.staged_candidates), 1)
        self.assertEqual(staged_candidates[0].source_kind, "operator_note")
        self.assertEqual(staged_candidates[0].topic, "routing")
        self.assertEqual(staged_candidates[0].source_ref, "note://operator")
        self.assertTrue(staged_candidates[0].source_task_id.startswith("note-"))

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

    def test_run_ingestion_bytes_pipeline_uses_clipboard_source_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            result = run_ingestion_bytes_pipeline(
                tmp_path,
                b"# Decisions\nDecision: keep clipboard ingest explicit.",
                source_name="clipboard.md",
                source_ref="clipboard://auto",
                source_task_id="ingest-clipboard-20260426-120000",
                dry_run=True,
            )

        self.assertEqual(result.source_path, "clipboard://auto")
        self.assertEqual(result.detected_format, "markdown")
        self.assertEqual(len(result.staged_candidates), 1)
        self.assertEqual(result.staged_candidates[0].source_ref, "clipboard://auto")
        self.assertEqual(result.staged_candidates[0].source_task_id, "ingest-clipboard-20260426-120000")

    def test_build_ingestion_summary_groups_fragments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "session.md"
            source.write_text(
                "# Decisions\nDecision: keep staged review manual.\n\n"
                "# Constraints\nConstraint: no realtime sync.\n\n"
                "# Rejected\nReject plan A and switch to plan B.",
                encoding="utf-8",
            )

            result = run_ingestion_pipeline(tmp_path, source, dry_run=True)

        summary = build_ingestion_summary(result)
        self.assertIn("# Ingestion Summary", summary)
        self.assertIn("## Decisions (1)", summary)
        self.assertIn("Decision: keep staged review manual.", summary)
        self.assertIn("## Constraints (1)", summary)
        self.assertIn("Constraint: no realtime sync.", summary)
        self.assertIn("## Rejected Alternatives (1)", summary)
        self.assertIn("Reject plan A and switch to plan B.", summary)
        self.assertIn("precision_estimate: N/A", summary)


if __name__ == "__main__":
    unittest.main()
