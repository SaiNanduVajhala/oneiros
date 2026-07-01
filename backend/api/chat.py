"""
Oneiros API Layer - Chat Controller

Exposes Wake Phase chat and memory ingestion endpoints via FastAPI routers.
"""

import os
import sys
# Resolve backend directory imports cleanly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from config import get_memory_provider
from memory.provider import MemoryProvider
from kernel.wake.agent import WakeAgent

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
