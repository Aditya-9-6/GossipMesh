# GitHub App Permissions Matrix

This document outlines the minimum required GitHub App permissions for each operation performed by GossipMesh.

When configuring the GitHub App or verifying installation tokens, ensure that these scopes are granted. Requesting broad permissions unnecessarily violates the principle of least privilege.

| Operation | GitHub API Resource / Endpoint | Required Permission Scope |
| :--- | :--- | :--- |
| **Repository metadata** | `/repos/{owner}/{repo}` | `metadata: read` |
| **Pull request metadata** | `/repos/{owner}/{repo}/pulls/{pull_number}` | `pull_requests: read` |
| **Pull request files and diffs** | `/repos/{owner}/{repo}/pulls/{pull_number}/files` | `pull_requests: read` |
| **Pull request comments** | `/repos/{owner}/{repo}/pulls/{pull_number}/comments` | `pull_requests: write` |
| **Review creation** | `/repos/{owner}/{repo}/pulls/{pull_number}/reviews` | `pull_requests: write` |
| **Commit status** | `/repos/{owner}/{repo}/statuses/{sha}` | `statuses: write` |
| **Workflow logs** | `/repos/{owner}/{repo}/actions/runs/{run_id}/logs` | `actions: read` |
| **Branch creation** | `/repos/{owner}/{repo}/git/refs` | `contents: write` |
| **Pull request creation** | `/repos/{owner}/{repo}/pulls` | `pull_requests: write` |
| **Webhook management** | (Handled globally by the App or explicitly via repository hooks) | `administration: read` (if verifying hooks via API, otherwise N/A for App-level webhooks) |

## Automated Enforcement

To enforce these rules automatically, operations interacting with the GitHub API should validate the current access token's permissions before making any network requests. Operations lacking the necessary permissions will raise an `AuthorizationError`.
