from typing import Dict, List, Any

class ModelVote:
    def __init__(self, voter_id: str, vote_data: Any, signature: str = ""):
        self.voter_id = voter_id
        self.vote_data = vote_data
        self.signature = signature

class ByzantineConsensusEngine:
    """Byzantine consensus engine for model updates and voting in GossipMesh."""
    def __init__(self, node_id: str, tolerance: float = 0.33):
        self.node_id = node_id
        self.tolerance = tolerance

    def validate_vote(self, vote: ModelVote) -> bool:
        return bool(vote.voter_id and vote.vote_data)

    def reach_consensus(self, votes: List[ModelVote]) -> Any:
        if not votes:
            return None
        # Simple majority or valid consensus logic
        valid_votes = [v for v in votes if self.validate_vote(v)]
        if len(valid_votes) >= len(votes) * (1.0 - self.tolerance):
            return valid_votes[0].vote_data
        return None
