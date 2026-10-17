import unittest
from unittest.mock import AsyncMock, MagicMock
from gossipmesh.integrations.github import GitHubIntegration
from gossipmesh.integrations.github_pr import GitHubPRService
from gossipmesh.models.pr_review import SecurityFinding

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

        self.github_pr_service.post_pr_review_comment.return_value = {"id": 12345}

        await self.integration.generate_inline_comments([valid_finding, invalid_finding])

        self.github_pr_service.post_pr_review_comment.assert_called_once()
        call_args = self.github_pr_service.post_pr_review_comment.call_args[0]
        self.assertEqual(call_args[0], "owner")
        self.assertEqual(call_args[1], "repo")
        self.assertEqual(call_args[2], 42)
        payload = call_args[3]
        self.assertEqual(payload["path"], "file1.txt")
        self.assertEqual(payload["line"], 11)
        self.assertIn("**HIGH**: msg1", payload["body"])

        self.github_pr_service.post_pr_review.assert_called_once()
        review_call_args = self.github_pr_service.post_pr_review.call_args[0]
        self.assertEqual(review_call_args[0], "owner")
        self.assertEqual(review_call_args[1], "repo")
        self.assertEqual(review_call_args[2], 42)
        review_payload = review_call_args[3]
        self.assertIn("file1.txt:99", review_payload["body"])
        self.assertEqual(review_payload["event"], "COMMENT")

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

        self.github_pr_service.post_pr_review_comment.return_value = {"id": 12345}

        await self.integration.generate_inline_comments([finding1, finding2])

        self.github_pr_service.post_pr_review_comment.assert_called_once()
        call_args = self.github_pr_service.post_pr_review_comment.call_args[0]
        payload = call_args[3]
        self.assertIn("**HIGH**: msg1", payload["body"])
        self.assertNotIn("**LOW**: msg2", payload["body"])

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

        # First call fails, second succeeds
        self.github_pr_service.post_pr_review_comment.side_effect = [
            Exception("API error"),
            {"id": 54321}
        ]

        await self.integration.generate_inline_comments([finding1, finding2])

        self.assertEqual(self.github_pr_service.post_pr_review_comment.call_count, 2)

        # The failed one should go to fallback
        self.github_pr_service.post_pr_review.assert_called_once()
        review_call_args = self.github_pr_service.post_pr_review.call_args[0]
        review_payload = review_call_args[3]
        self.assertIn("file1.txt:11", review_payload["body"])

        # Second finding should have comment ID saved
        self.assertIsNone(finding1.github_comment_id)
        self.assertEqual(finding2.github_comment_id, "54321")

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
        self.github_pr_service.post_pr_review_comment.assert_not_called()
        self.github_pr_service.post_pr_review.assert_not_called()

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

        self.github_pr_service.post_pr_review_comment.return_value = {"id": 12345}

        await self.integration.generate_inline_comments([valid_finding_left])

        self.github_pr_service.post_pr_review_comment.assert_called_once()
        call_args = self.github_pr_service.post_pr_review_comment.call_args[0]
        payload = call_args[3]
        self.assertEqual(payload["path"], "file1.txt")
        self.assertEqual(payload["line"], 11)
        self.assertEqual(payload["side"], "LEFT")
        self.github_pr_service.post_pr_review.assert_not_called()

if __name__ == '__main__':
    unittest.main()
