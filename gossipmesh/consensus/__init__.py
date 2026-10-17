"""
GossipMesh Byzantine Fault Tolerant (BFT) Consensus Module.
Provides heterogeneous multi-model voting quorum, consensus scoring, and proposal validation.
"""

from .engine import ByzantineConsensusEngine, ModelVote, ConsensusResult
from .bft import BFTQuorumManager

__all__ = [
    "ByzantineConsensusEngine",
    "ModelVote",
    "ConsensusResult",
    "BFTQuorumManager",
]
