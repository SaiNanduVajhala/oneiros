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
        self.reasoning_engine = reasoning_engine or ReasoningEngine()

    async def extract_structured_fact(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extracts a typed fact dictionary from content using the LLM.
        """
        system_instruction = (
            "You are an AI fact-extraction engine. Analyze the statement and extract any personal "
            "facts regarding the user (identity, preferences, location, occupation, relationship, "
            "skills, goals, biography, schedules).\n"
            "Output a JSON object with keys:\n"
            "- 'subject': string representing who the fact is about. For facts about the user/speaker themselves, this MUST strictly be 'user'.\n"
            "- 'predicate': string representing the property (e.g. 'name', 'favorite_color', 'residence')\n"
            "- 'object': string value\n"
            "- 'type': string category (must be one of: Identity, Preference, Location, Occupation, Relationship, Skill, Goal, Biography, Schedule)\n"
            "- 'is_correction': boolean (set true if user explicitly corrects/changes a prior fact)\n"
            "- 'confidence': float (0.0 to 1.0)\n\n"
            "If no structured personal facts can be extracted from the text, return an empty object {}."
        )
        
        try:
            res = await self.reasoning_engine.generate_structured_response(system_instruction, content)
            if not res or "predicate" not in res:
                return None
                
            # Validate type
            fact_type = res.get("type", "Preference")
            if fact_type not in FACT_CATEGORIES:
                fact_type = "Preference"
            res["type"] = fact_type
            res.setdefault("status", "RAW")
            
            # Normalize subject to user
            sub = str(res.get("subject", "user")).lower()
            if sub in ("user", "me", "i", "self"):
                res["subject"] = "user"
                
            return res
        except Exception as e:
            logger.error(f"Structured fact extraction failed: {e}")
            return None

    def resolve_conflicts(self, snapshot: MemoryGraphSnapshot) -> Tuple[MemoryGraphSnapshot, List[str], List[str]]:
        """
        Identifies and marks conflicting structured facts. Runs after Consolidation and before Pruning.
        Implements the 4-stage factual memory lifecycle: ACTIVE -> SUPERSEDED -> ARCHIVED -> FORGOTTEN.
        Returns:
            Tuple[MemoryGraphSnapshot, List[str], List[str]]: Updated snapshot, timeline logs, and list of node IDs to forget.
        """
        logger.info("Executing structured fact conflict resolution with memory lifecycle...")
        timeline_events = []
        forgotten_ids = []
        
        from infrastructure.configuration.settings import settings
        archive_threshold = settings.archive_after_sleep_cycles
        forget_threshold = settings.forget_after_sleep_cycles

        # 1. Update cycle counters and check for stage transitions (SUPERSEDED -> ARCHIVED -> FORGOTTEN)
        remaining_nodes = []
        for node in snapshot.nodes:
            metadata = node.metadata or {}
            fact = metadata.get("fact")
            status = metadata.get("status", "RAW")
            
            if fact:
                if status == "SUPERSEDED":
                    cycles = metadata.get("sleep_cycles_in_status", 0) + 1
                    metadata["sleep_cycles_in_status"] = cycles
                    node.explain_log.append(f"Lifecycle check: Node is in SUPERSEDED status for {cycles} sleep cycles.")
                    
                    if cycles >= archive_threshold:
                        metadata["status"] = "ARCHIVED"
                        metadata["sleep_cycles_in_status"] = 0
                        if "fact" in metadata:
                            metadata["fact"]["status"] = "ARCHIVED"
                        node.explain_log.append(f"Lifecycle transition: Transitioned from SUPERSEDED to ARCHIVED (reached threshold {archive_threshold} cycles).")
                        timeline_events.append(f"Archived obsolete memory: '{node.content}'")
                        
                elif status == "ARCHIVED":
                    cycles = metadata.get("sleep_cycles_in_status", 0) + 1
                    metadata["sleep_cycles_in_status"] = cycles
                    node.explain_log.append(f"Lifecycle check: Node is in ARCHIVED status for {cycles} sleep cycles.")
                    
                    if cycles >= forget_threshold:
                        metadata["status"] = "FORGOTTEN"
                        forgotten_ids.append(node.id)
                        node.explain_log.append(f"Lifecycle transition: Flagged as FORGOTTEN (reached threshold {forget_threshold} cycles).")
                        timeline_events.append(f"Previous obsolete identities removed from Cognee via forget(): '{node.content}'")
                        continue  # Skip adding this node to remaining_nodes (it is forgotten/deleted)
            
            remaining_nodes.append(node)

        # 2. Gather all nodes with active/consolidated/raw facts for conflict checks
        active_nodes: List[MemoryNode] = []
        for node in remaining_nodes:
            metadata = node.metadata or {}
            fact = metadata.get("fact")
            status = metadata.get("status", "RAW")
            
            if fact and status in ("RAW", "ACTIVE", "CONSOLIDATED", "SUPERSEDED"):
                active_nodes.append(node)
                
        if not active_nodes:
            # Build snapshot excluding forgotten nodes
            clean_edges = [
                e for e in snapshot.edges 
                if e.source not in forgotten_ids and e.target not in forgotten_ids
            ]
            return MemoryGraphSnapshot(nodes=remaining_nodes, edges=clean_edges), timeline_events, forgotten_ids

        # 3. Group by subject & predicate
        groups: Dict[Tuple[str, str], List[MemoryNode]] = {}
        for node in active_nodes:
            fact = node.metadata["fact"]
            sub = str(fact.get("subject", "user")).lower()
            pred = str(fact.get("predicate", "")).lower()
            
            # Normalize user names and pronouns to user for correct conflict grouping
            if sub in ("user", "me", "i", "self", "nandu", "rithvik"):
                sub = "user"
                
            key = (sub, pred)
            groups.setdefault(key, []).append(node)

        new_edges: List[MemoryEdge] = []

        # 4. Detect and resolve conflicts / promote raw facts
        for (sub, pred), group_nodes in groups.items():
            if len(group_nodes) < 2:
                # Promote single RAW facts to ACTIVE if no contradiction is found
                single_node = group_nodes[0]
                if single_node.metadata.get("status") == "RAW":
                    single_node.metadata["status"] = "ACTIVE"
                    single_node.metadata["sleep_cycles_in_status"] = 0
                    if "fact" in single_node.metadata:
                        single_node.metadata["fact"]["status"] = "ACTIVE"
                    single_node.explain_log.append("Fact resolver: Promoted raw fact to active status.")
                    timeline_events.append(f"Promoted raw fact to active: '{single_node.content}'")
                continue
                
            # Check if there are different object values
            distinct_objects = {str(n.metadata["fact"].get("object", "")).lower() for n in group_nodes}
            if len(distinct_objects) < 2:
                continue

            logger.info(f"Conflict detected for ({sub}, {pred}) between objects: {distinct_objects}")
            
            # Sort by correction flag and then newest timestamp/id to identify the winner
            sorted_nodes = sorted(
                group_nodes,
                key=lambda n: (
                    1 if n.metadata["fact"].get("is_correction") else 0,
                    n.timestamp.isoformat() if hasattr(n, "timestamp") else n.id
                ),
                reverse=True
            )
            
            winner = sorted_nodes[0]
            
            # Keep winner's status or promote
            old_status = winner.metadata.get("status", "RAW")
            winner.metadata["status"] = "CONSOLIDATED" if old_status == "CONSOLIDATED" else "ACTIVE"
            winner.metadata["sleep_cycles_in_status"] = 0
            if "fact" in winner.metadata:
                winner.metadata["fact"]["status"] = winner.metadata["status"]
            winner.explain_log.append("Fact resolver: Confirmed as active winner.")
            
            # Transition immediate predecessor to SUPERSEDED and older ones to ARCHIVED
            if len(sorted_nodes) > 1:
                immediate_loser = sorted_nodes[1]
                immediate_loser.metadata["status"] = "SUPERSEDED"
                immediate_loser.metadata["sleep_cycles_in_status"] = 0
                if "fact" in immediate_loser.metadata:
                    immediate_loser.metadata["fact"]["status"] = "SUPERSEDED"
                
                # Check for existing SUPERSEDED_BY edge
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
                    older_loser.metadata["sleep_cycles_in_status"] = 0
                    if "fact" in older_loser.metadata:
                        older_loser.metadata["fact"]["status"] = "ARCHIVED"
                    older_loser.explain_log.append("Fact resolver: Archived as historical knowledge.")

        # Build clean snapshot adding the new SUPERSEDED_BY relationships and excluding forgotten nodes
        clean_edges = [
            e for e in snapshot.edges 
            if e.source not in forgotten_ids and e.target not in forgotten_ids
        ] + new_edges
        
        updated_snapshot = MemoryGraphSnapshot(nodes=remaining_nodes, edges=clean_edges)
        
        return updated_snapshot, timeline_events, forgotten_ids
