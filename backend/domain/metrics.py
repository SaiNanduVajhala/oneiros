"""
Oneiros Domain Layer - Metrics and Decay Scores
"""

from pydantic import BaseModel

class ActivationScore(BaseModel):
    """
    Decay and activation parameters evaluated on memory nodes.
    """
    node_id: str
    recency: float
    frequency: float
    importance: float
    score: float

class DreamMetrics(BaseModel):
    """
    Accumulator and statistical metrics for sleep cycles.
    """
    total_duration_seconds: float
    nodes_processed: int
    nodes_removed: int
    concepts_created: int
    relationships_created: int
    compression_ratio: float
