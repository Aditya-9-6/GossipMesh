"""
Unit tests for the Byzantine Fault Tolerant (BFT) Voting Quorum Engine.
"""

import unittest
from gossipmesh.consensus import ModelVote
from gossipmesh.consensus.bft import BFTQuorumEngine


class TestBFTQuorumEngine(unittest.TestCase):
    def test_bft_quorum_success(self):
        votes = [
            ModelVote(model_name="gpt-4", verdict="APPROVE", score=90, concerns=[], suggestions=["Looks good"]),
            ModelVote(model_name="claude-3", verdict="APPROVE", score=88, concerns=[], suggestions=[]),
            ModelVote(model_name="deepseek", verdict="REJECT", score=40, concerns=["Security risk"], suggestions=["Fix auth"]),
        ]
        # 2 out of 3 approvals = 66.67%, meeting standard 0.66 quorum threshold
        engine = BFTQuorumEngine(quorum_threshold=0.66, min_score_threshold=85)
        result = engine.evaluate_bft_quorum(votes)

        self.assertTrue(result.is_approved)
        self.assertGreaterEqual(result.approval_ratio, 0.66)
        self.assertIn("Security risk", result.combined_concerns)
        self.assertIn("Fix auth", result.combined_suggestions)

    def test_bft_quorum_failure(self):
        votes = [
            ModelVote(model_name="gpt-4", verdict="APPROVE", score=90),
            ModelVote(model_name="claude-3", verdict="REJECT", score=50, concerns=["Bug found"]),
            ModelVote(model_name="deepseek", verdict="REVISE", score=70, concerns=["Refactor required"]),
        ]
        # Only 1/3 approval = 33.3%, failing quorum
        engine = BFTQuorumEngine(quorum_threshold=0.66, min_score_threshold=85)
        result = engine.evaluate_bft_quorum(votes)

        self.assertFalse(result.is_approved)
        self.assertLess(result.approval_ratio, 0.66)
        self.assertEqual(len(result.combined_concerns), 2)

    def test_bft_empty_votes(self):
        engine = BFTQuorumEngine()
        result = engine.evaluate_bft_quorum([])

        self.assertFalse(result.is_approved)
        self.assertEqual(result.approval_ratio, 0.0)
        self.assertEqual(result.consensus_score, 0.0)
        self.assertTrue(any("No model votes" in c for c in result.combined_concerns))

    def test_bft_weighted_quorum(self):
        weights = {"trusted-model": 2.0, "untrusted-model": 1.0}
        votes = [
            ModelVote(model_name="trusted-model", verdict="APPROVE", score=95),
            ModelVote(model_name="untrusted-model", verdict="REJECT", score=30),
        ]
        # Trusted model has weight 2.0 out of total 3.0 -> ratio 2/3 (66.67%)
        engine = BFTQuorumEngine(quorum_threshold=0.66, min_score_threshold=85, model_weights=weights)
        result = engine.evaluate_bft_quorum(votes)

        self.assertTrue(result.is_approved)
        self.assertAlmostEqual(result.approval_ratio, 0.6666, places=3)


if __name__ == "__main":
    unittest.main()
