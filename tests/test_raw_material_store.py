from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.knowledge_retrieval.raw_material import (
    FilesystemRawMaterialStore,
    InvalidRawMaterialRef,
    UnsupportedRawMaterialScheme,
    artifact_source_ref_from_legacy_ref,
    parse_source_ref,
    source_ref_for_artifact,
    source_ref_for_file,
)
from swallow.application.infrastructure.paths import artifacts_dir


class RawMaterialStoreTest(unittest.TestCase):
    def test_parse_source_ref_combines_uri_authority_and_path(self) -> None:
        ref = parse_source_ref("file://workspace/docs/design/KNOWLEDGE.md#L10")

        self.assertEqual(ref.scheme, "file")
        self.assertEqual(ref.key, "workspace/docs/design/KNOWLEDGE.md")
        self.assertEqual(ref.fragment, "L10")

    def test_source_ref_for_file_prefers_workspace_relative_uri(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace_root = Path(tmp)
            source_path = workspace_root / "docs" / "note file.md"
            source_path.parent.mkdir(parents=True)
            source_path.write_text("raw note", encoding="utf-8")

            source_ref = source_ref_for_file(source_path, workspace_root=workspace_root)

        self.assertEqual(source_ref, "file://workspace/docs/note%20file.md")

    def test_filesystem_store_resolves_workspace_file_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace_root = Path(tmp)
            source_path = workspace_root / "docs" / "note.md"
            source_path.parent.mkdir(parents=True)
            source_path.write_text("raw note", encoding="utf-8")
            source_ref = source_ref_for_file(source_path, workspace_root=workspace_root)
            store = FilesystemRawMaterialStore(workspace_root)

            resolved = store.resolve(source_ref)
            exists = store.exists(source_ref)
            content_hash = store.content_hash(source_ref)

        expected_hash = hashlib.sha256(b"raw note").hexdigest()
        self.assertEqual(resolved, b"raw note")
        self.assertTrue(exists)
        self.assertEqual(content_hash, f"sha256:{expected_hash}")

    def test_filesystem_store_supports_legacy_absolute_file_uri(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace_root = Path(tmp)
            source_path = workspace_root / "outside-style.md"
            source_path.write_text("legacy absolute", encoding="utf-8")
            store = FilesystemRawMaterialStore(workspace_root)

            resolved = store.resolve(source_path.resolve().as_uri())

        self.assertEqual(resolved, b"legacy absolute")

    def test_filesystem_store_resolves_artifact_uri(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            artifact_path = artifacts_dir(base_dir, "task-abc") / "report.md"
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_text("artifact body", encoding="utf-8")
            source_ref = source_ref_for_artifact("task-abc", "report.md")
            store = FilesystemRawMaterialStore(base_dir)

            resolved = store.resolve(source_ref)
            exists = store.exists(source_ref)

        self.assertEqual(source_ref, "artifact://task-abc/report.md")
        self.assertEqual(resolved, b"artifact body")
        self.assertTrue(exists)

    def test_legacy_artifact_ref_converts_to_artifact_uri(self) -> None:
        self.assertEqual(
            artifact_source_ref_from_legacy_ref(".swl/tasks/task-abc/artifacts/nested/report.md#entry-1"),
            "artifact://task-abc/nested/report.md#entry-1",
        )

    def test_missing_artifact_returns_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = FilesystemRawMaterialStore(Path(tmp))

            exists = store.exists("artifact://task-abc/missing.md")

        self.assertFalse(exists)

    def test_artifact_ref_rejects_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = FilesystemRawMaterialStore(Path(tmp))

            with self.assertRaises(InvalidRawMaterialRef):
                source_ref_for_artifact("task-abc", "../secret.md")
            with self.assertRaises(InvalidRawMaterialRef):
                store.resolve("artifact://task-abc/../secret.md")

    def test_unsupported_scheme_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = FilesystemRawMaterialStore(Path(tmp))

            with self.assertRaises(UnsupportedRawMaterialScheme):
                store.exists("s3://bucket/key.md")

    def test_parse_source_ref_requires_scheme(self) -> None:
        with self.assertRaises(InvalidRawMaterialRef):
            parse_source_ref("docs/note.md")


if __name__ == "__main__":
    unittest.main()
