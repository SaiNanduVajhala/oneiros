import pytest
from datetime import datetime, timedelta
from domain.memory import MemoryGraphSnapshot, MemoryNode, MemoryEdge
from kernel.reasoning.fact_resolver import FactResolver, is_potential_fact


def test_fact_heuristics():
    """Verify is_potential_fact heuristic classification matches factual phrases and ignores noise."""
    assert is_potential_fact("My name is Nandu") is True
    assert is_potential_fact("Im a software engineer") is True
    assert is_potential_fact("I live in India") is True
    assert is_potential_fact("actually my age is 24") is True
    assert is_potential_fact("from now on I work at Google") is True
    assert is_potential_fact("how are you doing today?") is False
    assert is_potential_fact("hello world") is False


def test_fact_conflict_resolution():
    """Verify that conflicting facts transition correctly through the lifecycle."""
    node_a = MemoryNode(
        id="mem-1",
        content="My name is Nandu",
        source="user",
        timestamp=datetime.now() - timedelta(minutes=10),
        metadata={
            "fact": {
                "subject": "user",
                "predicate": "name",
                "object": "Nandu",
                "type": "Identity",
                "is_correction": False
            },
            "status": "ACTIVE"
        }
    )
    
    node_b = MemoryNode(
        id="mem-2",
        content="Actually my name is Rithvik",
        source="user",
        timestamp=datetime.now(),
        metadata={
            "fact": {
                "subject": "user",
                "predicate": "name",
                "object": "Rithvik",
                "type": "Identity",
                "is_correction": True
            },
            "status": "RAW"
        }
    )
    
    snapshot = MemoryGraphSnapshot(nodes=[node_a, node_b], edges=[])
    resolver = FactResolver()
    
    updated_snapshot, events, forgotten = resolver.resolve_conflicts(snapshot)
    
    # Check node status transitions
    assert node_b.metadata["status"] == "ACTIVE"
    assert node_a.metadata["status"] == "SUPERSEDED"
    
    # Check edge creation
    assert len(updated_snapshot.edges) == 1
    edge = updated_snapshot.edges[0]
    assert edge.source == "mem-1"
    assert edge.target == "mem-2"
    assert edge.type == "SUPERSEDED_BY"
    
    assert "Superseded obsolete fact" in events[0]


def test_fact_chaining_archived_transition():
    """Verify that multiple updates transition older facts to ARCHIVED status."""
    node_a = MemoryNode(
        id="mem-1",
        content="My name is Nandu",
        timestamp=datetime.now() - timedelta(minutes=20),
        metadata={
            "fact": {"subject": "user", "predicate": "name", "object": "Nandu", "type": "Identity"},
            "status": "SUPERSEDED"
        }
    )
    
    node_b = MemoryNode(
        id="mem-2",
        content="Actually my name is Rithvik",
        timestamp=datetime.now() - timedelta(minutes=10),
        metadata={
            "fact": {"subject": "user", "predicate": "name", "object": "Rithvik", "type": "Identity", "is_correction": True},
            "status": "ACTIVE"
        }
    )
    
    node_c = MemoryNode(
        id="mem-3",
        content="From now on my name is Sai",
        timestamp=datetime.now(),
        metadata={
            "fact": {"subject": "user", "predicate": "name", "object": "Sai", "type": "Identity", "is_correction": True},
            "status": "RAW"
        }
    )
    
    snapshot = MemoryGraphSnapshot(nodes=[node_a, node_b, node_c], edges=[])
    resolver = FactResolver()
    
    updated_snapshot, events, forgotten = resolver.resolve_conflicts(snapshot)
    
    # Winner
    assert node_c.metadata["status"] == "ACTIVE"
    # Immediate predecessor
    assert node_b.metadata["status"] == "SUPERSEDED"
    # Older predecessor
    assert node_a.metadata["status"] == "ARCHIVED"


