import pytest
from datetime import datetime, timedelta
from domain.memory import MemoryGraphSnapshot, MemoryNode, MemoryEdge
from kernel.sleep.pruning import PruningStage
from kernel.reasoning.llm import ReasoningEngine
from memory.provider import MemoryProvider
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_pruning_stage_lifecycle_transitions():
    """Verify that PruningStage correctly calculates retention scores and transitions nodes."""
    mock_provider = MagicMock(spec=MemoryProvider)
    mock_provider.update_node_properties = AsyncMock()
    mock_provider.forget = AsyncMock()
    
    mock_llm = MagicMock(spec=ReasoningEngine)
    
    # Configure settings thresholds
    from infrastructure.configuration.settings import settings
    settings.active_to_inactive_threshold = 0.50
    settings.inactive_to_archived_threshold = 0.30
    settings.superseded_to_archived_threshold = 0.30
    settings.forget_retention_threshold = 0.15

    # 1. An active node that stays active (high importance)
    node_active = MemoryNode(
        id="mem-active",
        content="Important fact",
        importance=0.9,
        access_count=2,
        timestamp=datetime.now()
    )
    node_active.metadata["status"] = "ACTIVE"
    
    # 2. An active node that decays to inactive (low importance + some age)
    node_decaying = MemoryNode(
        id="mem-decaying",
        content="Transient note",
        importance=0.4,
        access_count=1,
        timestamp=datetime.now() - timedelta(hours=24)
    )
    node_decaying.metadata["status"] = "ACTIVE"
    
    # 3. An archived node with low retention score that should be forgotten
    node_forgotten = MemoryNode(
        id="mem-forgotten",
        content="Obsolete memory",
        importance=0.2,
        access_count=1,
        timestamp=datetime.now() - timedelta(hours=72)
    )
    node_forgotten.metadata["status"] = "ARCHIVED"
    
    snapshot = MemoryGraphSnapshot(
        nodes=[node_active, node_decaying, node_forgotten],
        edges=[]
    )
    
    stage = PruningStage(mock_provider, mock_llm)
    updated_snapshot, events = await stage.execute(snapshot)
    
    # Check node status transitions
    assert node_active.metadata["status"] == "ACTIVE"
    assert node_decaying.metadata["status"] == "INACTIVE"
    
    # Check that forgotten node is removed from the updated snapshot and forget() is invoked
    remaining_ids = [n.id for n in updated_snapshot.nodes]
    assert "mem-forgotten" not in remaining_ids
    mock_provider.forget.assert_called_with("mem-forgotten")
