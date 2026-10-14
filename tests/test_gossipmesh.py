"""
Comprehensive Unit Test Suite for GossipMesh.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from gossipmesh.auction import TaskAuctioneer
from gossipmesh.bridge import CrossRepoBridge
from gossipmesh.consensus import ByzantineConsensusEngine, ModelVote
from gossipmesh.memetic import MemeticKnowledgeBase
from gossipmesh.node import GossipNode, GossipTopic
from gossipmesh.oracle import PerformanceOracle
from gossipmesh.red_team import RedTeamAuditor


class TestGossipMesh(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_p2p_gossip_dissemination(self):
        node_a = GossipNode("node_alpha", mesh_dir=self.test_dir)
        node_b = GossipNode("node_beta", mesh_dir=self.test_dir)

        # Node A broadcasts anti-pattern
        received_by_b = []
        node_b.subscribe(
            GossipTopic.ANTI_PATTERNS, lambda msg: received_by_b.append(msg)
        )

        msg = node_a.publish(
            GossipTopic.ANTI_PATTERNS,
            {"rule": "Use atomic buckets, avoid mutex on hot path"},
            repo="DevProxy",
        )
        self.assertIsNotNone(msg.message_id)

        # Node B runs anti-entropy sync
        synced = node_b.sync()
        self.assertEqual(len(synced), 1)
        self.assertEqual(len(received_by_b), 1)
        self.assertEqual(
            received_by_b[0].payload["rule"],
            "Use atomic buckets, avoid mutex on hot path",
        )

    def test_memetic_fitness_evolution(self):
        memes_path = Path(self.test_dir) / "memes.json"
        kb = MemeticKnowledgeBase(storage_path=memes_path)

        # Initial seed check
        top = kb.get_top_memes()
        self.assertTrue(len(top) > 0)
        initial_score = top[0].fitness_score

        # Reward meme
        kb.reward(top[0].meme_id, delta=2.0)
        self.assertEqual(top[0].fitness_score, initial_score + 2.0)

        # Penalize meme
        kb.penalize(top[0].meme_id, delta=1.0)
        self.assertEqual(top[0].fitness_score, initial_score + 1.0)

        # Context generation
        context = kb.format_prompt_context()
        self.assertIn("GOSSIPED ARCHITECTURAL MEMES", context)

    def test_byzantine_consensus_empty_votes(self):
        engine = ByzantineConsensusEngine()
        result = engine.evaluate([])

        self.assertFalse(result.is_approved)
        self.assertEqual(result.consensus_score, 0.0)
        self.assertEqual(result.approval_ratio, 0.0)
        self.assertEqual(result.votes, [])
        self.assertEqual(result.combined_concerns, ["No model votes submitted"])
        self.assertEqual(result.combined_suggestions, [])
        self.assertEqual(result.avg_confidence_score, 0.0)

    def test_byzantine_consensus_quorum(self):
        engine = ByzantineConsensusEngine(quorum_threshold=0.66, min_score_threshold=80)

        # Unanimous approval
        votes = [
            ModelVote("flash-3.8", "APPROVE", 95),
            ModelVote("pro-3.1", "APPROVE", 90),
            ModelVote("lite-3.1", "APPROVE", 88),
        ]
        result = engine.evaluate(votes)
        self.assertTrue(result.is_approved)
        self.assertGreaterEqual(result.consensus_score, 90.0)

        # Dissenting vote failing quorum
        divided_votes = [
            ModelVote("flash-3.8", "APPROVE", 95),
            ModelVote(
                "pro-3.1", "REJECT", 45, concerns=["Severe data race in map access"]
            ),
            ModelVote("lite-3.1", "REVISE", 60, concerns=["Mutex used on hot path"]),
        ]
        fail_result = engine.evaluate(divided_votes)
        self.assertFalse(fail_result.is_approved)
        self.assertIn("Severe data race in map access", fail_result.combined_concerns)

        # Weighted model consensus
        weighted_engine = ByzantineConsensusEngine(
            quorum_threshold=0.66,
            min_score_threshold=80,
            model_weights={"flash-3.8": 0.5, "pro-3.1": 2.0, "lite-3.1": 0.5},
        )
        weighted_result = weighted_engine.evaluate(divided_votes)
        self.assertFalse(weighted_result.is_approved)
        # Weight calculations:
        # total_weight = 0.5 + 2.0 + 0.5 = 3.0
        # approvals_weight = 0.5 (only flash-3.8 approves and >= 80)
        # approval_ratio = 0.5 / 3.0 ≈ 0.166... which is < 0.66
        self.assertLess(weighted_result.approval_ratio, 0.2)

    def test_byzantine_consensus_zero_weight(self):
        engine = ByzantineConsensusEngine(
            quorum_threshold=0.66,
            min_score_threshold=80,
            model_weights={"flash-3.8": 0.0, "pro-3.1": 0.0},
        )

        votes = [
            ModelVote("flash-3.8", "APPROVE", 95),
            ModelVote("pro-3.1", "APPROVE", 90),
        ]

        # This shouldn't raise a ZeroDivisionError due to total_weight=0.0
        result = engine.evaluate(votes)
        self.assertEqual(result.approval_ratio, 0.0)
        self.assertEqual(result.consensus_score, 0.0)
        self.assertFalse(result.is_approved)

    def test_node_sync_malformed_json_error_path(self):
        import json

        node = GossipNode("node_sync_error", mesh_dir=self.test_dir)

        # Write malformed JSON to the log file
        with open(node.log_file, "a", encoding="utf-8") as f:
            f.write("{invalid_json: 'missing_quotes'}\n")

        # Write valid JSON to the log file
        valid_msg = {
            "message_id": "valid_123",
            "topic": GossipTopic.HEARTBEATS.value,
            "origin_node": "other_node",
            "payload": {},
        }
        with open(node.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(valid_msg) + "\n")

        # Write another malformed JSON to the log file
        with open(node.log_file, "a", encoding="utf-8") as f:
            f.write("completely unparseable string\n")

        # Should not crash and should return the 1 valid message
        messages = node.sync()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message_id, "valid_123")

    def test_node_cleanup_ledger(self):
        import json
        import time

        node = GossipNode("node_cleaner", mesh_dir=self.test_dir)

        # Publish two messages, one recent, one artificially expired
        msg1 = node.publish(GossipTopic.HEARTBEATS, {"status": "alive"})
        msg2 = node.publish(GossipTopic.HEARTBEATS, {"status": "alive"})

        # Artificially expire msg1 in the ledger
        lines = []
        with open(node.log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        with open(node.log_file, "w", encoding="utf-8") as f:
            for line in lines:
                data = json.loads(line)
                if data["message_id"] == msg1.message_id:
                    data["timestamp"] = time.time() - (
                        data.get("ttl", 10) * 3600 + 100
                    )  # strictly expired
                f.write(json.dumps(data) + "\n")

        # Call cleanup
        node.cleanup_ledger()

        # Verify
        remaining = []
        with open(node.log_file, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line.strip())
                remaining.append(data["message_id"])

        self.assertEqual(len(remaining), 1)
        self.assertIn(msg2.message_id, remaining)
        self.assertNotIn(msg1.message_id, remaining)

    def test_red_team_auditor(self):
        auditor = RedTeamAuditor()
        bad_code = """
        func recordLatency(d time.Duration) {
            mu.Lock()
            defer mu.Unlock()
            slices = make([]time.Duration, len(all))
        }
        """
        probes = auditor.audit_diff(bad_code)
        self.assertTrue(len(probes) >= 2)
        categories = [p.category for p in probes]
        self.assertIn("Concurrency Lock Contention", categories)
        self.assertIn("Unbounded Heap Allocation", categories)

    def test_cross_repo_bridge_codegen(self):
        bridge = CrossRepoBridge()
        bridge.register(
            name="TrafficMetric",
            version=1,
            fields={"latency_ms": "int64", "client_ip": "string", "is_tls": "bool"},
            source_repo="DevProxy",
        )
        go_code = bridge.get_go_definitions()
        rust_code = bridge.get_rust_definitions()

        self.assertIn("type TrafficMetric struct", go_code)
        self.assertIn("LatencyMs int64", go_code)
        self.assertIn("pub struct TrafficMetric", rust_code)
        self.assertIn("pub latency_ms: i64", rust_code)

    def test_performance_oracle_veto(self):
        oracle = PerformanceOracle()
        oracle.record("serve_http", ns_per_op=120.5, bytes_per_op=0, allocs_per_op=0)

        # Should pass with 0 allocs
        regressed, msg = oracle.evaluate_regression(
            "serve_http", current_allocs=0, current_bytes=0
        )
        self.assertFalse(regressed)

        # Should VETO with 1 allocation
        regressed, msg = oracle.evaluate_regression(
            "serve_http", current_allocs=1, current_bytes=32
        )
        self.assertTrue(regressed)
        self.assertIn("VETO", msg)

    def test_task_auction_bidding(self):
        auctioneer = TaskAuctioneer()
        bids = auctioneer.generate_bids(
            task_title="feat(crypto): Add WireGuard MTU discovery with Kyber PQC handshake",
            task_body="Implements post-quantum encryption for tunnels.",
        )
        winner = auctioneer.elect_winner(bids)
        self.assertIsNotNone(winner)
        self.assertEqual(winner.specialty, "crypto_specialist")

    def test_node_cleanup_ledger_error(self):
        import contextlib
        import io
        from unittest.mock import patch

        node = GossipNode("test_node", mesh_dir=self.test_dir)
        # Create an empty file so the initial exists() check passes
        node.log_file.touch()

        with patch("builtins.open", side_effect=OSError("Permission denied")):
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                node.cleanup_ledger()
            self.assertIn(
                "[test_node] Ledger cleanup error: Permission denied", f.getvalue()
            )


if __name__ == "__main__":
    unittest.main()
