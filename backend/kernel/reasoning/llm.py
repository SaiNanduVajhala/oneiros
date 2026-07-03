"""
Oneiros Reasoning Subsystem - Reasoning Engine

Responsible for prompt construction, LLM delegation, and response parsing.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from infrastructure.gemini.client import GeminiClient
from kernel.reasoning.prompts import SYSTEM_WAKE_PROMPT, USER_WAKE_TEMPLATE

logger = logging.getLogger("oneiros.kernel.reasoning.llm")

class ReasoningEngine:
    """
    Reasoning engine coordinating prompt building and LLM response execution.
    """
    def __init__(self, client: Optional[GeminiClient] = None):
        self.client = client or GeminiClient()

    async def reason_wake(self, user_message: str, working_memory_str: str, long_term_memory_str: str) -> str:
        """
        Coordinates reasoning for the Wake Phase conversation.
        """
        user_prompt = USER_WAKE_TEMPLATE.format(
            working_memory_str=working_memory_str,
            long_term_memory_str=long_term_memory_str,
            user_message=user_message
        )
        return await self.client.generate_response(
            system_instruction=SYSTEM_WAKE_PROMPT,
            user_prompt=user_prompt
        )

    async def generate_structured_response(self, system_instruction: str, user_prompt: str) -> Dict[str, Any]:
        """
        Delegates reasoning and attempts to parse the response as a JSON dictionary.
        """
        instruction_with_format = (
            system_instruction + 
            "\nYour response must be a single valid JSON object. Do not include markdown wraps like ```json ... ```, just raw JSON."
        )
        raw_response = await self.client.generate_response(instruction_with_format, user_prompt)
        
        # Clean potential markdown wrapping if present
        clean_text = raw_response.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()
        
        try:
            return json.loads(clean_text)
        except Exception as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}. Raw response: {raw_response}")
            # Fallback wrapper
            return {"raw_text": raw_response, "parse_error": str(e)}
