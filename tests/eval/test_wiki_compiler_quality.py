from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from swallow.application.services.wiki_compiler import (
    WIKI_COMPILER_PARSER_VERSION,
    WikiCompilerAgent,
    build_wiki_compiler_source_pack,
)


pytestmark = pytest.mark.eval


SOURCE_PACK_FIXTURE: list[dict[str, object]] = [
    {
        "reference": "source-1",
        "path": "notes/compiler-a.md",
        "source_ref": "file://workspace/notes/compiler-a.md",
    },
    {
        "reference": "source-2",
        "path": "notes/compiler-b.md",
        "source_ref": "file://workspace/notes/compiler-b.md",
    },
]


def _rationale_cites_source(rationale: str, source_pack: list[dict[str, object]]) -> bool:
    tokens: set[str] = set()
    for source in source_pack:
        for key in ("reference", "source_ref", "path"):
            value = str(source.get(key, "")).strip()
            if value:
                tokens.add(value)
    return any(token in rationale for token in tokens)


def _relation_types(relation_metadata: list[dict[str, object]]) -> set[str]:
    return {str(item.get("relation_type", "")).strip() for item in relation_metadata}


def test_wiki_compiler_eval_source_pack_has_anchor_for_every_source(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "compiler-a.md").write_text(
        "# Compiler A\n\nDrafts must remain staged.\n",
        encoding="utf-8",
    )
    (notes_dir / "compiler-b.md").write_text(
        "# Compiler B\n\nEvidence anchors need parser versions.\n",
        encoding="utf-8",
    )
    source_refs = [
        "file://workspace/notes/compiler-a.md",
        "file://workspace/notes/compiler-b.md",
    ]

    source_pack = build_wiki_compiler_source_pack(
        tmp_path,
        source_refs,
        workspace_root=tmp_path,
    )

    assert len(source_pack) == len(source_refs)
    for index, (anchor, source_ref) in enumerate(zip(source_pack, source_refs, strict=True), start=1):
        assert anchor["reference"] == f"source-{index}"
        assert anchor["source_ref"] == source_ref
        assert anchor["resolution_status"] == "resolved"
        assert str(anchor["content_hash"]).startswith("sha256:")
        assert anchor["parser_version"] == WIKI_COMPILER_PARSER_VERSION
        assert str(anchor["span"]).startswith("L1-L")
        assert int(anchor["line_start"]) == 1
        assert int(anchor["line_end"]) >= 1
        assert str(anchor["preview"]).strip()


@pytest.mark.parametrize(
    ("case_id", "action", "mode", "target_object_id", "payload", "expected_relation", "forbidden_relations"),
    [
        (
            "draft_filters_supersedes",
            "draft",
            "draft",
            "",
            {
                "title": "Wiki Compiler Boundary",
                "text": "Wiki Compiler drafts staged knowledge for operator review.",
                "rationale": "source-1 says drafts must remain staged.",
                "relation_metadata": [
                    {
                        "relation_type": "derived_from",
                        "target_ref": "file://workspace/notes/compiler-a.md",
                    },
                    {
                        "relation_type": "supersedes",
                        "target_object_id": "wiki-old",
                    },
                ],
                "conflict_flag": "contradicts(wiki-conflict)",
            },
            "derived_from",
            {"supersedes", "refines"},
        ),
        (
            "refine_refines_inserts_requested_relation",
            "refine",
            "refines",
            "wiki-target",
            {
                "title": "Refined Wiki",
                "text": "A narrower entry that refines the target wiki.",
                "rationale": "source-2 narrows the target wiki.",
                "relation_metadata": [],
                "conflict_flag": "",
            },
            "refines",
            {"supersedes"},
        ),
        (
            "refine_supersede_preserves_conflict_signal",
            "refine",
            "supersede",
            "wiki-old",
            {
                "title": "Replacement Wiki",
                "text": "A replacement draft for an outdated wiki entry.",
                "rationale": "source-1 contradicts the old wiki evidence.",
                "relation_metadata": [
                    {
                        "relation_type": "refers_to",
                        "target_object_id": "wiki-context",
                    }
                ],
                "conflict_flag": "contradicts(wiki-old)",
            },
            "supersedes",
            {"refines"},
        ),
    ],
)
def test_wiki_compiler_eval_draft_payload_preserves_reviewable_structure(
    case_id: str,
    action: str,
    mode: str,
    target_object_id: str,
    payload: dict[str, object],
    expected_relation: str,
    forbidden_relations: set[str],
) -> None:
    draft = WikiCompilerAgent()._draft_from_payload(
        payload,
        action=action,
        mode=mode,
        target_object_id=target_object_id,
    )

    relations = _relation_types(draft.relation_metadata)
    assert draft.text.strip(), case_id
    assert _rationale_cites_source(draft.rationale, SOURCE_PACK_FIXTURE), case_id
    assert expected_relation in relations, case_id
    assert relations.isdisjoint(forbidden_relations), case_id
    assert draft.conflict_flag == str(payload.get("conflict_flag", "")).strip()
    if action == "refine":
        assert draft.relation_metadata[0] == {
            "relation_type": expected_relation,
            "target_object_id": target_object_id,
        }
