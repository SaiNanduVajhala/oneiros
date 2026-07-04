"""
Oneiros API Layer - Chat Controller

Exposes Wake Phase chat and memory ingestion endpoints via FastAPI routers.
"""

import os
import sys
# Resolve backend directory imports cleanly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
import sqlite3
logger = logging.getLogger("oneiros.api.chat")

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from config import get_memory_provider
from memory.provider import MemoryProvider
from kernel.wake.agent import WakeAgent
from infrastructure.configuration.settings import settings

router = APIRouter(prefix="/api/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    message: str

@router.post("")
async def chat_endpoint(request: ChatRequest, provider: MemoryProvider = Depends(get_memory_provider)):
    """
    Standard chat route that runs the user input through the Wake Agent workflow.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="User message content cannot be empty.")
        
    try:
        # Reset dream coordinator snapshots so the main graph defaults to the live DB mirror
        try:
            from api.dream import reset_dream_coordinator
            reset_dream_coordinator()
        except Exception:
            pass

        agent = WakeAgent(provider)
        result = await agent.handle_interaction(request.message)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Interaction execution failed: {e}")



@router.get("/memories")
async def list_memories(provider: MemoryProvider = Depends(get_memory_provider)):
    """
    Returns all stored episodic and semantic memory nodes.
    Reads from SQLite first; falls back to Cognee Cloud graph when SQLite is empty.
    """
    nodes = []

    # 1. Try SQLite
    try:
        db_path = settings.database_path
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, content, access_count, importance, source, semantic_tags, metadata FROM nodes ORDER BY rowid DESC")
            rows = cursor.fetchall()
            for row in rows:
                try:
                    tags = json.loads(row[5]) if row[5] else []
                except Exception:
                    tags = [row[5]] if row[5] else []
                try:
                    meta = json.loads(row[6]) if row[6] else {}
                except Exception:
                    meta = {}
                nodes.append({
                    "id": row[0],
                    "content": row[1],
                    "access_count": row[2] or 1,
                    "importance": row[3] or 0.5,
                    "source": row[4] or "user",
                    "semantic_tags": tags,
                    "metadata": meta
                })
    except Exception:
        pass

    # 2. Fall back to Cognee Cloud graph when SQLite is empty
    if not nodes:
        try:
            raw_nodes, _ = await provider.get_graph_data()
            for node_id, props in raw_nodes:
                content = props.get("content") or props.get("name") or props.get("text") or ""
                if not content:
                    continue
                nodes.append({
                    "id": node_id,
                    "content": content,
                    "access_count": props.get("access_count", 1),
                    "importance": float(props.get("importance", 0.5)),
                    "source": props.get("source", "user"),
                    "semantic_tags": props.get("semantic_tags") or [],
                    "metadata": {k: v for k, v in props.items() if k not in ("content", "access_count", "importance", "source", "semantic_tags")},
                })
        except Exception as e:
            logger.warning(f"Fallback graph fetch failed: {e}")

    return {"nodes": nodes}



@router.delete("/memories/{node_id}")
async def delete_memory(node_id: str, provider: MemoryProvider = Depends(get_memory_provider)):
    """
    Deletes a single memory node by ID from both the graph provider and the local SQLite mirror.
    """
    try:
        # Remove from provider graph
        await provider.forget(node_id)
    except Exception as e:
        pass  # Provider may not have it; still try local DB

    try:
        db_path = settings.database_path
        with sqlite3.connect(db_path) as conn:
            conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
            conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete from local store: {e}")

    return {"status": "deleted", "id": node_id}


@router.delete("/memories")
async def delete_all_memories(provider: MemoryProvider = Depends(get_memory_provider)):
    """
    Wipes all memory nodes from the provider and the local SQLite mirror.
    """
    try:
        from kernel.wake.working_memory import working_memory
        working_memory.clear()
    except Exception as e:
        logger.error(f"Failed to clear working memory context: {e}")

    try:
        await provider.clear_all()
    except Exception as e:
        pass  # Log but continue to wipe local DB

    try:
        db_path = settings.database_path
        with sqlite3.connect(db_path) as conn:
            conn.execute("DELETE FROM nodes")
            conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear local store: {e}")

    return {"status": "cleared"}
