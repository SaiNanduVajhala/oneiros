"""
Oneiros Reasoning Layer - MemoryExtractor
Handles LLM-based classification of incoming user messages and extracts structured knowledge.
"""

import logging
from typing import Optional, Dict, Any
from domain.memory import MemoryCandidate
from kernel.reasoning.llm import ReasoningEngine

logger = logging.getLogger("oneiros.kernel.reasoning.memory_extractor")

SYSTEM_EXTRACTOR_PROMPT = (
    "You are the Memory Extractor of Oneiros, a cognitive operating system.\n"
    "Your task is to analyze the incoming user message and extract structured personal knowledge.\n"
    "You must classify the message into one of these categories:\n"
    "- 'CHAT': General greetings, thanks, general informational questions ('Explain DBSCAN', 'What is Python?'), or self-referential questions ('Who am I?').\n"
    "- 'FACT': A new durable personal fact about the user (identity, job, location, studies, biography, etc.). Example: 'My name is Alice', 'I study Computer Science'.\n"
    "- 'FACT_UPDATE': A correction, change, or update to a prior fact. Example: 'Actually my name is Bob', 'I no longer live in Hyderabad'.\n"
    "- 'PREFERENCE': Personal preferences, likes, dislikes. Example: 'I love Chemex coffee', 'I hate horror movies'.\n"
    "- 'TASK': Persistent tasks, reminders, actions to be taken. Example: 'Remind me tomorrow to build CUDA FlashAttention'.\n"
    "- 'DELETE_REQUEST': An instruction to delete or forget previously saved information. Example: 'Forget my coffee preference', 'Delete my hometown'.\n\n"
    "Output a JSON object with keys:\n"
    "- 'category': string, one of [CHAT, FACT, FACT_UPDATE, PREFERENCE, TASK, DELETE_REQUEST]\n"
    "- 'subject': string representing who or what the memory is about. For facts/preferences about the user, this MUST be strictly 'user'.\n"
    "- 'predicate': string representing the relationship/property (e.g. 'name', 'favorite_color', 'likes', 'hates', 'residence', 'occupation', 'reminder') or null if not applicable.\n"
    "- 'object': string representing the value/object of the predicate (e.g. 'Alice', 'Chemex coffee', 'build CUDA FlashAttention', 'Hyderabad') or null if not applicable.\n"
    "- 'confidence': float (0.0 to 1.0) indicating your confidence in this classification and extraction.\n"
    "- 'importance': float (0.0 to 1.0) indicating how critical, valuable, or durable this information is over the long term (e.g. peanut allergy or legal name is 0.9-1.0; favorite color or general preference is 0.4-0.6; transient notes or basic facts are 0.2-0.4).\n"
    "- 'reason': string briefly explaining your classification."
)

class MemoryExtractor:
    """
    Cognitive memory extraction pipeline component.
    Classifies incoming messages and extracts structured knowledge into typed MemoryCandidates.
    """
    def __init__(self, reasoning_engine: Optional[ReasoningEngine] = None):
        self.reasoning_engine = reasoning_engine or ReasoningEngine()

    async def extract_candidate(self, user_message: str) -> MemoryCandidate:
        """
        Classifies user message and extracts structured knowledge if applicable.
        """
        try:
            extracted = await self.reasoning_engine.generate_structured_response(
                system_instruction=SYSTEM_EXTRACTOR_PROMPT,
                user_prompt=user_message
            )
            
            category = str(extracted.get("category", "CHAT")).upper().strip()
            if category not in ("CHAT", "FACT", "FACT_UPDATE", "PREFERENCE", "TASK", "DELETE_REQUEST"):
                category = "CHAT"
                
            # Normalize subject
            subject = extracted.get("subject")
            if subject and str(subject).lower() in ("user", "me", "i", "self"):
                subject = "USER"
                
            # Normalize predicate
            predicate = extracted.get("predicate")
            if predicate and str(predicate).lower() in ("name", "identity.name"):
                predicate = "identity.name"
                
            # Extract importance and run heuristic fallback if missing or invalid
            importance = extracted.get("importance")
            if importance is None:
                importance_map = {"FACT": 0.75, "FACT_UPDATE": 0.75, "PREFERENCE": 0.50, "TASK": 0.40}
                importance = importance_map.get(category, 0.30)
            else:
                importance = float(importance)
                
            return MemoryCandidate(
                category=category,
                subject=subject,
                predicate=predicate,
                object=extracted.get("object"),
                confidence=float(extracted.get("confidence", 1.0)),
                importance=importance,
                source_message=user_message
            )
        except Exception as e:
            logger.error(f"Error during memory extraction: {e}")
            return MemoryCandidate(
                category="CHAT",
                confidence=1.0,
                importance=0.30,
                source_message=user_message
            )
