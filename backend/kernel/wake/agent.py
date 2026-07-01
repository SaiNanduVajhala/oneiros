"""
Oneiros Wake Subsystem - WakeAgent

Coordinates conversation flow during the Wake Phase. Delegates context building and
reasoning to reasoning components, and persists experiences via the memory provider.
"""

import os
import sys
import logging
from typing import Dict, Any, List, Optional
from memory.provider import MemoryProvider
from events.event_bus import event_bus
from events.events import Event
from kernel.reasoning.context_builder import ContextBuilder
from kernel.reasoning.llm import ReasoningEngine

logger = logging.getLogger("oneiros.kernel.wake.agent")

class WakeAgent:
    """
    Wake Agent coordinating the conversation workflow and memory integration cycles.
    """
    def __init__(self, provider: MemoryProvider, reasoning_engine: Optional[ReasoningEngine] = None):
        self.provider = provider
        self.reasoning_engine = reasoning_engine or ReasoningEngine()

    async def handle_interaction(self, user_message: str) -> Dict[str, Any]:
        """
        Processes a single conversational exchange.
        
        Args:
            user_message: The raw text prompt from the user.
            
        Returns:
            Dict[str, Any]: Payload containing answer response, retrieved memory contexts, and status flags.
        """
        # Publish user query reception event to the EventBus
        await event_bus.publish(Event(
            event_type="MessageReceived",
            payload={"message": user_message}
        ))
        
        # 1. Recall relevant memories from the memory provider
        context_items = []
        memory_status = "active"
        try:
            recall_results = await self.provider.recall(user_message)
            context_items = [r.get("text", str(r)) for r in recall_results]
        except NotImplementedError as e:
            # Catch CogneeCloudProvider stub exceptions cleanly
            memory_status = "stubbed"
            logger.info(f"Recall stubbed: {e}")
        except Exception as e:
            memory_status = "error"
            logger.error(f"Error retrieving memories: {e}")

        # 2. Build prompt and context string using ContextBuilder
        context_str = ContextBuilder.build_context_string(recall_results if 'recall_results' in locals() else [])

        # 3. Call Reasoning Engine to generate response
        try:
            answer = await self.reasoning_engine.reason_wake(user_message, context_str)
        except Exception as e:
            logger.error(f"LLM Reasoning execution failed: {e}")
            answer = f"Error generating answer: {e}"

        # 4. Store new interaction as an episodic memory
        memory_id = None
        try:
            memory_id = await self.provider.remember(user_message)
            await event_bus.publish(Event(
                event_type="MemoryRemembered",
                payload={"node_id": memory_id, "content": user_message}
            ))
        except NotImplementedError as e:
            # Catch CogneeCloudProvider stub exceptions cleanly
            logger.info(f"Memory ingestion stubbed: {e}")
        except Exception as e:
            logger.error(f"Error storing memory: {e}")

        return {
            "response": answer,
            "context": context_items,
            "memory_status": memory_status,
            "memory_id": memory_id
        }
