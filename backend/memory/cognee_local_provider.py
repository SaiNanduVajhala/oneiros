"""
Oneiros Memory Subsystem - LocalCogneeProvider

Implements the concrete MemoryProvider interface targeting the local Cognee SDK.
Acts as a thin adapter querying Cognee directly. Eliminates duplicate SQLite memory storage,
using local SQLite database purely to persist layout coordinates metadata.
"""

import os
import uuid
import sqlite3
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Tuple

import cognee
from memory.provider import MemoryProvider
from infrastructure.configuration.settings import settings

logger = logging.getLogger("oneiros.memory.local_cognee")

# Skip connection test on startup to prevent blocking if offline/no key
os.environ["COGNEE_SKIP_CONNECTION_TEST"] = "true"


class LocalCogneeProvider(MemoryProvider):
    """
    Thin adapter connecting Oneiros Kernel directly to local Cognee SDK as single source of truth.
    """

    def __init__(self):
        super().__init__()
        self._fallback_nodes: Dict[str, Dict[str, Any]] = {}
        self._fallback_edges: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

        # 1. Configure local Cognee instance parameters
        try:
            cognee.config.set_llm_provider("gemini")
            cognee.config.set_llm_api_key(settings.llm_api_key)
            cognee.config.set_llm_model("gemini/gemini-1.5-flash")
            
            cognee.config.set_embedding_provider("fastembed")
            cognee.config.set_embedding_model("BAAI/bge-small-en-v1.5")
            cognee.config.set_embedding_dimensions(384)
            cognee.config.set_vector_db_provider("lancedb")
        except Exception as e:
            logger.warning(f"Failed to configure local Cognee settings: {e}")

        # 2. Initialize local SQLite purely for metadata (visual layout caching)
        self.db_path = settings.database_path
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
            # Drop old duplicate memory storage tables to avoid database pollution
            cursor.execute("DROP TABLE IF EXISTS nodes")
            cursor.execute("DROP TABLE IF EXISTS edges")
            conn.commit()

    async def remember(self, content: str, access_count: int = 1, importance: float = 0.5) -> str:
        """
        Stores an episodic memory node in local Cognee.
        """
        if self.is_sleeping():
            self.queue_memory(content)
            logger.info("Memory ingestion queued during sleep cycle (local).")
            return f"queued-{uuid.uuid4().hex[:8]}"

        node_id = f"mem-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        
        try:
            await cognee.remember(content, dataset_name="oneiros_local")
            logger.info("Successfully registered memory in local Cognee SDK.")
        except Exception as e:
            logger.warning(f"Local Cognee remember failed: {e}. Using local fallback substrate.")

        # Sync memory to fallback cache
        words = content.lower().split()
        tags = [w for w in ["gpu", "cuda", "coffee", "caffeine", "python", "fastapi", "web", "ml", "neuroscience", "sleep", "memory"] if w in words]
        if not tags:
            tags = ["general"]

        self._fallback_nodes[node_id] = {
            "content": content,
            "access_count": access_count,
            "importance": importance,
            "source": "user",
            "semantic_tags": tags,
            "last_accessed": now
        }

        return node_id

    async def recall(self, query: str) -> List[Dict[str, Any]]:
        """
        Queries Cognee for matching memory vectors.
        """
        try:
            results = await cognee.recall(query, dataset_name="oneiros_local")
            if results:
                return [{"text": str(r)} for r in results]
        except Exception as e:
            logger.warning(f"Local Cognee recall failed: {e}. Querying fallback cache.")

        # Local fallback search
        res = []
        for nid, val in self._fallback_nodes.items():
            if query.lower() in val["content"].lower():
                res.append({"id": nid, "text": val["content"], "access_count": val["access_count"]})
        return res

    async def improve(self, label: str, description: str, confidence: float) -> str:
        """
        Calls local Cognee improve ontology builders.
        """
        try:
            await cognee.improve(dataset="oneiros_local")
            logger.info("Successfully invoked local Cognee improve.")
        except Exception as e:
            logger.warning(f"Local Cognee improve failed: {e}")

        # Sync concept to fallback cache
        node_id = f"concept-{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        
        self._fallback_nodes[node_id] = {
            "content": f"Concept: {label}. {description}",
            "access_count": 1,
            "importance": confidence,
            "source": "sleep",
            "semantic_tags": ["concept"],
            "last_accessed": now
        }

        return node_id

    async def forget(self, node_id: str) -> bool:
        """
        Deletes memory nodes from both Cognee and local caches.
        """
        try:
            try:
                data_uuid = uuid.UUID(node_id.replace("mem-", "").replace("concept-", ""))
                await cognee.forget(data_id=data_uuid, dataset="oneiros_local")
            except ValueError:
                await cognee.forget(data_id=node_id, dataset="oneiros_local")
        except Exception as e:
            logger.warning(f"Local Cognee forget failed: {e}")

        deleted = (node_id in self._fallback_nodes)
        if node_id in self._fallback_nodes:
            del self._fallback_nodes[node_id]

        # Evict related edges
        edges_to_delete = [k for k in self._fallback_edges.keys() if k[0] == node_id or k[1] == node_id]
        for k in edges_to_delete:
            del self._fallback_edges[k]

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM node_positions WHERE id = ?", (node_id,))
            conn.commit()

        return deleted

    async def get_graph_data(self) -> Tuple[List[Tuple[str, Dict[str, Any]]], List[Tuple[str, str, str, Dict[str, Any]]]]:
        """
        Extracts all nodes and edges directly from local Cognee and merges metadata.
        """
        nodes_res = []
        edges_res = []

        cognee_nodes = []
        cognee_edges = []
        try:
            cognee_nodes, cognee_edges = await cognee.get_memory_provenance_graph(include_memory=True)
        except Exception as e:
            logger.warning(f"Local Cognee provenance retrieval failed: {e}")

        # Merge nodes
        nodes_map = {}
        for nid, props in self._fallback_nodes.items():
            nodes_map[nid] = props.copy()

        for n in cognee_nodes:
            props = n.properties.copy() if n.properties else {}
            props.setdefault("content", props.get("name", props.get("text", props.get("description", n.id))))
            props.setdefault("access_count", getattr(n, "count", 1) or 1)
            props.setdefault("importance", 0.5)
            props.setdefault("source", "user" if props.get("type") != "Concept" else "sleep")
            props.setdefault("semantic_tags", [props.get("type", "general").lower()])
            props.setdefault("last_accessed", datetime.now().isoformat())
            nodes_map[n.id] = props

        for nid, props in nodes_map.items():
            nodes_res.append((nid, props))

        # Merge edges
        edges_map = {}
        for (src, tgt, rel), props in self._fallback_edges.items():
            edges_map[(src, tgt, rel)] = props.copy()

        for e in cognee_edges:
            props = e.properties.copy() if e.properties else {}
            props.setdefault("weight", 1.0)
            edges_map[(e.source, e.target, e.relation or "related_to")] = props

        for (src, tgt, rel), props in edges_map.items():
            edges_res.append((src, tgt, rel, props))

        # Load or generate visual positions
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
        Clears local Cognee vector collections and cache databases.
        """
        try:
            await cognee.forget(everything=True, dataset="oneiros_local")
        except Exception as e:
            logger.warning(f"Local Cognee clear failed: {e}")

        self._fallback_nodes.clear()
        self._fallback_edges.clear()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM node_positions")
            conn.commit()

    def save_graph_snapshot(self, snapshot: Any):
        """
        Synchronizes updated MemoryGraphSnapshot modifications back into Cognee database.
        """
        import asyncio
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
        # Fetch current dataset state
        nodes_raw, edges_raw = await self.get_graph_data()
        current_node_ids = {nid for nid, _ in nodes_raw}
        snapshot_node_ids = {node.id for node in snapshot.nodes}

        # 1. Prune nodes removed in algorithms from Cognee
        for nid in current_node_ids:
            if nid not in snapshot_node_ids:
                logger.info(f"Sync: Pruning node {nid} from Cognee substrate.")
                await self.forget(nid)

        # 2. Reset fallbacks
        self._fallback_nodes.clear()
        self._fallback_edges.clear()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM node_positions")

            for node in snapshot.nodes:
                self._fallback_nodes[node.id] = {
                    "content": node.content,
                    "access_count": node.access_count,
                    "importance": node.importance,
                    "source": node.source,
                    "semantic_tags": node.semantic_tags,
                    "last_accessed": node.last_accessed.isoformat() if hasattr(node.last_accessed, "isoformat") else str(node.last_accessed)
                }

                import hashlib
                h = int(hashlib.md5(node.id.encode()).hexdigest(), 16)
                x = (h % 600) - 300
                y = ((h >> 4) % 600) - 300
                cursor.execute(
                    "INSERT OR REPLACE INTO node_positions (id, x, y) VALUES (?, ?, ?)",
                    (node.id, x, y)
                )

            for edge in snapshot.edges:
                self._fallback_edges[(edge.source, edge.target, edge.type)] = {
                    "weight": edge.weight
                }
            conn.commit()
