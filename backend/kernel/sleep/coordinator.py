"""
Oneiros Sleep Subsystem - Sleep Coordinator

Orchestrates sequential execution of stages on a single evolving MemoryGraphSnapshot,
emits immutable VisEvents through the EventBus, captures AlgorithmTraces,
stores StageSnapshots for temporal playback, and derives structural metrics.
"""

import uuid
import logging
import time
import asyncio
from datetime import datetime
from typing import List, Optional

from memory.provider import MemoryProvider
from domain.dream import DreamReport
from domain.memory import MemoryGraphSnapshot, MemoryNode, MemoryEdge
from domain.vis_events import VisEvent, MetricsSnapshot, AlgorithmTrace, StageSnapshot
from events.event_bus import event_bus
from events.events import Event

from kernel.sleep.replay import ReplayStage
from kernel.sleep.consolidation import ConsolidationStage
from kernel.sleep.pruning import PruningStage
from kernel.sleep.rem import REMStage
from kernel.reasoning.llm import ReasoningEngine
from kernel.algorithms.graph_metrics import (
    calculate_graph_density,
    calculate_average_degree,
    compute_memory_health
)
from kernel.algorithms.activation import calculate_activation_scores
from kernel.algorithms.similarity import detect_duplicate_candidates
from kernel.algorithms.contradiction import find_potential_contradiction_pairs

logger = logging.getLogger("oneiros.kernel.sleep.coordinator")


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def _snapshot_graph(
    stage: str,
    snapshot: MemoryGraphSnapshot,
    metrics: Optional[MetricsSnapshot] = None,
    vis_events: Optional[List[VisEvent]] = None,
    health: float = 0.0,
    algorithm_traces: Optional[List[AlgorithmTrace]] = None
) -> StageSnapshot:
    return StageSnapshot(
        stage=stage,
        node_count=len(snapshot.nodes),
        edge_count=len(snapshot.edges),
        nodes_json=[n.model_dump(exclude={"embedding"}) for n in snapshot.nodes],
        edges_json=[e.model_dump() for e in snapshot.edges],
        metrics=metrics,
        events_json=[ve.model_dump() for ve in vis_events] if vis_events else [],
        health=health,
        algorithm_traces_json=[at.model_dump() for at in algorithm_traces] if algorithm_traces else []
    )


