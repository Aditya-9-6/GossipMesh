"""
Enterprise Dependency and Network Policy Engine (Task 86).

Enforces allowed package registries, dependency caching, network egress rules,
lockfile requirements, and offline / restricted sandbox execution modes.
"""

from __future__ import annotations

import hashlib
import ipaddress
import os
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field

from gossipmesh.core.exceptions import (
    LockfileRequiredError,
    NetworkEgressForbiddenError,
    SandboxSecurityError,
)

# Cloud metadata and forbidden private CIDR blocks
FORBIDDEN_CIDRS = [
    ipaddress.ip_network("169.254.169.254/32"),  # AWS / GCP / Azure metadata service
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("10.0.0.0/8"),  # RFC 1918 Private
    ipaddress.ip_network("172.16.0.0/12"),  # RFC 1918 Private
    ipaddress.ip_network("192.168.0.0/16"),  # RFC 1918 Private
    ipaddress.ip_network("::1/128"),  # IPv6 Loopback
    ipaddress.ip_network("fe80::/10"),  # IPv6 Link-Local
]


class EgressMode(str, Enum):
    OFFLINE = "OFFLINE"
    RESTRICTED = "RESTRICTED"
    UNRESTRICTED = "UNRESTRICTED"


class AllowedRegistry(BaseModel):
    name: str
    hosts: List[str]
    allowed_ports: List[int] = Field(default_factory=lambda: [443])
    require_https: bool = True


DEFAULT_ALLOWED_REGISTRIES: Dict[str, AllowedRegistry] = {
    "python": AllowedRegistry(
        name="PyPI",
        hosts=["pypi.org", "files.pythonhosted.org", "pypi.python.org"],
        allowed_ports=[443],
    ),
    "node": AllowedRegistry(
        name="npm",
        hosts=["registry.npmjs.org"],
        allowed_ports=[443],
    ),
    "rust": AllowedRegistry(
        name="crates.io",
        hosts=["crates.io", "static.crates.io", "index.crates.io"],
        allowed_ports=[443],
    ),
    "golang": AllowedRegistry(
        name="GoProxy",
        hosts=["proxy.golang.org", "sum.golang.org"],
        allowed_ports=[443],
    ),
}

MANIFEST_LOCKFILE_PAIRS: Dict[str, List[str]] = {
    "package.json": ["package-lock.json", "yarn.lock", "pnpm-lock.yaml"],
    "pyproject.toml": ["poetry.lock", "Pipfile.lock", "requirements.lock", "requirements.txt.lock", "pdm.lock"],
    "setup.py": ["poetry.lock", "Pipfile.lock", "requirements.lock", "requirements.txt.lock", "pdm.lock"],
    "Cargo.toml": ["Cargo.lock"],
    "go.mod": ["go.sum"],
}


