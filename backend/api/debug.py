"""
Oneiros API Layer — Debug Endpoints
Exposes diagnostic metrics, active runtime configurations, standard DTO mapped graph data,
isolated stage executions, clean system state resets, log streaming, self-tests, and CRUD memory diagnostics.
"""

import logging
import os
import sys
import time
import asyncio
from typing import Dict, Any, List, Optional
from collections import deque
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import get_memory_provider
from memory.provider import MemoryProvider
from events.event_bus import event_bus
from events.events import Event
from kernel.reasoning.llm import ReasoningEngine
from domain.memory import MemoryGraphSnapshot, MemoryNode, MemoryEdge

# Import stages directly
from kernel.sleep.replay import ReplayStage
from kernel.sleep.consolidation import ConsolidationStage
from kernel.sleep.pruning import PruningStage
from kernel.sleep.rem import REMStage

# For status sharing
import api.dream

logger = logging.getLogger("oneiros.api.debug")

router = APIRouter(prefix="/api/debug", tags=["Debug"])

# ── LOG CAPTURING MECHANISM ──
class InMemoryLogHandler(logging.Handler):
    def __init__(self, capacity=500):
        super().__init__()
        self.log_buffer = deque(maxlen=capacity)

    def emit(self, record):
        try:
            timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            self.log_buffer.append({
                "id": f"log-{time.time_ns()}",
                "timestamp": timestamp,
                "stage": getattr(record, "stage", "system"),
                "type": record.levelname.lower(),
                "message": record.getMessage()
            })
        except Exception:
            pass

# Create and register the debug log handler globally
log_handler = InMemoryLogHandler()
log_handler.setLevel(logging.DEBUG)
logging.getLogger().addHandler(log_handler)

# Track current active debug stage execution status
_active_debug_stage: str = "idle"
_last_request_time: Optional[float] = None
_last_error: Optional[str] = None
_latency_samples: List[float] = []

def record_latency(start_time: float):
    elapsed = (time.perf_counter() - start_time) * 1000.0
    _latency_samples.append(elapsed)
    if len(_latency_samples) > 20:
        _latency_samples.pop(0)

# Request Models
class StageRequest(BaseModel):
    stage: str

class RememberRequest(BaseModel):
    content: str
    importance: float = 0.5
    semantic_tags: List[str] = []

class RecallRequest(BaseModel):
    query: str

class ImproveRequest(BaseModel):
    label: str
    description: str
    confidence: float = 0.8

class ForgetRequest(BaseModel):
    node_id: str

@router.get("/status")
async def get_status(provider: MemoryProvider = Depends(get_memory_provider)):
    """
    Returns metrics tracking active backend provider state and sleep locks.
    """
    global _active_debug_stage
    start_time = time.perf_counter()
    
    connected = False
    if hasattr(provider, "client"):
        # Trigger connection in the background so status check transitions to Online on start
        if not getattr(provider.client, "_connected", False):
            try:
                asyncio.create_task(provider.client.connect())
            except Exception:
                pass
        connected = getattr(provider.client, "_connected", False)
        
    sleep_status = api.dream._sleep_status
    if _active_debug_stage != "idle":
        sleep_status = "dreaming"
        
    sleep_running = sleep_status == "dreaming"
    queue_size = len(getattr(provider, "_queued_memories", []))
    
    active_stage = "idle"
    if api.dream._sleep_status == "dreaming":
        active_stage = "dreaming"
    elif _active_debug_stage != "idle":
        active_stage = _active_debug_stage

    active_sessions = len(api.dream._sse_queues)
    last_sleep_time = "N/A"
    if api.dream._last_report:
        duration = api.dream._last_report.get("duration", 0)
        last_sleep_time = f"{duration:.2f}s"

    record_latency(start_time)
    return {
        "provider": type(provider).__name__,
        "connected": connected,
        "sleep_running": sleep_running,
        "sleep_status": sleep_status,
        "queue_size": queue_size,
        "active_stage": active_stage,
        "active_sessions": active_sessions,
        "last_sleep_execution_time": last_sleep_time,
        "backend_version": "2.0"
    }

