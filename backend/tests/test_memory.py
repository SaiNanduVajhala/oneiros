"""
Oneiros Unit and Integration Tests - Memory Subsystem (Local & Cloud)
"""

import os
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from infrastructure.cognee_client import CogneeClient
from memory.cognee_cloud_provider import CogneeCloudProvider
from infrastructure.configuration.settings import settings

# Helper class representing mock Cognee nodes/edges returned by get_memory_provenance_graph
class MockCogneeNode:
    def __init__(self, node_id: str, properties: dict, count: int = 1):
        self.id = node_id
        self.properties = properties
        self.count = count

class MockCogneeEdge:
    def __init__(self, source: str, target: str, relation: str, properties: dict):
        self.source = source
        self.target = target
        self.relation = relation
        self.properties = properties


@pytest.mark.asyncio
async def test_cognee_cloud_provider_validation_failure():
    """
    Verifies settings.py raises ValueError on startup if cloud mode is selected without keys.
    """
    with patch("infrastructure.configuration.settings.settings.cognee_api_key", ""):
        # Force settings reload or call registration directly to check fast-fail
        from infrastructure.configuration.settings import register_memory_provider
        # Since _PROVIDER_INSTANCE might be cached, we patch it to None inside settings
        with patch("infrastructure.configuration.settings._PROVIDER_INSTANCE", None):
            with pytest.raises(ValueError) as excinfo:
                register_memory_provider()
            assert "CRITICAL CONFIGURATION ERROR" in str(excinfo.value)


@pytest.mark.asyncio
async def test_cognee_cloud_provider_mocked_crud():
    """
    Verifies that CogneeCloudProvider correctly translates domain operations to CogneeClient SDK calls.
    """
    # Create mocked client
    mock_client = MagicMock(spec=CogneeClient)
    mock_client.remember = AsyncMock()
    mock_client.recall = AsyncMock(return_value=[{"text": "recalled experience"}])
    mock_client.improve = AsyncMock()
    mock_client.forget = AsyncMock()
    
    mock_node = MockCogneeNode("mem-12345", {"content": "mocked experience", "type": "Memory"})
    mock_edge = MockCogneeEdge("mem-12345", "concept-6789", "ABSTRACTED_BY", {})
    mock_client.get_provenance_graph = AsyncMock(return_value=([mock_node], [mock_edge]))
    mock_client.clear_all = AsyncMock()

    provider = CogneeCloudProvider(mock_client)

    # 1. Test remember
    node_id = await provider.remember("I write high performance CUDA kernels")
    assert node_id.startswith("mem-")
    mock_client.remember.assert_awaited_once_with("I write high performance CUDA kernels", dataset_name="oneiros_cloud")

    # 2. Test recall
    results = await provider.recall("CUDA optimization")
    assert len(results) == 1
    assert results[0]["text"] == "{'text': 'recalled experience'}"
    mock_client.recall.assert_awaited_once_with("CUDA optimization", dataset_name="oneiros_cloud")

    # 3. Test improve
    concept_id = await provider.improve("GPU Optimizations", "Studies on CUDA loops", 0.9)
    assert concept_id.startswith("concept-")
    mock_client.improve.assert_awaited_once_with(dataset_name="oneiros_cloud")

    # 4. Test forget
    await provider.forget(node_id)
    mock_client.forget.assert_awaited_once()

    # 5. Test get_graph_data
    nodes, edges = await provider.get_graph_data()
    assert len(nodes) == 1
    assert nodes[0][0] == "mem-12345"
    assert nodes[0][1]["content"] == "mocked experience"
    assert len(edges) == 1
    assert edges[0][0] == "mem-12345"
    assert edges[0][1] == "concept-6789"
    assert edges[0][2] == "ABSTRACTED_BY"

    # 6. Test clear_all
    await provider.clear_all()
    mock_client.clear_all.assert_awaited_once_with(dataset_name="oneiros_cloud")


@pytest.mark.asyncio
async def test_cognee_cloud_provider_queueing():
    """
    Tests write lock queuing behavior during sleep cycles.
    """
    mock_client = MagicMock(spec=CogneeClient)
    mock_client.remember = AsyncMock()

    provider = CogneeCloudProvider(mock_client)

    # 1. Start sleep cycle (lock writes)
    provider.set_sleep_state(True)
    assert provider.is_sleeping() is True

    # 2. Ingest memory (should be queued, returning temp ID)
    temp_id = await provider.remember("Memory queued during dream sleep")
    assert temp_id.startswith("queued-")
    mock_client.remember.assert_not_called()

    # 3. Finish sleep cycle (unlock writes)
    provider.set_sleep_state(False)
    assert provider.is_sleeping() is False

    # 4. Flush/replay queue
    await provider.process_queued_memories()
    mock_client.remember.assert_awaited_once_with("Memory queued during dream sleep", dataset_name="oneiros_cloud")




# =====================================================================
# OPTIONAL INTEGRATION TESTS (REAL COGNEE CLOUD)
# =====================================================================
# Automatically skipped if valid COGNEE_API_KEY is not defined in the environment.
API_KEY_PRESENT = os.environ.get("COGNEE_API_KEY") is not None and os.environ.get("COGNEE_API_KEY") != "" and os.environ.get("COGNEE_API_KEY") != "mock-key"

@pytest.mark.skipif(not API_KEY_PRESENT, reason="Cognee Cloud credentials (COGNEE_API_KEY) are missing in this environment.")
@pytest.mark.asyncio
async def test_cognee_cloud_integration_live():
    """
    E2E integration test executing queries against the real Cognee Cloud client tenant.
    """
    api_key = os.environ.get("COGNEE_API_KEY")
    base_url = os.environ.get("COGNEE_BASE_URL", "https://api.cognee.ai/v1")
    
    client = CogneeClient(api_key=api_key, base_url=base_url)
    provider = CogneeCloudProvider(client)
    
    # Clear live test dataset
    await provider.clear_all()
    
    # remember memory
    content = "The Quick brown fox jumps over the lazy dog"
    node_id = await provider.remember(content)
    assert node_id.startswith("mem-")
    
    # recall check
    results = await provider.recall("brown fox")
    assert len(results) > 0
    
    # cleanup memory
    await provider.forget(node_id)
