"""
Oneiros Cognitive Algorithms - Graph Centrality

Calculates node graph centrality metrics based on graph topology.
"""

import networkx as nx
from typing import List, Dict
from domain.memory import MemoryNode, MemoryEdge

def compute_graph_centrality(nodes: List[MemoryNode], edges: List[MemoryEdge]) -> Dict[str, float]:
    """
    Computes normalized degree centrality for each node in the graph.
    
    Returns:
        Dict[str, float]: Mapping of node_id to degree centrality score.
    """
    if not nodes:
        return {}
        
    g = nx.Graph()
    for n in nodes:
        g.add_node(n.id)
        
    for e in edges:
        if g.has_node(e.source) and g.has_node(e.target):
            g.add_edge(e.source, e.target)

    if len(g.nodes) <= 1:
        return {nid: 0.0 for nid in g.nodes}
        
    # Calculate degree centrality (normalized by N-1)
    centrality_scores = nx.degree_centrality(g)
    return {nid: float(score) for nid, score in centrality_scores.items()}