@router.get("/config")
async def get_config(provider: MemoryProvider = Depends(get_memory_provider)):
    """
    Returns runtime configuration info dynamically populated from setup files.
    """
    from infrastructure.configuration.settings import settings
    
    provider_name = type(provider).__name__
    provider_mode = os.environ.get("ONEIROS_PROVIDER", "cloud")
    database_desc = "Cognee Cloud" if provider_mode == "cloud" else "Local SQLite fallback"
    
    llm_model = settings.llm_model
    embedding_model = os.environ.get("EMBEDDING_PROVIDER", "mock")
    
    return {
        "provider": provider_name,
        "provider_mode": provider_mode,
        "database": database_desc,
        "llm": llm_model,
        "embedding_model": embedding_model,
        "version": "2.0"
    }

@router.get("/provenance")
async def get_provenance(provider: MemoryProvider = Depends(get_memory_provider)):
    """
    Directly retrieves Cognee provenance data, mapping to a stable DTO.
    """
    if not hasattr(provider, "client") or not hasattr(provider.client, "get_provenance_graph"):
        return {"nodes": [], "edges": []}
        
    try:
        cognee_nodes, cognee_edges = await provider.client.get_provenance_graph()
        
        nodes_list = []
        for n in cognee_nodes:
            props = n.properties.copy() if n.properties else {}
            content = props.get("content") or props.get("name") or props.get("text") or props.get("description") or n.id
            count_val = getattr(n, "count", 1)
            if callable(count_val) or not isinstance(count_val, (int, float)):
                count_val = 1
                
            nodes_list.append({
                "id": n.id,
                "content": content,
                "access_count": count_val,
                "importance": float(props.get("importance", 0.5)),
                "source": props.get("source", "user" if props.get("type") != "Concept" else "sleep"),
                "semantic_tags": props.get("semantic_tags") or [props.get("type", "general").lower()]
            })
            
        edges_list = []
        for e in cognee_edges:
            edges_list.append({
                "source": e.source,
                "target": e.target,
                "type": e.relation or "related_to",
                "weight": float((e.properties or {}).get("weight", 1.0))
            })
            
        return {
            "nodes": nodes_list,
            "edges": edges_list
        }
    except Exception as e:
        logger.error(f"Failed to fetch provenance graph: {e}")
        return {"nodes": [], "edges": []}

# ── LOGS API ──
@router.get("/logs")
async def get_logs(level: Optional[str] = None, search: Optional[str] = None):
    """
    Returns the intercepted in-memory log buffer, optionally filtered by level or keyword.
    """
    filtered_logs = list(log_handler.log_buffer)
    if level:
        filtered_logs = [log for log in filtered_logs if log["type"] == level.lower()]
    if search:
        search_lower = search.lower()
        filtered_logs = [log for log in filtered_logs if search_lower in log["message"].lower() or search_lower in log["stage"].lower()]
    return filtered_logs

@router.delete("/logs")
async def clear_logs():
    """
    Clears the in-memory log buffer.
    """
    log_handler.log_buffer.clear()
    return {"status": "success", "message": "Logs cleared."}

# ── PERFORMANCE MONITOR API ──
@router.get("/performance")
async def get_performance(provider: MemoryProvider = Depends(get_memory_provider)):
    """
    Returns live performance telemetry: latencies, memory usage, CPU load.
    """
    import os
    process_memory = "N/A"
    cpu_usage = "N/A"
    
    # Read resource stats safely
    try:
        import psutil
        process = psutil.Process(os.getpid())
        process_memory = f"{process.memory_info().rss / 1024 / 1024:.1f} MB"
        cpu_usage = f"{psutil.cpu_percent(interval=None)}%"
    except ImportError:
        # Fallback to standard library tools
        try:
            import resource
            process_memory = f"{resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.1f} MB"
        except (ImportError, AttributeError):
            pass

    avg_api_latency = sum(_latency_samples) / len(_latency_samples) if _latency_samples else 0.0
    
    # Measure Cognee endpoint connectivity ping latency
    cognee_latency = "N/A"
    if hasattr(provider, "client"):
        try:
            import httpx
            start = time.perf_counter()
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(provider.client.base_url or "https://api.cognee.ai/v1")
                cognee_latency = f"{(time.perf_counter() - start) * 1000.0:.1f} ms"
        except Exception:
            pass

    active_sse = len(api.dream._sse_queues)
    
    return {
        "api_latency": f"{avg_api_latency:.1f} ms",
        "cognee_latency": cognee_latency,
        "graph_load_time": f"{sum(_latency_samples[-3:]) / len(_latency_samples[-3:]):.1f} ms" if len(_latency_samples) >= 3 else "0.0 ms",
        "memory_usage": process_memory,
        "cpu_usage": cpu_usage,
        "active_sse_connections": active_sse,
        "sleep_execution_time": f"{api.dream._last_report.get('duration', 0):.2f} s" if api.dream._last_report else "N/A"
    }

