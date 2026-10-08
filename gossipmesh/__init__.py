"""
GossipMesh: Decentralized P2P Gossip Protocol Multi-Agent Autonomous Engineering Engine.

Provides an epidemic knowledge mesh, memetic learning with fitness scores,
Byzantine multi-model consensus, cross-repo schema synchronization, and
adversarial red-team pre-flight audits.
"""

from .node import GossipNode, GossipMessage, GossipTopic
from .memetic import MemeticKnowledgeBase, KnowledgeMeme
from .consensus import ByzantineConsensusEngine, ModelVote
from .red_team import RedTeamAuditor, VulnerabilityProbe
from .bridge import CrossRepoBridge, WireContract
from .oracle import PerformanceOracle, BenchmarkRecord
from .auction import TaskAuctioneer, AgentBid

__version__ = "0.1.0"
__all__ = [
    "GossipNode",
    "GossipMessage",
    "GossipTopic",
    "MemeticKnowledgeBase",
    "KnowledgeMeme",
    "ByzantineConsensusEngine",
    "ModelVote",
    "RedTeamAuditor",
    "VulnerabilityProbe",
    "CrossRepoBridge",
    "WireContract",
    "PerformanceOracle",
    "BenchmarkRecord",
    "TaskAuctioneer",
    "AgentBid",
]
