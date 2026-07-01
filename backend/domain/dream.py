"""
Oneiros Domain Layer - Dream Cycles
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class DreamReport(BaseModel):
    """
    Metacognitive log of the Dream Cycle processing steps and outputs.
    """
    dream_id: str
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None
    duration: float = 0.0
    stages_completed: List[str] = Field(default_factory=list)
    nodes_processed: int = 0
    nodes_removed: int = 0
    concepts_created: int = 0
    relationships_created: int = 0
    compression_ratio: float = 0.0
    memory_health_before: float = 1.0
    memory_health_after: float = 1.0
    summary_narrative: Optional[str] = None
    timeline: List[str] = Field(default_factory=list)
