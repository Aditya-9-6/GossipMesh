# GossipMesh Enterprise Sandbox Threat Model & Security Architecture

**Document Version:** 1.0  
**Phase:** Phase 9 — Secure Code Execution (Task 81)  
**Security Status:** PRODUCTION MANDATORY  
**Target Environment:** Isolated MicroVMs / Rootless Containers (gVisor, Firecracker, Podman)

---

## 1. Executive Summary & Sandbox Philosophy

GossipMesh executes untrusted, third-party code as part of its automated pull request review, testing, AST inspection, and benchmark workflows. Because pull requests can originate from external contributors or compromised developer accounts, **all code under review and all test execution suites are treated as actively hostile by default**.

The GossipMesh Sandbox Architecture operates under a strict **Zero-Trust, Ephemeral Isolation Model**:
1. **Never Trust Repository Code:** Code executed in the sandbox has zero assumed legitimacy.
2. **Never Mount the Host Environment:** The sandbox has no access to the host filesystem, Docker daemon sockets, host networking, or parent processes.
3. **Never Expose Credentials:** Secret keys, cloud IAM credentials, and provider API tokens are strictly scrubbed before job execution.
4. **Deterministic Overrides:** Deterministic gates take precedence over AI approvals.

---

## 2. Comprehensive Threat Matrix

| Threat Category | Attack Vector & Mechanism | Impact Severity | Defense-in-Depth Mitigation |
| :--- | :--- | :--- | :--- |
| **Malicious Code Execution** | PR contains payloads designed to spawn reverse shells (`nc`, `bash -i`, Python sockets). | **CRITICAL** | Non-root users (`uid=10001`), rootless execution namespaces, strict network egress block, and read-only base images. |
| **Dependency Attacks** | Malicious packages in `setup.py`, `package.json`, or unpinned requirements that execute scripts during install. | **CRITICAL** | Offline test modes, pinned lockfile requirements, banned package scanning (`telnetlib3`, `pycrypto`), and ephemeral container teardown. |
| **Data Exfiltration** | PR sends source code, diffs, or env data to external servers via DNS tunneling, HTTP POST, or raw sockets. | **CRITICAL** | Network namespace isolation (`--network none` by default). Cloud egress completely blocked; cloud metadata service (`169.254.169.254`) unroutable. |
| **Credential Theft** | Reading `/proc/1/environ`, searching environment variables for `SECRET_KEY`, `POSTGRES_PASSWORD`, or querying instance metadata. | **CRITICAL** | Environment scrubbing (zero production secrets passed to worker), mock credentials, and dedicated execution service accounts. |
| **Container / VM Escapes** | Exploiting kernel vulnerabilities, sysfs/procfs leaks, or shared `/var/run/docker.sock` to gain host node root access. | **CRITICAL** | Strict prohibition of Docker socket mounts; rootless containers with user namespace remapping (`userns-remap`); seccomp BPF filters blocking dangerous syscalls. |
| **Fork Bombs & Process Exhaustion** | Code executes `while True: os.fork()` or thread bombs to exhaust system PID table and crash the host OS. | **HIGH** | `cgroups v2` process limits (`pids.max = 64`), preemptive CPU quotas (`cpu.max = 200000`), and watchdog execution timeouts. |
| **Resource & Memory Exhaustion** | Allocating gigabytes of RAM (`[0] * 10**9`) or writing giant multi-gigabyte files to fill disk partitions. | **HIGH** | `cgroups v2` memory hard ceiling (`memory.max = 2048M`), read-only root filesystems, and bounded tmpfs mounts (`tmpfs-size = 256M`). |
| **Prompt Injection in Tests** | Malicious docstrings or test names designed to trick the LLM into generating "APPROVED" verdicts or ignoring security findings. | **HIGH** | Strict boundary isolation (`<untrusted_repository_content>`), passive data interpretation rules, and non-overridable deterministic security gates. |
| **Artifact Poisoning** | Malicious test suites outputting backdoored binaries, symlinks traversing outside workspace, or poisoned coverage reports. | **HIGH** | Post-execution artifact quarantine, strict MIME/extension whitelisting, symlink escape checks (`os.path.realpath` boundary validation), and virus scanning. |
| **Side Channels & Shared State** | Timing attacks, CPU cache contention, or persisting files across sequential runs for different tenants. | **HIGH** | Ephemeral, throwaway sandbox environments destroyed completely upon job termination; dedicated tenant concurrency partitions. |

