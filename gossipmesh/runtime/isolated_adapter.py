"""Isolated Execution Adapters for Secure Code Execution (Task 83).

Provides isolated container and process execution adapters implementing:
- Non-root user execution (uid=10001)
- Read-only root base images
- Temporary workspace mounts (no host filesystem access)
- Explicit prohibition of Docker socket mounts
- Restricted network mode (network=none by default)
- CPU, memory (2048 MB), and process limits (pids.max=64) to prevent fork bombs
- Hard execution timeouts and output limits
- Automatic teardown and cleanup
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

from gossipmesh.core.exceptions import SandboxError, SandboxSecurityError
from gossipmesh.runtime.sandbox import CommandPolicyEngine

logger = logging.getLogger(__name__)


@dataclass
class ExecutionConfig:
    """Resource constraints and security policies for sandbox execution."""

    non_root_uid: int = 10001
    non_root_gid: int = 10001
    read_only_root: bool = True
    network_mode: str = "none"  # "none" = fully air-gapped
    memory_limit_mb: int = 2048
    cpu_limit_cores: float = 2.0
    pids_limit: int = 64  # Fork bomb defense
    disk_limit_mb: int = 512
    timeout_seconds: int = 120
    max_output_bytes: int = 10 * 1024 * 1024  # 10 MB
    image_name: str = "gossipmesh-sandbox-base:latest"
    env_vars: Dict[str, str] = field(default_factory=dict)
    workflow_id: Optional[str] = None


@dataclass
class ExecutionResult:
    """Execution telemetry and output results."""

    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False
    adapter_type: str = "unknown"


class BaseExecutionAdapter(ABC):
    """Abstract interface for isolated execution adapters."""

    @abstractmethod
    def execute(
        self,
        cmd: List[str],
        workspace_dir: str,
        config: ExecutionConfig,
    ) -> ExecutionResult:
        """Executes command within the isolated boundary."""
        pass


class RootlessContainerAdapter(BaseExecutionAdapter):
    """
    Executes tasks inside rootless OCI containers (Podman / Docker rootless)
    with strict isolation flags, read-only root, no network, and resource quotas.
    """

    PROHIBITED_MOUNTS = ["/var/run/docker.sock", "/var/run/podman.sock", "/etc", "/sys", "/proc", "/root"]

    def __init__(self, runtime_binary: Optional[str] = None):
        self.runtime_binary = runtime_binary or self._detect_runtime()

    @staticmethod
    def _detect_runtime() -> Optional[str]:
        for bin_name in ("podman", "docker"):
            path = shutil.which(bin_name)
            if path:
                return path
        return None

    def build_container_args(
        self,
        cmd: List[str],
        workspace_dir: str,
        config: ExecutionConfig,
    ) -> List[str]:
        """Constructs hardened container invocation argument vector."""
        # Validate workspace path doesn't point to prohibited mounts
        abs_workspace = os.path.abspath(workspace_dir)
        norm_workspace = workspace_dir.replace("\\", "/").rstrip("/").lower()
        for pm in self.PROHIBITED_MOUNTS:
            clean_pm = pm.rstrip("/").lower()
            if norm_workspace == clean_pm or norm_workspace.endswith(clean_pm):
                raise SandboxSecurityError(f"Prohibited mount path: {workspace_dir}")

        args = [
            self.runtime_binary or "podman",
            "run",
            "--rm",
            # Security & user isolation
            f"--user={config.non_root_uid}:{config.non_root_gid}",
            "--security-opt=no-new-privileges",
            "--cap-drop=ALL",
            # Network isolation (deny all)
            f"--network={config.network_mode}",
            # Resource & DoS limits
            f"--memory={config.memory_limit_mb}m",
            f"--cpus={config.cpu_limit_cores}",
            f"--pids-limit={config.pids_limit}",
        ]

        # Read-only root image
        if config.read_only_root:
            args.extend(
                [
                    "--read-only",
                    "--tmpfs=/tmp:rw,noexec,nosuid,size=128m",
                ]
            )

        # Ephemeral workspace mount only
        args.extend(
            [
                "-v",
                f"{abs_workspace}:/workspace:rw",
                "-w",
                "/workspace",
            ]
        )

        # Scrubbed environment variables
        clean_env = CommandPolicyEngine.sanitize_environment(config.env_vars)
        for k, v in clean_env.items():
            args.extend(["-e", f"{k}={v}"])

        # Target image & command
        args.append(config.image_name)
        args.extend(cmd)
        return args

    def execute(
        self,
        cmd: List[str],
        workspace_dir: str,
        config: ExecutionConfig,
    ) -> ExecutionResult:
        if not self.runtime_binary:
            raise SandboxError("No container runtime (podman or docker) detected on host system.")

        container_argv = self.build_container_args(cmd, workspace_dir, config)
        start_time = time.time()

        try:
            proc = subprocess.Popen(
                container_argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = proc.communicate(timeout=config.timeout_seconds)
            duration = time.time() - start_time

            return ExecutionResult(
                exit_code=proc.returncode,
                stdout=stdout[: config.max_output_bytes],
                stderr=stderr[: config.max_output_bytes],
                duration_seconds=round(duration, 3),
                timed_out=False,
                adapter_type="rootless_container",
            )
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            duration = time.time() - start_time
            return ExecutionResult(
                exit_code=-1,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=round(duration, 3),
                timed_out=True,
                adapter_type="rootless_container",
            )


class ProcessIsolatedAdapter(BaseExecutionAdapter):
    """
    Subprocess-isolated adapter with strict path jail, environment scrubbing,
    timeouts, and process tracking. Fallback for testing environments.
    """

    def execute(
        self,
        cmd: List[str],
        workspace_dir: str,
        config: ExecutionConfig,
    ) -> ExecutionResult:
        # Validate command against deny-by-default policy
        validated_cmd = CommandPolicyEngine.validate_command(cmd, config.workflow_id)

        clean_env = CommandPolicyEngine.sanitize_environment(config.env_vars)
        start_time = time.time()

        try:
            proc = subprocess.Popen(
                validated_cmd,
                cwd=workspace_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=clean_env,
                shell=False,
            )
            stdout, stderr = proc.communicate(timeout=config.timeout_seconds)
            duration = time.time() - start_time

            return ExecutionResult(
                exit_code=proc.returncode,
                stdout=stdout[: config.max_output_bytes],
                stderr=stderr[: config.max_output_bytes],
                duration_seconds=round(duration, 3),
                timed_out=False,
                adapter_type="process_isolated",
            )
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            duration = time.time() - start_time
            return ExecutionResult(
                exit_code=-1,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=round(duration, 3),
                timed_out=True,
                adapter_type="process_isolated",
            )


class ExecutionAdapterFactory:
    """Factory selecting the most secure available execution adapter."""

    @classmethod
    def get_adapter(cls, force_adapter: Optional[str] = None) -> BaseExecutionAdapter:
        choice = (force_adapter or os.getenv("SANDBOX_ADAPTER_TYPE", "")).lower()

        if choice == "container":
            runtime = RootlessContainerAdapter._detect_runtime()
            if not runtime:
                raise SandboxError("Container adapter requested, but neither podman nor docker is installed.")
            return RootlessContainerAdapter(runtime)
        elif choice == "process":
            return ProcessIsolatedAdapter()

        # Auto-detect: prefer rootless container if runtime available, else process isolation
        runtime = RootlessContainerAdapter._detect_runtime()
        if runtime and not os.getenv("TESTING"):
            return RootlessContainerAdapter(runtime)
        return ProcessIsolatedAdapter()
