"""
Oneiros Services Layer - Graph Service

Transforms internal graph structures into formatted visual nodes and edges for visualizers.
"""

import logging
from typing import Dict, Any, List
from memory.provider import MemoryProvider
from domain.graph import GraphData, GraphNodeVisual, GraphEdgeVisual

logger = logging.getLogger("oneiros.services.graph_service")

class GraphService:
    """
    Service for parsing database node/edge tuples into visual layouts.
    """
    def __init__(self, provider: MemoryProvider):
        self.provider = provider

    async def get_visual_graph(self) -> GraphData:
        """
        Retrieves current graph layout and formats styling.
        """
        try:
            nodes, edges = await self.provider.get_graph_data()
        except NotImplementedError:
            logger.warning("MemoryProvider get_graph_data is stubbed. Returning empty visual graph.")
            return GraphData(nodes=[], edges=[])

        visual_nodes = []
        visual_edges = []

        # Color mapping based on node type
        color_map = {
            "episodic": "#4F46E5", # Sleek Indigo
            "semantic": "#10B981", # Elegant Emerald
            "concept": "#F59E0B",  # Golden Amber
            "report": "#EF4444"    # Rose Red
        }

        for node_id, props in nodes:
            node_type = props.get("type", "episodic")
            label = props.get("content") or props.get("label") or props.get("description") or node_id
            
            # Truncate long labels
            if len(label) > 40:
                label = label[:37] + "..."

            visual_nodes.append(GraphNodeVisual(
                id=node_id,
                label=label,
                type=node_type,
                color=color_map.get(node_type, "#6B7280"), # Muted gray default
                size=1.2 if node_type in ("semantic", "concept") else 1.0
            ))

        for source_id, target_id, rel_type, props in edges:
            weight = float(props.get("weight", 1.0))
            visual_edges.append(GraphEdgeVisual(
                source=source_id,
                target=target_id,
                type=rel_type,
                weight=weight
            ))

        return GraphData(nodes=visual_nodes, edges=visual_edges)
