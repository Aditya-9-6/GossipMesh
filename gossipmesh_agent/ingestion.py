import json
from typing import Any, Dict
from .utils import logger


def _verify_signature(headers: Dict[str, str], payload: bytes, secret: str) -> bool:
    """Verify GitHub webhook HMAC signature (X-Hub-Signature-256)."""
    import hmac, hashlib

    digest = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, headers.get("X-Hub-Signature-256", ""))


def handle_github_event(event_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Entry point for the GitHub App webhook.
    Returns a minimal JSON payload for the background worker.
    """
    logger.info("Received GitHub event %s", event_name)
    if event_name == "issues":
        action = payload.get("action")
        if action == "opened":
            return {
                "type": "issue_opened",
                "repo": payload["repository"]["full_name"],
                "issue_number": payload["issue"]["number"],
                "issue_body": payload["issue"].get("body", ""),
            }
    elif event_name == "pull_request":
        action = payload.get("action")
        if action in {"opened", "synchronize"}:
            return {
                "type": "pr_opened",
                "repo": payload["repository"]["full_name"],
                "pr_number": payload["pull_request"]["number"],
                "head_sha": payload["pull_request"]["head"]["sha"],
                "base_branch": payload["pull_request"]["base"]["ref"],
            }
    # TODO: handle comment commands like `/gossipmesh fix`
    logger.warning("Unsupported event %s with action %s", event_name, payload.get("action"))
    return {"type": "unsupported"}
