import unittest
from gossipmesh.p2p.scoring import PeerScoreTracker


class TestPeerScoreTracker(unittest.TestCase):
    def test_scoring_initialization(self):
        tracker = PeerScoreTracker()
        self.assertIsNotNone(tracker)


if __name__ == "__main__":
    unittest.main()
