"""
Oneiros Services Layer - Dream Service

Handles running sleep cycles, managing historical reports, and orchestrating sleep states.
"""

import logging
from typing import List, Dict, Any, Optional
from memory.provider import MemoryProvider
from domain.dream import DreamReport
from kernel.sleep.coordinator import SleepCoordinator

logger = logging.getLogger("oneiros.services.dream_service")

class DreamService:
    """
    Service for executing sleep cycles and accessing past dream reports.
    """
    def __init__(self, provider: MemoryProvider, coordinator: Optional[SleepCoordinator] = None):
        self.provider = provider
        self.coordinator = coordinator or SleepCoordinator(provider)
        self.reports_history: List[DreamReport] = []

    async def trigger_sleep_cycle(self) -> DreamReport:
        """
        Executes a sleep cycle, records the report, and returns it.
        """
        logger.info("Service triggering a new sleep cycle...")
        report = await self.coordinator.execute_cycle()
        self.reports_history.append(report)
        return report

    def get_dream_history(self) -> List[DreamReport]:
        """
        Returns all executed dream reports in history.
        """
        return self.reports_history

    def get_last_dream_report(self) -> Optional[DreamReport]:
        """
        Returns the most recent dream report, if any.
        """
        if self.reports_history:
            return self.reports_history[-1]
        return None
