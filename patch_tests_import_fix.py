with open("tests/test_webhooks.py", "r") as f:
    content = f.read()

# I see ModuleNotFoundError: No module named 'gossipmesh.worker.tasks.webhook_dispatch'; 'gossipmesh.worker.tasks' is not a package
# This usually happens if `gossipmesh/worker/tasks/__init__.py` is missing! Let's check.
