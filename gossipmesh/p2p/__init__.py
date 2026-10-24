"""
P2P Module initialization.
"""

from __future__ import annotations

from gossipmesh.p2p.entropy import VectorClockEntropy
from gossipmesh.p2p.syncer import P2PSyncer

__all__ = ["VectorClockEntropy", "P2PSyncer"]
