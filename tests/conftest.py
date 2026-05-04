from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests.helpers.builders import KnowledgeBuilder, TaskBuilder, WorkspaceBuilder

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


@pytest.fixture
def workspace_builder(tmp_path: Path) -> WorkspaceBuilder:
    return WorkspaceBuilder(tmp_path)


@pytest.fixture
def task_builder(tmp_path: Path) -> TaskBuilder:
    return TaskBuilder(tmp_path)


@pytest.fixture
def knowledge_builder(tmp_path: Path) -> KnowledgeBuilder:
    return KnowledgeBuilder(tmp_path)
