import { useState, useCallback, useRef, useEffect } from 'react';
import type { VisEvent, MetricsSnapshot, DreamReport, StageSnapshot, ChatMessage, SleepStatus, MemoryNode, MemoryEdge } from '../types';

const API = 'http://localhost:8000/api';

export interface DreamState {
  status: SleepStatus;
  events: VisEvent[];
  report: DreamReport | null;
  metrics: MetricsSnapshot | null;
  graphNodes: MemoryNode[];
  graphEdges: MemoryEdge[];
  snapshots: StageSnapshot[];
  chatMessages: ChatMessage[];
  selectedItem: { type: string; data: unknown } | null;
  startDream: () => Promise<void>;
  loadDemoData: () => Promise<void>;
  wakeUp: () => void;
  sendMessage: (msg: string) => Promise<void>;
  setSelectedItem: (item: { type: string; data: unknown } | null) => void;
}

export function useDreamState(): DreamState {
  const [status, setStatus] = useState<SleepStatus>('idle');
  const [events, setEvents] = useState<VisEvent[]>([]);
  const [report, setReport] = useState<DreamReport | null>(null);
  const [metrics, setMetrics] = useState<MetricsSnapshot | null>(null);
  const [graphNodes, setGraphNodes] = useState<MemoryNode[]>([]);
  const [graphEdges, setGraphEdges] = useState<MemoryEdge[]>([]);
  const [snapshots, setSnapshots] = useState<StageSnapshot[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [selectedItem, setSelectedItem] = useState<{ type: string; data: unknown } | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Connect SSE
  const connectSSE = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    const es = new EventSource(`${API}/sleep/events`);
    eventSourceRef.current = es;

    es.onmessage = (e) => {
      try {
        const visEvent: VisEvent = JSON.parse(e.data);
        setEvents(prev => [...prev, visEvent]);
      } catch { /* ignore parse errors */ }
    };

    es.onerror = () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, []);

  // Cleanup SSE on unmount
  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  // Fetch final data after dream completes
  const fetchResults = useCallback(async () => {
    try {
      const [reportRes, metricsRes, graphRes, snapshotsRes] = await Promise.all([
        fetch(`${API}/dream-report`),
        fetch(`${API}/metrics`),
        fetch(`${API}/graph`),
        fetch(`${API}/graph/snapshots`),
      ]);

      const reportData = await reportRes.json();
      if (reportData.dream_id) setReport(reportData);

      const metricsData = await metricsRes.json();
      if (metricsData.memory_health !== undefined) setMetrics(metricsData);

      const graphData = await graphRes.json();
      if (graphData.nodes) {
        setGraphNodes(graphData.nodes);
        setGraphEdges(graphData.edges);
      }

      const snapshotsData = await snapshotsRes.json();
      if (Array.isArray(snapshotsData)) setSnapshots(snapshotsData);
    } catch (err) {
      console.error('Failed to fetch results:', err);
    }
  }, []);

  const startDream = useCallback(async () => {
    setStatus('dreaming');
    setEvents([]);
    setReport(null);
    setMetrics(null);

    // Connect SSE before triggering
    connectSSE();

    try {
      const res = await fetch(`${API}/sleep/start`, { method: 'POST' });
      const data = await res.json();

      if (data.status === 'complete') {
        setStatus('complete');
        // Close SSE after a short delay to capture final events
        setTimeout(() => {
          eventSourceRef.current?.close();
          eventSourceRef.current = null;
        }, 500);
        await fetchResults();
      } else {
        setStatus('idle');
      }
    } catch (err) {
      console.error('Dream failed:', err);
      setStatus('idle');
      eventSourceRef.current?.close();
    }
  }, [connectSSE, fetchResults]);

  const loadDemoData = useCallback(async () => {
    try {
      const res = await fetch(`${API}/demo/load`, { method: 'POST' });
      const data = await res.json();
      if (data.status === 'loaded') {
        await fetchResults();
      }
    } catch (err) {
      console.error('Failed to load demo data:', err);
    }
  }, [fetchResults]);

  // Load initial demo data on mount
  useEffect(() => {
    loadDemoData();
  }, [loadDemoData]);

  const sendMessage = useCallback(async (msg: string) => {
    const userMsg: ChatMessage = {
      role: 'user',
      content: msg,
      timestamp: new Date().toISOString(),
    };
    setChatMessages(prev => [...prev, userMsg]);

    try {
      const res = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg }),
      });
      const data = await res.json();
      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: data.response || data.detail || JSON.stringify(data),
        timestamp: new Date().toISOString(),
      };
      setChatMessages(prev => [...prev, assistantMsg]);
    } catch {
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Connection error — is the backend running?',
        timestamp: new Date().toISOString(),
      }]);
    }
  }, []);

  const wakeUp = useCallback(() => {
    setStatus('idle');
  }, []);

  return {
    status,
    events,
    report,
    metrics,
    graphNodes,
    graphEdges,
    snapshots,
    chatMessages,
    selectedItem,
    startDream,
    loadDemoData,
    wakeUp,
    sendMessage,
    setSelectedItem,
  };
}
