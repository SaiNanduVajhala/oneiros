"""
Oneiros Unit Tests - Asynchronous Event Bus checks
"""

import pytest
import asyncio
from events.event_bus import EventBus
from events.events import Event

@pytest.mark.asyncio
async def test_event_bus_pub_sub():
    bus = EventBus()
    received_events = []
    
    async def handler(event: Event):
        received_events.append(event)
        
    bus.subscribe("TestEvent", handler)
    
    test_event = Event(event_type="TestEvent", payload={"data": "hello"})
    await bus.publish(test_event)
    
    assert len(received_events) == 1
    assert received_events[0].event_type == "TestEvent"
    assert received_events[0].payload["data"] == "hello"
