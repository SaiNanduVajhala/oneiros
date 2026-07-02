"""
Oneiros Memory Subsystem - CogneeCloudProvider

Implements the MemoryProvider wrapper for Cognee Cloud.
All queries and updates route directly to the Cognee Cloud service via CogneeClient.
"""

import os
import uuid
import sqlite3
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Tuple

from memory.provider import MemoryProvider
from infrastructure.cognee_client import CogneeClient
from infrastructure.configuration.settings import settings

logger = logging.getLogger("oneiros.memory.cognee_cloud")

class CogneeCloudProvider(MemoryProvider):
    """
    Adapter class connecting Oneiros Kernel directly to Cognee Cloud via an injected CogneeClient.
    """
    def __init__(self, client: CogneeClient):
        super().__init__()
        self.client = client
        self.db_path = settings.database_path

        # Initialize SQLite purely for metadata (visual layout coordinates caching)
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS node_positions (
                    id TEXT PRIMARY KEY,
                    x REAL,
                    y REAL
                )
            """)
            cursor.execute("DROP TABLE IF EXISTS nodes")
            cursor.execute("DROP TABLE IF EXISTS edges")
            conn.commit()

    async def remember(self, content: str, access_count: int = 1, importance: float = 0.5) -> str:
        """
        Stores an episodic memory node in Cognee Cloud (or queues it if sleeping).
        """
        if self.is_sleeping():
            self.queue_memory(content)
            logger.info("Memory ingestion queued during sleep cycle.")
            return f"queued-{uuid.uuid4().hex[:8]}"

        node_id = f"mem-{uuid.uuid4().hex[:8]}"
        try:
            await self.client.remember(content, dataset_name="oneiros_cloud")
            logger.info("Successfully registered memory in Cognee Cloud.")
        except Exception as e:
            logger.error(f"Cognee Cloud remember failed: {e}")
            raise
        return node_id

    async def recall(self, query: str) -> List[Dict[str, Any]]:
        """
        Queries Cognee Cloud for semantic/episodic retrieval.
        """
        try:
            results = await self.client.recall(query, dataset_name="oneiros_cloud")
            if results:
                return [{"text": str(r)} for r in results]
            return []
        except Exception as e:
            logger.error(f"Cognee Cloud recall failed: {e}")
            raise

    async def improve(self, label: str, description: str, confidence: float) -> str:
        """
        Triggers concept ontology generation inside Cognee Cloud.
        """
        try:
            await self.client.improve(dataset_name="oneiros_cloud")
            logger.info("Successfully invoked Cognee Cloud improve ontology.")
        except Exception as e:
            logger.error(f"Cognee Cloud improve failed: {e}")
            raise
        return f"concept-{uuid.uuid4().hex[:8]}"

    async def forget(self, node_id: str) -> bool:
        """
        Deletes memory nodes from both Cognee Cloud and layout caches.
        """
        try:
            try:
                data_uuid = uuid.UUID(node_id.replace("mem-", "").replace("concept-", ""))
                await self.client.forget(data_id=data_uuid, dataset_name="oneiros_cloud")
            except ValueError:
                await self.client.forget(data_id=node_id, dataset_name="oneiros_cloud")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM node_positions WHERE id = ?", (node_id,))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Cognee Cloud forget failed: {e}")
            raise

    async def get_graph_data(self) -> Tuple[List[Tuple[str, Dict[str, Any]]], List[Tuple[str, str, str, Dict[str, Any]]]]:
        """
        Pulls nodes and edges from Cognee Cloud and maps properties.
        """
        nodes_res = []
        edges_res = []
        try:
            cognee_nodes, cognee_edges = await self.client.get_provenance_graph()
        except Exception as e:
            logger.error(f"Cognee Cloud provenance retrieval failed: {e}")
            raise

        # Map nodes
        for n in cognee_nodes:
            props = n.properties.copy() if n.properties else {}
            props.setdefault("content", props.get("name", props.get("text", props.get("description", n.id))))
            count_val = getattr(n, "count", 1)
            if callable(count_val) or not isinstance(count_val, (int, float)):
                count_val = 1
            props.setdefault("access_count", count_val)
            props.setdefault("importance", 0.5)
            props.setdefault("source", "user" if props.get("type") != "Concept" else "sleep")
            props.setdefault("semantic_tags", [props.get("type", "general").lower()])
            props.setdefault("last_accessed", datetime.now().isoformat())
            nodes_res.append((n.id, props))

        # Map edges
        for e in cognee_edges:
            props = e.properties.copy() if e.properties else {}
            props.setdefault("weight", 1.0)
            edges_res.append((e.source, e.target, e.relation or "related_to", props))

        # Load or generate visual positions in SQLite
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, x, y FROM node_positions")
            positions = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

            for nid, props in nodes_res:
                if nid in positions:
                    props["x"], props["y"] = positions[nid]
                else:
                    import hashlib
                    h = int(hashlib.md5(nid.encode()).hexdigest(), 16)
                    props["x"] = (h % 600) - 300
                    props["y"] = ((h >> 4) % 600) - 300
                    cursor.execute(
                        "INSERT OR REPLACE INTO node_positions (id, x, y) VALUES (?, ?, ?)",
                        (nid, props["x"], props["y"])
                    )
            conn.commit()

        return nodes_res, edges_res

    async def clear_all(self):
        """
        Clears the Cognee Cloud dataset.
        """
        try:
            await self.client.clear_all(dataset_name="oneiros_cloud")
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM node_positions")
                conn.commit()
        except Exception as e:
            logger.error(f"Cognee Cloud clear failed: {e}")
            raise

    def save_graph_snapshot(self, snapshot: Any):
        """
        Synchronizes snapshot changes by executing incremental forget commands against deleted items.
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            loop.create_task(self._async_save_graph_snapshot(snapshot))
        else:
            loop.run_until_complete(self._async_save_graph_snapshot(snapshot))

    async def _async_save_graph_snapshot(self, snapshot: Any):
        try:
            nodes_raw, _ = await self.get_graph_data()
            current_node_ids = {nid for nid, _ in nodes_raw}
            snapshot_node_ids = {node.id for node in snapshot.nodes}

            # Prune obsolete elements from Cognee Cloud incrementally
            for nid in current_node_ids:
                if nid not in snapshot_node_ids:
                    logger.info(f"Sync: Pruning node {nid} from Cognee Cloud.")
                    await self.forget(nid)

            # Update cache positions for surviving snapshot nodes
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM node_positions")
                for node in snapshot.nodes:
                    import hashlib
                    h = int(hashlib.md5(node.id.encode()).hexdigest(), 16)
                    x = (h % 600) - 300
                    y = ((h >> 4) % 600) - 300
                    cursor.execute(
                        "INSERT OR REPLACE INTO node_positions (id, x, y) VALUES (?, ?, ?)",
                        (node.id, x, y)
                    )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to synchronize graph snapshot: {e}")
