import unittest
import asyncio
from gossipmesh.consensus.bft import BFTQuorumManager


class TestBFTQuorumManager(unittest.TestCase):

    def test_invalid_total_nodes(self):
        with self.assertRaises(ValueError):
            BFTQuorumManager(0)

    def test_quorum_calculation(self):
        # 1 node -> quorum 1
        self.assertEqual(BFTQuorumManager(1).required_quorum, 1)
        # 3 nodes -> 2/3 is 2
        self.assertEqual(BFTQuorumManager(3).required_quorum, 2)
        # 4 nodes -> (8+2)//3 = 3
        self.assertEqual(BFTQuorumManager(4).required_quorum, 3)
        # 10 nodes -> (20+2)//3 = 7
        self.assertEqual(BFTQuorumManager(10).required_quorum, 7)

    def test_bft_proposal_lifecycle_async(self):
        async def run_test():
            manager = BFTQuorumManager(total_nodes=4)
            # Quorum needed for 4 nodes is 3
            self.assertEqual(manager.required_quorum, 3)

            proposal = await manager.create_proposal("prop-1", "node-1", {"action": "upgrade"})
            self.assertEqual(proposal.proposal_id, "prop-1")

            # Vote 1
            reached = await manager.cast_vote("prop-1", "node-1")
            self.assertFalse(reached)
            self.assertFalse(await manager.has_consensus("prop-1"))

            # Vote 2
            reached = await manager.cast_vote("prop-1", "node-2")
            self.assertFalse(reached)

            # Vote 3 (reaches quorum of 3)
            reached = await manager.cast_vote("prop-1", "node-3")
            self.assertTrue(reached)
            self.assertTrue(await manager.has_consensus("prop-1"))

            # Duplicate vote from node-3 shouldn't cause issues
            reached_again = await manager.cast_vote("prop-1", "node-3")
            self.assertTrue(reached_again)

            # Test nonexistent proposal vote
            with self.assertRaises(KeyError):
                await manager.cast_vote("nonexistent", "node-1")

            # Test duplicate proposal creation
            with self.assertRaises(ValueError):
                await manager.create_proposal("prop-1", "node-2", {})

            missing = await manager.get_proposal("nonexistent")
            self.assertIsNone(missing)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
