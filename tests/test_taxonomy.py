from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.orchestration.models import (
    LIBRARIAN_MEMORY_AUTHORITY,
    LIBRARIAN_SYSTEM_ROLE,
    MEMORY_AUTHORITY_SEMANTICS,
    MEMORY_AUTHORITIES,
    SYSTEM_ROLES,
    TaxonomyProfile,
    allowed_memory_authority_side_effects,
    build_librarian_taxonomy_profile,
    describe_memory_authority,
)


class TaxonomyProfileTest(unittest.TestCase):
    def test_taxonomy_profile_accepts_valid_values(self) -> None:
        profile = TaxonomyProfile(
            system_role="general-executor",
            memory_authority="task-state",
        )

        self.assertEqual(profile.system_role, "general-executor")
        self.assertEqual(profile.memory_authority, "task-state")
        self.assertEqual(profile.to_dict(), {"system_role": "general-executor", "memory_authority": "task-state"})

    def test_taxonomy_profile_rejects_invalid_system_role(self) -> None:
        with self.assertRaises(ValueError) as raised:
            TaxonomyProfile(
                system_role="invalid-role",
                memory_authority="task-state",
            )

        self.assertIn("Invalid system_role: invalid-role", str(raised.exception))
        self.assertIn(", ".join(SYSTEM_ROLES), str(raised.exception))

    def test_taxonomy_profile_rejects_invalid_memory_authority(self) -> None:
        with self.assertRaises(ValueError) as raised:
            TaxonomyProfile(
                system_role="validator",
                memory_authority="invalid-memory-authority",
            )

        self.assertIn("Invalid memory_authority: invalid-memory-authority", str(raised.exception))
        self.assertIn(", ".join(MEMORY_AUTHORITIES), str(raised.exception))

    def test_build_librarian_taxonomy_profile_uses_specialist_canonical_promotion(self) -> None:
        profile = build_librarian_taxonomy_profile()

        self.assertEqual(profile.system_role, LIBRARIAN_SYSTEM_ROLE)
        self.assertEqual(profile.memory_authority, LIBRARIAN_MEMORY_AUTHORITY)

    def test_memory_authority_semantics_cover_every_registered_authority(self) -> None:
        self.assertEqual(set(MEMORY_AUTHORITY_SEMANTICS), set(MEMORY_AUTHORITIES))

    def test_describe_memory_authority_clarifies_canonical_write_forbidden_scope(self) -> None:
        description = describe_memory_authority("canonical-write-forbidden")
        side_effects = allowed_memory_authority_side_effects("canonical-write-forbidden")

        self.assertIn("may not write to canonical knowledge truth", description.lower())
        self.assertIn("proposal_bundles", side_effects)
        self.assertIn("audit_artifacts", side_effects)

    def test_describe_memory_authority_rejects_unknown_value(self) -> None:
        with self.assertRaises(ValueError):
            describe_memory_authority("unknown-authority")
