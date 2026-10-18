from typing import Dict, List, Tuple
import secrets
from gossipmesh.consensus.vss import VerifiableSecretSharing, Point, G, scalar_mult, point_add, CURVE_ORDER


class DKGNodeState:
    """Represents state of an individual node participating in Distributed Key Generation."""
    def __init__(self, node_id: int, total_nodes: int, threshold: int):
        self.node_id = node_id
        self.total_nodes = total_nodes
        self.threshold = threshold
        self.secret_polynomial: List[int] = []
        self.commitments: List[Point] = []
        self.received_shares: Dict[int, int] = {}
        self.verified_shares: Dict[int, int] = {}
        self.all_commitments: Dict[int, List[Point]] = {}
        self.private_key_share: int = 0
        self.group_public_key: Point = Point(0, 0)

    def phase1_generate_shares(self) -> Tuple[List[int], List[Point]]:
        """Phase 1: Generate random secret polynomial and Feldman commitments."""
        secret = secrets.randbelow(CURVE_ORDER - 1) + 1
        self.secret_polynomial = VerifiableSecretSharing.generate_polynomial(secret, self.threshold)
        self.commitments = VerifiableSecretSharing.commit(self.secret_polynomial)
        return self.secret_polynomial, self.commitments

    def phase2_compute_share_for(self, peer_id: int) -> int:
        """Computes secret evaluation share for peer_id."""
        return VerifiableSecretSharing.evaluate_polynomial(self.secret_polynomial, peer_id)

    def phase3_receive_and_verify_share(self, sender_id: int, share_y: int, commitments: List[Point]) -> bool:
        """Phase 3: Verify received share against broadcaster's commitments."""
        self.all_commitments[sender_id] = commitments
        if VerifiableSecretSharing.verify_share(self.node_id, share_y, commitments):
            self.verified_shares[sender_id] = share_y
            return True
        return False

    def phase4_compute_private_key_share(self):
        """Phase 4: Accumulate verified shares to derive final node private key share."""
        total_share = 0
        for sender_id, share in self.verified_shares.items():
            total_share = (total_share + share) % CURVE_ORDER
        # Also include own share generated for self
        own_share = VerifiableSecretSharing.evaluate_polynomial(self.secret_polynomial, self.node_id)
        total_share = (total_share + own_share) % CURVE_ORDER
        self.private_key_share = total_share

    def phase5_compute_group_public_key(self):
        """Phase 5: Aggregate constant term commitments to form collective group public key."""
        group_pk = Point(0, 0)
        for sender_id, comms in self.all_commitments.items():
            if comms:
                group_pk = point_add(group_pk, comms[0])
        # Add own commitment constant term
        if self.commitments:
            group_pk = point_add(group_pk, self.commitments[0])
        self.group_public_key = group_pk
