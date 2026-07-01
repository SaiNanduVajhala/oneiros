"""
Oneiros API Layer — Dream / Sleep Endpoints

Resource-oriented REST API exposing the cognitive engine.
SSE endpoint streams VisEvents for real-time frontend rendering.
"""

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from config import get_memory_provider
from memory.provider import MemoryProvider
from kernel.sleep.coordinator import SleepCoordinator
from kernel.reasoning.llm import ReasoningEngine
from events.event_bus import event_bus
from events.events import Event

logger = logging.getLogger("oneiros.api.dream")

router = APIRouter(prefix="/api", tags=["Dream"])

# Module-level state for the current/last dream cycle
_current_coordinator: Optional[SleepCoordinator] = None
_sleep_status: str = "idle"  # idle, dreaming, complete
_last_report: Optional[dict] = None

# SSE event queue — subscribers get events pushed here
_sse_queues: list[asyncio.Queue] = []


def _broadcast_sse(event_data: dict):
    """Push a VisEvent dict to all active SSE subscribers."""
    for q in _sse_queues:
        try:
            q.put_nowait(event_data)
        except asyncio.QueueFull:
            pass


# Subscribe to VisEvents on the EventBus
async def _vis_event_handler(event: Event):
    _broadcast_sse(event.payload)

event_bus.subscribe("VisEvent", _vis_event_handler)


@router.post("/sleep/start")
async def start_sleep(provider: MemoryProvider = Depends(get_memory_provider)):
    """
    Starts a sleep consolidation cycle using the current graph data.
    """
    global _current_coordinator, _sleep_status, _last_report

    if _sleep_status == "dreaming":
        return {"status": "already_dreaming", "message": "A sleep cycle is already in progress."}

    _sleep_status = "dreaming"
    _last_report = None

    # Resolve snapshot from the currently loaded coordinator if available
    snapshot = None
    if _current_coordinator and _current_coordinator.stage_snapshots:
        latest = _current_coordinator.stage_snapshots[-1]
        from domain.memory import MemoryGraphSnapshot, MemoryNode, MemoryEdge
        nodes = [MemoryNode(**n) for n in latest.nodes_json]
        edges = [MemoryEdge(**e) for e in latest.edges_json]
        snapshot = MemoryGraphSnapshot(nodes=nodes, edges=edges)

    coordinator = SleepCoordinator(provider)
    _current_coordinator = coordinator

    try:
        report = await coordinator.execute_cycle(snapshot)
        _last_report = report.model_dump()
        _sleep_status = "complete"
        return {"status": "complete", "dream_id": report.dream_id}
    except Exception as e:
        _sleep_status = "idle"
        provider.set_sleep_state(False)
        logger.error(f"Sleep cycle failed: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/demo/load")
async def load_demo(provider: MemoryProvider = Depends(get_memory_provider)):
    """
    Loads the curated demo dataset into the system to initialize the graph state.
    Allows visualizing the fragmented memories prior to running consolidation.
    """
    global _current_coordinator, _sleep_status, _last_report

    if _sleep_status == "dreaming":
        return {"status": "already_dreaming"}

    from scripts.load_demo_dataset import load_demo_snapshot
    from kernel.algorithms.similarity import detect_duplicate_candidates
    from kernel.algorithms.contradiction import find_potential_contradiction_pairs
    from kernel.algorithms.graph_metrics import compute_memory_health
    from domain.vis_events import MetricsSnapshot
    from kernel.sleep.coordinator import _snapshot_graph

    _sleep_status = "idle"
    _last_report = None

    coordinator = SleepCoordinator(provider)
    _current_coordinator = coordinator

    try:
        demo_snapshot = load_demo_snapshot()

        if hasattr(provider, "save_graph_snapshot"):
            provider.save_graph_snapshot(demo_snapshot)

        # Calculate pre-dream diagnostics and metrics
        initial_duplicates = len(detect_duplicate_candidates(demo_snapshot.nodes, 0.90))
        initial_contradictions = len(find_potential_contradiction_pairs(demo_snapshot.nodes))
        health_before = compute_memory_health(
            nodes=demo_snapshot.nodes, edges=demo_snapshot.edges,
            duplicate_count=initial_duplicates, contradiction_count=initial_contradictions
        )

        initial_metrics = MetricsSnapshot(
            memory_health=round(health_before, 1),
            nodes_replayed=0,
            nodes_pruned=0,
            duplicates_merged=0,
            contradictions_resolved=0,
            concepts_generated=0,
            cluster_count=0,
            graph_density=0.0,
            fragmentation=100.0,
            semantic_cohesion=0.0
        )

        # Capture pre-sleep stage snapshot
        coordinator.stage_snapshots = [
            _snapshot_graph("before", demo_snapshot, initial_metrics, vis_events=[], health=health_before, algorithm_traces=[])
        ]

        return {
            "status": "loaded",
            "nodes_loaded": len(demo_snapshot.nodes)
        }
    except Exception as e:
        logger.error(f"Demo loading failed: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/sleep/status")
async def sleep_status():
    return {"status": _sleep_status}


@router.get("/sleep/events")
async def sleep_events_sse():
    """SSE endpoint streaming VisEvents in real-time."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=500)
    _sse_queues.append(queue)

    async def event_generator():
        try:
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    yield f": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if queue in _sse_queues:
                _sse_queues.remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/graph")
async def get_graph():
    """Returns the current graph state from the latest coordinator."""
    if _current_coordinator and _current_coordinator.stage_snapshots:
        latest = _current_coordinator.stage_snapshots[-1]
        return {
            "stage": latest.stage,
            "nodes": latest.nodes_json,
            "edges": latest.edges_json,
            "node_count": latest.node_count,
            "edge_count": latest.edge_count
        }
    return {"stage": "none", "nodes": [], "edges": [], "node_count": 0, "edge_count": 0}


@router.get("/graph/snapshots")
async def get_graph_snapshots():
    """Returns all stage snapshots for temporal playback scrubbing."""
    if _current_coordinator and _current_coordinator.stage_snapshots:
        return [
            {
                "stage": s.stage,
                "timestamp": s.timestamp,
                "node_count": s.node_count,
                "edge_count": s.edge_count,
                "nodes": s.nodes_json,
                "edges": s.edges_json,
                "metrics": s.metrics.model_dump() if s.metrics else None
            }
            for s in _current_coordinator.stage_snapshots
        ]
    return []


@router.get("/metrics")
async def get_metrics():
    """Returns the latest algorithm-derived metrics snapshot."""
    if _current_coordinator and _current_coordinator.stage_snapshots:
        final = _current_coordinator.stage_snapshots[-1]
        if final.metrics:
            return final.metrics.model_dump()
    return {}


@router.get("/dream-report")
async def get_dream_report():
    """Returns the latest DreamReport."""
    if _last_report:
        return _last_report
    return {"status": "no_report"}


@router.get("/traces")
async def get_algorithm_traces():
    """Returns all AlgorithmTraces from the latest cycle for explainability."""
    if _current_coordinator:
        # Extract traces from VisEvents that have them
        traces = [
            ve.trace.model_dump()
            for ve in _current_coordinator.vis_events
            if ve.trace is not None
        ]
        return traces
    return []


@router.get("/vis-events")
async def get_all_vis_events():
    """Returns all accumulated VisEvents from the latest cycle."""
    if _current_coordinator:
        return [ve.model_dump() for ve in _current_coordinator.vis_events]
    return []
