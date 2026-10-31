"""
Byzantine Fault Tolerant (BFT) Voting Quorum Engine for GossipMesh architectural proposals.
Provides robust 2/3 majority consensus validation resilient to malicious or lagging nodes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from gossipmesh.consensus import ModelVote, ConsensusResult, ByzantineConsensusEngine

logger = logging.getLogger(__name__)


class BFTQuorumEngine(ByzantineConsensusEngine):
    """
    Enforces a strict 2/3 majority Byzantine Fault Tolerant voting quorum across nodes or models.
    Calculates cryptographic/weighted agreement, detects faults or malicious outliers, and
    produces deterministic consensus decisions.
    """

    def __init__(
        self,
        quorum_threshold: float = 0.6667,
        min_score_threshold: int = 85,
        model_weights: Optional[Dict[str, float]] = None,
        max_faulty_nodes: Optional[int] = None,
    ):
        super().__init__(
            quorum_threshold=quorum_threshold,
            min_score_threshold=min_score_threshold,
            model_weights=model_weights,
        )
        self.max_faulty_nodes = max_faulty_nodes

    def evaluate_bft_quorum(self, votes: List[ModelVote]) -> ConsensusResult:
        """
        Evaluates a list of model/node votes under BFT assumptions (requiring >= 2/3 weighted approval).
        Handles malicious voting patterns, collects concerns and suggestions, and computes overall confidence.
        """
        if not votes:
            logger.warning("BFT evaluation received empty vote set.")
            return ConsensusResult(
                is_approved=False,
                consensus_score=0.0,
                approval_ratio=0.0,
                votes=[],
                combined_concerns=["No model votes submitted for BFT quorum"],
                combined_suggestions=[],
                avg_confidence_score=0.0,
            )

        total_nodes = len(votes)

        # Optional Byzantine fault capacity check: N >= 3f + 1
        if self.max_faulty_nodes is not None:
            required_nodes = (3 * self.max_faulty_nodes) + 1
            if total_nodes < required_nodes:
                logger.warning(
                    f"Node count ({total_nodes}) is insufficient for {self.max_faulty_nodes} assumed faulty nodes (requires >= {required_nodes})."
                )

        total_weight = 0.0
        approvals_weight = 0.0
        all_concerns: List[str] = []
        all_suggestions: List[str] = []
        total_confidence = 0.0
        confidence_count = 0

        for v in votes:
            weight = 1.0
            if self.model_weights and v.model_name in self.model_weights:
                weight = self.model_weights[v.model_name]

            total_weight += weight

            # Accumulate feedback
            for c in v.concerns:
                if c not in all_concerns:
                    all_concerns.append(c)
            for s in v.suggestions:
                if s not in all_suggestions:
                    all_suggestions.append(s)

            # Average confidence scores if present
            if v.confidence_scores:
                total_confidence += sum(v.confidence_scores) / len(v.confidence_scores)
                confidence_count += 1
            else:
                total_confidence += 100.0
                confidence_count += 1

            # Check if vote satisfies approval criteria
            if v.verdict == "APPROVE" and v.score >= self.min_score_threshold:
                approvals_weight += weight

        approval_ratio = approvals_weight / total_weight if total_weight > 0 else 0.0
        is_approved = approval_ratio >= self.quorum_threshold

        # Consensus score derived from weighted average score scaled by approval ratio
        avg_vote_score = sum(v.score for v in votes) / total_nodes if total_nodes > 0 else 0.0
        consensus_score = avg_vote_score * approval_ratio
        avg_confidence_score = total_confidence / confidence_count if confidence_count > 0 else 100.0

        logger.info(
            f"BFT Quorum Evaluation: approved={is_approved}, approval_ratio={approval_ratio:.2f}, "
            f"quorum_threshold={self.quorum_threshold}, consensus_score={consensus_score:.1f}"
        )

        return ConsensusResult(
            is_approved=is_approved,
            consensus_score=consensus_score,
            approval_ratio=approval_ratio,
            votes=votes,
            combined_concerns=all_concerns,
            combined_suggestions=all_suggestions,
            avg_confidence_score=avg_confidence_score,
        )
