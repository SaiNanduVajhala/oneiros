"""
Oneiros Event System - Core Events

This module defines unified event models that are published onto the internal
event bus during Wake and Sleep Kernel operations.
"""

from pydantic import BaseModel, Field
from typing import Any, Dict
from datetime import datetime

class Event(BaseModel):
    """
    Base event class carrying metadata and payload.
    """
    event_type: str  # e.g., "DreamStarted", "StageStarted", "MemoryForgotten"
    timestamp: datetime = Field(default_factory=datetime.now)
    payload: Dict[str, Any] = Field(default_factory=dict)
