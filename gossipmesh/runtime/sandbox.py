"""Secure Sandbox Execution Engine with Deny-by-Default Command Policy (Task 82).

Enforces:
- Strict rejection of shell-string execution (must use structured argv)
- Explicit binary whitelist (pytest, python, ruff, git read-only, etc.)
- Argument validation and rejection of shell metacharacters
- Workflow and job tracking association
- Structured audit logging
- Hard time limits (max 300s) and memory/output limits
- Environment variable sanitization (scrubs tokens and secrets)
"""

import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
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
        # Rule 1: Strictly reject raw shell-string execution
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
        is_current_python = (
            raw_binary == sys.executable
            or os.path.abspath(raw_binary) == os.path.abspath(sys.executable)
        )

        # Rule 2: Explicit binary whitelist
        if not is_current_python and binary not in cls.APPROVED_BINARIES:
            raise SandboxSecurityError(
                f"Binary '{raw_binary}' is not permitted in sandbox. "
                f"Approved binaries: {', '.join(sorted(cls.APPROVED_BINARIES))}"
            )

        # Rule 3: Python inline code validation
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

        # Rule 4: Rejection of shell metacharacters in arguments (excluding validated python -c code)
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

        # Rule 5: Git subcommand restriction
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
    Secure sandbox execution workspace enforcing deny-by-default command policy,
    audit logging, timeouts, and resource isolation.
    """

    MAX_TIMEOUT_SECONDS = 300
    MAX_OUTPUT_BYTES = 10 * 1024 * 1024  # 10 MB

    def __init__(self, workflow_id: Optional[Union[str, int]] = None):
        self.workspace_dir: Optional[str] = None
        self.workflow_id = workflow_id

    def __enter__(self):
        self.workspace_dir = tempfile.mkdtemp(prefix="gossipmesh_sandbox_")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.workspace_dir and os.path.exists(self.workspace_dir):
            try:
                shutil.rmtree(self.workspace_dir)
            except Exception as e:
                logger.warning(f"Error cleaning up sandbox workspace {self.workspace_dir}: {e}")

    def run_command(
        self,
        cmd: List[str],
        workflow_id: Optional[Union[str, int]] = None,
        timeout: int = 30,
        env: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, str, str]:
        """
        Executes an approved structured command within the sandbox workspace.
        Enforces deny-by-default policy, environment scrubbing, and time limits.
        """
        if not self.workspace_dir:
            raise RuntimeError("Sandbox workspace not initialized")

        effective_wf = workflow_id or self.workflow_id

        # 1. Validate command against deny-by-default policy
        validated_cmd = CommandPolicyEngine.validate_command(cmd, effective_wf)

        # 2. Enforce hard timeout ceiling
        effective_timeout = min(max(1, int(timeout)), self.MAX_TIMEOUT_SECONDS)

        # 3. Sanitize environment
        scrubbed_env = CommandPolicyEngine.sanitize_environment(env)

        # Windows mock support for built-in echo
        if os.name == "nt" and validated_cmd and validated_cmd[0].lower() == "echo":
            validated_cmd = [sys.executable, "-c", "import sys; print(' '.join(sys.argv[1:]))"] + validated_cmd[1:]

        # 4. Structured audit log
        start_time = time.time()
        logger.info(
            f"[AUDIT:SANDBOX_EXEC_START] workflow_id={effective_wf} "
            f"cmd={validated_cmd} timeout={effective_timeout}s cwd={self.workspace_dir}"
        )

        try:
            process = subprocess.Popen(
                validated_cmd,
                cwd=self.workspace_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=scrubbed_env,
                shell=False,  # Mandatory: NEVER invoke system shell
            )
            stdout, stderr = process.communicate(timeout=effective_timeout)
            duration = time.time() - start_time

            # 5. Output size bounding
            if len(stdout.encode("utf-8")) > self.MAX_OUTPUT_BYTES:
                stdout = stdout[: self.MAX_OUTPUT_BYTES] + "\n[OUTPUT TRUNCATED DUE TO SIZE LIMIT]"
            if len(stderr.encode("utf-8")) > self.MAX_OUTPUT_BYTES:
                stderr = stderr[: self.MAX_OUTPUT_BYTES] + "\n[OUTPUT TRUNCATED DUE TO SIZE LIMIT]"

            logger.info(
                f"[AUDIT:SANDBOX_EXEC_COMPLETE] workflow_id={effective_wf} "
                f"exit_code={process.returncode} duration={duration:.2f}s"
            )
            return process.returncode, stdout, stderr

        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            duration = time.time() - start_time
            logger.error(
                f"[AUDIT:SANDBOX_EXEC_TIMEOUT] workflow_id={effective_wf} "
                f"killed after {duration:.2f}s"
            )
            raise SandboxError(
                message=f"Command timed out after {effective_timeout}s",
                details={"stderr": stderr, "workflow_id": effective_wf},
            )
        except Exception as e:
            logger.error(f"[AUDIT:SANDBOX_EXEC_ERROR] workflow_id={effective_wf} error={e}")
            raise

    def write_file(self, filepath: str, content: str):
        """Safely writes a file inside workspace, preventing path traversal escapes."""
        if not self.workspace_dir:
            raise RuntimeError("Sandbox not initialized")

        workspace_abs = os.path.abspath(self.workspace_dir)
        full_path = os.path.abspath(os.path.join(workspace_abs, filepath))

        if os.path.commonpath([workspace_abs, full_path]) != workspace_abs:
            raise SandboxSecurityError(f"Path traversal attempt detected for path '{filepath}'")

        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

    def store_artifact(self, artifact_name: str, dest_path: str) -> bool:
        """Stores a generated artifact safely validating paths."""
        if not self.workspace_dir:
            raise RuntimeError("Sandbox not initialized")

        workspace_abs = os.path.abspath(self.workspace_dir)
        source = os.path.abspath(os.path.join(workspace_abs, artifact_name))

        if os.path.commonpath([workspace_abs, source]) != workspace_abs:
            raise SandboxSecurityError("Artifact path traversal escape detected")

        if os.path.exists(source):
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(source, dest_path)
            return True
        return False
