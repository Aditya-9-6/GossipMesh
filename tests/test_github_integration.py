import unittest
import asyncio
from unittest.mock import AsyncMock

from gossipmesh.integrations.github import GitHubIntegration
from gossipmesh.models.pr_review import SecurityFinding
from gossipmesh.integrations.github_pr import GitHubPRService

class TestGitHubIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_generate_inline_comments(self):
        finding1 = SecurityFinding(
            id="FINDING-1",
            file_path="src/main.py",
            line=10,
            side="RIGHT",
            commit_sha="abcd123",
            severity="HIGH",
            message="SQL injection vulnerability",
            evidence="User input used directly in query",
            confidence_score=95,
            is_ai_generated=True
        )

        finding2 = SecurityFinding(
            id="FINDING-2",
            file_path="src/main.py",
            line=10,
            side="RIGHT",
            commit_sha="abcd123",
            severity="LOW",
            message="Use of print statement",
            is_ai_generated=True
            # missing evidence and confidence_score
        )

        finding3 = SecurityFinding(
            id="FINDING-3",
            file_path="src/main.py",
            line=10,
            side="RIGHT",
            commit_sha="abcd123",
            severity="HIGH",
            message="Another issue same line",
            evidence="Evidence",
            confidence_score=80,
            is_ai_generated=True
        )

        pr_service_mock = AsyncMock(spec=GitHubPRService)
        integration = GitHubIntegration(
            owner="test-owner",
            repo="test-repo",
            pr_number=1,
            github_pr_service=pr_service_mock
        )

        await integration.generate_inline_comments([finding1, finding2, finding3])

        pr_service_mock.post_pr_review_comment.assert_called_once()
        args, kwargs = pr_service_mock.post_pr_review_comment.call_args
        self.assertEqual(args[0], "test-owner")
        self.assertEqual(args[1], "test-repo")
        self.assertEqual(args[2], 1)

        payload = args[3]
        self.assertEqual(payload["commit_id"], "abcd123")
        self.assertEqual(payload["path"], "src/main.py")
        self.assertEqual(payload["line"], 10)
        self.assertEqual(payload["side"], "RIGHT")
        self.assertIn("FINDING-1", payload["body"])
        self.assertIn("FINDING-3", payload["body"])
        self.assertNotIn("FINDING-2", payload["body"])

        # Test duplicate prevention
        pr_service_mock.post_pr_review_comment.reset_mock()
        await integration.generate_inline_comments([finding1])
        pr_service_mock.post_pr_review_comment.assert_not_called()

if __name__ == '__main__':
    unittest.main()