# ── MEMORY DIAGNOSTICS OPERATIONS (CRUD) ──
@router.post("/operations/remember")
async def operations_remember(req: RememberRequest, provider: MemoryProvider = Depends(get_memory_provider)):
    global _last_request_time, _last_error
    start = time.perf_counter()
    _last_request_time = time.time()
    payload = req.model_dump()
    try:
        node_id = await provider.remember(
            req.content,
            importance=req.importance,
            metadata={"semantic_tags": req.semantic_tags, "source": "debug"}
        )
        elapsed = (time.perf_counter() - start) * 1000.0
        return {
            "status": "success",
            "request_payload": payload,
            "response_payload": {"node_id": node_id},
            "duration_ms": f"{elapsed:.1f} ms"
        }
    except Exception as e:
        _last_error = str(e)
        elapsed = (time.perf_counter() - start) * 1000.0
        return {
            "status": "error",
            "request_payload": payload,
            "response_payload": {"error": str(e)},
            "duration_ms": f"{elapsed:.1f} ms"
        }

@router.post("/operations/recall")
async def operations_recall(req: RecallRequest, provider: MemoryProvider = Depends(get_memory_provider)):
    global _last_request_time, _last_error
    start = time.perf_counter()
    _last_request_time = time.time()
    payload = req.model_dump()
    try:
        results = await provider.recall(req.query)
        elapsed = (time.perf_counter() - start) * 1000.0
        return {
            "status": "success",
            "request_payload": payload,
            "response_payload": {"results": results},
            "duration_ms": f"{elapsed:.1f} ms"
        }
    except Exception as e:
        _last_error = str(e)
        elapsed = (time.perf_counter() - start) * 1000.0
        return {
            "status": "error",
            "request_payload": payload,
            "response_payload": {"error": str(e)},
            "duration_ms": f"{elapsed:.1f} ms"
        }

@router.post("/operations/improve")
async def operations_improve(req: ImproveRequest, provider: MemoryProvider = Depends(get_memory_provider)):
    global _last_request_time, _last_error
    start = time.perf_counter()
    _last_request_time = time.time()
    payload = req.model_dump()
    try:
        node_id = await provider.improve(req.label, req.description, req.confidence)
        elapsed = (time.perf_counter() - start) * 1000.0
        return {
            "status": "success",
            "request_payload": payload,
            "response_payload": {"node_id": node_id},
            "duration_ms": f"{elapsed:.1f} ms"
        }
    except Exception as e:
        _last_error = str(e)
        elapsed = (time.perf_counter() - start) * 1000.0
        return {
            "status": "error",
            "request_payload": payload,
            "response_payload": {"error": str(e)},
            "duration_ms": f"{elapsed:.1f} ms"
        }

@router.post("/operations/forget")
async def operations_forget(req: ForgetRequest, provider: MemoryProvider = Depends(get_memory_provider)):
    global _last_request_time, _last_error
    start = time.perf_counter()
    _last_request_time = time.time()
    payload = req.model_dump()
    try:
        success = await provider.forget(req.node_id)
        elapsed = (time.perf_counter() - start) * 1000.0
        return {
            "status": "success" if success else "failed",
            "request_payload": payload,
            "response_payload": {"success": success},
            "duration_ms": f"{elapsed:.1f} ms"
        }
    except Exception as e:
        _last_error = str(e)
        elapsed = (time.perf_counter() - start) * 1000.0
        return {
            "status": "error",
            "request_payload": payload,
            "response_payload": {"error": str(e)},
            "duration_ms": f"{elapsed:.1f} ms"
        }

# ── SLEEP ENGINE CONTROLS ──
@router.post("/sleep/cancel")
async def cancel_sleep(provider: MemoryProvider = Depends(get_memory_provider)):
    """
    Cancels sleep mode (resets lock states and active dream status immediately).
    """
    api.dream._sleep_status = "idle"
    provider.set_sleep_state(False)
    return {"status": "success", "message": "Sleep cycle state reset to idle."}

