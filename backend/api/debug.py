"""
Oneiros API Layer — Debug Endpoints
Exposes diagnostic metrics, active runtime configurations, standard DTO mapped graph data,
isolated stage executions, and clean system state resets.
"""

import logging
import os
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import get_memory_provider
from memory.provider import MemoryProvider
from events.event_bus import event_bus
from events.events import Event
from kernel.reasoning.llm import ReasoningEngine

# Import stages directly
from kernel.sleep.replay import ReplayStage
from kernel.sleep.consolidation import ConsolidationStage
from kernel.sleep.pruning import PruningStage
from kernel.sleep.rem import REMStage

from domain.memory import MemoryGraphSnapshot, MemoryNode, MemoryEdge

# For status sharing
import api.dream

logger = logging.getLogger("oneiros.api.debug")

router = APIRouter(prefix="/api/debug", tags=["Debug"])

# Track current active debug stage execution status
_active_debug_stage: str = "idle"

class StageRequest(BaseModel):
    stage: str


@router.get("/status")
async def get_status(provider: MemoryProvider = Depends(get_memory_provider)):
    """
    Returns metrics tracking active backend provider state and sleep locks.
    """
    global _active_debug_stage
    
    connected = False
    if hasattr(provider, "client"):
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

    return {
        "provider": type(provider).__name__,
        "connected": connected,
        "sleep_running": sleep_running,
        "sleep_status": sleep_status,
        "queue_size": queue_size,
        "active_stage": active_stage
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
        
        # Standardized DTO formatting
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
        # Fallback to empty DTO rather than breaking
        return {"nodes": [], "edges": []}


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
