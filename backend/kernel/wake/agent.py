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
        
        # 1. Ingestion Pipeline & Structured Memory Extraction
        from kernel.reasoning.memory_extractor import MemoryExtractor
        from datetime import datetime
        
        extractor = MemoryExtractor(self.reasoning_engine)
        candidate = await extractor.extract_candidate(user_message)
        logger.info(f"Memory Ingestion classified user message: category={candidate.category}, confidence={candidate.confidence}")
        
        memory_id = None
        
        # Action based on category classification
        if candidate.category == "DELETE_REQUEST":
            deleted_count = 0
            try:
                nodes_raw, _ = await self.provider.get_graph_data()
                for nid, props in nodes_raw:
                    content = (props.get("content") or props.get("description") or "").lower()
                    meta = props.get("metadata") or {}
                    fact = meta.get("fact") or {}
                    
                    pred = str(fact.get("predicate", "")).lower()
                    obj = str(fact.get("object", "")).lower()
                    
                    target_pred = str(candidate.predicate or "").lower()
                    target_obj = str(candidate.object or "").lower()
                    
                    match = False
                    if target_obj and (target_obj in obj or obj in target_obj or target_obj in content):
                        match = True
                    if target_pred and (target_pred in pred or pred in target_pred):
                        match = True
                        
                    if match:
                        await self.provider.forget(nid)
                        deleted_count += 1
                logger.info(f"Delete request matched and forgot {deleted_count} memories.")
            except Exception as e:
                logger.error(f"Error handling delete request: {e}")
                
        elif candidate.category in ("FACT", "FACT_UPDATE", "PREFERENCE", "TASK"):
            metadata_to_save = {
                "status": "RAW",
                "category": candidate.category,
                "confidence": candidate.confidence,
                "source_message": user_message,
                "timestamp": datetime.now().isoformat()
            }
            
            if candidate.predicate:
                if candidate.category in ("FACT", "FACT_UPDATE"):
                    fact_type = "Identity"
                elif candidate.category == "PREFERENCE":
                    fact_type = "Preference"
                elif candidate.category == "TASK":
                    fact_type = "Task"
                else:
                    fact_type = "Identity"
                    
                metadata_to_save["fact"] = {
                    "subject": candidate.subject or "user",
                    "predicate": candidate.predicate,
                    "object": candidate.object,
                    "type": fact_type,
                    "is_correction": candidate.category == "FACT_UPDATE",
                    "confidence": candidate.confidence
                }
                
            try:
                memory_id = await self.provider.remember(user_message, importance=candidate.confidence, metadata=metadata_to_save)
                await event_bus.publish(Event(
                    event_type="MemoryRemembered",
                    payload={"node_id": memory_id, "content": user_message}
                ))
                logger.info(f"Ingested durable memory candidate into Cognee with ID {memory_id}")
            except NotImplementedError as e:
                logger.info(f"Memory ingestion stubbed: {e}")
            except Exception as e:
                logger.error(f"Error storing ingested memory: {e}")
                
        else:
            logger.info("Message classified as CHAT. Bypassing long-term memory storage.")

        # 2. Context Building & Retrieval for Response Generation
        is_history = any(kw in user_message.lower() for kw in ["history", "previous", "correction", "belief", "changed", "why did", "explain why", "before", "remember before", "changelog"])
        allowed_statuses = ("ACTIVE", "CONSOLIDATED", "RAW")
        if is_history:
            allowed_statuses = ("ACTIVE", "CONSOLIDATED", "SUPERSEDED", "ARCHIVED", "RAW")
            
        active_facts = []
        try:
            nodes_raw, _ = await self.provider.get_graph_data()
            for nid, props in nodes_raw:
                meta = props.get("metadata") or {}
                fact = meta.get("fact")
                status = meta.get("status", "RAW")
                # Filter out superseded and archived facts unless history is requested
                if fact and status in allowed_statuses:
                    # Normalize subject and predicate values for consistency
                    subj = str(fact.get("subject", "USER")).upper()
                    pred = str(fact.get("predicate", "")).lower()
                    if subj in ("USER", "I", "ME", "SELF"):
                        fact["subject"] = "USER"
                    if pred == "name":
                        fact["predicate"] = "identity.name"
                    active_facts.append(fact)
        except Exception as e:
            logger.warning(f"Failed to query active structured facts index: {e}")

        # 3. Categorize Facts into Identity, Preferences, and Long-Term Facts
        identities = []
        preferences = []
        other_facts = []
        
        for f in active_facts:
            subj = str(f.get("subject", "USER")).upper()
            pred = str(f.get("predicate", "")).lower()
            fact_type = str(f.get("type", "")).lower()
            
            desc = f"USER's {f.get('predicate')} is {f.get('object')}"
            
            if pred == "identity.name" or fact_type == "identity":
                identities.append(desc)
            elif fact_type == "preference" or pred in ("likes", "hates", "preference"):
                preferences.append(desc)
            else:
                other_facts.append(desc)

        # 4. Fallback/Semantic Recall from Cognee Cloud
        recall_results = []
        memory_status = "active"
        try:
            recall_results = await self.provider.recall(user_message)
        except NotImplementedError as e:
            memory_status = "stubbed"
            logger.info(f"Recall stubbed: {e}")
        except Exception as e:
            memory_status = "error"
            logger.error(f"Error retrieving memories: {e}")

        semantic_items = [r.get("text", str(r)) for r in recall_results]
        
        # Combine structural other_facts and semantic recall items
        all_lt_facts = [f"- {item}" for item in other_facts]
        all_lt_facts.extend([f"- {item}" for item in semantic_items])
        
        # Format structured prompt inputs
        user_identity_str = "\n".join([f"- {item}" for item in identities]) if identities else "- (No identity facts stored)"
        user_preferences_str = "\n".join([f"- {item}" for item in preferences]) if preferences else "- (No preference facts stored)"
        long_term_facts_str = "\n".join(all_lt_facts) if all_lt_facts else "- (No long-term facts stored)"
        
        context_items = identities + preferences + other_facts + semantic_items

        # Get recent Working Memory history string
        working_memory_str = working_memory.get_context_string()

        # 5. Call Reasoning Engine to generate response
        try:
            answer = await self.reasoning_engine.reason_wake(
                user_message=user_message,
                working_memory_str=working_memory_str,
                user_identity_str=user_identity_str,
                user_preferences_str=user_preferences_str,
                long_term_facts_str=long_term_facts_str
            )
        except Exception as e:
            logger.error(f"LLM Reasoning execution failed: {e}")
            answer = f"Error generating answer: {e}"

        # 6. Save turn to Working Memory
        working_memory.add_message("user", user_message)
        working_memory.add_message("assistant", answer)

        return {
            "response": answer,
            "context": context_items,
            "memory_status": memory_status,
            "memory_id": memory_id
        }


