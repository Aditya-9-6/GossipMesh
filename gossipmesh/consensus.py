"""
Heterogeneous Multi-Model Byzantine Consensus Engine.
Audits code proposals across multiple model personas and enforces quorum consensus.
"""

from typing import List, Dict, Any, Optional

class ModelVote:
    def __init__(
        self,
        model_name: str,
        verdict: str,
        score: int,
        concerns: Optional[List[str]] = None,
        suggestions: Optional[List[str]] = None,
    ):
        self.model_name = model_name
        self.verdict = verdict.upper()  # APPROVE, REVISE, REJECT
        self.score = max(0, min(100, score))
        self.concerns = concerns or []
        self.suggestions = suggestions or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "verdict": self.verdict,
            "score": self.score,
            "concerns": self.concerns,
            "suggestions": self.suggestions,
        }

class ConsensusResult:
    def __init__(
        self,
        is_approved: bool,
        consensus_score: float,
        approval_ratio: float,
        votes: List[ModelVote],
        combined_concerns: List[str],
        combined_suggestions: List[str],
    ):
        self.is_approved = is_approved
        self.consensus_score = consensus_score
        self.approval_ratio = approval_ratio
        self.votes = votes
        self.combined_concerns = combined_concerns
        self.combined_suggestions = combined_suggestions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_approved": self.is_approved,
            "consensus_score": round(self.consensus_score, 1),
            "approval_ratio": round(self.approval_ratio, 2),
            "votes": [v.to_dict() for v in self.votes],
            "combined_concerns": self.combined_concerns,
            "combined_suggestions": self.combined_suggestions,
        }

class ByzantineConsensusEngine:
    """Enforces Byzantine Fault Tolerant quorum across multi-model peer audits."""
    def __init__(self, quorum_threshold: float = 0.66, min_score_threshold: int = 85, model_weights: Optional[Dict[str, float]] = None):
        self.quorum_threshold = quorum_threshold
        self.min_score_threshold = min_score_threshold
        self.model_weights = model_weights

    def evaluate(self, votes: List[ModelVote]) -> ConsensusResult:
        if not votes:
            return ConsensusResult(
                is_approved=False,
                consensus_score=0.0,
                approval_ratio=0.0,
                votes=[],
                combined_concerns=["No model votes submitted"],
                combined_suggestions=[]
            )

        if self.model_weights:
            total_weight = sum(self.model_weights.get(v.model_name, 1.0) for v in votes)
            approvals_weight = sum(self.model_weights.get(v.model_name, 1.0) for v in votes if v.verdict == "APPROVE" and v.score >= self.min_score_threshold)
            approval_ratio = approvals_weight / total_weight if total_weight > 0 else 0.0
            avg_score = sum(v.score * self.model_weights.get(v.model_name, 1.0) for v in votes) / total_weight if total_weight > 0 else 0.0
        else:
            approvals = sum(1 for v in votes if v.verdict == "APPROVE" and v.score >= self.min_score_threshold)
            approval_ratio = approvals / len(votes)
            avg_score = sum(v.score for v in votes) / len(votes)

        all_concerns = []
        all_suggestions = []
        for v in votes:
            for c in v.concerns:
                if c not in all_concerns:
                    all_concerns.append(c)
            for s in v.suggestions:
                if s not in all_suggestions:
                    all_suggestions.append(s)

        is_approved = (approval_ratio >= self.quorum_threshold) and (avg_score >= self.min_score_threshold)

        return ConsensusResult(
            is_approved=is_approved,
            consensus_score=avg_score,
            approval_ratio=approval_ratio,
            votes=votes,
            combined_concerns=all_concerns,
            combined_suggestions=all_suggestions,
        )
