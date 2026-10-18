from typing import Dict, List, Any, Optional

class ModelVote:
    def __init__(self, voter_id: str, vote_data: Any, signature: str = ""):
        self.voter_id = voter_id
        self.vote_data = vote_data
        self.signature = signature

class ByzantineConsensusEngine:
    """Byzantine consensus engine for model updates and voting in GossipMesh."""
    def __init__(
        self,
        node_id: Optional[str] = None,
        tolerance: float = 0.33,
        quorum_threshold: Optional[float] = None,
        min_score_threshold: Optional[float] = None,
        model_weights: Optional[Dict[str, float]] = None
    ):
        self.node_id = node_id or "default-node"
        self.tolerance = tolerance
        self.quorum_threshold = quorum_threshold if quorum_threshold is not None else (1.0 - tolerance)
        self.min_score_threshold = min_score_threshold or 0
        self.model_weights = model_weights or {}

    def validate_vote(self, vote: ModelVote) -> bool:
        return bool(vote.voter_id and vote.vote_data)

    def reach_consensus(self, votes: List[ModelVote]) -> Any:
        if not votes:
            return None
        valid_votes = [v for v in votes if self.validate_vote(v)]
        if len(valid_votes) >= len(votes) * self.quorum_threshold:
            return valid_votes[0].vote_data
        return None
