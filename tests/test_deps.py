import os
import unittest
from unittest.mock import patch

from gossipmesh.api import deps

class TestEnvironmentFlags(unittest.TestCase):

    @patch.dict(os.environ, {"GOSSIPMESH_AUTOMATION_ENABLED": "true"})
    def test_get_env_flag_true(self):
        self.assertTrue(deps.get_env_flag("GOSSIPMESH_AUTOMATION_ENABLED"))

    @patch.dict(os.environ, {"GOSSIPMESH_AUTOMATION_ENABLED": "false"})
    def test_get_env_flag_false(self):
        self.assertFalse(deps.get_env_flag("GOSSIPMESH_AUTOMATION_ENABLED"))

    @patch.dict(os.environ, {"GOSSIPMESH_AUTOMATION_ENABLED": "invalid"})
    def test_get_env_flag_invalid(self):
        self.assertFalse(deps.get_env_flag("GOSSIPMESH_AUTOMATION_ENABLED"))

    def test_default_pr_creation_disabled(self):
        with patch.dict(os.environ, {"GOSSIPMESH_ALLOW_PR_CREATION": "false"}):
            deps.GOSSIPMESH_ALLOW_PR_CREATION = deps.get_env_flag("GOSSIPMESH_ALLOW_PR_CREATION")
            self.assertFalse(deps.GOSSIPMESH_ALLOW_PR_CREATION)
            self.assertIn("PR creation is disabled.", deps.get_env_flag("GOSSIPMESH_ALLOW_PR_CREATION"))

    def test_default_push_disabled(self):
        with patch.dict(os.environ, {"GOSSIPMESH_ALLOW_PUSH": "false"}):
            deps.GOSSIPMESH_ALLOW_PUSH = deps.get_env_flag("GOSSIPMESH_ALLOW_PUSH")
            self.assertFalse(deps.GOSSIPMESH_ALLOW_PUSH)
            self.assertIn("Push is disabled.", deps.get_env_flag("GOSSIPMESH_ALLOW_PUSH"))

    def test_default_force_push_disabled(self):
        with patch.dict(os.environ, {"GOSSIPMESH_ALLOW_FORCE_PUSH": "false"}):
            deps.GOSSIPMESH_ALLOW_FORCE_PUSH = deps.get_env_flag("GOSSIPMESH_ALLOW_FORCE_PUSH")
            self.assertFalse(deps.GOSSIPMESH_ALLOW_FORCE_PUSH)
            self.assertIn("Force push is disabled.", deps.get_env_flag("GOSSIPMESH_ALLOW_FORCE_PUSH"))

    def test_default_auto_merge_disabled(self):
        with patch.dict(os.environ, {"GOSSIPMESH_ALLOW_AUTO_MERGE": "false"}):
            deps.GOSSIPMESH_ALLOW_AUTO_MERGE = deps.get_env_flag("GOSSIPMESH_ALLOW_AUTO_MERGE")
            self.assertFalse(deps.GOSSIPMESH_ALLOW_AUTO_MERGE)
            self.assertIn("Auto merge is disabled.", deps.get_env_flag("GOSSIPMESH_ALLOW_AUTO_MERGE"))

if __name__ == "__main__":
    unittest.main()