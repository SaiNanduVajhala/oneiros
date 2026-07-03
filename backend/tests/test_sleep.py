"""
Oneiros Unit Tests - Sleep Coordinator and Cognitive Stage Verification

Contains Dataset A (Small), Dataset B (Medium), and Dataset C (Messy) validations.
"""

import pytest
from datetime import datetime, timedelta
from typing import List
from domain.memory import MemoryGraphSnapshot, MemoryNode, MemoryEdge
from unittest.mock import AsyncMock, MagicMock
from infrastructure.cognee_client import CogneeClient
from memory.cognee_cloud_provider import CogneeCloudProvider
from kernel.sleep.coordinator import SleepCoordinator
from kernel.algorithms.graph_metrics import compute_memory_health
from kernel.algorithms.similarity import detect_duplicate_candidates
from kernel.algorithms.contradiction import find_potential_contradiction_pairs

def get_mock_provider():
    mock_client = MagicMock(spec=CogneeClient)
    mock_client.remember = AsyncMock()
    mock_client.improve = AsyncMock()
    mock_client.forget = AsyncMock()
    mock_client.clear_all = AsyncMock()
    mock_client.get_provenance_graph = AsyncMock(return_value=([], []))
    
    provider = CogneeCloudProvider(mock_client)
    return provider

# --- Evaluation Dataset Builders ---

def build_dataset_a() -> MemoryGraphSnapshot:
    """
    Dataset A (Small): 20 coherent user episodic memories on technology/coffee topics.
    """
    nodes = []
    current_time = datetime.now()
    
    # 20 distinct memories
    contents = [
        "I drink espresso in the morning",
        "Espresso helps me wake up and stay alert",
        "I write Python code for my projects",
        "Python is a highly readable coding language",
        "FastAPI is great for writing web api endpoints",
        "I use FastAPI for building backends",
        "Cognitive systems mimic biological brain cycles",
        "Sleeping helps consolidate active short term memories",
        "I love training deep learning models",
        "Model weights represent learned parameters",
        "GPU kernels optimize matrix computations",
        "CUDA allows programming directly on Nvidia graphics processors",
        "Vector databases help store semantic embeddings",
        "Graph databases model node relationships",
        "I jog in the evening for physical health",
        "Cardio exercise improves heart stamina",
        "I read books on cognitive science",
        "Reading expands vocabulary and concepts",
        "I listen to jazz music while working",
        "Ambient sound helps focus concentration"
    ]
    
    for idx, content in enumerate(contents):
        nodes.append(MemoryNode(
            id=f"node-a-{idx}",
            content=content,
            timestamp=current_time - timedelta(hours=idx),
            last_accessed=current_time - timedelta(minutes=idx * 10),
            access_count=1 + (idx % 3),
            importance=0.5 + (0.02 * idx),
            source="user"
        ))
        
    return MemoryGraphSnapshot(nodes=nodes, edges=[])

def build_dataset_b() -> MemoryGraphSnapshot:
    """
    Dataset B (Medium): 200 normal multi-topic memories.
    """
    nodes = []
    current_time = datetime.now()
    
    topics = ["Database", "Cooking", "Space Exploration", "Music Theory", "Sports Science"]
    
    for idx in range(200):
        topic = topics[idx % len(topics)]
        content = f"Experience report {idx}: details on research topic {topic} execution log."
        nodes.append(MemoryNode(
            id=f"node-b-{idx}",
            content=content,
            timestamp=current_time - timedelta(minutes=idx),
            last_accessed=current_time - timedelta(seconds=idx),
            access_count=1 + (idx % 5),
            importance=0.4 + (0.002 * idx),
            source="user"
        ))
        
    return MemoryGraphSnapshot(nodes=nodes, edges=[])

