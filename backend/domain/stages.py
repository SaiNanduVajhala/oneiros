"""
Oneiros Domain Layer - Sleep Cycle Stages
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class SleepStage(BaseModel):
    """
    State tracking object representing progress through one sleep stage.
    """
    name: str  # "Idle", "N1_Replay", "N2_Consolidation", "N3_Pruning", "REM_Dream"
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None
    status: str = "running"  # "running", "completed", "failed"
    details: Optional[str] = None
