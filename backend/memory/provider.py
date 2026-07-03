"""
Oneiros Memory Subsystem - MemoryProvider Interface

This module defines the abstract base class (MemoryProvider) for all persistent and mock
memory operations within the Oneiros kernel. Under Dependency Inversion, the rest of the
Cognitive Operating System kernel interacts only with this abstract interface.
"""

from abc import ABC, abstractmethod
import logging
from typing import List, Dict, Any, Tuple, Optional

class MemoryProvider(ABC):
    """
    Abstract interface defining standard operations for Oneiros memory backends.
    """
    def __init__(self):
        self._is_sleeping = False
        self._queued_memories: List[str] = []

    def set_sleep_state(self, active: bool):
        """Sets whether the provider is currently locked for sleep operations."""
        self._is_sleeping = active

    def is_sleeping(self) -> bool:
        """Returns True if the provider has locked mutations due to sleep consolidation."""
        return getattr(self, "_is_sleeping", False)

    def queue_memory(self, content: str):
        """Queues an incoming memory write during the sleep lock."""
        if not hasattr(self, "_queued_memories"):
            self._queued_memories = []
        self._queued_memories.append(content)

    async def process_queued_memories(self):
        """Flushes and executes all queued memory writes sequentially after sleep completes."""
        if not hasattr(self, "_queued_memories") or not self._queued_memories:
            return
        logger = logging.getLogger("oneiros.memory.provider")
        logger.info(f"Processing {len(self._queued_memories)} queued memories post-sleep...")
        while self._queued_memories:
            content = self._queued_memories.pop(0)
            try:
                await self.remember(content)
            except Exception as e:
                logger.error(f"Failed to process queued memory: {e}")


    @abstractmethod
    async def remember(self, content: str, access_count: int = 1, importance: float = 0.5, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Stores a raw episodic memory statement on the persistent brain substrate.

        Args:
            content: The text description of the experience.
            access_count: Initial activation count.
            importance: User-specified initial significance weight (0.0 to 1.0).
            metadata: Optional metadata properties to attach to the node.

        Returns:
            str: The unique identifier of the stored episodic memory node.
        """
        pass

    @abstractmethod
    async def recall(self, query: str) -> List[Dict[str, Any]]:
        """
        Queries the memory substrate to retrieve episodic and semantic nodes relevant to the query.

        Args:
            query: The search query text.

        Returns:
            List[Dict[str, Any]]: A list of matching memory properties, e.g.
                                 [{"text": "memory content", "access_count": 3}]
        """
        pass

    @abstractmethod
    async def improve(self, label: str, description: str, confidence: float) -> str:
        """
        Stores a generalized semantic concept node derived from sleep consolidation cycles.

        Args:
            label: The brief concept name (e.g. "Pizza Preference").
            description: The summarized concept detail statement.
            confidence: The concept's generation confidence score (0.0 to 1.0).

        Returns:
            str: The unique identifier of the generated concept node.
        """
        pass

    @abstractmethod
    async def forget(self, node_id: str) -> bool:
        """
        Permanently deletes a memory node by ID (episodic, semantic, or metadata).

        Args:
            node_id: The unique identifier of the target node.

        Returns:
            bool: True if the node was successfully found and removed, False otherwise.
        """
        pass

    @abstractmethod
    async def get_graph_data(self, consolidated_only: bool = False) -> Tuple[List[Tuple[str, Dict[str, Any]]], List[Tuple[str, str, str, Dict[str, Any]]]]:
        """
        Extracts all nodes and edges from the graph database formatted for dashboard visualization.

        Returns:
            Tuple[List[Tuple[str, Dict[str, Any]]], List[Tuple[str, str, str, Dict[str, Any]]]]:
                - A list of nodes, where each node is (node_id, properties_dict).
                - A list of edges, where each edge is (source_id, target_id, relation_type, properties_dict).
        """
        pass

    @abstractmethod
    async def clear_all(self):
        """
        Wipes all graph nodes and edges. Used primarily to reset storage during database seeding.
        """
        pass

    async def update_node_properties(
        self,
        node_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: Optional[float] = None,
        access_count: Optional[int] = None
    ):
        """
        Optionally updates a node's properties and metadata in the database.
        """
        pass

