"""
Oneiros Working Memory Layer

Maintains a transient in-memory window of recent conversation turns to provide 
immediate conversational continuity and contradiction detection, independent of database retrieval.
"""

import logging
from typing import List, Dict

logger = logging.getLogger("oneiros.kernel.wake.working_memory")

class WorkingMemory:
    """
    In-memory working memory representing the immediate context of recent conversation turns.
    """
    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self.history: List[Dict[str, str]] = []

    def add_message(self, role: str, content: str):
        """
        Appends a message (role: 'user' or 'assistant') to the history.
        Pops the oldest messages if max_turns is exceeded.
        """
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_turns:
            self.history.pop(0)
        logger.debug(f"Added to working memory ({role}): {content[:40]}...")

    def get_history(self) -> List[Dict[str, str]]:
        """
        Returns the raw conversation history turns.
        """
        return self.history

    def get_context_string(self) -> str:
        """
        Formats the history into a clean markdown structure for prompt construction.
        """
        if not self.history:
            return "- (No recent conversation history)"
            
        formatted = []
        for turn in self.history:
            role_label = "User" if turn["role"] == "user" else "Assistant"
            formatted.append(f"- {role_label}: {turn['content']}")
        return "\n".join(formatted)

    def clear(self):
        """
        Clears working memory (e.g. on database wipe/reset).
        """
        self.history.clear()
        logger.info("Working memory cleared.")

# Global working memory singleton instance
working_memory = WorkingMemory(max_turns=20)
