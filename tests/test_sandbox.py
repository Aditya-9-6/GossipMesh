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

    def test_run_command_string(self):
        code, stdout, stderr = self.sandbox.run_command("echo hello")
        self.assertEqual(code, 0)
        self.assertEqual(stdout.strip(), "hello")

    def test_run_command_list(self):
        code, stdout, stderr = self.sandbox.run_command(["echo", "hello list"])
        self.assertEqual(code, 0)
        self.assertEqual(stdout.strip(), "hello list")

    def test_run_command_shell_injection(self):
        # If shell=True, this would execute `echo injected`, and we'd see 'hello' and 'injected'.
        # With shell=False and shlex.split, this gets treated as arguments to `echo`.
        code, stdout, stderr = self.sandbox.run_command("echo hello ; echo injected")
        self.assertEqual(code, 0)
        # Should literally output 'hello ; echo injected'
        self.assertEqual(stdout.strip(), "hello ; echo injected")

    def test_store_artifact_normal(self):
        self.sandbox.write_file("output.bin", "data")
        dest_dir = tempfile.mkdtemp()
        try:
            dest_path = os.path.join(dest_dir, "output.bin")
            result = self.sandbox.store_artifact("output.bin", dest_path)
            self.assertTrue(result)
            self.assertTrue(os.path.exists(dest_path))
            with open(dest_path, "r") as f:
                self.assertEqual(f.read(), "data")
        finally:
            shutil.rmtree(dest_dir, ignore_errors=True)

    def test_store_artifact_path_traversal(self):
        dest_dir = tempfile.mkdtemp()
        try:
            dest_path = os.path.join(dest_dir, "output.bin")
            with self.assertRaises(ValueError):
                self.sandbox.store_artifact("../../../etc/passwd", dest_path)

            with self.assertRaises(ValueError):
                self.sandbox.store_artifact("/etc/passwd", dest_path)
        finally:
            shutil.rmtree(dest_dir, ignore_errors=True)

if __name__ == "__main__":
    unittest.main()
