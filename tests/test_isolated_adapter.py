"""Unit tests for Isolated Execution Adapters (Task 83)."""

import os
import sys
import tempfile
import pytest
from gossipmesh.core.exceptions import SandboxSecurityError
from gossipmesh.runtime.isolated_adapter import (
    ExecutionAdapterFactory,
    ExecutionConfig,
    ProcessIsolatedAdapter,
    RootlessContainerAdapter,
)


def test_rootless_container_hardened_argument_construction():
    """Verify that container invocation arguments strictly enforce rootless isolation flags."""
    adapter = RootlessContainerAdapter(runtime_binary="podman")
    config = ExecutionConfig(
        non_root_uid=10001,
        non_root_gid=10001,
        read_only_root=True,
        network_mode="none",
        memory_limit_mb=2048,
        cpu_limit_cores=2.0,
        pids_limit=64,
        image_name="gossipmesh-sandbox-base:latest",
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        args = adapter.build_container_args(["pytest", "tests/"], temp_dir, config)

        args_str = " ".join(args)

        # 1. Non-root user isolation
        assert "--user=10001:10001" in args

        # 2. Network air-gap
        assert "--network=none" in args

        # 3. Read-only base rootfs
        assert "--read-only" in args
        assert "--tmpfs=/tmp:rw,noexec,nosuid,size=128m" in args

        # 4. Resource quotas & fork bomb limits
        assert "--memory=2048m" in args
        assert "--cpus=2.0" in args
        assert "--pids-limit=64" in args

        # 5. Privilege escalation defenses
        assert "--security-opt=no-new-privileges" in args
        assert "--cap-drop=ALL" in args

        # 6. Safe workspace mount
        assert f"-v {os.path.abspath(temp_dir)}:/workspace:rw" in args_str
        assert "-w /workspace" in args_str


def test_prohibits_docker_socket_and_sensitive_host_mounts():
    """Verify attempting to mount docker.sock or root filesystem triggers security violation."""
    adapter = RootlessContainerAdapter(runtime_binary="podman")
    config = ExecutionConfig()

    for forbidden in ["/var/run/docker.sock", "/sys", "/proc", "/root"]:
        with pytest.raises(SandboxSecurityError) as exc_info:
            adapter.build_container_args(["pytest"], forbidden, config)
        assert "Prohibited mount path" in str(exc_info.value)


def test_process_isolated_adapter_execution():
    """Verify ProcessIsolatedAdapter executes an approved python command."""
    adapter = ProcessIsolatedAdapter()
    config = ExecutionConfig(timeout_seconds=10)

    with tempfile.TemporaryDirectory() as temp_dir:
        result = adapter.execute(
            cmd=[sys.executable, "-c", "import sys; print('hello sandbox')"],
            workspace_dir=temp_dir,
            config=config,
        )

        assert result.exit_code == 0
        assert "hello sandbox" in result.stdout
        assert result.timed_out is False
        assert result.adapter_type == "process_isolated"
        assert result.duration_seconds >= 0.0


def test_execution_timeout_kills_process():
    """Verify execution timeout kills long-running processes."""
    adapter = ProcessIsolatedAdapter()
    # 1 second timeout for 10 second sleep
    config = ExecutionConfig(timeout_seconds=1)

    with tempfile.TemporaryDirectory() as temp_dir:
        result = adapter.execute(
            cmd=[sys.executable, "-c", "import time; time.sleep(10)"],
            workspace_dir=temp_dir,
            config=config,
        )

        assert result.timed_out is True
        assert result.exit_code == -1


def test_execution_adapter_factory():
    """Verify adapter factory selection."""
    process_adapter = ExecutionAdapterFactory.get_adapter(force_adapter="process")
    assert isinstance(process_adapter, ProcessIsolatedAdapter)
