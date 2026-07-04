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
  storedMemories: MemoryNode[];
  chatMessages: ChatMessage[];
  chatHistory: ChatMessage[];
  clearChatHistory: () => void;
  selectedItem: { type: string; data: unknown } | null;
  startDream: () => Promise<void>;
  wakeUp: () => void;
  sendMessage: (msg: string) => Promise<void>;
  setSelectedItem: (item: { type: string; data: unknown } | null) => void;
  isSending: boolean;
  deleteNode: (nodeId: string) => Promise<void>;
  deleteAllMemories: () => Promise<void>;
  showHistory: boolean;
  setShowHistory: (val: boolean) => void;
}

export function useDreamState(): DreamState {
  const [status, setStatus] = useState<SleepStatus>('idle');
  const [events, setEvents] = useState<VisEvent[]>([]);
  const [report, setReport] = useState<DreamReport | null>(null);
  const [metrics, setMetrics] = useState<MetricsSnapshot | null>(null);
  const [graphNodes, setGraphNodes] = useState<MemoryNode[]>([]);
  const [graphEdges, setGraphEdges] = useState<MemoryEdge[]>([]);
  const [storedMemories, setStoredMemories] = useState<MemoryNode[]>([]);
  const [snapshots, setSnapshots] = useState<StageSnapshot[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>(() => {
    try {
      const saved = localStorage.getItem('oneiros_chat_history');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [selectedItem, setSelectedItem] = useState<{ type: string; data: unknown } | null>(null);
  const [isSending, setIsSending] = useState<boolean>(false);
  const [showHistory, setShowHistory] = useState<boolean>(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem('oneiros_chat_history', JSON.stringify(chatHistory));
    } catch (err) {
      console.error('Failed to save chat history to localStorage:', err);
    }
  }, [chatHistory]);

  const clearChatHistory = useCallback(() => {
    setChatHistory([]);
    try {
      localStorage.removeItem('oneiros_chat_history');
    } catch (err) {
      console.error('Failed to clear chat history:', err);
    }
  }, []);

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

  const fetchMemories = useCallback(async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/chat/memories`);
      const data = await res.json();
      if (data.nodes) {
        const isInternal = (n: any) =>
          /^text_[a-f0-9]{10,}$/i.test(n.id) ||              // cognee text chunks
          /^user:[a-f0-9]+$/i.test(n.id) ||                  // cognee user nodes
          (Array.isArray(n.semantic_tags) && (
            n.semantic_tags.includes('textdocument') ||
            n.semantic_tags.includes('dataset') ||
            n.semantic_tags.includes('user')
          )) ||
          /^oneiros_/i.test(n.content || '') ||              // cognee dataset names
          /^user:[a-f0-9]+$/i.test(n.content || '');        // user:<hash> content

        setStoredMemories(
          data.nodes
            .filter((n: any) => !isInternal(n))
            .map((n: any) => ({
              ...n,
              timestamp: n.timestamp || new Date().toISOString(),
              last_accessed: n.last_accessed || new Date().toISOString(),
              metadata: n.metadata || {},
              explain_log: n.explain_log || [],
            }))
        );
      }
    } catch (err) {
      console.error('Failed to fetch memories:', err);
    }
  }, []);

  // Fetch final data after dream completes
  const fetchResults = useCallback(async () => {
    try {
      const [reportRes, metricsRes, graphRes, snapshotsRes] = await Promise.all([
        fetch(`${API}/dream-report`),
        fetch(`${API}/metrics`),
        fetch(`${API}/graph?show_history=${showHistory}`),
        fetch(`${API}/graph/snapshots`),
      ]);

      const reportData = await reportRes.json();
      if (reportData.dream_id) setReport(reportData);

      const metricsData = await metricsRes.json();
      if (metricsData.memory_health !== undefined) setMetrics(metricsData);

      const graphData = await graphRes.json();
      if (graphData.nodes) {
        const isInternalGraphNode = (n: any) =>
          /^text_[a-f0-9]{10,}$/i.test(n.id) ||
          /^user:[a-f0-9]+$/i.test(n.id) ||
          (Array.isArray(n.semantic_tags) && n.semantic_tags.some((t: string) =>
            ['textdocument', 'dataset', 'user'].includes(t)
          )) ||
          /^oneiros_/i.test(n.content || '') ||
          /^user:[a-f0-9]+$/i.test(n.content || '');

        const cleanNodes = graphData.nodes.filter((n: any) => !isInternalGraphNode(n));
        const cleanNodeIds = new Set(cleanNodes.map((n: any) => n.id));
        const cleanEdges = (graphData.edges || []).filter((e: any) =>
          cleanNodeIds.has(e.source) && cleanNodeIds.has(e.target)
        );
        setGraphNodes(cleanNodes);
        setGraphEdges(cleanEdges);
      }

      const snapshotsData = await snapshotsRes.json();
      if (Array.isArray(snapshotsData)) setSnapshots(snapshotsData);

      // Trigger memories refresh too
      await fetchMemories();
    } catch (err) {
      console.error('Failed to fetch results:', err);
    }
  }, [showHistory, fetchMemories]);


  // Fetch initial graph and state on mount
  useEffect(() => {
    fetchResults();
    fetchMemories();
  }, [fetchResults, fetchMemories]);

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



  const sendMessage = useCallback(async (msg: string) => {
    const userMsg: ChatMessage = {
      role: 'user',
      content: msg,
      timestamp: new Date().toISOString(),
    };
    setChatMessages(prev => [...prev, userMsg]);
    setChatHistory(prev => [...prev, userMsg]);
    setIsSending(true);

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
      setChatHistory(prev => [...prev, assistantMsg]);
      await fetchResults();
      await fetchMemories();
    } catch {
      const errMsg: ChatMessage = {
        role: 'assistant',
        content: 'Connection error — is the backend running?',
        timestamp: new Date().toISOString(),
      };
      setChatMessages(prev => [...prev, errMsg]);
      setChatHistory(prev => [...prev, errMsg]);
    } finally {
      setIsSending(false);
    }
  }, [fetchResults]);

  const wakeUp = useCallback(() => {
    setStatus('idle');
  }, []);

  const deleteNode = useCallback(async (nodeId: string) => {
    try {
      await fetch(`${API}/chat/memories/${encodeURIComponent(nodeId)}`, { method: 'DELETE' });
      await fetchMemories();
      await fetchResults();
    } catch (err) {
      console.error('Failed to delete node:', err);
    }
  }, [fetchMemories, fetchResults]);

  const deleteAllMemories = useCallback(async () => {
    try {
      await fetch(`${API}/chat/memories`, { method: 'DELETE' });
      setGraphNodes([]);
      setGraphEdges([]);
      setStoredMemories([]);
    } catch (err) {
      console.error('Failed to clear memories:', err);
    }
  }, []);

  return {
    status,
    events,
    report,
    metrics,
    graphNodes,
    graphEdges,
    snapshots,
    storedMemories,
    chatMessages,
    chatHistory,
    clearChatHistory,
    selectedItem,
    startDream,
    wakeUp,
    sendMessage,
    setSelectedItem,
    isSending,
    deleteNode,
    deleteAllMemories,
    showHistory,
    setShowHistory,
  };
}
