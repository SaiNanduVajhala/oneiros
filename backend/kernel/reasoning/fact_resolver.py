"""
Oneiros Reasoning Layer - FactResolver & Conflict Resolution
Handles structured fact heuristics, extraction prompts, and sleep-cycle conflict resolution.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from domain.memory import MemoryGraphSnapshot, MemoryNode, MemoryEdge
from kernel.reasoning.llm import ReasoningEngine

logger = logging.getLogger("oneiros.kernel.reasoning.fact_resolver")

FACT_CATEGORIES = {
    "Identity", "Preference", "Location", "Occupation",
    "Relationship", "Skill", "Goal", "Biography", "Schedule"
}

# Grammatical indicators that target potential facts across categories
FACT_HEURISTICS = [
    "my ", "i ", "im ", "actually", "changed", "prefer", "love", "hate",
    "like", "want", "goal", "live in", "work at", "work as", "study"
]

def is_potential_fact(text: str) -> bool:
    """
    Cheap heuristic check to bypass extraction on casual conversation.
    Returns True if the text matches general personal statement pronouns or verbs.
    """
    text_lower = text.lower().strip()
    return any(h in text_lower for h in FACT_HEURISTICS)


class FactResolver:
    """
    Cognitive resolver identifying and transitioning conflicting facts during sleep.
    """
    def __init__(self, reasoning_engine: Optional[ReasoningEngine] = None):
        self.reasoning_engine = reasoning_engine

    def resolve_conflicts(self, snapshot: MemoryGraphSnapshot) -> Tuple[MemoryGraphSnapshot, List[str], List[str]]:
        """
        Identifies and marks conflicting structured facts. Runs after Consolidation and before Pruning.
        Returns:
            Tuple[MemoryGraphSnapshot, List[str], List[str]]: Updated snapshot, timeline logs, and list of node IDs to forget.
        """
        logger.info("Executing structured fact conflict resolution...")
        timeline_events = []
        
        # 1. Group active facts by subject & predicate
        active_nodes: List[MemoryNode] = []
        for node in snapshot.nodes:
            metadata = node.metadata or {}
            fact = metadata.get("fact")
            status = metadata.get("status", "RAW")
            
            if fact and status in ("RAW", "ACTIVE", "CONSOLIDATED", "SUPERSEDED", "INACTIVE"):
                active_nodes.append(node)
                
        if not active_nodes:
            return snapshot, timeline_events, []

        # 2. Group by subject & predicate (dynamically resolving self-referential subjects)
        user_names = {"user", "me", "i", "self"}
        for node in active_nodes:
            fact_data = node.metadata.get("fact")
            if isinstance(fact_data, dict):
                pred = str(fact_data.get("predicate", "")).lower()
                obj = str(fact_data.get("object", "")).lower()
                if "name" in pred and obj:
                    user_names.add(obj)

        groups: Dict[Tuple[str, str], List[MemoryNode]] = {}
        for node in active_nodes:
            fact = node.metadata["fact"]
            sub = str(fact.get("subject", "USER")).lower()
            pred = str(fact.get("predicate", "")).lower()
            obj = str(fact.get("object", "")).lower().strip()
            
            if sub in user_names:
                sub = "user"
                
            # Group preference facts dynamically by their semantic category
            fact_type = str(fact.get("type", "")).lower()
            category = str(node.metadata.get("category", "")).lower()
            if fact_type == "preference" or category == "preference":
                key = (sub, f"preference.{obj}")
            else:
                key = (sub, pred)
                
            groups.setdefault(key, []).append(node)

        new_edges: List[MemoryEdge] = []

        # 3. Detect and resolve conflicts / promote raw facts
        for (sub, pred), group_nodes in groups.items():
            if len(group_nodes) < 2:
                single_node = group_nodes[0]
                if single_node.metadata.get("status") == "RAW":
                    single_node.metadata["status"] = "ACTIVE"
                    if "fact" in single_node.metadata:
                        single_node.metadata["fact"]["status"] = "ACTIVE"
                    single_node.explain_log.append("Fact resolver: Promoted raw fact to active status.")
                    timeline_events.append(f"Promoted raw fact to active: '{single_node.content}'")
                continue
                
            distinct_values = {f"{n.metadata['fact'].get('predicate')}:{n.metadata['fact'].get('object')}".lower() for n in group_nodes}
            if len(distinct_values) < 2:
                continue

            logger.info(f"Conflict detected for ({sub}, {pred}) between values: {distinct_values}")
            
            def get_sort_key(node):
                ts = ""
                if isinstance(node.metadata, dict) and "timestamp" in node.metadata and node.metadata["timestamp"]:
                    ts = str(node.metadata["timestamp"])
                elif hasattr(node, "timestamp") and node.timestamp:
                    ts = node.timestamp.isoformat() if hasattr(node.timestamp, "isoformat") else str(node.timestamp)
                is_corr = 1 if isinstance(node.metadata, dict) and node.metadata.get("fact", {}).get("is_correction") else 0
                return (ts, is_corr)

            sorted_nodes = sorted(
                group_nodes,
                key=get_sort_key,
                reverse=True
            )
            
            winner = sorted_nodes[0]
            
            old_status = winner.metadata.get("status", "RAW")
            winner.metadata["status"] = "CONSOLIDATED" if old_status == "CONSOLIDATED" else "ACTIVE"
            if "fact" in winner.metadata:
                winner.metadata["fact"]["status"] = winner.metadata["status"]
            winner.explain_log.append("Fact resolver: Confirmed as active winner.")
            
            if len(sorted_nodes) > 1:
                immediate_loser = sorted_nodes[1]
                immediate_loser.metadata["status"] = "SUPERSEDED"
                if "fact" in immediate_loser.metadata:
                    immediate_loser.metadata["fact"]["status"] = "SUPERSEDED"
                
                edge_exists = any(
                    e.source == immediate_loser.id and e.target == winner.id and e.type == "SUPERSEDED_BY"
                    for e in snapshot.edges
                )
                if not edge_exists:
                    new_edges.append(MemoryEdge(
                        source=immediate_loser.id,
                        target=winner.id,
                        type="SUPERSEDED_BY",
                        weight=1.0,
                        metadata={"reason": "corrected_by_user"}
                    ))
                
                immediate_loser.explain_log.append(f"Fact resolver: Superseded by node {winner.id} (Winner: {winner.content})")
                
                msg = f"Superseded obsolete fact: '{immediate_loser.content}' -> '{winner.content}'"
                timeline_events.append(msg)
                logger.info(msg)

                for older_loser in sorted_nodes[2:]:
                    older_loser.metadata["status"] = "ARCHIVED"
                    if "fact" in older_loser.metadata:
                        older_loser.metadata["fact"]["status"] = "ARCHIVED"
                    older_loser.explain_log.append("Fact resolver: Archived as historical knowledge.")

        updated_edges = snapshot.edges + new_edges
        updated_snapshot = MemoryGraphSnapshot(nodes=snapshot.nodes, edges=updated_edges)
        
        return updated_snapshot, timeline_events, []

