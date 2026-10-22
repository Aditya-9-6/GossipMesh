import unittest
import tempfile
from pathlib import Path
from gossipmesh.memetic import MemeticKnowledgeBase, KnowledgeMeme


class TestMemeticKnowledgeBase(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory and file for storage to avoid polluting real paths
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = Path(self.temp_dir.name) / "memes.json"

        # Initialize knowledge base with no default seeds if we clear them immediately
        self.kb = MemeticKnowledgeBase(storage_path=self.storage_path)
        # Clear out seeds to start with a clean state for deterministic tests
        self.kb.memes.clear()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_format_prompt_context_empty(self):
        # With no memes, it should return an empty string
        result = self.kb.format_prompt_context(repo="test_repo")
        self.assertEqual(result, "")

    def test_format_prompt_context_with_memes(self):
        # Add a couple of memes with high fitness scores
        self.kb.record_or_update(
            meme_id="meme_1",
            title="Test Meme 1",
            rule="Always do X.",
            anti_pattern="Doing Y instead of X.",
            correct_pattern="Do X.",
            repo="global"
        )
        self.kb.reward("meme_1", 2.0) # Ensure fitness is high enough

        self.kb.record_or_update(
            meme_id="meme_2",
            title="Test Meme 2",
            rule="Never do Z.",
            anti_pattern="Doing Z.",
            correct_pattern="Avoid Z.",
            repo="test_repo"
        )
        self.kb.reward("meme_2", 3.0)

        # Ensure correct string formatting
        result = self.kb.format_prompt_context(repo="test_repo")

        # Verify the header
        self.assertIn("### 🧬 GOSSIPED ARCHITECTURAL MEMES & HARD INVARIANTS:", result)

        # Verify meme_2 (higher fitness, should be first or just present)
        self.assertIn("- **Test Meme 2** (Fitness: 4.0★)", result)
        self.assertIn("  • Directive: Never do Z.", result)
        self.assertIn("  • Anti-Pattern To Avoid: Doing Z.", result)
        self.assertIn("  • Required Pattern: Avoid Z.", result)

        # Verify meme_1
        self.assertIn("- **Test Meme 1** (Fitness: 3.0★)", result)
        self.assertIn("  • Directive: Always do X.", result)
        self.assertIn("  • Anti-Pattern To Avoid: Doing Y instead of X.", result)
        self.assertIn("  • Required Pattern: Do X.", result)

    def test_format_prompt_context_repo_filtering(self):
        # Add memes for different repos
        self.kb.record_or_update(
            meme_id="meme_repo_a",
            title="Repo A Meme",
            rule="Rule A",
            anti_pattern="Anti A",
            correct_pattern="Correct A",
            repo="repo_a"
        )
        self.kb.reward("meme_repo_a", 5.0)

        self.kb.record_or_update(
            meme_id="meme_repo_b",
            title="Repo B Meme",
            rule="Rule B",
            anti_pattern="Anti B",
            correct_pattern="Correct B",
            repo="repo_b"
        )
        self.kb.reward("meme_repo_b", 5.0)

        self.kb.record_or_update(
            meme_id="meme_global",
            title="Global Meme",
            rule="Rule Global",
            anti_pattern="Anti Global",
            correct_pattern="Correct Global",
            repo="global"
        )
        self.kb.reward("meme_global", 5.0)

        # Check filtering for repo_a
        result_a = self.kb.format_prompt_context(repo="repo_a")
        self.assertIn("Repo A Meme", result_a)
        self.assertIn("Global Meme", result_a)
        self.assertNotIn("Repo B Meme", result_a)

        # Check filtering for repo_b
        result_b = self.kb.format_prompt_context(repo="repo_b")
        self.assertIn("Repo B Meme", result_b)
        self.assertIn("Global Meme", result_b)
        self.assertNotIn("Repo A Meme", result_b)


if __name__ == "__main__":
    unittest.main()
