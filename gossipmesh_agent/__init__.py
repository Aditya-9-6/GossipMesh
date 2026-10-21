# gaggle package init
"""Top‑level package for the GossipMesh Agent.
Exports the entry points used by the GitHub Actions workflow.
"""

from .ingestion import handle_github_event
from .queue_worker import start_worker
from .autoscaler import autoscale_worker_pool

__all__ = ["handle_github_event", "start_worker", "autoscale_worker_pool"]
