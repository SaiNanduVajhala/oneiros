"""
Oneiros Utilities - Graph Helpers

Common functions for formatting, counting, or manipulating graph objects.
"""

from typing import List, Tuple, Dict, Any

def get_node_degree_map(edges: List[Tuple[str, str, str, Dict[str, Any]]]) -> Dict[str, int]:
    """
    Computes degree count (total connections) for all nodes referenced in edges.
    """
    degrees = {}
    for source, target, _, _ in edges:
        degrees[source] = degrees.get(source, 0) + 1
        degrees[target] = degrees.get(target, 0) + 1
    return degrees
