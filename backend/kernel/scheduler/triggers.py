"""
Oneiros Scheduler - Trigger Conditions

Defines criteria that signal the system to start a consolidation sleep cycle.
"""

import time
from abc import ABC, abstractmethod
from typing import List
from domain.memory import MemoryGraphSnapshot

class BaseTrigger(ABC):
    """
    Abstract base class for all scheduler triggers.
    """
    @abstractmethod
    def evaluate(self, context: dict) -> bool:
        """
        Evaluates trigger conditions. Returns True if dream cycle should fire.
        """
        pass

class MessageCountTrigger(BaseTrigger):
    """
    Fires dreaming after receiving a threshold number of new memories.
    """
    def __init__(self, threshold: int = 5):
        self.threshold = threshold

    def evaluate(self, context: dict) -> bool:
        count = context.get("message_count", 0)
        return count >= self.threshold

class TimeIntervalTrigger(BaseTrigger):
    """
    Fires dreaming at regular elapsed time intervals.
    """
    def __init__(self, interval_seconds: float = 3600.0):
        self.interval_seconds = interval_seconds
        self.last_fired = time.time()

    def evaluate(self, context: dict) -> bool:
        now = time.time()
        if now - self.last_fired >= self.interval_seconds:
            self.last_fired = now
            return True
        return False

class ContextWindowPressureTrigger(BaseTrigger):
    """
    Fires dreaming if the active memory count or estimated tokens exceed thresholds.
    """
    def __init__(self, max_nodes: int = 15, max_tokens: int = 500):
        self.max_nodes = max_nodes
        self.max_tokens = max_tokens

    def evaluate(self, context: dict) -> bool:
        node_count = context.get("active_node_count", 0)
        token_count = context.get("active_token_count", 0)
        return node_count >= self.max_nodes or token_count >= self.max_tokens

class MemoryHealthTrigger(BaseTrigger):
    """
    Fires dreaming if the overall memory health score falls below a critical threshold.
    """
    def __init__(self, min_health: float = 70.0):
        self.min_health = min_health

    def evaluate(self, context: dict) -> bool:
        health_score = context.get("memory_health_score", 100.0)
        return health_score < self.min_health

class GraphDensityTrigger(BaseTrigger):
    """
    Fires dreaming if the graph density exceeds a threshold (indicating high noise or high linkage).
    """
    def __init__(self, max_density: float = 0.45):
        self.max_density = max_density

    def evaluate(self, context: dict) -> bool:
        density = context.get("graph_density", 0.0)
        return density >= self.max_density
