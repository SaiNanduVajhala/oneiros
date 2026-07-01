"""
Oneiros Sleep Subsystem - Replay Stage (N1)

Assembles the active working set of memories using multi-factor ranking.
"""

import logging
from datetime import datetime
from typing import List
from memory.provider import MemoryProvider
from domain.memory import MemoryGraphSnapshot, MemoryNode
from kernel.algorithms.centrality import compute_graph_centrality
from kernel.algorithms.activation import calculate_node_activation

logger = logging.getLogger("oneiros.kernel.sleep.replay")

class ReplayStage:
    """
    N1 Sleep Stage: Constructs and ranks the Active Working Set.
    """
    def __init__(self, provider: MemoryProvider):
        self.provider = provider

    async def execute(self, snapshot: MemoryGraphSnapshot) -> List[MemoryNode]:
        """
        Processes snapshot nodes, computes weighted activations, and builds the ranked Active Working Set.
        """
        logger.info("Executing Replay (N1) Stage...")
        
        # Calculate topological centrality
        centrality_map = compute_graph_centrality(snapshot.nodes, snapshot.edges)
        
        current_time = datetime.now()
        ranked_nodes = []
        
        for node in snapshot.nodes:
            if node.source != "user":
                continue  # focus replay on raw user episodic content
                
            centrality_score = centrality_map.get(node.id, 0.0)
            activation_score = calculate_node_activation(
                node=node,
                centrality=centrality_score,
                current_time=current_time
            )
            
            # Log rationale
            explain = (
                f"Ranked in Replay AWS: Activation={activation_score:.3f} "
                f"(RecencyDecay factor applied, Centrality={centrality_score:.2f}, FreqCount={node.access_count})"
            )
            node.explain_log.append(explain)
            
            # Use metadata to store transient metrics
            node.metadata["calculated_activation"] = activation_score
            ranked_nodes.append(node)

        # Sort by computed activation levels
        ranked_nodes.sort(key=lambda n: n.metadata.get("calculated_activation", 0.0), reverse=True)
        
        logger.info(f"Replay stage completed. Ranked {len(ranked_nodes)} nodes into Active Working Set.")
        return ranked_nodes
