"""
Oneiros Domain Layer - Canonical Memory Models

Defines the structure for nodes, edges, and snapshots in the Cognitive Memory Graph.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class MemoryNode(BaseModel):
    """
    Canonical memory node containing all cognitive metadata.
    """
    id: str
    content: str
    embedding: Optional[List[float]] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    last_accessed: datetime = Field(default_factory=datetime.now)
    access_count: int = 1
    importance: float = 0.5
    source: str = "user"  # "user", "agent", "sleep"
    semantic_tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    explain_log: List[str] = Field(default_factory=list)

class MemoryEdge(BaseModel):
    """
    Canonical relationship linking two memory nodes.
    """
    source: str
    target: str
    type: str  # e.g., "ABSTRACTS", "RELATES_TO", "CONTRADICTS"
    weight: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SemanticConcept(BaseModel):
    """
    Synthesized semantic concepts created during REM.
    """
    label: str
    description: str
    confidence: float = 1.0

class MemoryGraphSnapshot(BaseModel):
    """
    Single evolving snapshot of the memory graph passed between stages.
    """
    nodes: List[MemoryNode] = Field(default_factory=list)
    edges: List[MemoryEdge] = Field(default_factory=list)


class MemoryCandidate(BaseModel):
    """
    Typed model representing extracted memory candidates from user input.
    """
    category: str  # "CHAT", "FACT", "FACT_UPDATE", "PREFERENCE", "TASK", "DELETE_REQUEST"
    subject: Optional[str] = None
    predicate: Optional[str] = None
    object: Optional[str] = None
    confidence: float = 1.0
    importance: float = 0.5
    source_message: str


