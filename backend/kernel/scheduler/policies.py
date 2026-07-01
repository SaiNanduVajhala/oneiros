"""
Oneiros Scheduler - Sleep Policies

Defines policy validations to block or allow consolidation cycles.
"""

import time
from abc import ABC, abstractmethod

class BasePolicy(ABC):
    """
    Abstract base class for all sleep safety policies.
    """
    @abstractmethod
    def is_allowed(self, context: dict) -> bool:
        """
        Validates the policy. Returns True if sleep cycle is allowed to run.
        """
        pass

class UserActivityPolicy(BasePolicy):
    """
    Blocks sleep cycles if a user has interacted with the agent very recently.
    """
    def __init__(self, quiet_period_seconds: float = 30.0):
        self.quiet_period_seconds = quiet_period_seconds

    def is_allowed(self, context: dict) -> bool:
        last_activity = context.get("last_user_interaction_time", 0.0)
        now = time.time()
        # If quiet period has elapsed, it is allowed
        return (now - last_activity) >= self.quiet_period_seconds

class ProcessingLoadPolicy(BasePolicy):
    """
    Blocks sleep cycles if current CPU or memory load thresholds are exceeded.
    """
    def __init__(self, max_cpu_percent: float = 85.0):
        self.max_cpu_percent = max_cpu_percent

    def is_allowed(self, context: dict) -> bool:
        cpu_load = context.get("cpu_load_percent", 10.0)
        return cpu_load <= self.max_cpu_percent
