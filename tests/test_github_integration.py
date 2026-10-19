import unittest
<<<<<<< HEAD
from gossipmesh.repository.github import GitHubIntegration
from gossipmesh.core.exceptions import AuthorizationError

class TestGitHubIntegration(unittest.TestCase):
    def test_sync_repository_insufficient_permissions(self):
        # Provide empty permissions to force AuthorizationError on sync_repository
        github_integration = GitHubIntegration(app_id="test_app_id", private_key="test_key", permissions={})

        with self.assertRaises(AuthorizationError) as context:
            github_integration.sync_repository("owner/repo", 123)

        self.assertIn("Missing required permission scope: 'metadata'", str(context.exception))

if __name__ == "__main__":
=======
from unittest.mock import AsyncMock, MagicMock
from gossipmesh.integrations.github import GitHubIntegration
from gossipmesh.integrations.github_pr import GitHubPRService
from gossipmesh.models.pr_review import SecurityFinding, RemediationModel

class TestGitHubIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.github_pr_service = MagicMock(spec=GitHubPRService)
        self.github_pr_service.get_pr_diff = AsyncMock()
        self.github_pr_service.get_pr_review_comments = AsyncMock(return_value=[])
        self.github_pr_service.post_pr_review_comment = AsyncMock()
        self.github_pr_service.post_pr_review = AsyncMock()
        self.integration = GitHubIntegration(
            owner="owner", repo="repo", pr_number=42, github_pr_service=self.github_pr_service
        )

    async def test_generate_inline_comments_valid_and_fallback(self):
        diff = """--- a/file1.txt
+++ b/file1.txt
@@ -10,3 +10,4 @@
 unchanged
-removed
+added1
+added2
 unchanged
"""
        self.github_pr_service.get_pr_diff.return_value = diff

        valid_finding = SecurityFinding(
            id="f1", file_path="file1.txt", line=11, side="RIGHT",
            commit_sha="abc1234", severity="HIGH", message="msg1"
        )
        invalid_finding = SecurityFinding(
            id="f2", file_path="file1.txt", line=99, side="RIGHT",
            commit_sha="abc1234", severity="LOW", message="msg2"
        )

        self.github_pr_service.post_pr_review.return_value = {"id": 12345}

        await self.integration.generate_inline_comments([valid_finding, invalid_finding])

        self.assertEqual(self.github_pr_service.post_pr_review.call_count, 2)

        # Call 1: The valid inline comment review
        inline_call_args = self.github_pr_service.post_pr_review.call_args_list[0][0]
        self.assertEqual(inline_call_args[0], "owner")
        self.assertEqual(inline_call_args[1], "repo")
        self.assertEqual(inline_call_args[2], 42)
        inline_payload = inline_call_args[3]
        self.assertEqual(inline_payload["comments"][0]["path"], "file1.txt")
        self.assertEqual(inline_payload["comments"][0]["line"], 11)
        self.assertIn("**HIGH**: msg1", inline_payload["comments"][0]["body"])
        self.assertEqual(inline_payload["event"], "COMMENT")

        # Call 2: The fallback review
        fallback_call_args = self.github_pr_service.post_pr_review.call_args_list[1][0]
        self.assertEqual(fallback_call_args[0], "owner")
        self.assertEqual(fallback_call_args[1], "repo")
        self.assertEqual(fallback_call_args[2], 42)
        fallback_payload = fallback_call_args[3]
        self.assertIn("file1.txt:99", fallback_payload["body"])
        self.assertEqual(fallback_payload["event"], "COMMENT")

    async def test_generate_inline_comments_deduplication(self):
        diff = """--- a/file1.txt
+++ b/file1.txt
@@ -10,3 +10,4 @@
 unchanged
-removed
+added1
+added2
 unchanged
"""
        self.github_pr_service.get_pr_diff.return_value = diff

        finding1 = SecurityFinding(
            id="f1", file_path="file1.txt", line=11, side="RIGHT",
            commit_sha="abc1234", severity="HIGH", message="msg1",
            fingerprint="fp1"
        )
        finding2 = SecurityFinding(
            id="f2", file_path="file1.txt", line=12, side="RIGHT",
            commit_sha="abc1234", severity="LOW", message="msg2",
            fingerprint="fp1" # duplicate fingerprint
        )

        self.github_pr_service.post_pr_review.return_value = {"id": 12345}

        await self.integration.generate_inline_comments([finding1, finding2])

        self.github_pr_service.post_pr_review.assert_called_once()
        call_args = self.github_pr_service.post_pr_review.call_args[0]
        payload = call_args[3]
        self.assertIn("**HIGH**: msg1", payload["comments"][0]["body"])
        self.assertNotIn("**LOW**: msg2", payload["comments"][0]["body"])

    async def test_generate_inline_comments_partial_failure(self):
        diff = """--- a/file1.txt
+++ b/file1.txt
@@ -10,3 +10,4 @@
 unchanged
-removed
+added1
+added2
 unchanged
"""
        self.github_pr_service.get_pr_diff.return_value = diff

        finding1 = SecurityFinding(
            id="f1", file_path="file1.txt", line=11, side="RIGHT",
            commit_sha="abc1234", severity="HIGH", message="msg1"
        )
        finding2 = SecurityFinding(
            id="f2", file_path="file1.txt", line=12, side="RIGHT",
            commit_sha="abc1234", severity="LOW", message="msg2"
        )

        # Both go to the same post_pr_review call now, so if it fails, both go to fallback
        self.github_pr_service.post_pr_review.side_effect = [
            Exception("API error"),  # Fails inline review
            {"id": 54321}            # Succeeds fallback review
        ]

        await self.integration.generate_inline_comments([finding1, finding2])

        self.assertEqual(self.github_pr_service.post_pr_review.call_count, 2)

        # The second call should be the fallback containing both
        fallback_call_args = self.github_pr_service.post_pr_review.call_args_list[1][0]
        fallback_payload = fallback_call_args[3]
        self.assertIn("file1.txt:11", fallback_payload["body"])
        self.assertIn("file1.txt:12", fallback_payload["body"])

        # Comment ID should not be set for fallback findings
        self.assertIsNone(finding1.github_comment_id)
        self.assertIsNone(finding2.github_comment_id)

    async def test_generate_inline_comments_retry_safety(self):
        diff = """--- a/file1.txt
+++ b/file1.txt
@@ -10,3 +10,4 @@
 unchanged
-removed
+added1
+added2
 unchanged
"""
        self.github_pr_service.get_pr_diff.return_value = diff

        # Mock an existing comment with the fingerprint
        self.github_pr_service.get_pr_review_comments.return_value = [
            {"id": 999, "body": "Some comment\n<!-- fingerprint: fp_retry -->"}
        ]

        finding = SecurityFinding(
            id="f1", file_path="file1.txt", line=11, side="RIGHT",
            commit_sha="abc1234", severity="HIGH", message="msg",
            fingerprint="fp_retry"
        )

        await self.integration.generate_inline_comments([finding])

        # Should be skipped completely due to retry safety
        self.github_pr_service.post_pr_review.assert_not_called()

    async def test_generate_inline_comments_auto_patch(self):
        diff = """--- a/file1.txt
+++ b/file1.txt
@@ -10,3 +10,4 @@
 unchanged
-removed
+added1
+added2
 unchanged
"""
        self.github_pr_service.get_pr_diff.return_value = diff

        remediation = RemediationModel(description="Fix it", auto_patch="patched_code1\npatched_code2")

        valid_finding = SecurityFinding(
            id="f1", file_path="file1.txt", line=11, side="RIGHT",
            commit_sha="abc1234", severity="HIGH", message="msg1",
            remediation=remediation
        )
        invalid_finding = SecurityFinding(
            id="f2", file_path="file1.txt", line=99, side="RIGHT",
            commit_sha="abc1234", severity="LOW", message="msg2",
            remediation=remediation
        )

        self.github_pr_service.post_pr_review.return_value = {"id": 12345}

        await self.integration.generate_inline_comments([valid_finding, invalid_finding])

        self.assertEqual(self.github_pr_service.post_pr_review.call_count, 2)

        inline_call_args = self.github_pr_service.post_pr_review.call_args_list[0][0]
        inline_payload = inline_call_args[3]
        self.assertIn("```suggestion\npatched_code1\npatched_code2\n```", inline_payload["comments"][0]["body"])

        fallback_call_args = self.github_pr_service.post_pr_review.call_args_list[1][0]
        fallback_payload = fallback_call_args[3]
        self.assertIn("```suggestion\npatched_code1\npatched_code2\n```", fallback_payload["body"])

    async def test_generate_inline_comments_left_side(self):
        diff = """--- a/file1.txt
+++ b/file1.txt
@@ -10,3 +10,4 @@
 unchanged
-removed
+added1
+added2
 unchanged
"""
        self.github_pr_service.get_pr_diff.return_value = diff

        valid_finding_left = SecurityFinding(
            id="f1", file_path="file1.txt", line=11, side="LEFT",
            commit_sha="abc1234", severity="HIGH", message="msg1"
        )

        self.github_pr_service.post_pr_review.return_value = {"id": 12345}

        await self.integration.generate_inline_comments([valid_finding_left])

        self.github_pr_service.post_pr_review.assert_called_once()
        call_args = self.github_pr_service.post_pr_review.call_args[0]
        payload = call_args[3]
        self.assertEqual(payload["comments"][0]["path"], "file1.txt")
        self.assertEqual(payload["comments"][0]["line"], 11)
        self.assertEqual(payload["comments"][0]["side"], "LEFT")

if __name__ == '__main__':
>>>>>>> origin/main
    unittest.main()
