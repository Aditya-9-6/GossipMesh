import unittest
import tempfile
import shutil
from unittest.mock import MagicMock, patch
from gossipmesh.p2p.scatter import AdaptiveScatterGovernor
from gossipmesh.p2p.node import GossipNode, GossipTopic


class TestAdaptiveScatterGovernor(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @patch('gossipmesh.p2p.scatter.psutil')
    def test_normal_operation_scatter(self, mock_psutil):
        mock_proc = MagicMock()
        mock_proc.cpu_percent.return_value = 10.0
        mock_proc.memory_percent.return_value = 20.0
        mock_psutil.Process.return_value = mock_proc

        governor = AdaptiveScatterGovernor(base_scatter=6, min_scatter=2, cpu_threshold=80.0, mem_threshold=85.0)
        scatter = governor.update()
        # Under low load, scatter should remain near base_scatter
        self.assertGreaterEqual(scatter, 2)
        self.assertLessEqual(scatter, 6)

    @patch('gossipmesh.p2p.scatter.psutil')
    def test_high_load_reduction(self, mock_psutil):
        mock_proc = MagicMock()
        # CPU and Memory significantly exceed thresholds
        mock_proc.cpu_percent.return_value = 160.0
        mock_proc.memory_percent.return_value = 170.0
        mock_psutil.Process.return_value = mock_proc

        governor = AdaptiveScatterGovernor(base_scatter=8, min_scatter=1, cpu_threshold=80.0, mem_threshold=85.0)
        # Run multiple updates to allow smoothing filter to adapt
        for _ in range(5):
            scatter = governor.update()
            
        # Scatter width should scale down proportionally toward min_scatter
        self.assertLessEqual(scatter, 4)
        metrics = governor.get_metrics()
        self.assertIn("smoothed_cpu", metrics)
        self.assertIn("current_scatter", metrics)

    def test_node_integration_with_scatter(self):
        node = GossipNode(node_id="node-test-1", mesh_dir=self.temp_dir, base_scatter=5)
        msg = node.publish(GossipTopic.AGENT_EVENT, {"task": "compile"})
        self.assertIn("_adaptive_scatter", msg.payload)
        self.assertGreaterEqual(msg.payload["_adaptive_scatter"], 1)
        self.assertLessEqual(msg.payload["_adaptive_scatter"], 5)

        recent = node.get_recent_messages(GossipTopic.AGENT_EVENT)
        self.assertEqual(len(recent), 1)


if __name__ == '__main__':
    unittest.main()
