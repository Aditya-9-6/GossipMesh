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
        "concurrency_specialist": {"lock-free": 2.0, "atomic": 1.5, "ringbuffer": 1.5, "mutex": 1.0, "channel": 1.0, "concurrency": 1.0, "race": 1.0},
        "security_specialist": {"waf": 2.0, "sanitizer": 1.5, "injection": 1.5, "jwt": 1.0, "tls": 1.0, "fingerprint": 1.0, "xss": 1.5, "cve": 2.0},
        "crypto_specialist": {"wireguard": 2.0, "pqc": 2.0, "kyber": 2.0, "noise": 1.5, "handshake": 1.0, "encryption": 1.0, "mtu": 1.0},
        "systems_specialist": {"simd": 2.0, "ebpf": 2.0, "streaming": 1.5, "zero-allocation": 2.0, "buffer": 1.0, "memory": 1.0, "cache": 1.0},
    }

    def generate_bids(self, task_title: str, task_body: str) -> List[AgentBid]:
        """Calculates domain fitness bids across standard specialized agent roles."""
        text = f"{task_title} {task_body}".lower()
        bids = []

        for role, keywords in self.DOMAIN_KEYWORDS.items():
            weighted_matches = sum(weight for kw, weight in keywords.items() if kw in text)
            score = min(100.0, 40.0 + (weighted_matches * 15.0))
            rationale = f"Matched weighted core domain keywords for {role}."
            bids.append(AgentBid(role, role, score, rationale))

        return bids

    def elect_winner(self, bids: List[AgentBid]) -> Optional[AgentBid]:
        if not bids:
            return None
        return max(bids, key=lambda b: b.bid_score)
