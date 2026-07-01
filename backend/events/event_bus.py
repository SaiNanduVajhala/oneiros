"""
Oneiros Event System - Event Bus

This module implements a process-wide asynchronous EventBus. It allows core components
to register subscriptions and publish events decoupling cognitive orchestration from
telemetry reporting or UI pushes.
"""

import asyncio
from typing import Callable, List, Dict
from events.events import Event

class EventBus:
    """
    Publish-Subscribe event dispatching hub.
    """
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        """
        Registers a callback listener for a specific event type.
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)

    async def publish(self, event: Event):
        """
        Dispatches an event asynchronously to all active listeners.
        """
        event_type = event.event_type
        if event_type in self._listeners:
            tasks = []
            for callback in self._listeners[event_type]:
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(callback(event))
                else:
                    callback(event)
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

# ponytail: Singleton instance allows global subscriber bindings across module files
event_bus = EventBus()
