# GossipMesh GitHub Permissions Matrix & Least-Privilege Security Audit

## 1. Executive Summary & Security Policy
GossipMesh integrates with GitHub through GitHub Apps using fine-grained repository permissions. In strict adherence to the **Principle of Least Privilege (PoLP)**:
- GossipMesh **never** requests or requires administrative repository access (`administration: write` or `organization_administration: write`).
- GossipMesh **never** accesses repository secrets, deployment keys, or environments.
- All code inspection operations run with read-only permissions (`contents: read`, `pull_requests: read`).
- Write permissions are strictly isolated to creating bugfix pull requests (`pull_requests: write`), posting review comments, and updating check runs.

---

## 2. GitHub API Operations & Permission Matrix

| Operation Name | Target GitHub Endpoint | Required GitHub Resource | Minimum Permission Level | Business & Technical Justification |
| :--- | :--- | :--- | :--- | :--- |
| `sync_repository` | `GET /repos/{owner}/{repo}` | `metadata` | `read` | Retrieve repository metadata, visibility, and default branch configuration. |
| `read_file_contents` | `GET /repos/{owner}/{repo}/contents/{path}` | `contents` | `read` | Extract source code files for AST analysis, semantic symbol chunking, and vector indexing. |
| `get_pr_diff` | `GET /repos/{owner}/{repo}/pulls/{number}` | `pull_requests` | `read` | Fetch unified diffs and metadata for incoming code review workflows. |
| `get_pr_comments` | `GET /repos/{owner}/{repo}/pulls/{number}/comments` | `pull_requests` | `read` | Retrieve existing inline comments to prevent duplicate review notifications across retry runs. |
| `create_inline_comment` | `POST /repos/{owner}/{repo}/pulls/{number}/comments` | `pull_requests` | `write` | Post line-specific security, architectural, and performance review findings. |
| `submit_pr_review` | `POST /repos/{owner}/{repo}/pulls/{number}/reviews` | `pull_requests` | `write` | Submit comprehensive PR review verdict (`COMMENT`, `REQUEST_CHANGES`, or `APPROVE`). |
| `create_pull_request` | `POST /repos/{owner}/{repo}/pulls` | `pull_requests` | `write` | Open automated Pull Requests containing autonomous bugfixes, test fixes, and optimizations. |
| `create_branch_and_commit` | `POST /repos/{owner}/{repo}/git/refs`<br>`PUT /repos/{owner}/{repo}/contents/{path}` | `contents` | `write` | Push verified bugfix commits to isolated feature branches (never to protected branches). |
| `list_issues` | `GET /repos/{owner}/{repo}/issues` | `issues` | `read` | Read open backlog issues for autonomous triage and resolution workflows. |
| `create_issue` | `POST /repos/{owner}/{repo}/issues` | `issues` | `write` | Create tracking issues for newly discovered security vulnerabilities or regressions. |
| `post_issue_comment` | `POST /repos/{owner}/{repo}/issues/{number}/comments` | `issues` | `write` | Post status updates, diagnosis logs, and resolution details on issues. |
| `create_check_run` | `POST /repos/{owner}/{repo}/check-runs` | `checks` | `write` | Publish verification test run results, lint gates, and security scan status directly to GitHub checks. |

---

## 3. Strictly Prohibited & Excluded Permissions

Under no circumstances does GossipMesh request, accept, or utilize the following permissions:
- ❌ `administration` (No repository admin access permitted)
- ❌ `secrets` (Zero access to repository or environment secrets)
- ❌ `deployments` (No access to trigger or alter customer deployments)
- ❌ `packages` (No access to package registries)
- ❌ `organization_administration` (No organization-level administrative access)

---

## 4. Minimum Production GitHub App Manifest

When registering the GossipMesh GitHub App in production or staging, configure the following permission manifest:

```json
{
  "default_permissions": {
    "metadata": "read",
    "contents": "write",
    "pull_requests": "write",
    "issues": "write",
    "checks": "write"
  },
  "default_events": [
    "pull_request",
    "pull_request_review_comment",
    "issues",
    "issue_comment",
    "push"
  ]
}
```

---

## 5. Token Lifecycle, Scope Isolation & Runtime Enforcement

1. **Short-Lived Installation Access Tokens:**
   - GossipMesh generates asymmetric RSA RS256 JWTs valid for a maximum of 10 minutes to authenticate as the GitHub App.
   - Using this JWT, GossipMesh exchanges for scoped installation access tokens that expire within 1 hour.
2. **Runtime Permission Verification:**
   - The runtime module `gossipmesh/integrations/github_permissions.py` enforces permissions before any external API request is dispatched.
   - Any attempt to perform an operation without the required permission level or with excessive forbidden permissions raises an immediate `AuthorizationError`.
3. **Audit Logging:**
   - Every GitHub API interaction is correlated with a distributed request ID and logged to the immutable audit ledger.
