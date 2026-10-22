import pytest
from pathlib import Path
from gossipmesh.core.exceptions import (
    LockfileRequiredError,
    NetworkEgressForbiddenError,
    SandboxSecurityError,
)
from gossipmesh.runtime.dependency_policy import (
    AllowedRegistry,
    DEFAULT_ALLOWED_REGISTRIES,
    DependencyCacheManager,
    DependencyPolicyEngine,
    EgressMode,
)


def test_egress_offline_mode_blocks_all():
    engine = DependencyPolicyEngine(mode=EgressMode.OFFLINE)
    with pytest.raises(NetworkEgressForbiddenError) as exc_info:
        engine.validate_network_egress("pypi.org", 443)
    assert "OFFLINE mode" in str(exc_info.value)

    with pytest.raises(NetworkEgressForbiddenError):
        engine.validate_network_egress("registry.npmjs.org", 443)


def test_egress_restricted_mode_allowed_registries():
    engine = DependencyPolicyEngine(mode=EgressMode.RESTRICTED)
    # Allowed
    engine.validate_network_egress("pypi.org", 443)
    engine.validate_network_egress("files.pythonhosted.org", 443)
    engine.validate_network_egress("registry.npmjs.org", 443)
    engine.validate_network_egress("crates.io", 443)
    engine.validate_network_egress("proxy.golang.org", 443)

    # Disallowed host
    with pytest.raises(NetworkEgressForbiddenError) as exc_info:
        engine.validate_network_egress("malicious-repo.com", 443)
    assert "not in allowed package registries" in str(exc_info.value)

    # Disallowed port on allowed host
    with pytest.raises(NetworkEgressForbiddenError) as exc_info:
        engine.validate_network_egress("pypi.org", 80)
    assert "only port 443 is allowed" in str(exc_info.value)


def test_egress_forbidden_cidrs_and_metadata():
    engine = DependencyPolicyEngine(mode=EgressMode.UNRESTRICTED)

    # AWS / GCP / Azure metadata IP
    with pytest.raises(NetworkEgressForbiddenError) as exc_info:
        engine.validate_network_egress("169.254.169.254", 80)
    assert "matches protected CIDR" in str(exc_info.value)

    # Loopback
    with pytest.raises(NetworkEgressForbiddenError):
        engine.validate_network_egress("127.0.0.1", 8080)

    # RFC 1918 Private
    with pytest.raises(NetworkEgressForbiddenError):
        engine.validate_network_egress("10.0.0.5", 443)
    with pytest.raises(NetworkEgressForbiddenError):
        engine.validate_network_egress("192.168.1.1", 443)

    # Metadata hostnames
    with pytest.raises(NetworkEgressForbiddenError):
        engine.validate_network_egress("metadata.google.internal", 80)
    with pytest.raises(NetworkEgressForbiddenError):
        engine.validate_network_egress("instance-data", 80)


def test_lockfile_validation_enforcement(tmp_path: Path):
    engine = DependencyPolicyEngine(require_lockfile=True)

    # Case 1: Manifest exists without lockfile
    pkg_json = tmp_path / "package.json"
    pkg_json.write_text('{"name": "test"}')

    with pytest.raises(LockfileRequiredError) as exc_info:
        engine.validate_lockfile_requirements(tmp_path)
    assert "no valid lockfile" in str(exc_info.value)

    # Case 2: Lockfile added
    lock_file = tmp_path / "package-lock.json"
    lock_file.write_text('{"lockfileVersion": 2}')
    engine.validate_lockfile_requirements(tmp_path)

    # Case 3: Python pyproject.toml without lockfile
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'test'")
    with pytest.raises(LockfileRequiredError):
        engine.validate_lockfile_requirements(tmp_path)

    # Case 4: Poetry lock added
    (tmp_path / "poetry.lock").write_text("package = []")
    engine.validate_lockfile_requirements(tmp_path)

    # Case 5: When require_lockfile is disabled, manifests without lockfiles are allowed
    engine_permissive = DependencyPolicyEngine(require_lockfile=False)
    cargo_toml = tmp_path / "Cargo.toml"
    cargo_toml.write_text("[package]\nname = 'rust-test'")
    engine_permissive.validate_lockfile_requirements(tmp_path)


def test_dependency_cache_manager(tmp_path: Path):
    cache_base = tmp_path / "cache"
    manager = DependencyCacheManager(base_cache_dir=cache_base)

    tenant_cache = manager.get_tenant_cache_dir("tenant_abc", "pip")
    assert tenant_cache.is_dir()
    assert tenant_cache.resolve().is_relative_to(cache_base)

    # Path traversal attempt rejected
    with pytest.raises(SandboxSecurityError):
        manager.get_tenant_cache_dir("../tenant_escape", "pip")

    with pytest.raises(SandboxSecurityError):
        manager.get_tenant_cache_dir("tenant_abc", "../pip_escape")

    # Lockfile hash calculation
    dummy_lock = tmp_path / "test.lock"
    dummy_lock.write_text("dependency-v1-pin")
    digest = manager.calculate_lockfile_hash(dummy_lock)
    assert len(digest) == 64  # SHA-256


def test_generate_install_command_args(tmp_path: Path):
    cache_base = tmp_path / "cache"
    manager = DependencyCacheManager(base_cache_dir=cache_base)

    # Pip in RESTRICTED mode
    restricted_engine = DependencyPolicyEngine(
        mode=EgressMode.RESTRICTED,
        cache_manager=manager,
    )
    pip_args = restricted_engine.generate_install_command_args("pip", "tenant-1")
    assert "--cache-dir" in pip_args

    # Pip in OFFLINE mode
    offline_engine = DependencyPolicyEngine(
        mode=EgressMode.OFFLINE,
        cache_manager=manager,
    )
    offline_pip_args = offline_engine.generate_install_command_args("pip", "tenant-1")
    assert "--no-index" in offline_pip_args
    assert "--find-links" in offline_pip_args

    # npm in OFFLINE mode
    offline_npm_args = offline_engine.generate_install_command_args("npm", "tenant-1")
    assert "--offline" in offline_npm_args
    assert "--cache" in offline_npm_args
