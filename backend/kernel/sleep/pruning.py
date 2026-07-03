"""
Oneiros Sleep Subsystem - Pruning Stage (N3)

Prunes low-activation nodes, resolves duplicates via a two-stage checker,
and processes contradiction detections.
"""

import logging
from datetime import datetime
from typing import List, Tuple, Set, Dict, Any
from memory.provider import MemoryProvider
from domain.memory import MemoryGraphSnapshot, MemoryNode, MemoryEdge
from kernel.algorithms.centrality import compute_graph_centrality
from kernel.algorithms.activation import calculate_node_activation
from kernel.algorithms.similarity import detect_duplicate_candidates
from kernel.algorithms.contradiction import find_potential_contradiction_pairs
from kernel.reasoning.llm import ReasoningEngine

logger = logging.getLogger("oneiros.kernel.sleep.pruning")

class PruningStage:
    """
    N3 Sleep Stage: Performs duplicate merges, contradiction resolutions, and score decay.
    """
    def __init__(self, provider: MemoryProvider, reasoning_engine: ReasoningEngine):
        self.provider = provider
        self.reasoning_engine = reasoning_engine
        
        from infrastructure.configuration.settings import settings
        from kernel.sleep.lifecycle_engine import MemoryLifecycleEngine
        self.lifecycle_engine = MemoryLifecycleEngine(
            active_to_inactive_threshold=settings.active_to_inactive_threshold,
            inactive_to_archived_threshold=settings.inactive_to_archived_threshold,
            superseded_to_archived_threshold=settings.superseded_to_archived_threshold,
            forget_retention_threshold=settings.forget_retention_threshold
        )

    async def execute(
        self,
        snapshot: MemoryGraphSnapshot,
        retention_threshold: float = 0.15
    ) -> Tuple[MemoryGraphSnapshot, List[str]]:
        """
        Calculates activation decay, resolves duplicates/contradictions, and deletes obsolete items.
        
        Returns:
            Tuple[MemoryGraphSnapshot, List[str]]: Updated snapshot and timeline log events.
        """
        logger.info("Executing Pruning (N3) Stage with Life Cycle Engine...")
        timeline_events = []
        
        nodes_to_delete: Set[str] = set()
        nodes_dict: Dict[str, MemoryNode] = {n.id: n for n in snapshot.nodes}

        # --- 1. Compute Retention Score & Manage State Transitions ---
        centrality_map = compute_graph_centrality(snapshot.nodes, snapshot.edges)
        current_time = datetime.now()
        
        for node in snapshot.nodes:
            is_concept = node.source in ("sleep", "semantic")
            if is_concept:
                continue
                
            node_centrality = centrality_map.get(node.id, 0.0)
            
            # Compute dynamic score
            retention_score = self.lifecycle_engine.calculate_retention_score(node, node_centrality, current_time)
            node.metadata["retention_score"] = retention_score
            
            # Sync retention score to SQLite
            try:
                await self.provider.update_node_properties(
                    node_id=node.id,
                    metadata={"retention_score": retention_score}
                )
            except Exception as e:
                logger.warning(f"Failed to save retention score for node {node.id}: {e}")
                
            # Transition evaluation
            new_status, transition_desc = self.lifecycle_engine.evaluate_transition(node, retention_score)
            if transition_desc:
                node.metadata["status"] = new_status
                if "fact" in node.metadata:
                    node.metadata["fact"]["status"] = new_status
                node.explain_log.append(transition_desc)
                timeline_events.append(transition_desc)
                
                if new_status == "FORGOTTEN":
                    nodes_to_delete.add(node.id)
                else:
                    try:
                        await self.provider.update_node_properties(
                            node_id=node.id,
                            metadata={"status": new_status}
                        )
                    except Exception as e:
                        logger.warning(f"Failed to update node status for {node.id}: {e}")

        # --- 2. Two-Stage Duplicate Detection ---
        # Filter out superseded, archived, and forgotten nodes from active processing checks
        active_nodes_for_checks = [n for n in snapshot.nodes if n.metadata.get("status", "RAW") not in ("SUPERSEDED", "ARCHIVED", "FORGOTTEN")]

        candidates = detect_duplicate_candidates(active_nodes_for_checks, threshold=0.90)
        
        for node_a, node_b, score in candidates:
            # Skip if either is already marked for deletion
            if node_a.id in nodes_to_delete or node_b.id in nodes_to_delete:
                continue
                
            if score >= 0.995:
                # Stage 1: Auto-merge
                preferred, obsolete = (node_a, node_b) if node_a.access_count >= node_b.access_count else (node_b, node_a)
                preferred.access_count += obsolete.access_count
                preferred.importance = max(preferred.importance, obsolete.importance)
                nodes_to_delete.add(obsolete.id)
                
                msg = f"Auto-merged duplicate memory: '{obsolete.content[:25]}...' into '{preferred.content[:25]}...'"
                preferred.explain_log.append(f"Auto-merged node {obsolete.id} (Similarity: {score:.3f})")
                timeline_events.append(msg)
                
            elif score >= 0.90:
                # Stage 2: Ask Gemini for validation
                system_prompt = "You are a cognitive memory system resolving duplicates. Determine if these two memories describe the same experience."
                user_prompt = (
                    f"Memory A (ID: {node_a.id}): {node_a.content}\n"
                    f"Memory B (ID: {node_b.id}): {node_b.content}\n\n"
                    "Output a JSON object with keys:\n"
                    "- 'duplicate': boolean\n"
                    "- 'preferred_id': string (either memory ID)\n"
                    "- 'reason': string explaining the choice"
                )
                try:
                    result = await self.reasoning_engine.generate_structured_response(system_prompt, user_prompt)
                    if result.get("duplicate") is True:
                        preferred_id = result.get("preferred_id")
                        preferred = nodes_dict.get(preferred_id)
                        obsolete = node_b if preferred_id == node_a.id else node_a
                        
                        if preferred and obsolete:
                            preferred.access_count += obsolete.access_count
                            nodes_to_delete.add(obsolete.id)
                            
                            reason = result.get("reason", "LLM validated similarity match.")
                            preferred.explain_log.append(f"LLM-merged node {obsolete.id} - Reason: {reason}")
                            timeline_events.append(f"Merged duplicate: '{obsolete.content[:25]}...' -> '{preferred.content[:25]}...' ({reason[:40]})")
                except Exception as e:
                    logger.error(f"Error executing LLM duplicate check: {e}")
 
        # --- 3. Contradiction Resolution ---
        contradiction_pairs = find_potential_contradiction_pairs(active_nodes_for_checks)
        for node_a, node_b in contradiction_pairs:
            if node_a.id in nodes_to_delete or node_b.id in nodes_to_delete:
                continue

            # Query Gemini to verify contradiction and resolve
            system_prompt = "You are a cognitive memory system resolving logical contradictions in persistent memories."
            user_prompt = (
                f"Memory A (ID: {node_a.id}): {node_a.content}\n"
                f"Memory B (ID: {node_b.id}): {node_b.content}\n\n"
                "Output a JSON object with keys:\n"
                "- 'contradiction': boolean\n"
                "- 'resolution': string ('delete_a', 'delete_b', or 'keep_both')\n"
                "- 'reason': string explaining why they conflict and how to resolve it"
            )
            try:
                result = await self.reasoning_engine.generate_structured_response(system_prompt, user_prompt)
                if result.get("contradiction") is True:
                    resolution = result.get("resolution")
                    reason = result.get("reason", "")
                    
                    if resolution == "delete_a":
                        nodes_to_delete.add(node_a.id)
                        node_b.explain_log.append(f"Resolved contradiction: Deleted node {node_a.id} (Reason: {reason})")
                        timeline_events.append(f"Resolved conflict: Kept '{node_b.content[:30]}...', pruned contradictory '{node_a.content[:30]}...'")
                    elif resolution == "delete_b":
                        nodes_to_delete.add(node_b.id)
                        node_a.explain_log.append(f"Resolved contradiction: Deleted node {node_b.id} (Reason: {reason})")
                        timeline_events.append(f"Resolved conflict: Kept '{node_a.content[:30]}...', pruned contradictory '{node_b.content[:30]}...'")
            except Exception as e:
                logger.error(f"Error resolving contradiction via LLM: {e}")

        # --- 4. Synchronize Snapshot Deletions ---
        # Sync deleted memories back to the physical database provider
        for target_id in nodes_to_delete:
            try:
                # Call persist engine deletion
                await self.provider.forget(target_id)
            except NotImplementedError:
                pass  # Ignore stub errors
            except Exception as e:
                logger.error(f"Failed to sync node deletion {target_id} with database: {e}")

        # Build clean snapshot arrays excluding purged nodes and edges referencing them
        clean_nodes = [n for n in snapshot.nodes if n.id not in nodes_to_delete]
        clean_edges = [
            e for e in snapshot.edges 
            if e.source not in nodes_to_delete and e.target not in nodes_to_delete
        ]

        updated_snapshot = MemoryGraphSnapshot(nodes=clean_nodes, edges=clean_edges)
        
        logger.info(f"Pruning completed. Nodes purged/merged: {len(nodes_to_delete)}.")
        return updated_snapshot, timeline_events
