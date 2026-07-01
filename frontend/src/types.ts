/* Oneiros Frontend — Type Definitions (mirrors backend domain models) */

export interface MemoryNode {
  id: string;
  content: string;
  timestamp?: string;
  last_accessed?: string;
  access_count: number;
  importance: number;
  source: 'user' | 'agent' | 'sleep';
  semantic_tags: string[];
  metadata?: Record<string, unknown>;
  explain_log: string[];
}

export interface MemoryEdge {
  source: string;
  target: string;
  type: string;
  weight: number;
  metadata?: Record<string, unknown>;
}

export interface VisEvent {
  stage: string;
  timestamp: string;
  type: 'cycle_start' | 'stage_start' | 'node_activate' | 'cluster_form' |
        'node_fade' | 'node_merge' | 'conflict_resolve' | 'concept_create' |
        'edge_create' | 'stage_complete' | 'cycle_complete';
  message: string;
  node_ids?: string[];
  cluster_id?: number;
  cluster_members?: string[];
  similarity?: number;
  concept_label?: string;
  source_id?: string;
  target_id?: string;
  edge_type?: string;
  algorithm?: string;
  input_count?: number;
  output_count?: number;
  health_before?: number;
  health_after?: number;
  duration_ms?: number;
  trace?: AlgorithmTrace;
}

export interface AlgorithmTrace {
  algorithm: string;
  stage: string;
  input_description: string;
  input_count: number;
  output_description: string;
  output_count: number;
  parameters?: Record<string, unknown>;
  duration_ms: number;
  details?: string[];
}

export interface MetricsSnapshot {
  activation_threshold: number;
  mean_activation: number;
  nodes_replayed: number;
  nodes_pruned: number;
  duplicates_merged: number;
  contradictions_resolved: number;
  concepts_generated: number;
  cluster_count: number;
  avg_cluster_size: number;
  compression_ratio: number;
  retrieval_latency_ms: number;
  memory_health: number;
  graph_density: number;
  fragmentation: number;
  semantic_cohesion: number;
}

export interface DreamReport {
  dream_id: string;
  started_at: string;
  finished_at: string;
  duration: number;
  stages_completed: string[];
  nodes_processed: number;
  nodes_removed: number;
  concepts_created: number;
  relationships_created: number;
  compression_ratio: number;
  memory_health_before: number;
  memory_health_after: number;
  summary_narrative: string;
  timeline: string[];
}

export interface StageSnapshot {
  stage: string;
  timestamp: string;
  node_count: number;
  edge_count: number;
  nodes: MemoryNode[];
  edges: MemoryEdge[];
  metrics?: MetricsSnapshot;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export type SleepStatus = 'idle' | 'dreaming' | 'complete';
