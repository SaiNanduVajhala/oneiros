"""
Oneiros Utilities - Timers

Context managers for measuring cognitive transaction times.
"""

import time
import logging
from typing import Callable, Any

logger = logging.getLogger("oneiros.utils.timers")

class ExecutionTimer:
    """
    Context manager to easily measure and log elapsed seconds.
    """
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = 0.0
        self.elapsed = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.perf_counter() - self.start_time
        logger.info(f"Operation '{self.operation_name}' completed in {self.elapsed:.4f} seconds.")
