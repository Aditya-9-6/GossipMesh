"""
Consensus package initialization.
"""

from typing import List, Dict, Any, Optional

from gossipmesh.consensus.byzantine import ByzantineConsensusEngine, ModelVote, ConsensusResult
from gossipmesh.consensus.raft import RaftLogCompactionEngine

__all__ = [
    "ByzantineConsensusEngine",
    "ModelVote",
    "ConsensusResult",
    "RaftLogCompactionEngine",
]
