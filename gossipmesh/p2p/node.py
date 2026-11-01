from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from gossipmesh.p2p.churn import ChurnManager
from gossipmesh.p2p.entropy import MerkleSyncer
from gossipmesh.p2p.merkle import MerkleDAG

logger = logging.getLogger(__name__)


class PeerNode:
    """
    Represents a remote peer node in the GossipMesh cluster.
    """

    def __init__(self, peer_id: str, address: str, port: int):
        self.peer_id = peer_id
        self.address = address
        self.port = port
        self.last_seen = time.time()
        self.metadata_vector: Dict[str, int] = {}


class P2PNode:
    """
    Main P2P Node managing peering, gossip broadcast, and entropy synchronization.
    """

    def __init__(self, node_id: str, bind_address: str, bind_port: int):
        self.node_id = node_id
        self.bind_address = bind_address
        self.bind_port = bind_port
        self.peers: Dict[str, PeerNode] = {}
        self.churn_manager = ChurnManager(node_id=node_id)
        self.state_dag = MerkleDAG()
        self.syncer = MerkleSyncer(node_id=node_id, dag=self.state_dag)
        self._running = False
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        self._running = True
        logger.info(f"P2P Node {self.node_id} started on {self.bind_address}:{self.bind_port}")

    async def stop(self) -> None:
        self._running = False
        logger.info(f"P2P Node {self.node_id} stopped.")

    def add_peer(self, peer_id: str, address: str, port: int) -> PeerNode:
        peer = PeerNode(peer_id, address, port)
        self.peers[peer_id] = peer
        return peer

    def remove_peer(self, peer_id: str) -> None:
        if peer_id in self.peers:
            del self.peers[peer_id]

    def record_peer_heartbeat(self, peer_id: str, metadata_vector: Dict[str, int]) -> Tuple[bool, float]:
        """Ingests a heartbeat vector and evaluates entropy-based churn defense."""
        is_sybil, variance = self.churn_manager.process_heartbeat(peer_id, metadata_vector)
        if peer_id in self.peers:
            self.peers[peer_id].last_seen = time.time()
            self.peers[peer_id].metadata_vector = metadata_vector
        return is_sybil, variance

    async def reconcile_state(self, peer_id: str, remote_root_hash: str) -> List[str]:
        """Reconciles local Merkle state DAG with a remote peer."""
        return self.state_dag.compare_roots(remote_root_hash, [])
