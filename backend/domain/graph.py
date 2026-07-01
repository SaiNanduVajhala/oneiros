"""
Oneiros Domain Layer - Graph Visualization Definitions
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class GraphNodeVisual(BaseModel):
    """
    Frontend-friendly node wrapper with visuals.
    """
    id: str
    label: str
    type: str
    color: Optional[str] = None
    size: float = 1.0

class GraphEdgeVisual(BaseModel):
    """
    Frontend-friendly edge wrapper with visuals.
    """
    source: str
    target: str
    type: str
    weight: float = 1.0

class GraphData(BaseModel):
    """
    Consolidated memory graph payload for frontend display.
    """
    nodes: List[GraphNodeVisual] = Field(default_factory=list)
    edges: List[GraphEdgeVisual] = Field(default_factory=list)