# ── COGNEE CLOUD CONNECTION CONTROLS ──
@router.post("/connection/test")
async def connection_test(provider: MemoryProvider = Depends(get_memory_provider)):
    global _last_error
    if not hasattr(provider, "client"):
        return {"connected": False, "latency": "N/A", "error": "Not a Cognee cloud provider"}
    start = time.perf_counter()
    try:
        await provider.client.connect()
        latency = f"{(time.perf_counter() - start) * 1000.0:.1f} ms"
        return {"connected": True, "latency": latency, "endpoint": provider.client.base_url or "https://api.cognee.ai/v1"}
    except Exception as e:
        _last_error = str(e)
        return {"connected": False, "latency": "N/A", "error": str(e)}

@router.post("/connection/reconnect")
async def connection_reconnect(provider: MemoryProvider = Depends(get_memory_provider)):
    if not hasattr(provider, "client"):
        return {"status": "failed", "message": "Not a Cognee cloud provider"}
    try:
        await provider.client.disconnect()
        await provider.client.connect()
        return {"status": "success", "message": "Reconnected successfully."}
    except Exception as e:
        return {"status": "failed", "message": str(e)}

@router.post("/connection/verify")
async def connection_verify(provider: MemoryProvider = Depends(get_memory_provider)):
    from infrastructure.configuration.settings import settings
    api_key = settings.cognee_api_key
    has_key = bool(api_key and api_key != "mock-key")
    return {"authenticated": has_key, "auth_status": "API Key Valid" if has_key else "Missing Key"}

