"""
Oneiros API Layer - Chat Controller

Exposes Wake Phase chat and memory ingestion endpoints via FastAPI routers.
"""

import os
import sys
# Resolve backend directory imports cleanly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import sqlite3
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
        agent = WakeAgent(provider)
        result = await agent.handle_interaction(request.message)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Interaction execution failed: {e}")


@router.get("/memories")
async def list_memories():
    """
    Returns all stored episodic and semantic memory nodes from the local database.
    """
    try:
        db_path = settings.database_path
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, content, access_count, importance, source, semantic_tags FROM nodes ORDER BY rowid DESC")
            rows = cursor.fetchall()
            nodes = []
            for row in rows:
                try:
                    tags = json.loads(row[5]) if row[5] else []
                except Exception:
                    tags = [row[5]] if row[5] else []
                nodes.append({
                    "id": row[0],
                    "content": row[1],
                    "access_count": row[2] or 1,
                    "importance": row[3] or 0.5,
                    "source": row[4] or "user",
                    "semantic_tags": tags,
                })
            return {"nodes": nodes}
    except Exception as e:
        return {"nodes": [], "error": str(e)}
