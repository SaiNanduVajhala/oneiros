import os
import sys

# Ensure backend folder is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from unittest.mock import patch

# Mock COGNEE_API_KEY before importing app to satisfy startup validation
with patch.dict(os.environ, {"COGNEE_API_KEY": "fake-active-test-key-123"}):
    from app import app

from fastapi.testclient import TestClient

client = TestClient(app)

from config import get_memory_provider
from unittest.mock import AsyncMock, MagicMock
from memory.cognee_cloud_provider import CogneeCloudProvider

class StubCloudProvider(CogneeCloudProvider):
    def __init__(self):
        pass
    async def get_graph_data(self):
        return [], []

StubCloudProvider.__name__ = "CogneeCloudProvider"

def test_health_check_endpoint():
    mock_provider = StubCloudProvider()
    
    # Override provider dependency injection
    app.dependency_overrides[get_memory_provider] = lambda: mock_provider
    try:
        response = client.get("/health")
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["status"] == "healthy"
        assert json_data["provider"] == "CogneeCloudProvider"
    finally:
        app.dependency_overrides.clear()