class SleepCoordinator:
    """Sleep Coordinator orchestrating N1-REM stages with VisEvent emission."""

    def __init__(self, provider: MemoryProvider, reasoning_engine: Optional[ReasoningEngine] = None):
        self.provider = provider
        self.reasoning_engine = reasoning_engine or ReasoningEngine()
        self.replay_stage = ReplayStage(self.provider)
        self.consolidation_stage = ConsolidationStage()
        self.pruning_stage = PruningStage(self.provider, self.reasoning_engine)
        self.rem_stage = REMStage(self.provider, self.reasoning_engine)
        self._lock = asyncio.Lock()

        # Accumulated during a cycle for external consumers
        self.vis_events: List[VisEvent] = []
        self.stage_snapshots: List[StageSnapshot] = []
        self.algorithm_traces: List[AlgorithmTrace] = []

    def _emit(self, event: VisEvent):
        """Append and publish an immutable VisEvent."""
        self.vis_events.append(event)
        if event.trace:
            self.algorithm_traces.append(event.trace)
        # Fire-and-forget publish through event bus for SSE subscribers
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(event_bus.publish(Event(
                event_type="VisEvent",
                payload=event.model_dump()
            )))
        except RuntimeError:
            pass  # No running loop during tests

    async def execute_cycle(self, input_snapshot: Optional[MemoryGraphSnapshot] = None, force: bool = False) -> DreamReport:
        if self._lock.locked():
            logger.warning("Sleep cycle execution blocked: coordinator is already running a cycle.")
            raise RuntimeError("A sleep cycle is already in progress.")

        async with self._lock:
            dream_id = str(uuid.uuid4())
            started_at = datetime.now()
            timeline: List[str] = []
            self.vis_events = []
            self.stage_snapshots = []
            self.algorithm_traces = []

            # Tracking counters for metrics
            duplicates_merged = 0
            contradictions_resolved = 0

            self.provider.set_sleep_state(True)

            # 1. Resolve starting snapshot
            snapshot = input_snapshot
            if snapshot is None:
                try:
                    nodes_raw, edges_raw = await self.provider.get_graph_data()
                    nodes = [
                        MemoryNode(
                            id=nid,
                            content=props.get("content") or props.get("description") or nid,
                            importance=float(props.get("importance", 0.5)),
                            access_count=int(props.get("access_count", 1)),
                            source=props.get("source", "user"),
                            semantic_tags=props.get("semantic_tags", []),
                            metadata=props.get("metadata", {})
                        ) for nid, props in nodes_raw
                    ]
                    edges = [
                        MemoryEdge(
                            source=src, target=tgt, type=rel,
                            weight=float(props.get("weight", 1.0))
                        ) for src, tgt, rel, props in edges_raw
                    ]
                    snapshot = MemoryGraphSnapshot(nodes=nodes, edges=edges)
                except NotImplementedError:
                    logger.warning("Provider stubbed. Running on empty snapshot.")
                    snapshot = MemoryGraphSnapshot(nodes=[], edges=[])

            # ── Cognitive gate: skip if nothing meaningful to consolidate ──
            import re as _re

            def _is_internal(n: MemoryNode) -> bool:
                """Matches the same filter used on the frontend to exclude Cognee infrastructure nodes."""
                tags = n.semantic_tags or []
                return (
                    bool(_re.match(r'^text_[a-f0-9]{10,}$', n.id, _re.I)) or
                    bool(_re.match(r'^user:[a-f0-9]+$', n.id, _re.I)) or
                    any(t in ('textdocument', 'dataset', 'user') for t in tags) or
                    bool(_re.match(r'^oneiros_', n.content or '', _re.I)) or
                    bool(_re.match(r'^user:[a-f0-9]+$', (n.content or '').strip(), _re.I))
                )

            MIN_MEMORIES = 3
            real_nodes = [n for n in snapshot.nodes if not _is_internal(n)]
            episodic_nodes = [n for n in real_nodes if n.source in ("user", "agent")]
            skip_reason: Optional[str] = None

            if not force:
                if len(real_nodes) == 0:
                    skip_reason = "No memories available for consolidation."
                elif len(episodic_nodes) < MIN_MEMORIES:
                    skip_reason = (
                        f"Only {len(episodic_nodes)} episodic memor{'y' if len(episodic_nodes) == 1 else 'ies'} found. "
                        f"Minimum threshold: {MIN_MEMORIES}."
                    )

            if skip_reason:
                self.provider.set_sleep_state(False)
                logger.info(f"Dream cycle skipped: {skip_reason}")
                self._emit(VisEvent(
                    stage="system", type="cycle_complete",
                    message=f"Sleep skipped — {skip_reason}",
                    health_before=0.0, health_after=0.0
                ))
                return DreamReport(
                    dream_id=dream_id,
                    started_at=started_at,
                    finished_at=datetime.now(),
                    duration=0.0,
                    stages_completed=[],
                    nodes_processed=len(snapshot.nodes),
                    nodes_removed=0,
                    concepts_created=0,
                    relationships_created=0,
                    compression_ratio=1.0,
                    memory_health_before=0.0,
                    memory_health_after=0.0,
                    summary_narrative=f"🛌 Sleep skipped\n\nReason:\n• {skip_reason}\n\nNo replay or consolidation was necessary.",
                    timeline=[f"{_ts()} — Skipped: {skip_reason}"]
                )
            # ── End gate ──

            timeline.append(f"{_ts()} — Dream cycle started")
            self._emit(VisEvent(
                stage="system", type="cycle_start",
                message="Dream cycle initiated"
            ))

            await event_bus.publish(Event(
                event_type="DreamStarted",
                payload={"dream_id": dream_id, "started_at": started_at.isoformat()}
            ))

            initial_node_count = len(snapshot.nodes)
            initial_edge_count = len(snapshot.edges)

            # Pre-dream diagnostics
            initial_duplicates = len(detect_duplicate_candidates(snapshot.nodes, 0.90))
            initial_contradictions = len(find_potential_contradiction_pairs(snapshot.nodes))
            health_before = compute_memory_health(
                nodes=snapshot.nodes, edges=snapshot.edges,
                duplicate_count=initial_duplicates, contradiction_count=initial_contradictions
            )

            timeline.append(f"{_ts()} — Loaded {initial_node_count} nodes, {initial_edge_count} edges")

            # Capture pre-sleep snapshot
            self.stage_snapshots.append(_snapshot_graph("before", snapshot, vis_events=self.vis_events, health=health_before, algorithm_traces=self.algorithm_traces))

            stages_completed: List[str] = []
            active_working_set: list = []
            clusters: list = []

            # --- N1: Replay ---
            t0 = time.perf_counter()
            timeline.append(f"{_ts()} — Replay (N1) stage started")
            self._emit(VisEvent(
                stage="N1_Replay", type="stage_start",
                message="Replay stage started — ranking memories by activation"
            ))
            try:
                active_working_set = await self.replay_stage.execute(snapshot)
                n1_duration = (time.perf_counter() - t0) * 1000
                stages_completed.append("N1_Replay")

                # Emit node activations
                activated_ids = [n.id for n in active_working_set]
                self._emit(VisEvent(
                    stage="N1_Replay", type="node_activate",
                    message=f"Activated {len(activated_ids)} memories in working set",
                    node_ids=activated_ids,
                    algorithm="weighted_activation_decay",
                    input_count=initial_node_count,
                    output_count=len(activated_ids),
                    duration_ms=round(n1_duration, 1),
                    trace=AlgorithmTrace(
                        algorithm="weighted_activation_decay",
                        stage="N1_Replay",
                        input_description=f"{initial_node_count} episodic memories",
                        input_count=initial_node_count,
                        output_description=f"{len(activated_ids)} activated memories ranked by score",
                        output_count=len(activated_ids),
                        parameters={"weights": "Wr=0.3, Wf=0.2, Wc=0.2, Wi=0.3", "decay_lambda": 0.1},
                        duration_ms=round(n1_duration, 1)
                    )
                ))
                self._emit(VisEvent(
                    stage="N1_Replay", type="stage_complete",
                    message=f"Replay complete in {n1_duration:.0f}ms",
                    duration_ms=round(n1_duration, 1)
                ))
                timeline.append(f"{_ts()} — Formed active working set with {len(active_working_set)} ranked items")
                self.stage_snapshots.append(_snapshot_graph("N1_Replay", snapshot, vis_events=self.vis_events, health=health_before, algorithm_traces=self.algorithm_traces))
            except Exception as e:
                logger.error(f"N1 Replay failed: {e}")
                timeline.append(f"{_ts()} — Replay stage failed: {e}")

            # --- N2: Consolidation ---
            t0 = time.perf_counter()
            timeline.append(f"{_ts()} — Consolidation (N2) stage started")
            self._emit(VisEvent(
                stage="N2_Consolidation", type="stage_start",
                message="Consolidation stage started — clustering semantically related memories"
            ))
            try:
                clusters = await self.consolidation_stage.execute(active_working_set)
                n2_duration = (time.perf_counter() - t0) * 1000
                stages_completed.append("N2_Consolidation")

                for idx, cluster in enumerate(clusters):
                    member_ids = [n.id for n in cluster]
                    self._emit(VisEvent(
                        stage="N2_Consolidation", type="cluster_form",
                        message=f"Cluster {idx}: {len(cluster)} related memories grouped",
                        cluster_id=idx,
                        cluster_members=member_ids,
                        algorithm="DBSCAN",
                        input_count=len(active_working_set),
                        output_count=len(clusters)
                    ))

                self._emit(VisEvent(
                    stage="N2_Consolidation", type="stage_complete",
                    message=f"Consolidated into {len(clusters)} semantic clusters in {n2_duration:.0f}ms",
                    input_count=len(active_working_set),
                    output_count=len(clusters),
                    duration_ms=round(n2_duration, 1),
                    trace=AlgorithmTrace(
                        algorithm="DBSCAN",
                        stage="N2_Consolidation",
                        input_description=f"{len(active_working_set)} activated memories",
                        input_count=len(active_working_set),
                        output_description=f"{len(clusters)} semantic clusters",
                        output_count=len(clusters),
                        parameters={"eps": 0.25, "min_samples": 1, "metric": "cosine"},
                        duration_ms=round(n2_duration, 1)
                    )
                ))
                timeline.append(f"{_ts()} — Consolidated into {len(clusters)} semantic clusters")
                self.stage_snapshots.append(_snapshot_graph("N2_Consolidation", snapshot, vis_events=self.vis_events, health=health_before, algorithm_traces=self.algorithm_traces))
            except Exception as e:
                logger.error(f"N2 Consolidation failed: {e}")
                timeline.append(f"{_ts()} — Consolidation stage failed: {e}")

            # --- Fact Resolution ---
            t0_fact = time.perf_counter()
            timeline.append(f"{_ts()} — Fact Resolution stage started")
            self._emit(VisEvent(
                stage="Fact_Resolution", type="stage_start",
                message="Fact Resolution stage started — checking for structured fact updates"
            ))
            try:
                from kernel.reasoning.fact_resolver import FactResolver
                fact_resolver = FactResolver(self.reasoning_engine)
                snapshot, fact_events, forgotten_ids = fact_resolver.resolve_conflicts(snapshot)
                
                # Delete forgotten nodes from Cognee Cloud and database
                for fid in forgotten_ids:
                    try:
                        await self.provider.forget(fid)
                        logger.info(f"Factual memory lifecycle: node {fid} has been permanently forgotten.")
                    except Exception as forget_err:
                        logger.error(f"Failed to delete forgotten node {fid}: {forget_err}")

                fact_duration = (time.perf_counter() - t0_fact) * 1000
                stages_completed.append("Fact_Resolution")


                for evt in fact_events:
                    self._emit(VisEvent(
                        stage="Fact_Resolution", type="conflict_resolve",
                        message=evt,
                        algorithm="structured_fact_resolution"
                    ))

                self._emit(VisEvent(
                    stage="Fact_Resolution", type="stage_complete",
                    message=f"Fact resolution complete: resolved {len(fact_events)} conflicts in {fact_duration:.0f}ms",
                    duration_ms=round(fact_duration, 1)
                ))
                timeline.extend([f"{_ts()} — {evt}" for evt in fact_events])
                self.stage_snapshots.append(_snapshot_graph("Fact_Resolution", snapshot, vis_events=self.vis_events, health=health_before, algorithm_traces=self.algorithm_traces))
            except Exception as e:
                logger.error(f"Fact Resolution stage failed: {e}")
                timeline.append(f"{_ts()} — Fact Resolution stage failed: {e}")

            # --- N3: Pruning ---
            t0 = time.perf_counter()
            timeline.append(f"{_ts()} — Pruning (N3) stage started")
            self._emit(VisEvent(
                stage="N3_Pruning", type="stage_start",
                message="Pruning stage started — detecting duplicates and contradictions"
            ))
            pre_prune_count = len(snapshot.nodes)
            try:
                snapshot, prune_events = await self.pruning_stage.execute(snapshot)
                n3_duration = (time.perf_counter() - t0) * 1000
                stages_completed.append("N3_Pruning")

                for evt in prune_events:
                    evt_lower = evt.lower()
                    if "merged" in evt_lower or "auto-merged" in evt_lower:
                        duplicates_merged += 1
                        self._emit(VisEvent(
                            stage="N3_Pruning", type="node_merge",
                            message=evt,
                            algorithm="cosine_similarity",
                            similarity=0.995
                        ))
                    elif "conflict" in evt_lower or "contradiction" in evt_lower or "resolved" in evt_lower:
                        contradictions_resolved += 1
                        self._emit(VisEvent(
                            stage="N3_Pruning", type="conflict_resolve",
                            message=evt,
                            algorithm="negation_detection + LLM_verification"
                        ))
                    else:
                        self._emit(VisEvent(
                            stage="N3_Pruning", type="node_fade",
                            message=evt
                        ))

                post_prune_count = len(snapshot.nodes)
                self._emit(VisEvent(
                    stage="N3_Pruning", type="stage_complete",
                    message=f"Pruning complete: {pre_prune_count - post_prune_count} nodes removed in {n3_duration:.0f}ms",
                    input_count=pre_prune_count,
                    output_count=post_prune_count,
                    duration_ms=round(n3_duration, 1),
                    trace=AlgorithmTrace(
                        algorithm="two_stage_duplicate_detection + contradiction_resolution",
                        stage="N3_Pruning",
                        input_description=f"{pre_prune_count} nodes",
                        input_count=pre_prune_count,
                        output_description=f"{post_prune_count} nodes ({pre_prune_count - post_prune_count} pruned)",
                        output_count=post_prune_count,
                        parameters={"auto_merge_threshold": 0.995, "candidate_threshold": 0.90},
                        duration_ms=round(n3_duration, 1),
                        details=[f"Duplicates merged: {duplicates_merged}", f"Contradictions resolved: {contradictions_resolved}"]
                    )
                ))
                timeline.extend([f"{_ts()} — {evt}" for evt in prune_events])
                health_n3 = compute_memory_health(
                    nodes=snapshot.nodes, edges=snapshot.edges,
                    duplicate_count=len(detect_duplicate_candidates(snapshot.nodes, 0.90)),
                    contradiction_count=len(find_potential_contradiction_pairs(snapshot.nodes))
                )
                self.stage_snapshots.append(_snapshot_graph("N3_Pruning", snapshot, vis_events=self.vis_events, health=health_n3, algorithm_traces=self.algorithm_traces))
            except Exception as e:
                logger.error(f"N3 Pruning failed: {e}")
                timeline.append(f"{_ts()} — Pruning stage failed: {e}")

            # --- REM: Abstraction ---
            t0 = time.perf_counter()
            timeline.append(f"{_ts()} — REM stage started")
            self._emit(VisEvent(
                stage="REM_Dream", type="stage_start",
                message="REM stage started — synthesizing abstract concepts"
            ))
            pre_rem_nodes = len(snapshot.nodes)
            pre_rem_edges = len(snapshot.edges)
            try:
                snapshot, rem_events = await self.rem_stage.execute(snapshot, clusters)
                rem_duration = (time.perf_counter() - t0) * 1000
                stages_completed.append("REM_Dream")

                for evt in rem_events:
                    evt_lower = evt.lower()
                    if "created concept" in evt_lower:
                        label = evt.split("'")[1] if "'" in evt else "Unknown"
                        self._emit(VisEvent(
                            stage="REM_Dream", type="concept_create",
                            message=evt,
                            concept_label=label,
                            algorithm="LLM_abstraction"
                        ))
                    elif "linked" in evt_lower or "association" in evt_lower:
                        self._emit(VisEvent(
                            stage="REM_Dream", type="edge_create",
                            message=evt,
                            algorithm="cross_cluster_linking"
                        ))
                    else:
                        self._emit(VisEvent(
                            stage="REM_Dream", type="concept_create",
                            message=evt
                        ))

                post_rem_nodes = len(snapshot.nodes)
                post_rem_edges = len(snapshot.edges)
                concepts_created = sum(1 for n in snapshot.nodes if n.source == "sleep")

                self._emit(VisEvent(
                    stage="REM_Dream", type="stage_complete",
                    message=f"REM complete: {concepts_created} concepts, {post_rem_edges - pre_rem_edges} new edges in {rem_duration:.0f}ms",
                    input_count=pre_rem_nodes,
                    output_count=post_rem_nodes,
                    duration_ms=round(rem_duration, 1),
                    trace=AlgorithmTrace(
                        algorithm="LLM_concept_synthesis + cross_cluster_linking",
                        stage="REM_Dream",
                        input_description=f"{len(clusters)} clusters from {pre_rem_nodes} nodes",
                        input_count=pre_rem_nodes,
                        output_description=f"{concepts_created} abstract concepts, {post_rem_edges - pre_rem_edges} semantic edges",
                        output_count=concepts_created,
                        duration_ms=round(rem_duration, 1)
                    )
                ))
                timeline.extend([f"{_ts()} — {evt}" for evt in rem_events])
                health_rem = compute_memory_health(
                    nodes=snapshot.nodes, edges=snapshot.edges,
                    duplicate_count=len(detect_duplicate_candidates(snapshot.nodes, 0.90)),
                    contradiction_count=len(find_potential_contradiction_pairs(snapshot.nodes))
                )
                self.stage_snapshots.append(_snapshot_graph("REM_Dream", snapshot, vis_events=self.vis_events, health=health_rem, algorithm_traces=self.algorithm_traces))
            except Exception as e:
                logger.error(f"REM Abstraction failed: {e}")
                timeline.append(f"{_ts()} — REM stage failed: {e}")

            # --- Final diagnostics ---
            final_node_count = len(snapshot.nodes)
            final_edge_count = len(snapshot.edges)
            final_duplicates = len(detect_duplicate_candidates(snapshot.nodes, 0.90))
            final_contradictions = len(find_potential_contradiction_pairs(snapshot.nodes))

            health_after = compute_memory_health(
                nodes=snapshot.nodes, edges=snapshot.edges,
                duplicate_count=final_duplicates, contradiction_count=final_contradictions
            )

            nodes_pruned = max(0, initial_node_count - final_node_count)
            concepts_created = sum(1 for n in snapshot.nodes if n.source == "sleep")
            compression_ratio = float(initial_node_count) / float(concepts_created) if concepts_created > 0 else 1.0
            density = calculate_graph_density(snapshot.nodes, snapshot.edges)
            avg_degree = calculate_average_degree(snapshot.nodes, snapshot.edges)

            # Calculate mean activation
            activation_scores = calculate_activation_scores(snapshot.nodes, snapshot.edges)
            mean_activation = sum(activation_scores.values()) / len(activation_scores) if activation_scores else 0.0

            # Fragmentation = orphan percentage
            orphan_count = sum(1 for n in snapshot.nodes if all(
                e.source != n.id and e.target != n.id for e in snapshot.edges
            ))
            fragmentation = orphan_count / len(snapshot.nodes) if snapshot.nodes else 0.0
            semantic_cohesion = 1.0 - fragmentation

            finished_at = datetime.now()
            duration = (finished_at - started_at).total_seconds()

            # Build final metrics
            final_metrics = MetricsSnapshot(
                mean_activation=round(mean_activation, 3),
                nodes_replayed=len(active_working_set),
                nodes_pruned=nodes_pruned,
                duplicates_merged=duplicates_merged,
                contradictions_resolved=contradictions_resolved,
                concepts_generated=concepts_created,
                cluster_count=len(clusters),
                avg_cluster_size=round(len(active_working_set) / len(clusters), 1) if clusters else 0.0,
                compression_ratio=round(compression_ratio, 1),
                retrieval_latency_ms=round(self.vis_events[2].duration_ms or 0, 1) if len(self.vis_events) > 2 else 0.0,
                memory_health=round(health_after, 1),
                graph_density=round(density, 3),
                fragmentation=round(fragmentation * 100, 1),
                semantic_cohesion=round(semantic_cohesion * 100, 1)
            )

            # Capture final snapshot with metrics
            self.stage_snapshots.append(_snapshot_graph("after", snapshot, final_metrics, vis_events=self.vis_events, health=health_after, algorithm_traces=self.algorithm_traces))

            # Synchronize updated snapshot modifications back to local Cognee
            if hasattr(self.provider, "save_graph_snapshot"):
                self.provider.save_graph_snapshot(snapshot)

            # Emit cycle complete
            self._emit(VisEvent(
                stage="system", type="cycle_complete",
                message=f"Dream cycle completed. Health: {health_before:.1f} → {health_after:.1f}",
                health_before=health_before,
                health_after=health_after
            ))

            timeline.append(f"{_ts()} — Dream cycle completed. Health: {health_before:.1f} → {health_after:.1f}")

            narrative = (
                f"Consolidated and reorganized mind graph. Initial size: {initial_node_count} nodes. "
                f"Pruned {nodes_pruned} redundant elements. Synthesized {concepts_created} abstract concepts. "
                f"Final health index verified at {health_after:.1f}/100."
            )

            report = DreamReport(
                dream_id=dream_id,
                started_at=started_at,
                finished_at=finished_at,
                duration=duration,
                stages_completed=stages_completed,
                nodes_processed=initial_node_count,
                nodes_removed=nodes_pruned,
                concepts_created=concepts_created,
                relationships_created=final_edge_count - initial_edge_count,
                compression_ratio=compression_ratio,
                memory_health_before=health_before,
                memory_health_after=health_after,
                summary_narrative=narrative,
                timeline=timeline
            )

            await event_bus.publish(Event(
                event_type="DreamCompleted",
                payload=report.model_dump()
            ))

            self.provider.set_sleep_state(False)
            await self.provider.process_queued_memories()

            return report
