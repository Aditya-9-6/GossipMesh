import os
import shutil
import tempfile
import subprocess
from typing import Optional, Tuple

class SandboxEnvironment:
    """
    Provides a temporary, isolated directory for executing jobs safely.
    In a full production environment, this would wrap Docker or Firecracker microVMs.
    """
    def __init__(self):
        self.workspace_dir: Optional[str] = None

    def __enter__(self):
        self.workspace_dir = tempfile.mkdtemp(prefix="gossipmesh_sandbox_")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.workspace_dir and os.path.exists(self.workspace_dir):
            shutil.rmtree(self.workspace_dir)

    def run_command(self, cmd: str, timeout: int = 30) -> Tuple[int, str, str]:
        """Runs a command within the sandbox workspace."""
        if not self.workspace_dir:
            raise RuntimeError("Sandbox not initialized")

        process = subprocess.Popen(
            cmd,
            shell=True,
            cwd=self.workspace_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            return process.returncode, stdout, stderr
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return -1, stdout, "Command timed out\n" + stderr

    def write_file(self, filepath: str, content: str):
        if not self.workspace_dir:
            raise RuntimeError("Sandbox not initialized")

        full_path = os.path.join(self.workspace_dir, filepath)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)

    def store_artifact(self, artifact_name: str, dest_path: str):
        """
        Moves a generated artifact from the sandbox to a durable storage path.
        In production, this would upload to S3 or similar.
        """
        if not self.workspace_dir:
            raise RuntimeError("Sandbox not initialized")

        source = os.path.join(self.workspace_dir, artifact_name)
        if os.path.exists(source):
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(source, dest_path)
            return True
        return False
