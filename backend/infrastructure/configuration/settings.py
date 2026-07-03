"""
Oneiros Infrastructure Layer - Configuration and Dependency Registration

Manages environment configuration validation and Dependency Injection mapping.
"""

import os
import sys
from dotenv import load_dotenv

# Resolve root workspace directory and load .env file
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
load_dotenv(os.path.join(root_dir, ".env"))

class Settings:
    """
    Standard configurations loaded from env variables.
    """
    def __init__(self):
        self.app_title = "Oneiros - Cognitive Memory Operating System Kernel"
        self.llm_model = os.environ.get("LLM_MODEL", "gemini/gemini-1.5-flash")
        self.llm_api_key = os.environ.get("GEMINI_API_KEY", os.environ.get("LLM_API_KEY", "mock-key"))
        self.cognee_api_key = os.environ.get("COGNEE_API_KEY")
        self.cognee_endpoint = os.environ.get("COGNEE_BASE_URL", os.environ.get("COGNEE_ENDPOINT", "https://api.cognee.ai/v1"))
        self.database_path = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "local_brain.db"))
        self.archive_after_sleep_cycles = int(os.environ.get("ARCHIVE_AFTER_SLEEP_CYCLES", 1))
        self.forget_after_sleep_cycles = int(os.environ.get("FORGET_AFTER_SLEEP_CYCLES", 2))


# Instantiate settings singleton
settings = Settings()

# Cache provider mapping
_PROVIDER_INSTANCE = None

def register_memory_provider():
    """
    Resolves dependency binding for the global active MemoryProvider.
    """
    global _PROVIDER_INSTANCE
    if _PROVIDER_INSTANCE is None:
        # Resolve imports dynamically to prevent circular dependencies
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if backend_dir not in sys.path:
            sys.path.append(backend_dir)
            
        api_key = settings.cognee_api_key
        if not api_key or api_key == "mock-key" or api_key == "":
            raise ValueError(
                "CRITICAL CONFIGURATION ERROR: 'COGNEE_API_KEY' is missing or set to placeholder!\n"
                "Please configure COGNEE_API_KEY in your .env environment file to use Cognee Cloud."
            )
        
        # Base URL is optional. Overrides Cognee default cloud URL only if set.
        base_url = os.environ.get("COGNEE_BASE_URL")
        
        from infrastructure.cognee_client import CogneeClient
        from memory.cognee_cloud_provider import CogneeCloudProvider
        
        client = CogneeClient(api_key=api_key, base_url=base_url)
        _PROVIDER_INSTANCE = CogneeCloudProvider(client)
        
    return _PROVIDER_INSTANCE

