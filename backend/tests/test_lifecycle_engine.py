import pytest
from datetime import datetime, timedelta
from domain.memory import MemoryNode
from kernel.sleep.lifecycle_engine import MemoryLifecycleEngine

def test_lifecycle_engine_retention_score():
    """Verify retention score computation integrates centrality, decay, access and penalties correctly."""
    engine = MemoryLifecycleEngine()
    current_time = datetime.now()
    
    # 1. Base Node
    node = MemoryNode(
        id="mem-1",
        content="Testing",
        importance=0.8,
        access_count=1,
        timestamp=current_time
    )
    node.metadata["status"] = "ACTIVE"
    
    score = engine.calculate_retention_score(node, centrality=0.2, current_time=current_time)
    # Expected: 0.8 (importance) + 0.0 (access bonus) + 0.01 (centrality bonus 0.05 * 0.2) - 0.0 (decay) - 0.0 (status penalty)
    assert pytest.approx(score, 0.01) == 0.81
    
    # 2. Node with higher access and centrality
    node_high = MemoryNode(
        id="mem-2",
        content="Testing high",
        importance=0.7,
        access_count=5,
        timestamp=current_time
    )
    node_high.metadata["status"] = "ACTIVE"
    score_high = engine.calculate_retention_score(node_high, centrality=0.5, current_time=current_time)
    assert score_high > 0.7
    
    # 3. Node with decay penalty (older node)
    node_old = MemoryNode(
        id="mem-3",
        content="Testing old",
        importance=0.8,
        access_count=1,
        timestamp=current_time - timedelta(hours=48)
    )
    node_old.metadata["status"] = "ACTIVE"
    score_old = engine.calculate_retention_score(node_old, centrality=0.0, current_time=current_time)
    # Expected age decay penalty: ~0.4 * (1 - 0.5) = 0.2
    assert score_old < 0.70

    # 4. Node with status penalty
    node_superseded = MemoryNode(
        id="mem-4",
        content="Testing superseded",
        importance=0.8,
        access_count=1,
        timestamp=current_time
    )
    node_superseded.metadata["status"] = "SUPERSEDED"
    score_sub = engine.calculate_retention_score(node_superseded, centrality=0.0, current_time=current_time)
    assert score_sub == 0.40 # 0.8 - 0.4 status penalty

def test_lifecycle_engine_transitions():
    """Verify evaluation and correct state transitions based on score thresholds."""
    engine = MemoryLifecycleEngine(
        active_to_inactive_threshold=0.50,
        inactive_to_archived_threshold=0.30,
        superseded_to_archived_threshold=0.30,
        forget_retention_threshold=0.15
    )
    
    # RAW -> ACTIVE
    node_raw = MemoryNode(id="n-raw", content="raw", importance=0.8)
    node_raw.metadata["status"] = "RAW"
    status, desc = engine.evaluate_transition(node_raw, 0.80)
    assert status == "ACTIVE"
    assert "Consolidated" in desc
    
    # ACTIVE -> INACTIVE
    node_active = MemoryNode(id="n-act", content="active", importance=0.4)
    node_active.metadata["status"] = "ACTIVE"
    status, desc = engine.evaluate_transition(node_active, 0.45)
    assert status == "INACTIVE"
    assert "transitioned ACTIVE -> INACTIVE" in desc
    
    # INACTIVE -> ARCHIVED
    node_inactive = MemoryNode(id="n-inact", content="inactive", importance=0.2)
    node_inactive.metadata["status"] = "INACTIVE"
    status, desc = engine.evaluate_transition(node_inactive, 0.25)
    assert status == "ARCHIVED"
    
    # SUPERSEDED -> ARCHIVED
    node_sup = MemoryNode(id="n-sup", content="superseded", importance=0.2)
    node_sup.metadata["status"] = "SUPERSEDED"
    status, desc = engine.evaluate_transition(node_sup, 0.25)
    assert status == "ARCHIVED"
    
    # ARCHIVED -> FORGOTTEN
    node_arc = MemoryNode(id="n-arc", content="archived", importance=0.1)
    node_arc.metadata["status"] = "ARCHIVED"
    status, desc = engine.evaluate_transition(node_arc, 0.10)
    assert status == "FORGOTTEN"