class DependencyCacheManager:
    """Manages tenant-isolated dependency caches with path safety and integrity checks."""

    def __init__(self, base_cache_dir: Path | str):
        self.base_cache_dir = Path(base_cache_dir).resolve()
        self.base_cache_dir.mkdir(parents=True, exist_ok=True)

    def get_tenant_cache_dir(self, tenant_id: str, ecosystem: str = "pip") -> Path:
        """Returns the isolated cache directory for a tenant and ecosystem."""
        if not tenant_id or ".." in tenant_id or "/" in tenant_id or "\\" in tenant_id:
            raise SandboxSecurityError(f"Invalid tenant_id for cache allocation: {tenant_id}")
        if not ecosystem or ".." in ecosystem or "/" in ecosystem or "\\" in ecosystem:
            raise SandboxSecurityError(f"Invalid ecosystem for cache allocation: {ecosystem}")

        tenant_dir = (self.base_cache_dir / tenant_id / ecosystem).resolve()
        if not tenant_dir.is_relative_to(self.base_cache_dir):
            raise SandboxSecurityError(f"Cache path escapes base directory: {tenant_dir}")

        tenant_dir.mkdir(parents=True, exist_ok=True)
        return tenant_dir

    def calculate_lockfile_hash(self, lockfile_path: Path | str) -> str:
        """Calculates SHA-256 hash of a lockfile for cache tagging."""
        path = Path(lockfile_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Lockfile does not exist: {path}")

        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()


class DependencyPolicyEngine:
    """Enforces dependency installation, network egress, and lockfile policies."""

    def __init__(
        self,
        mode: EgressMode = EgressMode.RESTRICTED,
        allowed_registries: Optional[Dict[str, AllowedRegistry]] = None,
        require_lockfile: bool = True,
        cache_manager: Optional[DependencyCacheManager] = None,
    ):
        self.mode = mode
        self.allowed_registries = allowed_registries or dict(DEFAULT_ALLOWED_REGISTRIES)
        self.require_lockfile = require_lockfile
        self.cache_manager = cache_manager

        # Flatten whitelist hosts for fast O(1) lookup
        self._allowed_hosts: Set[str] = set()
        for reg in self.allowed_registries.values():
            for h in reg.hosts:
                self._allowed_hosts.add(h.lower())

    def validate_network_egress(self, host: str, port: int = 443) -> None:
        """
        Validates outbound network requests against egress mode and destination policies.
        Raises NetworkEgressForbiddenError if destination violates security rules.
        """
        host_clean = host.strip().lower()

        # OFFLINE mode allows no external network egress whatsoever
        if self.mode == EgressMode.OFFLINE:
            raise NetworkEgressForbiddenError(
                f"Egress request to {host_clean}:{port} blocked: sandbox is in OFFLINE mode"
            )

        # Check for IP address literals
        try:
            ip_obj = ipaddress.ip_address(host_clean)
            for cidr in FORBIDDEN_CIDRS:
                if ip_obj in cidr:
                    raise NetworkEgressForbiddenError(
                        f"Egress request to forbidden IP {host_clean}:{port} blocked (matches protected CIDR {cidr})"
                    )
        except ValueError:
            # Not an IP literal, it is a hostname
            pass

        # Protect against metadata hostname aliases
        if host_clean in {"instance-data", "metadata.google.internal", "metadata"}:
            raise NetworkEgressForbiddenError(f"Egress request to cloud metadata hostname {host_clean} blocked")

        # RESTRICTED mode requires matching whitelisted package registry and allowed port
        if self.mode == EgressMode.RESTRICTED:
            if port != 443:
                raise NetworkEgressForbiddenError(
                    f"Egress to port {port} blocked in RESTRICTED mode (only port 443 is allowed)"
                )
            if host_clean not in self._allowed_hosts:
                raise NetworkEgressForbiddenError(
                    f"Egress to host '{host_clean}' blocked in RESTRICTED mode (not in allowed package registries)"
                )

    def validate_lockfile_requirements(self, workspace_path: Path | str) -> None:
        """
        Scans workspace directory for package manifests and verifies that an
        accompanying approved lockfile exists if require_lockfile is True.
        """
        if not self.require_lockfile:
            return

        workspace = Path(workspace_path).resolve()
        for manifest_name, allowed_lockfiles in MANIFEST_LOCKFILE_PAIRS.items():
            manifest_file = workspace / manifest_name
            if manifest_file.is_file():
                has_valid_lock = any((workspace / lf).is_file() for lf in allowed_lockfiles)
                if not has_valid_lock:
                    raise LockfileRequiredError(
                        f"Manifest '{manifest_name}' detected in {workspace}, but no valid lockfile "
                        f"({', '.join(allowed_lockfiles)}) found. Dependency installation blocked."
                    )

    def generate_install_command_args(
        self,
        ecosystem: str,
        tenant_id: str,
        workspace_path: Optional[Path | str] = None,
    ) -> List[str]:
        """
        Generates security and caching CLI flags for package managers (pip, npm) based on
        current policy mode and tenant cache configuration.
        """
        if workspace_path:
            self.validate_lockfile_requirements(workspace_path)

        cache_dir: Optional[Path] = None
        if self.cache_manager:
            cache_dir = self.cache_manager.get_tenant_cache_dir(tenant_id, ecosystem=ecosystem)

        args: List[str] = []

        if ecosystem.lower() == "pip":
            if self.mode == EgressMode.OFFLINE:
                args.extend(["--no-index"])
                if cache_dir:
                    args.extend(["--find-links", str(cache_dir)])
            elif cache_dir:
                args.extend(["--cache-dir", str(cache_dir)])

        elif ecosystem.lower() == "npm":
            if self.mode == EgressMode.OFFLINE:
                args.extend(["--prefer-offline", "--offline"])
                if cache_dir:
                    args.extend(["--cache", str(cache_dir)])
            elif cache_dir:
                args.extend(["--cache", str(cache_dir)])

        return args
