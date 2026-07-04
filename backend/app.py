"""
Oneiros Backend Application Entrypoint

Initializes the FastAPI application, sets up dependency injection for the active
MemoryProvider, registers health endpoints, and configures CORS for the frontend.
"""

import os
import sys
# Ensure backend folder is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import os
import sys
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from config import get_memory_provider
from memory.provider import MemoryProvider
from api.chat import router as chat_router
from api.dream import router as dream_router
from api.debug import router as debug_router
from infrastructure.configuration.settings import settings

logger = logging.getLogger("oneiros.app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Perform startup validations (skip during automated tests)
    is_test = "pytest" in sys.modules or os.environ.get("TESTING") == "true"
    if not is_test:
        import sqlite3
        # 1. Verify Database connectivity and write access
        try:
            db_dir = os.path.dirname(settings.database_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
            conn = sqlite3.connect(settings.database_path, timeout=5.0)
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS startup_check (id INTEGER PRIMARY KEY, ts TEXT)")
            cursor.execute("INSERT INTO startup_check (ts) VALUES (?)", (datetime.now().isoformat(),))
            conn.commit()
            cursor.execute("DROP TABLE startup_check")
            conn.commit()
            conn.close()
            logger.info(f"SQLite database validation succeeded at: {settings.database_path}")
        except Exception as e:
            logger.critical(f"DATABASE CONNECTIVITY FAILURE: Cannot write to SQLite database at '{settings.database_path}'. Error: {e}")
            sys.exit(1)

        # 2. Verify environment API Keys
        gemini_key = os.environ.get("GEMINI_API_KEY", os.environ.get("LLM_API_KEY"))
        cognee_key = os.environ.get("COGNEE_API_KEY")

        missing_prod_keys = []
        if not gemini_key or gemini_key == "":
            missing_prod_keys.append("GEMINI_API_KEY")
        if not cognee_key or cognee_key == "":
            missing_prod_keys.append("COGNEE_API_KEY")

        if settings.env == "production":
            if missing_prod_keys:
                logger.critical(f"PRODUCTION CONFIGURATION ERROR: Missing required environment variables: {', '.join(missing_prod_keys)}")
                sys.exit(1)
        else:
            if not gemini_key or gemini_key in ("", "mock-key"):
                logger.warning("DEVELOPMENT WARNING: GEMINI_API_KEY is missing or set to 'mock-key'. LLM features will operate in mock mode.")
            if not cognee_key or cognee_key in ("", "mock-key"):
                logger.warning("DEVELOPMENT WARNING: COGNEE_API_KEY is missing or set to 'mock-key'. Cognee cloud integration requires a valid key.")
    yield

app = FastAPI(title="Oneiros - Cognitive Memory Operating System Kernel", lifespan=lifespan)

# Parse multiple CORS origins from FRONTEND_URLS environment variable
frontend_urls_raw = os.environ.get("FRONTEND_URLS", "")
if frontend_urls_raw:
    origins = [origin.strip() for origin in frontend_urls_raw.split(",") if origin.strip()]
    allow_credentials = True
else:
    origins = ["*"]
    allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
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
    """Health check endpoint exposing extended deployment diagnostics."""
    import sqlite3
    db_conn = "failed"
    try:
        conn = sqlite3.connect(settings.database_path, timeout=2.0)
        conn.close()
        db_conn = "connected"
    except Exception:
        pass

    gemini_key = os.environ.get("GEMINI_API_KEY", os.environ.get("LLM_API_KEY"))
    llm_configured = bool(gemini_key and gemini_key != "mock-key")

    health_status = "healthy"
    try:
        await provider.get_graph_data()
    except Exception:
        health_status = "degraded"

    return {
        "status": health_status,
        "provider": type(provider).__name__,
        "database_connectivity": db_conn,
        "llm_config_state": {
            "model": settings.llm_model,
            "api_key_configured": llm_configured
        },
        "version": "2.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
