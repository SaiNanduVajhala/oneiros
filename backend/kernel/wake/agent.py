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
from kernel.wake.working_memory import working_memory

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
        
        # 1. Structured Fact Index consulting first
        from kernel.reasoning.fact_resolver import FactResolver, is_potential_fact
        fact_resolver = FactResolver(self.reasoning_engine)
        
        # Pre-fetch active structured facts to see if we can resolve the query deterministically
        is_history = any(kw in user_message.lower() for kw in ["history", "previous", "correction", "belief", "changed", "why did", "explain why", "before", "remember before", "changelog"])
        allowed_statuses = ("ACTIVE", "CONSOLIDATED")
        if is_history:
            allowed_statuses = ("ACTIVE", "CONSOLIDATED", "SUPERSEDED", "ARCHIVED")
            
        active_facts = []
        try:
            nodes_raw, _ = await self.provider.get_graph_data()
            for nid, props in nodes_raw:
                meta = props.get("metadata") or {}
                fact = meta.get("fact")
                status = meta.get("status", "RAW")
                # Filter out superseded and archived facts unless history is requested
                if fact and status in allowed_statuses:
                    active_facts.append(fact)
        except Exception as e:
            logger.warning(f"Failed to query active structured facts index: {e}")


        # Check if query targets personal facts and we have matches
        PERSONAL_FACT_KEYWORDS = [
            "who am i", "my name", "favorite", "where do i live",
            "what do i do", "my occupation", "where am i", "my age",
            "what language do i", "my preference", "my goal", "my skill"
        ]
        
        is_personal_query = any(kw in user_message.lower() for kw in PERSONAL_FACT_KEYWORDS)
        matched_facts = []
        if is_personal_query and active_facts:
            # Find facts whose predicate or category type is queried
            for f in active_facts:
                pred = str(f.get("predicate", "")).lower()
                fact_type = str(f.get("type", "")).lower()
                if pred in user_message.lower() or fact_type in user_message.lower() or "who am i" in user_message.lower():
                    matched_facts.append(f)

        context_items = []
        memory_status = "active"
        long_term_memory_str = ""
        
        # Consult structured facts index first. Only if nothing is found fall back to semantic recall.
        if matched_facts:
            context_items = [
                f"Structured Fact: {f.get('subject', 'user')}'s {f.get('predicate')} is {f.get('object')} (Type: {f.get('type')})"
                for f in matched_facts
            ]
            long_term_memory_str = "Structured Facts Context:\n" + "\n".join(context_items)
            logger.info(f"Structured facts index matched. Bypassing semantic recall. Context: {context_items}")
        else:
            # Fallback to semantic memory recall
            recall_results = []
            try:
                recall_results = await self.provider.recall(user_message)
                context_items = [r.get("text", str(r)) for r in recall_results]
            except NotImplementedError as e:
                memory_status = "stubbed"
                logger.info(f"Recall stubbed: {e}")
            except Exception as e:
                memory_status = "error"
                logger.error(f"Error retrieving memories: {e}")
            long_term_memory_str = ContextBuilder.build_context_string(recall_results)

        # Get recent Working Memory history string
        working_memory_str = working_memory.get_context_string()

        # 2. Call Reasoning Engine to generate response
        try:
            answer = await self.reasoning_engine.reason_wake(
                user_message=user_message,
                working_memory_str=working_memory_str,
                long_term_memory_str=long_term_memory_str
            )
        except Exception as e:
            logger.error(f"LLM Reasoning execution failed: {e}")
            answer = f"Error generating answer: {e}"

        # 3. Save turn to Working Memory
        working_memory.add_message("user", user_message)
        working_memory.add_message("assistant", answer)

        # 3. Heuristic Fact Detection & Structured Fact Ingestion
        metadata_to_save = {"status": "RAW"}
        if is_potential_fact(user_message):
            extracted_fact = await fact_resolver.extract_structured_fact(user_message)
            if extracted_fact:
                metadata_to_save["fact"] = extracted_fact
                logger.info(f"Heuristics hit. Extracted structured fact: {extracted_fact}")

        # 4. Store new interaction as an episodic memory
        memory_id = None
        try:
            memory_id = await self.provider.remember(user_message, metadata=metadata_to_save)
            await event_bus.publish(Event(
                event_type="MemoryRemembered",
                payload={"node_id": memory_id, "content": user_message}
            ))
        except NotImplementedError as e:
            logger.info(f"Memory ingestion stubbed: {e}")
        except Exception as e:
            logger.error(f"Error storing memory: {e}")

        return {
            "response": answer,
            "context": context_items,
            "memory_status": memory_status,
            "memory_id": memory_id
        }
