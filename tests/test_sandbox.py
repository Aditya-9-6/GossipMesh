import unittest
import os
import tempfile
import shutil
from gossipmesh.runtime.sandbox import SandboxEnvironment

class TestSandboxEnvironment(unittest.TestCase):
    def setUp(self):
        self.sandbox = SandboxEnvironment()
        self.sandbox.workspace_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.sandbox.workspace_dir)

    def test_write_file_success(self):
        # We try to write a file properly inside the workspace
        self.sandbox.write_file("test_normal.txt", "normal data")
        self.sandbox.write_file("dir/test_nested.txt", "nested data")

        with open(os.path.join(self.sandbox.workspace_dir, "test_normal.txt")) as f:
            self.assertEqual(f.read(), "normal data")

        with open(os.path.join(self.sandbox.workspace_dir, "dir", "test_nested.txt")) as f:
            self.assertEqual(f.read(), "nested data")

    def test_path_traversal_vulnerability(self):
        # We try to write a file outside the sandbox workspace_dir
        with self.assertRaises(ValueError):
            self.sandbox.write_file("../test_traversal.txt", "traversal data")

        # We try to write a file outside using absolute path
        with self.assertRaises(ValueError):
            self.sandbox.write_file("/tmp/test_traversal.txt", "traversal data")

if __name__ == "__main__":
    unittest.main()
