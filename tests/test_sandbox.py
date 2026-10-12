import os
import shutil
import tempfile
import unittest

from gossipmesh.runtime.sandbox import SandboxEnvironment

class TestSandboxEnvironment(unittest.TestCase):
    def setUp(self):
        self.dest_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dest_dir, ignore_errors=True)

    def test_write_file_normal(self):
        with SandboxEnvironment() as sandbox:
            sandbox.write_file("test.txt", "hello")

            # verify
            full_path = os.path.join(sandbox.workspace_dir, "test.txt")
            self.assertTrue(os.path.exists(full_path))
            with open(full_path, "r") as f:
                self.assertEqual(f.read(), "hello")

    def test_write_file_path_traversal(self):
        with SandboxEnvironment() as sandbox:
            with self.assertRaisesRegex(ValueError, "Path traversal detected"):
                sandbox.write_file("../../../etc/passwd", "hack")

            with self.assertRaisesRegex(ValueError, "Path traversal detected"):
                sandbox.write_file("/etc/passwd", "hack")

    def test_store_artifact_normal(self):
        with SandboxEnvironment() as sandbox:
            sandbox.write_file("output.bin", "data")
            dest_path = os.path.join(self.dest_dir, "output.bin")

            result = sandbox.store_artifact("output.bin", dest_path)
            self.assertTrue(result)
            self.assertTrue(os.path.exists(dest_path))
            with open(dest_path, "r") as f:
                self.assertEqual(f.read(), "data")

    def test_store_artifact_path_traversal(self):
        with SandboxEnvironment() as sandbox:
            dest_path = os.path.join(self.dest_dir, "output.bin")

            with self.assertRaisesRegex(ValueError, "Path traversal detected"):
                sandbox.store_artifact("../../../etc/passwd", dest_path)

            with self.assertRaisesRegex(ValueError, "Path traversal detected"):
                sandbox.store_artifact("/etc/passwd", dest_path)

if __name__ == "__main__":
    unittest.main()
