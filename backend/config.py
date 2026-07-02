"""
Oneiros Configuration Module

Exposes the active memory provider by wrapping infrastructure configurations.
"""

import os
import sys

# Ensure backend folder is in path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from memory.provider import MemoryProvider
from infrastructure.configuration.settings import register_memory_provider, settings

# Expose keys so Cognee libraries resolve offline
os.environ["MOCK_EMBEDDING"] = os.environ.get("MOCK_EMBEDDING", "false")
os.environ["EMBEDDING_PROVIDER"] = os.environ.get("EMBEDDING_PROVIDER", "gemini")
os.environ["LLM_API_KEY"] = settings.llm_api_key

def get_memory_provider() -> MemoryProvider:
    """
    Factory function returning the active MemoryProvider singleton.
    """
    return register_memory_provider()
