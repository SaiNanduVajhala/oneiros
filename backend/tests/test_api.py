"""
Oneiros Integration Tests - API endpoint checks
"""

from fastapi.testclient import TestClient
import os
import sys

# Ensure backend folder is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from app import app

client = TestClient(app)

def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] in ("healthy", "healthy_stub")
    assert json_data["provider"] in ("LocalCogneeProvider", "CogneeCloudProvider")
