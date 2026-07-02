import os
import sys
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

# Ensure backend folder is in path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# Mock COGNEE_API_KEY before importing app to satisfy startup validation
with patch.dict(os.environ, {"COGNEE_API_KEY": "fake-active-test-key-123"}):
    from app import app

from fastapi.testclient import TestClient
from config import get_memory_provider
from memory.cognee_cloud_provider import CogneeCloudProvider
from infrastructure.cognee_client import CogneeClient
from domain.dream import DreamReport
from domain.vis_events import VisEvent

client = TestClient(app)

class StubCogneeClient(MagicMock):
    pass

class StubProvider(CogneeCloudProvider):
    def __init__(self):
        self._is_sleeping = False
        self._queued_memories = []
        self.client = MagicMock(spec=CogneeClient)
        # Mock connection methods
        self.client.connect = AsyncMock()
        self.client.disconnect = AsyncMock()
        self.client.get_provenance_graph = AsyncMock(return_value=([], []))
        self.client.clear_all = AsyncMock()

    async def get_graph_data(self):
        return [
            ("node-1", {"content": "Test Node 1", "importance": 0.8, "access_count": 3, "source": "user", "semantic_tags": ["test"]})
        ], [
            ("node-1", "node-2", "related_to", {"weight": 1.0})
        ]

    async def clear_all(self):
        await self.client.clear_all(dataset_name="oneiros_cloud")
        self._queued_memories = []

StubProvider.__name__ = "StubProvider"


@pytest.fixture
def mock_provider():
    provider = StubProvider()
    app.dependency_overrides[get_memory_provider] = lambda: provider
    yield provider
    app.dependency_overrides.clear()


def test_debug_status_endpoint(mock_provider):
    response = client.get("/api/debug/status")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["provider"] == "StubProvider"
    assert json_data["sleep_running"] is False
    assert json_data["sleep_status"] == "idle"
    assert json_data["queue_size"] == 0
    assert json_data["active_stage"] == "idle"


def test_debug_config_endpoint(mock_provider):
    with patch.dict(os.environ, {"ONEIROS_PROVIDER": "cloud", "EMBEDDING_PROVIDER": "mock"}):
        response = client.get("/api/debug/config")
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["provider"] == "StubProvider"
        assert json_data["provider_mode"] == "cloud"
        assert json_data["database"] == "Cognee Cloud"
        assert json_data["embedding_model"] == "mock"
        assert json_data["version"] == "2.0"


def test_debug_provenance_endpoint(mock_provider):
    # Mock node and edge objects returned by Cognee
    mock_node = MagicMock()
    mock_node.id = "node-abc"
    mock_node.properties = {"name": "Episodic memory text", "importance": 0.7}
    mock_node.count = 2

    mock_edge = MagicMock()
    mock_edge.source = "node-abc"
    mock_edge.target = "node-xyz"
    mock_edge.relation = "associated_with"
    mock_edge.properties = {"weight": 0.5}

    mock_provider.client.get_provenance_graph.return_value = ([mock_node], [mock_edge])

    response = client.get("/api/debug/provenance")
    assert response.status_code == 200
    json_data = response.json()
    assert "nodes" in json_data
    assert "edges" in json_data
    
    nodes = json_data["nodes"]
    assert len(nodes) == 1
    assert nodes[0]["id"] == "node-abc"
    assert nodes[0]["content"] == "Episodic memory text"
    assert nodes[0]["access_count"] == 2
    assert nodes[0]["importance"] == 0.7
    assert nodes[0]["source"] == "user"

    edges = json_data["edges"]
    assert len(edges) == 1
    assert edges[0]["source"] == "node-abc"
    assert edges[0]["target"] == "node-xyz"
    assert edges[0]["type"] == "associated_with"
    assert edges[0]["weight"] == 0.5


@pytest.mark.asyncio
async def test_debug_stage_endpoint_n1(mock_provider):
    # Test N1 execution
    with patch("api.debug.ReplayStage") as MockReplay:
        mock_replay_instance = MagicMock()
        mock_replay_instance.execute = AsyncMock(return_value=[])
        MockReplay.return_value = mock_replay_instance

        response = client.post("/api/debug/stage", json={"stage": "N1_Replay"})
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["status"] == "success"
        assert json_data["stage"] == "N1_Replay"
        mock_replay_instance.execute.assert_called_once()


def test_debug_stage_invalid(mock_provider):
    response = client.post("/api/debug/stage", json={"stage": "N5_Invalid"})
    assert response.status_code == 400
    assert "Invalid stage name" in response.json()["detail"]


def test_debug_reset_endpoint(mock_provider):
    response = client.post("/api/debug/reset")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert "completely wiped" in json_data["message"]
    mock_provider.client.clear_all.assert_called_once_with(dataset_name="oneiros_cloud")
