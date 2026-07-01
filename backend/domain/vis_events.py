"""
Oneiros Domain Layer — Visualization Events

Immutable event objects emitted by the cognitive engine during sleep cycles.
Each VisEvent is a historical fact — never modified after creation.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


class AlgorithmTrace(BaseModel, frozen=True):
    """Immutable trace of an algorithm execution. Input → Algorithm → Output."""
    algorithm: str
    stage: str
    input_description: str
    input_count: int
    output_description: str
    output_count: int
    parameters: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = 0.0
    details: List[str] = Field(default_factory=list)


class VisEvent(BaseModel, frozen=True):
    """
    Immutable visualization event emitted by the sleep coordinator.
    The frontend renders these — it never decides what to animate.
    """
    stage: str  # N1_Replay, N2_Consolidation, N3_Pruning, REM_Dream
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M:%S.%f")[:-3])
    type: str  # stage_start, node_activate, cluster_form, node_fade, node_merge,
               # conflict_resolve, concept_create, edge_create, stage_complete, cycle_complete
    message: str
    node_ids: List[str] = Field(default_factory=list)
    cluster_id: Optional[int] = None
    cluster_members: List[str] = Field(default_factory=list)
    similarity: Optional[float] = None
    concept_label: Optional[str] = None
    source_id: Optional[str] = None
    target_id: Optional[str] = None
    edge_type: Optional[str] = None
    algorithm: Optional[str] = None
    input_count: Optional[int] = None
    output_count: Optional[int] = None
    health_before: Optional[float] = None
    health_after: Optional[float] = None
    duration_ms: Optional[float] = None
    trace: Optional[AlgorithmTrace] = None


class MetricsSnapshot(BaseModel, frozen=True):
    """Immutable snapshot of all algorithm-derived metrics at a point in time."""
    activation_threshold: float = 0.3
    mean_activation: float = 0.0
    nodes_replayed: int = 0
    nodes_pruned: int = 0
    duplicates_merged: int = 0
    contradictions_resolved: int = 0
    concepts_generated: int = 0
    cluster_count: int = 0
    avg_cluster_size: float = 0.0
    compression_ratio: float = 1.0
    retrieval_latency_ms: float = 0.0
    memory_health: float = 0.0
    graph_density: float = 0.0
    fragmentation: float = 0.0
    semantic_cohesion: float = 0.0


class StageSnapshot(BaseModel):
    """Graph state captured after each stage for temporal playback."""
    stage: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    node_count: int = 0
    edge_count: int = 0
    nodes_json: List[Dict[str, Any]] = Field(default_factory=list)
    edges_json: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: Optional[MetricsSnapshot] = None
    events_json: List[Dict[str, Any]] = Field(default_factory=list)
    health: float = 0.0
    algorithm_traces_json: List[Dict[str, Any]] = Field(default_factory=list)
