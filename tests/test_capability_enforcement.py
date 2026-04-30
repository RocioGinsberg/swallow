from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swallow.provider_router.capability_enforcement import enforce_capability_constraints


class CapabilityEnforcementTest(unittest.TestCase):
    def test_validator_route_downgrades_write_access_and_tool_loop(self) -> None:
        capabilities, constraints = enforce_capability_constraints(
            "validator",
            "task-state",
            {
                "execution_kind": "code_execution",
                "supports_tool_loop": True,
                "filesystem_access": "workspace_write",
                "network_access": "optional",
                "deterministic": False,
                "resumable": True,
            },
        )

        self.assertEqual(capabilities["filesystem_access"], "workspace_read")
        self.assertEqual(capabilities["supports_tool_loop"], False)
        self.assertEqual(capabilities["network_access"], "optional")
        self.assertEqual([constraint.field for constraint in constraints], ["filesystem_access", "supports_tool_loop"])

    def test_stateless_route_downgrades_filesystem_network_and_tool_loop(self) -> None:
        capabilities, constraints = enforce_capability_constraints(
            "general-executor",
            "stateless",
            {
                "execution_kind": "code_execution",
                "supports_tool_loop": True,
                "filesystem_access": "workspace_read",
                "network_access": "required",
                "deterministic": False,
                "resumable": True,
            },
        )

        self.assertEqual(capabilities["filesystem_access"], "none")
        self.assertEqual(capabilities["network_access"], "none")
        self.assertEqual(capabilities["supports_tool_loop"], False)
        self.assertEqual(
            [constraint.field for constraint in constraints],
            ["filesystem_access", "network_access", "supports_tool_loop"],
        )

    def test_general_executor_task_state_keeps_default_capabilities(self) -> None:
        original = {
            "execution_kind": "code_execution",
            "supports_tool_loop": True,
            "filesystem_access": "workspace_write",
            "network_access": "optional",
            "deterministic": False,
            "resumable": True,
        }

        capabilities, constraints = enforce_capability_constraints(
            "general-executor",
            "task-state",
            original,
        )

        self.assertEqual(capabilities, original)
        self.assertEqual(constraints, [])

    def test_multiple_constraints_apply_together(self) -> None:
        capabilities, constraints = enforce_capability_constraints(
            "validator",
            "stateless",
            {
                "execution_kind": "code_execution",
                "supports_tool_loop": True,
                "filesystem_access": "workspace_write",
                "network_access": "optional",
                "deterministic": False,
                "resumable": True,
            },
        )

        self.assertEqual(capabilities["filesystem_access"], "none")
        self.assertEqual(capabilities["network_access"], "none")
        self.assertEqual(capabilities["supports_tool_loop"], False)
        self.assertEqual(
            [constraint.field for constraint in constraints],
            ["filesystem_access", "supports_tool_loop", "filesystem_access", "network_access", "supports_tool_loop"],
        )


if __name__ == "__main__":
    unittest.main()
