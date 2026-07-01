"""
Oneiros Scheduler - Main Orchestrator

Evaluates triggers and coordinates background consolidation triggers based on graph state.
"""

import time
import logging
import asyncio
from typing import List, Optional
from memory.provider import MemoryProvider
from kernel.sleep.coordinator import SleepCoordinator
from kernel.scheduler.triggers import BaseTrigger, MessageCountTrigger
from kernel.scheduler.policies import BasePolicy, UserActivityPolicy
from domain.memory import MemoryNode, MemoryEdge
from kernel.algorithms.graph_metrics import calculate_graph_density, compute_memory_health
from kernel.algorithms.similarity import detect_duplicate_candidates
from kernel.algorithms.contradiction import find_potential_contradiction_pairs
from utils.embedding_utils import estimate_token_count

logger = logging.getLogger("oneiros.kernel.scheduler.scheduler")

class CognitiveScheduler:
    """
    Scheduler evaluating trigger inputs and initiating dream cycles.
    """
    def __init__(
        self,
        provider: MemoryProvider,
        coordinator: Optional[SleepCoordinator] = None,
        triggers: Optional[List[BaseTrigger]] = None,
        policies: Optional[List[BasePolicy]] = None
    ):
        self.provider = provider
        self.coordinator = coordinator or SleepCoordinator(provider)
        self.triggers = triggers if triggers is not None else [MessageCountTrigger(threshold=5)]
        self.policies = policies if policies is not None else [UserActivityPolicy(quiet_period_seconds=15.0)]
        
        # State counters
        self.message_counter = 0
        self.last_user_interaction_time = 0.0

    def record_interaction(self):
        """
        Signals the scheduler that a user query has occurred.
        """
        self.message_counter += 1
        self.last_user_interaction_time = time.time()
        logger.info(f"Scheduler recorded interaction. Current message count: {self.message_counter}")

    async def check_and_trigger(self) -> bool:
        """
        Checks trigger signals and runs a sleep cycle if policies approve.
        """
        # Gather dynamic snapshot parameters from memory provider
        active_node_count = 0
        active_token_count = 0
        graph_density = 0.0
        health_score = 100.0

        try:
            nodes_raw, edges_raw = await self.provider.get_graph_data()
            nodes = [
                MemoryNode(
                    id=nid,
                    content=props.get("content") or props.get("description") or nid,
                    importance=float(props.get("importance", 0.5)),
                    access_count=int(props.get("access_count", 1)),
                    source=props.get("source", "user")
                )
                for nid, props in nodes_raw
            ]
            edges = [
                MemoryEdge(source=src, target=tgt, type=rel, weight=float(props.get("weight", 1.0)))
                for src, tgt, rel, props in edges_raw
            ]

            active_node_count = len(nodes)
            active_token_count = sum(estimate_token_count(n.content) for n in nodes)
            graph_density = calculate_graph_density(nodes, edges)
            
            duplicates = len(detect_duplicate_candidates(nodes, 0.90))
            contradictions = len(find_potential_contradiction_pairs(nodes))
            
            health_score = compute_memory_health(
                nodes=nodes,
                edges=edges,
                duplicate_count=duplicates,
                contradiction_count=contradictions
            )
        except NotImplementedError:
            # Fallback stub values if provider offline
            pass

        context = {
            "message_count": self.message_counter,
            "last_user_interaction_time": self.last_user_interaction_time,
            "active_node_count": active_node_count,
            "active_token_count": active_token_count,
            "graph_density": graph_density,
            "memory_health_score": health_score,
            "cpu_load_percent": 10.0
        }

        # 1. Evaluate triggers
        triggered = False
        for trigger in self.triggers:
            if trigger.evaluate(context):
                triggered = True
                break

        if not triggered:
            return False

        logger.info(f"Scheduler triggers fired. Details: {context}. Evaluating safety policies...")

        # 2. Check safety policies
        for policy in self.policies:
            if not policy.is_allowed(context):
                logger.info(f"Sleep cycle blocked by safety policy: {policy.__class__.__name__}")
                return False

        logger.info("Policies approved. Spawning background sleep cycle...")
        
        # Reset message counter
        self.message_counter = 0
        
        # Execute asynchronously in the background
        asyncio.create_task(self.coordinator.execute_cycle())
        return True
