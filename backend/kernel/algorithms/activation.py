"""
Oneiros Cognitive Algorithms - Activation Calculations

Calculates memory node activation decay and importance ratings.
"""

import math
from datetime import datetime
from typing import Dict, Any, Optional
from domain.memory import MemoryNode

def calculate_node_activation(
    node: MemoryNode,
    centrality: float,
    current_time: datetime,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Computes a weighted activation score for a given memory node.
    
    Formula:
        Activation = Wr * RecencyDecay + Wf * AccessFrequency + Wc * GraphCentrality + Wi * Importance
    """
    if weights is None:
        weights = {
            "recency": 0.3,
            "frequency": 0.2,
            "centrality": 0.2,
            "importance": 0.3
        }

    # 1. Recency Decay
    # Exponential decay over hours since last accessed
    seconds_diff = (current_time - node.last_accessed).total_seconds()
    hours_diff = max(0.0, seconds_diff / 3600.0)
    # Decay rate (half-life of 24 hours: decay_factor = 0.0288)
    decay_rate = 0.01
    recency_decay = math.exp(-decay_rate * hours_diff)

    # 2. Access Frequency
    # Normalized frequency metric scaling between 0 and 1
    freq_norm = float(node.access_count) / (float(node.access_count) + 2.0)

    # 3. Weighted summation
    score = (
        weights.get("recency", 0.3) * recency_decay +
        weights.get("frequency", 0.2) * freq_norm +
        weights.get("centrality", 0.2) * centrality +
        weights.get("importance", 0.3) * node.importance
    )
    
    return float(max(0.0, min(1.0, score)))


def calculate_activation_scores(
    nodes: list,
    edges: list,
    current_time: Optional[datetime] = None
) -> Dict[str, float]:
    """
    Batch activation scoring for all nodes in a graph.
    Returns a dict mapping node_id → activation_score.
    """
    from kernel.algorithms.centrality import compute_graph_centrality

    if current_time is None:
        current_time = datetime.now()

    centrality_map = compute_graph_centrality(nodes, edges)
    scores = {}
    for node in nodes:
        c = centrality_map.get(node.id, 0.0)
        scores[node.id] = calculate_node_activation(node, c, current_time)
    return scores