def test_fact_lifecycle_forgetting():
    """Verify that ARCHIVED nodes transition to FORGOTTEN and get pruned after thresholds are met."""
    node_a = MemoryNode(
        id="mem-1",
        content="My name is Nandu",
        metadata={
            "fact": {"subject": "user", "predicate": "name", "object": "Nandu", "type": "Identity"},
            "status": "ARCHIVED",
            "sleep_cycles_in_status": 1
        }
    )
    
    snapshot = MemoryGraphSnapshot(nodes=[node_a], edges=[])
    resolver = FactResolver()
    
    # Assume settings forget_after_sleep_cycles is 2
    from infrastructure.configuration.settings import settings
    settings.forget_after_sleep_cycles = 2
    
    # First cycle: increments count from 1 to 2, meets threshold, gets forgotten
    updated_snapshot, events, forgotten = resolver.resolve_conflicts(snapshot)
    
    assert "mem-1" in forgotten
    assert len(updated_snapshot.nodes) == 0


def test_e2e_name_lifecycle_scenario():
    """Verify the exact user scenario: Nandu -> Rithvik -> I'm Nandu transitions over multiple sleep cycles."""
    from infrastructure.configuration.settings import settings
    settings.archive_after_sleep_cycles = 1
    settings.forget_after_sleep_cycles = 1
    
    resolver = FactResolver()
    
    # 1. "My name is Nandu"
    node_a = MemoryNode(
        id="mem-a",
        content="My name is Nandu",
        timestamp=datetime.now() - timedelta(minutes=30),
        metadata={
            "fact": {"subject": "user", "predicate": "name", "object": "Nandu", "type": "Identity"},
            "status": "RAW"
        }
    )
    
    # Sleep 1
    snapshot = MemoryGraphSnapshot(nodes=[node_a], edges=[])
    snapshot, _, forgotten = resolver.resolve_conflicts(snapshot)
    assert node_a.metadata["status"] == "ACTIVE"
    assert len(forgotten) == 0
    
    # 2. "Actually my name is Rithvik"
    node_b = MemoryNode(
        id="mem-b",
        content="Actually my name is Rithvik",
        timestamp=datetime.now() - timedelta(minutes=15),
        metadata={
            "fact": {"subject": "user", "predicate": "name", "object": "Rithvik", "type": "Identity", "is_correction": True},
            "status": "RAW"
        }
    )
    
    # Sleep 2
    snapshot = MemoryGraphSnapshot(nodes=[node_a, node_b], edges=snapshot.edges)
    snapshot, _, forgotten = resolver.resolve_conflicts(snapshot)
    assert node_b.metadata["status"] == "ACTIVE"
    assert node_a.metadata["status"] == "SUPERSEDED"
    assert len(forgotten) == 0
    
    # 3. "I'm actually Nandu"
    node_c = MemoryNode(
        id="mem-c",
        content="I'm actually Nandu",
        timestamp=datetime.now(),
        metadata={
            "fact": {"subject": "user", "predicate": "name", "object": "Nandu", "type": "Identity", "is_correction": True},
            "status": "RAW"
        }
    )
    
    # Sleep 3
    snapshot = MemoryGraphSnapshot(nodes=[node_a, node_b, node_c], edges=snapshot.edges)
    snapshot, _, forgotten = resolver.resolve_conflicts(snapshot)
    assert node_c.metadata["status"] == "ACTIVE"
    assert node_b.metadata["status"] == "SUPERSEDED"
    # Older loser node_a (Nandu) transitions: SUPERSEDED -> ARCHIVED (since archive_after_sleep_cycles = 1)
    assert node_a.metadata["status"] == "ARCHIVED"
    assert len(forgotten) == 0
    
    # Sleep 4: Retention period check
    # node_b (Rithvik) transitions: SUPERSEDED -> ARCHIVED
    # node_a (Nandu) transitions: ARCHIVED -> FORGOTTEN (and gets pruned)
    snapshot, _, forgotten = resolver.resolve_conflicts(snapshot)
    assert "mem-a" in forgotten
    assert node_c.metadata["status"] == "ACTIVE"
    assert node_b.metadata["status"] == "ARCHIVED"


