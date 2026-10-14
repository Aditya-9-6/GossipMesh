"""
GossipMesh: Decentralized P2P Gossip Protocol Multi-Agent Autonomous Engineering Engine.

Provides an epidemic knowledge mesh, memetic learning with fitness scores,
Byzantine multi-model consensus, cross-repo schema synchronization, and
adversarial red-team pre-flight audits.
"""

from .auction import AgentBid, TaskAuctioneer
from .bridge import CrossRepoBridge, WireContract
from .consensus import ByzantineConsensusEngine, ModelVote
from .memetic import KnowledgeMeme, MemeticKnowledgeBase
from .node import GossipMessage, GossipNode, GossipTopic
from .oracle import BenchmarkRecord, PerformanceOracle
from .red_team import RedTeamAuditor, VulnerabilityProbe

__version__ = "0.1.0"
__all__ = [
    "AgentBid",
    "BenchmarkRecord",
    "ByzantineConsensusEngine",
    "CrossRepoBridge",
    "GossipMessage",
    "GossipNode",
    "GossipTopic",
    "KnowledgeMeme",
    "MemeticKnowledgeBase",
    "ModelVote",
    "PerformanceOracle",
    "RedTeamAuditor",
    "TaskAuctioneer",
    "VulnerabilityProbe",
    "WireContract",
]
