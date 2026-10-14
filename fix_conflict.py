with open("tests/test_gossipmesh.py", "r") as f:
    content = f.read()

conflict_start = content.find("<<<<<<< Updated upstream")
conflict_end = content.find(">>>>>>> Stashed changes") + len(">>>>>>> Stashed changes")

if conflict_start != -1 and conflict_end != -1:
    resolved = """
    def test_byzantine_consensus_zero_weight(self):
        engine = ByzantineConsensusEngine(
            quorum_threshold=0.66,
            min_score_threshold=80,
            model_weights={"flash-3.8": 0.0, "pro-3.1": 0.0}
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
            f.write("{invalid_json: 'missing_quotes'}\\n")

        # Write valid JSON to the log file
        valid_msg = {"message_id": "valid_123", "topic": GossipTopic.HEARTBEATS.value, "origin_node": "other_node", "payload": {}}
        with open(node.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(valid_msg) + "\\n")

        # Write another malformed JSON to the log file
        with open(node.log_file, "a", encoding="utf-8") as f:
            f.write("completely unparseable string\\n")

        # Should not crash and should return the 1 valid message
        messages = node.sync()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message_id, "valid_123")
"""
    new_content = content[:conflict_start] + resolved.lstrip("\n") + content[conflict_end:]
    with open("tests/test_gossipmesh.py", "w") as f:
        f.write(new_content)
