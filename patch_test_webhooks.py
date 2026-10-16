import re
with open("tests/test_webhooks.py", "r") as f:
    content = f.read()

content = re.sub(
r"    @patch\(\"gossipmesh\.workflows\.issue_solver\.IssueSolverWorkflow\.execute\"\)\n    def test_replay_endpoint_admin_only\(self, mock_execute\):\n=======\n    @patch\(\"gossipmesh\.worker\.tasks\.process_issue_solver\.apply_async\"\)\n    def test_replay_endpoint_admin_only\(self, mock_apply_async\):\n>>>>>>> origin/main",
"""    @patch("gossipmesh.worker.tasks.process_issue_solver.apply_async")
    def test_replay_endpoint_admin_only(self, mock_apply_async):""",
content, flags=re.DOTALL)

with open("tests/test_webhooks.py", "w") as f:
    f.write(content)