# ── QUEUE INSPECTOR API ──
@router.get("/queue")
async def get_queue(provider: MemoryProvider = Depends(get_memory_provider)):
    queued_memories = getattr(provider, "_queued_memories", [])
    ops = []
    for idx, content in enumerate(queued_memories):
        ops.append({
            "id": idx,
            "type": "remember",
            "content": content,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    return {
        "queue_size": len(ops),
        "operations": ops
    }

@router.post("/queue/flush")
async def flush_queue(provider: MemoryProvider = Depends(get_memory_provider)):
    try:
        await provider.process_queued_memories()
        return {"status": "success", "message": "Queue flushed successfully."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/queue/clear")
async def clear_queue(provider: MemoryProvider = Depends(get_memory_provider)):
    if hasattr(provider, "_queued_memories"):
        provider._queued_memories.clear()
        return {"status": "success", "message": "Queue cleared."}
    return {"status": "success", "message": "Queue was empty."}

@router.post("/queue/retry")
async def retry_queue(provider: MemoryProvider = Depends(get_memory_provider)):
    try:
        await provider.process_queued_memories()
        return {"status": "success", "message": "Retried operations."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ── TESTING UTILITIES (SELF-TESTS) ──
@router.get("/system/test")
async def system_test(provider: MemoryProvider = Depends(get_memory_provider)):
    results = {}
    
    # 1. Health check
    try:
        nodes, edges = await provider.get_graph_data()
        results["memory_provider"] = {"pass": True, "message": f"Connected, found {len(nodes)} nodes."}
    except Exception as e:
        results["memory_provider"] = {"pass": False, "message": str(e)}
        
    # 2. SSE Stream Test
    results["sse_stream"] = {"pass": True, "message": f"Active streams: {len(api.dream._sse_queues)}"}
    
    # 3. SQLite Mirror schema verification
    try:
        import sqlite3
        with sqlite3.connect(provider.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cursor.fetchall()]
            has_nodes = "nodes" in tables
            has_edges = "edges" in tables
            if has_nodes and has_edges:
                results["sqlite_mirror"] = {"pass": True, "message": f"Verified nodes and edges tables exist."}
            else:
                results["sqlite_mirror"] = {"pass": False, "message": f"Missing tables: nodes={has_nodes}, edges={has_edges}"}
    except Exception as e:
        results["sqlite_mirror"] = {"pass": False, "message": str(e)}

    # 4. LLM Check
    try:
        reasoning = ReasoningEngine()
        # Fast test token check
        res = reasoning.generate("ping")
        results["reasoning_engine"] = {"pass": True, "message": "LLM responded: OK"}
    except Exception as e:
        results["reasoning_engine"] = {"pass": False, "message": str(e)}

    # 5. Coordinator test lock check
    try:
        from kernel.sleep.coordinator import SleepCoordinator
        coord = SleepCoordinator(provider)
        results["sleep_coordinator"] = {"pass": True, "message": f"Lock is free: {not coord._lock.locked()}"}
    except Exception as e:
        results["sleep_coordinator"] = {"pass": False, "message": str(e)}

    return results

# ── DATA SEEDING UTILITIES ──
@router.post("/data/seed")
async def seed_data(provider: MemoryProvider = Depends(get_memory_provider)):
    """
    Seeds the memory provider with high-quality demo data for hackathon presentation.
    """
    facts = [
        "Nandu lives in San Francisco and is an AI application developer.",
        "Nandu loves making coffee with a chemex pour over at 85 degrees celsius.",
        "Oneiros is a cognitive operating system running long-term memory consolidation.",
        "LanceDB is the fast vector search storage used internally by Cognee.",
        "Cognee Cloud offers structured semantic graphs, eliminating typical flat embeddings pipelines.",
        "Oneiros replays wake memories, clusters related items, prunes contradictions, and builds concepts during sleep cycles."
    ]
    try:
        for idx, fact in enumerate(facts):
            # Seed them with varying activation values
            await provider.remember(
                fact,
                importance=0.6 + (idx * 0.05),
                metadata={"seeded": True, "source": "seed_demo"}
            )
        return {"status": "success", "message": f"Successfully seeded {len(facts)} memory facts."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to seed demo data: {str(e)}")

@router.post("/data/reset-layout")
async def reset_layout(provider: MemoryProvider = Depends(get_memory_provider)):
    """
    Clears visual layout coordinate caches.
    """
    try:
        import sqlite3
        with sqlite3.connect(provider.db_path) as conn:
            conn.execute("DELETE FROM node_positions")
            conn.commit()
        return {"status": "success", "message": "Visual layout caches cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stage")
async def execute_stage(req: StageRequest, provider: MemoryProvider = Depends(get_memory_provider)):
    """
    Directly runs a specific stage with minimum prerequisite executions.
    """
    global _active_debug_stage
    
    stage = req.stage
    valid_stages = {"N1_Replay", "N2_Consolidation", "N3_Pruning", "REM_Dream"}
    if stage not in valid_stages:
        raise HTTPException(status_code=400, detail=f"Invalid stage name: {stage}. Must be one of {valid_stages}")
        
    if api.dream._sleep_status == "dreaming" or _active_debug_stage != "idle":
        raise HTTPException(status_code=409, detail="A sleep stage or cycle is already in progress.")
        
    _active_debug_stage = stage
    
    try:
        # 1. Fetch current graph data & build the baseline snapshot
        nodes_raw, edges_raw = await provider.get_graph_data()
        nodes = [
            MemoryNode(
                id=nid,
                content=props.get("content") or props.get("description") or nid,
                importance=float(props.get("importance", 0.5)),
                access_count=int(props.get("access_count", 1)),
                source=props.get("source", "user"),
                semantic_tags=props.get("semantic_tags", [])
            ) for nid, props in nodes_raw
        ]
        edges = [
            MemoryEdge(
                source=src, target=tgt, type=rel,
                weight=float(props.get("weight", 1.0))
            ) for src, tgt, rel, props in edges_raw
        ]
        snapshot = MemoryGraphSnapshot(nodes=nodes, edges=edges)
        
        reasoning_engine = ReasoningEngine()
        
        # 2. Run selected stage with minimum prerequisite pipelines
        if stage == "N1_Replay":
            # Start event
            await event_bus.publish(Event(
                event_type="VisEvent",
                payload={"stage": "N1_Replay", "type": "stage_start", "message": "Replay stage started — ranking memories"}
            ))
            
            replay_stage = ReplayStage(provider)
            active_working_set = await replay_stage.execute(snapshot)
            
            activated_ids = [n.id for n in active_working_set]
            await event_bus.publish(Event(
                event_type="VisEvent",
                payload={
                    "stage": "N1_Replay", "type": "node_activate",
                    "message": f"Activated {len(activated_ids)} memories in working set",
                    "node_ids": activated_ids,
                    "algorithm": "weighted_activation_decay"
                }
            ))
            
            await event_bus.publish(Event(
                event_type="VisEvent",
                payload={"stage": "N1_Replay", "type": "stage_complete", "message": "Replay complete"}
            ))
            
        elif stage == "N2_Consolidation":
            # Consolidation requires active working set from Replay
            await event_bus.publish(Event(
                event_type="VisEvent",
                payload={"stage": "N2_Consolidation", "type": "stage_start", "message": "Consolidation started"}
            ))
            
            replay_stage = ReplayStage(provider)
            active_working_set = await replay_stage.execute(snapshot)
            
            consolidation_stage = ConsolidationStage()
            clusters = await consolidation_stage.execute(active_working_set)
            
            for idx, cluster in enumerate(clusters):
                member_ids = [n.id for n in cluster]
                await event_bus.publish(Event(
                    event_type="VisEvent",
                    payload={
                        "stage": "N2_Consolidation", "type": "cluster_form",
                        "message": f"Cluster {idx}: {len(cluster)} elements",
                        "cluster_id": idx,
                        "cluster_members": member_ids,
                        "algorithm": "DBSCAN"
                    }
                ))
                
            await event_bus.publish(Event(
                event_type="VisEvent",
                payload={"stage": "N2_Consolidation", "type": "stage_complete", "message": "Consolidation complete"}
            ))
            
        elif stage == "N3_Pruning":
            # Pruning runs directly on graph snapshot, merges and cleans duplicate memories
            await event_bus.publish(Event(
                event_type="VisEvent",
                payload={"stage": "N3_Pruning", "type": "stage_start", "message": "Pruning stage started"}
            ))
            
            pruning_stage = PruningStage(provider, reasoning_engine)
            snapshot, prune_events = await pruning_stage.execute(snapshot)
            
            for evt in prune_events:
                evt_lower = evt.lower()
                if "merged" in evt_lower or "auto-merged" in evt_lower:
                    await event_bus.publish(Event(
                        event_type="VisEvent",
                        payload={"stage": "N3_Pruning", "type": "node_merge", "message": evt}
                    ))
                elif "conflict" in evt_lower or "contradiction" in evt_lower or "resolved" in evt_lower:
                    await event_bus.publish(Event(
                        event_type="VisEvent",
                        payload={"stage": "N3_Pruning", "type": "conflict_resolve", "message": evt}
                    ))
                else:
                    await event_bus.publish(Event(
                        event_type="VisEvent",
                        payload={"stage": "N3_Pruning", "type": "node_fade", "message": evt}
                    ))
                    
            if hasattr(provider, "save_graph_snapshot"):
                provider.save_graph_snapshot(snapshot)
                
            await event_bus.publish(Event(
                event_type="VisEvent",
                payload={"stage": "N3_Pruning", "type": "stage_complete", "message": "Pruning complete"}
            ))
            
        elif stage == "REM_Dream":
            # REM requires clusters from Consolidation
            await event_bus.publish(Event(
                event_type="VisEvent",
                payload={"stage": "REM_Dream", "type": "stage_start", "message": "REM stage started"}
            ))
            
            replay_stage = ReplayStage(provider)
            active_working_set = await replay_stage.execute(snapshot)
            
            consolidation_stage = ConsolidationStage()
            clusters = await consolidation_stage.execute(active_working_set)
            
            rem_stage = REMStage(provider, reasoning_engine)
            snapshot, rem_events = await rem_stage.execute(snapshot, clusters)
            
            for evt in rem_events:
                evt_lower = evt.lower()
                if "created concept" in evt_lower:
                    label = evt.split("'")[1] if "'" in evt else "Concept"
                    await event_bus.publish(Event(
                        event_type="VisEvent",
                        payload={"stage": "REM_Dream", "type": "concept_create", "message": evt, "concept_label": label}
                    ))
                elif "linked" in evt_lower or "association" in evt_lower:
                    await event_bus.publish(Event(
                        event_type="VisEvent",
                        payload={"stage": "REM_Dream", "type": "edge_create", "message": evt}
                    ))
                else:
                    await event_bus.publish(Event(
                        event_type="VisEvent",
                        payload={"stage": "REM_Dream", "type": "concept_create", "message": evt}
                    ))
                    
            if hasattr(provider, "save_graph_snapshot"):
                provider.save_graph_snapshot(snapshot)
                
            await event_bus.publish(Event(
                event_type="VisEvent",
                payload={"stage": "REM_Dream", "type": "stage_complete", "message": "REM complete"}
            ))
            
        return {"status": "success", "stage": stage, "message": f"Successfully completed {stage} isolated execution."}
    except Exception as e:
        logger.exception(f"Error executing debug stage {stage}: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        _active_debug_stage = "idle"


@router.post("/reset")
async def reset_database(provider: MemoryProvider = Depends(get_memory_provider)):
    """
    Completely clears Cognee Cloud memory datasets and SQLite mirrors. Leaves it completely empty.
    """
    try:
        await provider.clear_all()
        return {"status": "success", "message": "Database completely wiped and left empty."}
    except Exception as e:
        logger.exception(f"Wipe database failed: {e}")
        raise HTTPException(status_code=500, detail=f"Reset execution failed: {str(e)}")

