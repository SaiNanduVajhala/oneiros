"""
Oneiros Sleep Subsystem - MemoryLifecycleEngine
Handles retention score calculation and memory lifecycle transitions (ACTIVE -> INACTIVE -> ARCHIVED -> FORGOTTEN).
"""

import math
import logging
from typing import Tuple, Optional
from datetime import datetime
from domain.memory import MemoryNode

logger = logging.getLogger("oneiros.kernel.sleep.lifecycle_engine")

class MemoryLifecycleEngine:
    """
    Unified engine managing memory retention scores and status transitions.
    """
    def __init__(
        self,
        active_to_inactive_threshold: float = 0.50,
        inactive_to_archived_threshold: float = 0.30,
        superseded_to_archived_threshold: float = 0.30,
        forget_retention_threshold: float = 0.15
    ):
        self.active_to_inactive_threshold = active_to_inactive_threshold
        self.inactive_to_archived_threshold = inactive_to_archived_threshold
        self.superseded_to_archived_threshold = superseded_to_archived_threshold
        self.forget_retention_threshold = forget_retention_threshold

    def calculate_retention_score(self, node: MemoryNode, centrality: float, current_time: datetime) -> float:
        """
        Calculates a dynamic retention score for a node.
        Score = Importance + Recency + Access frequency + Centrality - Age decay - Contradiction penalty
        """
        # 1. Base Importance (dominates the score)
        importance = getattr(node, "importance", 0.5)
        
        # 2. Access frequency / reinforcement count (small bonus)
        access_count = getattr(node, "access_count", 1)
        access_bonus = 0.1 * math.log(access_count) if access_count > 0 else 0.0
        
        # 3. Centrality (small bonus)
        centrality_bonus = 0.05 * centrality
        
        # 4. Age Decay (exponential age penalty, halflife of 48h)
        node_timestamp = node.timestamp if hasattr(node, "timestamp") else current_time
        age_seconds = (current_time - node_timestamp).total_seconds()
        half_life = 172800.0  # 48 hours
        # Age penalty grows from 0 to 0.4 over time
        age_decay_penalty = 0.4 * (1.0 - math.exp(-0.693 * age_seconds / half_life))
        
        # 5. Status Contradiction / Lifecycle Penalty
        status = node.metadata.get("status", "RAW")
        if status == "SUPERSEDED":
            status_penalty = 0.4
        elif status == "ARCHIVED":
            status_penalty = 0.6
        else:
            status_penalty = 0.0
            
        score = importance + access_bonus + centrality_bonus - age_decay_penalty - status_penalty
        return max(0.0, min(1.0, score))

    def evaluate_transition(self, node: MemoryNode, score: float) -> Tuple[str, Optional[str]]:
        """
        Evaluates and transitions memory status based on retention score.
        Returns:
            Tuple[str, Optional[str]]: The new status, and a transition description (if changed).
        """
        current_status = node.metadata.get("status", "RAW")
        
        # If node is RAW, sleep cycle transitions it to ACTIVE
        if current_status == "RAW":
            return "ACTIVE", f"Consolidated raw fact to ACTIVE status (Retention score: {score:.3f})."
            
        if current_status == "ACTIVE":
            if score < self.active_to_inactive_threshold:
                return "INACTIVE", f"Dormant fact transitioned ACTIVE -> INACTIVE (Retention score: {score:.3f} fell below {self.active_to_inactive_threshold})."
                
        elif current_status == "INACTIVE":
            if score < self.inactive_to_archived_threshold:
                return "ARCHIVED", f"Inactive node archived: INACTIVE -> ARCHIVED (Retention score: {score:.3f} fell below {self.inactive_to_archived_threshold})."
                
        elif current_status == "SUPERSEDED":
            if score < self.superseded_to_archived_threshold:
                return "ARCHIVED", f"Superseded node archived: SUPERSEDED -> ARCHIVED (Retention score: {score:.3f} fell below {self.superseded_to_archived_threshold})."
                
        elif current_status == "ARCHIVED":
            if score < self.forget_retention_threshold:
                return "FORGOTTEN", f"Archived node forgotten: ARCHIVED -> FORGOTTEN (Retention score: {score:.3f} fell below {self.forget_retention_threshold})."
                
        return current_status, None
