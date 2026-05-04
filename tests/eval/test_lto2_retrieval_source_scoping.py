from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from swallow.knowledge_retrieval.knowledge_plane import build_retrieval_request, retrieve_knowledge_context


pytestmark = pytest.mark.eval


def test_lto2_eval_declared_document_scope_beats_generated_and_archive_noise(tmp_path: Path) -> None:
    declared_doc = tmp_path / "docs" / "design" / "KNOWLEDGE.md"
    archive_doc = tmp_path / "docs" / "archive_phases" / "old" / "closeout.md"
    generated_doc = tmp_path / "src" / "swallow.egg-info" / "SOURCES.txt"
    for path in (declared_doc, archive_doc, generated_doc):
        path.parent.mkdir(parents=True, exist_ok=True)

    declared_doc.write_text(
        "# Knowledge\n\nretrieval source scoping truth reuse visibility.\n",
        encoding="utf-8",
    )
    noisy_terms = "retrieval source scoping truth reuse visibility " * 25
    archive_doc.write_text("# Old Closeout\n\n" + noisy_terms + "\n", encoding="utf-8")
    generated_doc.write_text("SOURCES\n" + noisy_terms + "\n", encoding="utf-8")

    request = build_retrieval_request(
        query="retrieval source scoping truth reuse visibility",
        source_types=["notes", "repo"],
        declared_document_paths=("docs/design/KNOWLEDGE.md",),
        limit=5,
    )

    with patch.dict("os.environ", {"SWL_RETRIEVAL_RERANK_ENABLED": "false"}, clear=False):
        items = retrieve_knowledge_context(tmp_path, request=request)

    assert items
    assert items[0].path == "docs/design/KNOWLEDGE.md"
    assert items[0].score_breakdown["declared_document_priority"] > 0

    noise_items = {item.path: item for item in items if item.path != "docs/design/KNOWLEDGE.md"}
    assert noise_items["docs/archive_phases/old/closeout.md"].metadata["source_policy_label"] == "archive_note"
    assert noise_items["src/swallow.egg-info/SOURCES.txt"].metadata["source_policy_label"] == "generated_metadata"
    assert noise_items["src/swallow.egg-info/SOURCES.txt"].score_breakdown["source_noise_penalty"] < 0
