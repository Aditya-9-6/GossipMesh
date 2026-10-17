import asyncio
import logging
from typing import Dict, Set, Optional, Any

logger = logging.getLogger(__name__)


class BFTProposal:
    def __init__(self, proposal_id: str, proposer_id: str, payload: Any):
        self.proposal_id = proposal_id
        self.proposer_id = proposer_id
        self.payload = payload
        self.votes: Set[str] = set()


class BFTQuorumManager:
    """Manages 2/3 majority Byzantine Fault Tolerant voting quorums for consensus proposals."""

    def __init__(self, total_nodes: int):
        if total_nodes <= 0:
            raise ValueError("Total nodes must be greater than zero.")
        self.total_nodes = total_nodes
        self._proposals: Dict[str, BFTProposal] = {}
        self._lock = asyncio.Lock()

    @property
    def required_quorum(self) -> int:
        # 2/3 majority (strictly greater than 2/3, or ceiling of 2/3 * total)
        return (2 * self.total_nodes + 2) // 3

    async def create_proposal(self, proposal_id: str, proposer_id: str, payload: Any) -> BFTProposal:
        async with self._lock:
            if proposal_id in self._proposals:
                raise ValueError(f"Proposal {proposal_id} already exists.")
            proposal = BFTProposal(proposal_id, proposer_id, payload)
            self._proposals[proposal_id] = proposal
            logger.info(f"Created BFT proposal {proposal_id} by node {proposer_id}")
            return proposal

    async def cast_vote(self, proposal_id: str, node_id: str) -> bool:
        """Casts a vote for a proposal. Returns True if quorum is reached with this vote."""
        async with self._lock:
            if proposal_id not in self._proposals:
                raise KeyError(f"Proposal {proposal_id} not found.")
            
            proposal = self._proposals[proposal_id]
            proposal.votes.add(node_id)
            
            has_reached_quorum = len(proposal.votes) >= self.required_quorum
            logger.debug(f"Node {node_id} voted on proposal {proposal_id}. Current votes: {len(proposal.votes)}/{self.required_quorum}")
            return has_reached_quorum

    async def has_consensus(self, proposal_id: str) -> bool:
        async with self._lock:
            if proposal_id not in self._proposals:
                return False
            return len(self._proposals[proposal_id].votes) >= self.required_quorum

    async def get_proposal(self, proposal_id: str) -> Optional[BFTProposal]:
        async with self._lock:
            return self._proposals.get(proposal_id)
