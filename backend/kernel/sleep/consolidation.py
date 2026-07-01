"""
Oneiros Sleep Subsystem - Consolidation Stage (N2)

Groups active working set memories into semantic clusters.
"""

import logging
from typing import List
from domain.memory import MemoryNode
from kernel.algorithms.clustering import cluster_memories

logger = logging.getLogger("oneiros.kernel.sleep.consolidation")

class ConsolidationStage:
    """
    N2 Sleep Stage: Groups related nodes into thematic clusters.
    """
    def __init__(self):
        pass

    async def execute(self, active_set: List[MemoryNode]) -> List[List[MemoryNode]]:
        """
        Groups nodes based on semantic and topological similarity.
        """
        logger.info("Executing Consolidation (N2) Stage...")
        if not active_set:
            logger.info("Active set is empty. Consolidation stage complete.")
            return []

        # Run DBSCAN vector/TF-IDF clustering
        clusters = cluster_memories(active_set, preference="embeddings")

        # Log explanations on clustered nodes
        for idx, cluster in enumerate(clusters):
            cluster_size = len(cluster)
            for node in cluster:
                explain = f"Grouped in Cluster {idx} (Cluster size: {cluster_size} nodes)"
                node.explain_log.append(explain)

        logger.info(f"Consolidation stage complete. Formed {len(clusters)} clusters from {len(active_set)} nodes.")
        return clusters
