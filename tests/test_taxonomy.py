from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.models import MEMORY_AUTHORITIES, SYSTEM_ROLES, TaxonomyProfile


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