def build_dataset_c() -> MemoryGraphSnapshot:
    """
    Dataset C (Messy): Highly redundant with duplicates, noise, and logical contradictions.
    """
    nodes = []
    current_time = datetime.now()
    
    # 1. Base clean memories
    nodes.append(MemoryNode(
        id="c-node-clean-1",
        content="I use React for frontend development",
        timestamp=current_time,
        last_accessed=current_time,
        importance=0.8,
        source="user"
    ))
    
    # 2. Duplicate nodes (> 0.995 similarity)
    nodes.append(MemoryNode(
        id="c-node-dup-1",
        content="I write high performance CUDA kernels for GPUs",
        timestamp=current_time,
        last_accessed=current_time,
        access_count=3,
        importance=0.9,
        source="user"
    ))
    nodes.append(MemoryNode(
        id="c-node-dup-2",
        content="I write high performance CUDA kernels for GPUs",
        timestamp=current_time,
        last_accessed=current_time,
        access_count=1,
        importance=0.9,
        source="user"
    ))
    
    # 3. Contradiction nodes (highly similar but opposite verbs/sentiment)
    nodes.append(MemoryNode(
        id="c-node-contra-1",
        content="I absolutely love drinking black coffee in the morning",
        timestamp=current_time,
        last_accessed=current_time,
        importance=0.7,
        source="user"
    ))
    nodes.append(MemoryNode(
        id="c-node-contra-2",
        content="I do not love drinking black coffee in the morning",
        timestamp=current_time,
        last_accessed=current_time,
        importance=0.7,
        source="user"
    ))
    
    # 4. Low-activation noise nodes (very old, never accessed, low importance)
    for idx in range(10):
        nodes.append(MemoryNode(
            id=f"c-node-noise-{idx}",
            content=f"Irrelevant spam memory noise trace {idx}",
            timestamp=current_time - timedelta(days=10),
            last_accessed=current_time - timedelta(days=9),
            access_count=1,
            importance=0.1,
            source="user"
        ))
        
    return MemoryGraphSnapshot(nodes=nodes, edges=[])

# --- Test Executions ---

@pytest.mark.asyncio
async def test_dataset_a_consolidation():
    """
    Tests Dataset A execution: Verify replay, clustering fallback, and metrics compilation.
    """
    provider = get_mock_provider()
    coordinator = SleepCoordinator(provider)
    snapshot = build_dataset_a()
    
    report = await coordinator.execute_cycle(snapshot)
    
    assert report.nodes_processed == 20
    assert len(report.stages_completed) == 5
    assert report.memory_health_after >= report.memory_health_before
    assert len(report.timeline) > 0

@pytest.mark.asyncio
async def test_dataset_b_performance():
    """
    Tests Dataset B execution: Large batch scale run checks.
    """
    provider = get_mock_provider()
    coordinator = SleepCoordinator(provider)
    snapshot = build_dataset_b()
    
    report = await coordinator.execute_cycle(snapshot)
    
    assert report.nodes_processed == 200
    assert report.duration >= 0.0

@pytest.mark.asyncio
async def test_dataset_c_pruning_and_contradictions():
    """
    Tests Dataset C execution: Duplicates must auto-merge, noise must prune, contradictions detected.
    """
    snapshot = build_dataset_c()
    
    # Verify algorithms find contradictions and duplicates beforehand
    dups = detect_duplicate_candidates(snapshot.nodes, 0.90)
    contras = find_potential_contradiction_pairs(snapshot.nodes)
    
    assert len(dups) >= 1
    assert len(contras) >= 1
    
    provider = get_mock_provider()
    coordinator = SleepCoordinator(provider)
    
    report = await coordinator.execute_cycle(snapshot)
    
    # Low activation noise (10 nodes) should be pruned
    # Duplicate CUDA node (1 node) should be merged
    # Contradiction might be handled depending on LLM resolver
    assert report.nodes_removed > 0
    # Health should improve due to pruning of orphans / duplicate consolidations
    assert report.memory_health_after > report.memory_health_before
