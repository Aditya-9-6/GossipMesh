import unittest
from gossipmesh.p2p.rto import RTOEstimator


class TestRTOEstimator(unittest.TestCase):
    def setUp(self):
        self.estimator = RTOEstimator()

    def test_initial_sample(self):
        rto = self.estimator.update(0.1)
        self.assertEqual(self.estimator.srtt, 0.1)
        self.assertEqual(self.estimator.rttvar, 0.05)
        self.assertGreaterEqual(rto, self.estimator.min_rto)

    def test_subsequent_updates(self):
        self.estimator.update(0.1)
        rto = self.estimator.update(0.12)
        self.assertIsNotNone(self.estimator.srtt)
        self.assertIsNotNone(self.estimator.rttvar)
        self.assertGreater(rto, 0.0)

    def test_negative_sample_raises_error(self):
        with self.assertRaises(ValueError):
            self.estimator.update(-0.05)

    def test_rto_clamping(self):
        # Test max RTO bound
        self.estimator.srtt = 100.0
        self.estimator.rttvar = 10.0
        self.estimator.rto = self.estimator.update(100.0)
        self.assertEqual(self.estimator.rto, self.estimator.max_rto)

        # Test min RTO bound
        self.estimator.reset()
        self.estimator.srtt = 0.001
        self.estimator.rttvar = 0.0001
        self.estimator.rto = self.estimator.update(0.001)
        self.assertEqual(self.estimator.rto, self.estimator.min_rto)

    def test_reset(self):
        self.estimator.update(0.2)
        self.estimator.reset()
        self.assertIsNone(self.estimator.srtt)
        self.assertIsNone(self.estimator.rttvar)
        self.assertEqual(self.estimator.rto, 1.0)


if __name__ == "__main__":
    unittest.main()
