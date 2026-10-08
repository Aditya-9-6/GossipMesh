"""
Decentralized Task Auction & Contract Net Protocol.
Selects optimal agent personas for tasks via competitive capability bidding.
"""

from typing import List, Dict, Any, Optional

class AgentBid:
    def __init__(self, agent_id: str, specialty: str, bid_score: float, rationale: str):
        self.agent_id = agent_id
        self.specialty = specialty
        self.bid_score = max(0.0, min(100.0, bid_score))
        self.rationale = rationale

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "specialty": self.specialty,
            "bid_score": round(self.bid_score, 1),
            "rationale": self.rationale,
        }

class TaskAuctioneer:
    """Evaluates task specifications and elects winning agent nodes."""

    DOMAIN_KEYWORDS = {
        "concurrency_specialist": ["lock-free", "atomic", "ringbuffer", "mutex", "channel", "concurrency", "race"],
        "security_specialist": ["waf", "sanitizer", "injection", "jwt", "tls", "fingerprint", "xss", "cve"],
        "crypto_specialist": ["wireguard", "pqc", "kyber", "noise", "handshake", "encryption", "mtu"],
        "systems_specialist": ["simd", "ebpf", "streaming", "zero-allocation", "buffer", "memory", "cache"],
    }

    def generate_bids(self, task_title: str, task_body: str) -> List[AgentBid]:
        """Calculates domain fitness bids across standard specialized agent roles."""
        text = f"{task_title} {task_body}".lower()
        bids = []

        for role, keywords in self.DOMAIN_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in text)
            score = min(100.0, 40.0 + (matches * 15.0))
            rationale = f"Matched {matches} core domain keywords for {role}."
            bids.append(AgentBid(role, role, score, rationale))

        return bids

    def elect_winner(self, bids: List[AgentBid]) -> Optional[AgentBid]:
        if not bids:
            return None
        return max(bids, key=lambda b: b.bid_score)
