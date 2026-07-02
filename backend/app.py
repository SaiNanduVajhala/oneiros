"""
Oneiros Backend Application Entrypoint

Initializes the FastAPI application, sets up dependency injection for the active
MemoryProvider, registers health endpoints, and configures CORS for the frontend.
"""

import os
import sys
# Ensure backend folder is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from config import get_memory_provider
from memory.provider import MemoryProvider
from api.chat import router as chat_router
from api.dream import router as dream_router
from api.debug import router as debug_router

app = FastAPI(title="Oneiros - Cognitive Memory Operating System Kernel")

# CORS for Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost:5175", "http://127.0.0.1:5175"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include sub-routers
app.include_router(chat_router)
app.include_router(dream_router)
app.include_router(debug_router)

@app.get("/")
async def root():
    return {"name": "Oneiros - Hackathon Cognitive OS", "version": "2.0", "status": "awake"}

@app.get("/health")
async def health_check(provider: MemoryProvider = Depends(get_memory_provider)):
    """Health check endpoint demonstrating MemoryProvider dependency injection."""
    try:
        nodes, edges = await provider.get_graph_data()
        return {
            "status": "healthy",
            "provider": type(provider).__name__,
            "graph_summary": {
                "nodes_count": len(nodes),
                "edges_count": len(edges)
            }
        }
    except NotImplementedError as e:
        return {
            "status": "healthy_stub",
            "provider": type(provider).__name__,
            "message": str(e)
        }
    except Exception as e:
        return {
            "status": "degraded",
            "provider": type(provider).__name__,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