---

## 3. Defense Architecture & Hardening Controls

```
+-----------------------------------------------------------------------------------+
| Host Node (GossipMesh Worker VM / Bare Metal)                                     |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  | Unprivileged Worker Runner (uid: 2000, no sudo, no docker.sock)             |  |
|  |                                                                             |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  |  | Isolated MicroVM / Rootless Container Boundary                       |  |  |
|  |  |                                                                       |  |  |
|  |  |  [cgroups v2 Hard Limits]                                             |  |  |
|  |  |   - pids.max: 64              (Fork bomb prevention)                  |  |  |
|  |  |   - memory.max: 2048 MB       (OOM containment)                       |  |  |
|  |  |   - cpu.max: 2.0 cores        (CPU starvation prevention)             |  |  |
|  |  |                                                                       |  |  |
|  |  |  [Filesystem Policy]                                                  |  |  |
|  |  |   - Root: Read-Only (squashfs / overlayfs)                            |  |  |
|  |  |   - Workspace: Ephemeral RAM tmpfs (max 256MB)                        |  |  |
|  |  |   - Host filesystem: Zero mounts                                      |  |  |
|  |  |                                                                       |  |  |
|  |  |  [Network Policy]                                                     |  |  |
|  |  |   - Egress: Deny All (isolated network namespace)                     |  |  |
|  |  |   - Metadata IP (169.254.169.254): Dropped via iptables/nftables      |  |  |
|  |  |                                                                       |  |  |
|  |  |  [Execution Rules]                                                     |  |  |
|  |  |   - Commands: Approved whitelist only (pytest, python -m unittest)    |  |  |
|  |  |   - Shell strings: Strictly rejected (no sh -c or /bin/bash)          |  |  |
|  |  |   - Wall-clock timeout: 300s hard kill                               |  |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

### 3.1 Command Whitelist & Shell Rejection (Task 82)
The sandbox rejects shell-string execution (such as `sh -c "cmd1; cmd2"`). Commands must be submitted as structured argv arrays, where the executable binary must match an explicit whitelist:
- Allowed: `pytest`, `python -m pytest`, `python -m unittest`, `ruff check`, `bandit`
- Forbidden: `bash`, `sh`, `curl`, `wget`, `nc`, `ncat`, `python -c "import socket..."`

### 3.2 Ephemeral Workspace Lifecycle
1. Workspace directory is allocated as an ephemeral `tmpfs` volume with a randomized GUID.
2. Code is copied into the tmpfs volume.
3. Execution runs with non-root UID.
4. On job completion or timeout, the entire `tmpfs` volume is unmounted and securely shredded. Zero residual state persists between runs.

### 3.3 Symlink & Traversal Protections
Before reading or copying any artifact out of the sandbox workspace:
- All paths are canonicalized with `os.path.realpath()`.
- Paths resolving outside the sandbox root directory trigger immediate quarantine and flag a security alert.

---

## 4. Operational Runbook & Escape Incident Response

In the event of an attempted sandbox escape or resource abuse:
1. **Immediate Termination:** The watchdog kills the container process tree using `SIGKILL`.
2. **Forensic Snapshot:** Sandbox logs, command argv, and tenant ID are securely written to the audit log.
3. **Tenant Quarantine:** If malicious code execution (e.g. reverse shell or metadata access attempt) is verified, the tenant organization is suspended and all active workflows are halted.
4. **Credential Verification:** Automated rotation check verifies whether any host credentials were exposed.
