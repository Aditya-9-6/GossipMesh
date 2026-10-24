import os
import shutil
import tempfile
import subprocess
import shlex
import time
import sys
import re
import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from gossipmesh.core.exceptions import SandboxError, SandboxSecurityError

logger = logging.getLogger(__name__)


class CommandPolicyEngine:
    """Enforces deny-by-default execution policy on all sandbox processes."""

    APPROVED_BINARIES: Set[str] = {
        "python",
        "python3",
        "pytest",
        "ruff",
        "black",
        "flake8",
        "coverage",
        "git",
        "echo",
    }

    ALLOWED_GIT_SUBCOMMANDS: Set[str] = {
        "status",
        "diff",
        "log",
        "show",
        "rev-parse",
        "checkout",
        "branch",
    }

    DANGEROUS_SHELL_PATTERNS: List[re.Pattern] = [
        re.compile(r"[;&|`$><]"),
        re.compile(r"\$\(.*\)"),
        re.compile(r"`.*`"),
    ]

    SENSITIVE_ENV_PREFIXES: Tuple[str, ...] = (
        "AWS_",
        "GITHUB_",
        "GH_",
        "SECRET_",
        "POSTGRES_",
        "DATABASE_",
        "GEMINI_",
        "OPENAI_",
        "ANTHROPIC_",
        "GROQ_",
        "DEEPSEEK_",
        "SLACK_",
    )

    @classmethod
    def get_canonical_binary_name(cls, binary_path: str) -> str:
        """Extracts the base executable name without extensions."""
        base = os.path.basename(binary_path).lower()
        if base.endswith(".exe"):
            base = base[:-4]
        return base

    @classmethod
    def validate_command(
        cls,
        cmd: Any,
        workflow_id: Optional[Union[str, int]] = None,
    ) -> List[str]:
        """
        Validates command against deny-by-default rules.
        Rejects raw shell strings, unapproved binaries, and dangerous arguments.
        """
        if isinstance(cmd, str):
            raise SandboxSecurityError(
                "Raw shell strings are strictly prohibited under deny-by-default policy. "
                "Commands must be submitted as structured argv lists without shell invocation."
            )

        if not isinstance(cmd, (list, tuple)) or len(cmd) == 0:
            raise SandboxSecurityError("Command must be a non-empty list of string arguments.")

        cmd_list = [str(arg) for arg in cmd]
        raw_binary = cmd_list[0]
        binary = cls.get_canonical_binary_name(raw_binary)

        # Allow current python executable
        is_current_python = raw_binary == sys.executable or os.path.abspath(raw_binary) == os.path.abspath(
            sys.executable
        )

        if not is_current_python and binary not in cls.APPROVED_BINARIES:
            raise SandboxSecurityError(
                f"Binary '{raw_binary}' is not permitted in sandbox. "
                f"Approved binaries: {', '.join(sorted(cls.APPROVED_BINARIES))}"
            )

        if binary in ("python", "python3") or is_current_python:
            if "-c" in cmd_list:
                c_idx = cmd_list.index("-c")
                if c_idx + 1 < len(cmd_list):
                    code = cmd_list[c_idx + 1]
                    dangerous_tokens = ["os.system", "subprocess", "socket", "pty", "shutil.rmtree(/"]
                    for dt in dangerous_tokens:
                        if dt in code:
                            raise SandboxSecurityError(
                                f"Dangerous inline Python construct '{dt}' is prohibited in sandbox."
                            )

        args_to_check = []
        for i, arg in enumerate(cmd_list[1:], start=1):
            if (binary in ("python", "python3") or is_current_python) and i > 1 and cmd_list[i - 1] == "-c":
                continue
            args_to_check.append(arg)

        for arg in args_to_check:
            for pat in cls.DANGEROUS_SHELL_PATTERNS:
                if pat.search(arg):
                    raise SandboxSecurityError(
                        f"Dangerous shell operator or metacharacter detected in argument '{arg}'."
                    )

        if binary == "git" and len(cmd_list) > 1:
            subcommand = cmd_list[1].lower()
            if subcommand not in cls.ALLOWED_GIT_SUBCOMMANDS:
                raise SandboxSecurityError(
                    f"Git subcommand '{subcommand}' is forbidden in sandbox. "
                    f"Allowed subcommands: {', '.join(sorted(cls.ALLOWED_GIT_SUBCOMMANDS))}"
                )

        return cmd_list

    @classmethod
    def sanitize_environment(cls, base_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Creates a scrubbed environment stripped of credentials and API keys."""
        source_env = base_env or os.environ
        scrubbed = {}
        for k, v in source_env.items():
            if any(k.upper().startswith(prefix) for prefix in cls.SENSITIVE_ENV_PREFIXES):
                continue
            if "TOKEN" in k.upper() or "KEY" in k.upper() or "PASSWORD" in k.upper():
                continue
            scrubbed[k] = v

        scrubbed["GOSSIPMESH_SANDBOX"] = "true"
        return scrubbed


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

    def run_command(
        self, cmd: Union[str, List[str]], timeout: int = 30, workflow_id: Optional[Union[str, int]] = None
    ) -> Tuple[int, str, str]:
        """Runs a command within the sandbox workspace."""
        if not self.workspace_dir:
            raise RuntimeError("Sandbox not initialized")

        effective_wf = workflow_id
        effective_timeout = timeout

        if isinstance(cmd, str):
            cmd = shlex.split(cmd)

        cmd = CommandPolicyEngine.validate_command(cmd, workflow_id=effective_wf)

        if os.name == "nt" and cmd and cmd[0].lower() == "echo":
            cmd = [sys.executable, "-c", "import sys; print(' '.join(sys.argv[1:]))"] + cmd[1:]

        env = CommandPolicyEngine.sanitize_environment()

        start_time = time.time()
        process = subprocess.Popen(
            cmd, cwd=self.workspace_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env
        )
        try:
            stdout, stderr = process.communicate(timeout=effective_timeout)
            return process.returncode, stdout, stderr
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            duration = time.time() - start_time
            logger.error(f"[AUDIT:SANDBOX_EXEC_TIMEOUT] workflow_id={effective_wf} killed after {duration:.2f}s")
            raise SandboxError(
                message=f"Command timed out after {effective_timeout}s",
                details={"stderr": stderr, "workflow_id": effective_wf},
            )
        except Exception as e:
            logger.error(f"[AUDIT:SANDBOX_EXEC_ERROR] workflow_id={effective_wf} error={e}")
            raise

    def write_file(self, filepath: str, content: str):
        if not self.workspace_dir:
            raise RuntimeError("Sandbox not initialized")

        workspace_abs = os.path.abspath(self.workspace_dir)
        full_path = os.path.abspath(os.path.join(workspace_abs, filepath))

        if os.path.commonpath([workspace_abs, full_path]) != workspace_abs:
            raise ValueError("Path traversal attempt detected")

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
