from __future__ import annotations

import secrets
import logging
from typing import Dict, List, Tuple, Optional

from gossipmesh.consensus.vss import VSSScheme

logger = logging.getLogger(__name__)


class DKGNode:
    def __init__(self, node_id: str, node_index: int, total_nodes: int, threshold: int):
        self.node_id = node_id
        self.node_index = node_index
        self.total_nodes = total_nodes
        self.threshold = threshold
        self.vss = VSSScheme()

        self.secret_polynomial: List[int] = []
        self.commitments: List[int] = []
        self.my_secret_share: int = 0

        self.received_shares: Dict[int, int] = {}
        self.received_commitments: Dict[int, List[int]] = {}
        self.verified_shares: List[Tuple[int, int]] = []

        self.collective_public_key: Optional[int] = None
        self.node_private_share: Optional[int] = None

    def phase1_propose(self) -> Tuple[List[int], List[int]]:
        self.my_secret_share = secrets.randbelow(self.vss.order - 1) + 1
        self.secret_polynomial = self.vss.generate_polynomial(self.my_secret_share, self.threshold)
        self.commitments = self.vss.create_commitments(self.secret_polynomial)
        return self.commitments, self.secret_polynomial

    def compute_peer_share(self, peer_index: int) -> int:
        return self.vss.evaluate_polynomial(self.secret_polynomial, peer_index)

    def receive_share_and_commitments(
        self,
        sender_index: int,
        share: int,
        commitments: List[int],
    ) -> bool:
        return self.process_peer_contribution(sender_index, share, commitments)

    def process_peer_contribution(self, sender_index: int, share_y: int, commitments: List[int]) -> bool:
        if self.vss.verify_share(self.node_index, share_y, commitments):
            self.received_shares[sender_index] = share_y
            self.received_commitments[sender_index] = commitments
            return True
        logger.warning(
            f"Node {self.node_id} rejected share from sender {sender_index} due to VSS verification failure."
        )
        return False

    def finalize_dkg(self) -> int:
        if len(self.received_shares) < self.threshold:
            raise ValueError(
                f"Insufficient valid shares collected: {len(self.received_shares)} < threshold {self.threshold}"
            )

        total_private_share = sum(self.received_shares.values()) % self.vss.order
        self.node_private_share = total_private_share

        joint_pub_key = 1
        for comms in self.received_commitments.values():
            joint_pub_key = (joint_pub_key * comms[0]) % self.vss.order

        self.collective_public_key = joint_pub_key
        return joint_pub_key


class DistributedKeyGenerationProtocol:
    def __init__(self, nodes: List[DKGNode], threshold: int):
        self.nodes = nodes
        self.threshold = threshold

    def run_dkg_setup(self) -> bool:
        commitments_map: Dict[int, List[int]] = {}
        polynomials_map: Dict[int, List[int]] = {}

        for node in self.nodes:
            comms, polys = node.phase1_propose()
            commitments_map[node.node_index] = comms
            polynomials_map[node.node_index] = polys

        for receiver in self.nodes:
            for sender in self.nodes:
                poly = polynomials_map[sender.node_index]
                share_y = receiver.vss.evaluate_polynomial(poly, receiver.node_index) if poly else 0
                receiver.process_peer_contribution(sender.node_index, share_y, commitments_map[sender.node_index])

        joint_keys = set()
        for node in self.nodes:
            pub_key = node.finalize_dkg()
            joint_keys.add(pub_key)

        return len(joint_keys) == 1
