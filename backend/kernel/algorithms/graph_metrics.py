"""
Oneiros Cognitive Algorithms - Graph Metrics & Memory Health

Derived calculations for graph structure analytics and memory substrate health scores.
"""

from typing import List
from domain.memory import MemoryNode, MemoryEdge
from kernel.algorithms.centrality import compute_graph_centrality

def calculate_graph_density(nodes: List[MemoryNode], edges: List[MemoryEdge]) -> float:
    """
    Computes density of the memory graph.
    
    Density = 2 * E / (V * (V - 1))
    """
    v = len(nodes)
    if v <= 1:
        return 0.0
    e = len(edges)
    return float((2.0 * e) / (v * (v - 1.0)))

def calculate_average_degree(nodes: List[MemoryNode], edges: List[MemoryEdge]) -> float:
    """
    Computes average connections per node.
    """
    v = len(nodes)
    if v == 0:
        return 0.0
    e = len(edges)
    return float((2.0 * e) / v)

def compute_memory_health(
    nodes: List[MemoryNode],
    edges: List[MemoryEdge],
    duplicate_count: int,
    contradiction_count: int
) -> float:
    """
    Derives a memory health score between 0.0 and 100.0.
    
    Deducts points for duplicates, contradictions, and orphan nodes.
    Only ACTIVE, CONSOLIDATED, and RAW nodes participate.
    """
    active_nodes = [n for n in nodes if n.metadata.get("status", "RAW") not in ("SUPERSEDED", "ARCHIVED")]
    if not active_nodes:
        return 100.0

    score = 100.0

    # 1. Deduct for contradictions (high penalty)
    score -= (contradiction_count * 15.0)

    # 2. Deduct for duplicates (medium penalty)
    score -= (duplicate_count * 5.0)

    # 3. Deduct for orphan nodes (degree 0)
    active_ids = {n.id for n in active_nodes}
    active_edges = [e for e in edges if e.source in active_ids and e.target in active_ids]
    
    centrality_map = compute_graph_centrality(active_nodes, active_edges)
    orphans = sum(1 for nid, c in centrality_map.items() if c == 0.0)
    score -= (orphans * 2.0)

    # Bound result between 0.0 and 100.0
    return float(max(0.0, min(100.0, score)))
