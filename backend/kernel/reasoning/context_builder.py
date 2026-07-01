"""
Oneiros Reasoning Subsystem - Context Builder

Formats retrieved memories (episodic and semantic concepts) into cohesive text context.
"""

from typing import List, Dict, Any

class ContextBuilder:
    """
    Utility class for translating raw retrieved memory objects into markdown context.
    """
    @staticmethod
    def build_context_string(recalled_items: List[Dict[str, Any]]) -> str:
        """
        Synthesizes recalled memory elements into a structured text context.
        """
        if not recalled_items:
            return "- (No memory context available)"
            
        formatted_memories = []
        for index, item in enumerate(recalled_items, 1):
            if isinstance(item, str):
                formatted_memories.append(f"{index}. {item}")
            elif isinstance(item, dict):
                text = item.get("text", "")
                if not text and "properties" in item:
                    text = item["properties"].get("content", item["properties"].get("description", str(item)))
                
                # Check for concept/semantic tags
                concept_type = item.get("type", "episodic")
                formatted_memories.append(f"{index}. [{concept_type.upper()}] {text}")
            else:
                formatted_memories.append(f"{index}. {str(item)}")
                
        return "\n".join(formatted_memories)
