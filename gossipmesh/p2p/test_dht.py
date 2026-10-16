import unittest
from unittest.mock import patch, MagicMock

from gossipmesh.p2p.dht import KademliaDHT
from gossipmesh.p2p.node import Node

class TestKademliaDHT(unittest.TestCase):

    def setUp(self):
        self.node = Node('node_id', '192.168.0.1', 8000)
        self.dht = KademliaDHT(self.node)

    def test_join_network(self):
        bootstrap_nodes = [Node('node1', '10.0.0.1', 8001), Node('node2', '10.0.0.2', 8002)]
        with patch('gossipmesh.p2p.dht.KademliaDHT.connect') as mock_connect:
            self.dht.join_network(bootstrap_nodes)
            mock_connect.assert_called_with(bootstrap_nodes)

    def test_find_node(self):
        # Test XOR metric routing
        pass

    def test_update_buckets(self):
        # Test bucket updates
        pass

    def test_ping_nodes(self):
        nodes = [Node('node3', '10.0.1.1', 8003), Node('node4', '10.0.1.2', 8004)]
        with patch('asyncio.gather') as mock_gather:
            self.dht.ping_nodes(nodes)
            mock_gather.assert_called_once()
