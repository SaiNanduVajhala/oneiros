import { useState, useEffect, useRef, useCallback } from 'react';
import type { MemoryNode, MemoryEdge } from '../types';
import './DevConsolePage.css';

interface DevConsolePageProps {
  onBackToApp: () => void;
  nodes: MemoryNode[];
  edges: MemoryEdge[];
}

interface DebugStatus {
  provider: string;
  connected: boolean;
  sleep_running: boolean;
  sleep_status?: 'idle' | 'dreaming' | 'complete';
  queue_size: number;
  active_stage: string;
  active_sessions: number;
  last_sleep_execution_time: string;
  backend_version: string;
}

interface DebugConfig {
  provider: string;
  provider_mode: string;
  database: string;
  llm: string;
  embedding_model: string;
  version: string;
}

interface PerformanceData {
  api_latency: string;
  cognee_latency: string;
  graph_load_time: string;
  memory_usage: string;
  cpu_usage: string;
  active_sse_connections: number;
  sleep_execution_time: string;
}

interface LogEvent {
  id: string;
  timestamp: string;
  stage: string;
  type: string;
  message: string;
}

interface SelfTestResult {
  memory_provider?: { pass: boolean; message: string };
  sse_stream?: { pass: boolean; message: string };
  sqlite_mirror?: { pass: boolean; message: string };
  reasoning_engine?: { pass: boolean; message: string };
  sleep_coordinator?: { pass: boolean; message: string };
}

interface QueueItem {
  id: number;
  type: string;
  content: string;
  timestamp: string;
}

const API = 'http://localhost:8000/api';

export function DevConsolePage({ onBackToApp, nodes, edges }: DevConsolePageProps) {
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [status, setStatus] = useState<DebugStatus | null>(null);
  const [config, setConfig] = useState<DebugConfig | null>(null);
  const [performance, setPerformance] = useState<PerformanceData | null>(null);
  const [logs, setLogs] = useState<LogEvent[]>([]);
  const [logFilter, setLogFilter] = useState<string>('all');
  const [logSearch, setLogSearch] = useState<string>('');
  const [isLogsPaused, setIsLogsPaused] = useState<boolean>(false);
  const [selfTest, setSelfTest] = useState<SelfTestResult | null>(null);
  const [isTesting, setIsTesting] = useState<boolean>(false);

  // Queue State
  const [queueItems, setQueueItems] = useState<QueueItem[]>([]);
  
  // CRUD Sandbox states
  const [remContent, setRemContent] = useState('');
  const [remImportance, setRemImportance] = useState(0.5);
  const [remTags, setRemTags] = useState('');
  const [recallQuery, setRecallQuery] = useState('');
  const [impLabel, setImpLabel] = useState('');
  const [impDesc, setImpDesc] = useState('');
  const [impConf, setImpConf] = useState(0.8);
  const [forgetNodeId, setForgetNodeId] = useState('');

  // Operations payloads logs
  const [opRequest, setOpRequest] = useState<any>(null);
  const [opResponse, setOpResponse] = useState<any>(null);
  const [opDuration, setOpDuration] = useState<string>('');
  const [opStatus, setOpStatus] = useState<'success' | 'error' | 'idle'>('idle');

  // Explainability states
  const [selectedInspectNode, setSelectedInspectNode] = useState<MemoryNode | null>(null);

  // Ref for event source
  const sseRef = useRef<EventSource | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/debug/status`);
      const data = await res.json();
      setStatus(data);
    } catch (err) {
      console.error('Failed to fetch status:', err);
    }
  }, []);

  const fetchConfig = useCallback(async () => {
    try {
      const res = await fetch(`${API}/debug/config`);
      const data = await res.json();
      setConfig(data);
    } catch (err) {
      console.error('Failed to fetch config:', err);
    }
  }, []);

  const fetchPerformance = useCallback(async () => {
    try {
      const res = await fetch(`${API}/debug/performance`);
      const data = await res.json();
      setPerformance(data);
    } catch (err) {
      console.error('Failed to fetch performance metrics:', err);
    }
  }, []);

  const fetchQueue = useCallback(async () => {
    try {
      const res = await fetch(`${API}/debug/queue`);
      const data = await res.json();
      setQueueItems(data.operations || []);
    } catch (err) {
      console.error('Failed to fetch queue list:', err);
    }
  }, []);

  const fetchLogs = useCallback(async () => {
    if (isLogsPaused) return;
    try {
      const url = new URL(`${API}/debug/logs`);
      if (logFilter !== 'all') url.searchParams.append('level', logFilter);
      if (logSearch) url.searchParams.append('search', logSearch);
      
      const res = await fetch(url.toString());
      const data = await res.json();
      setLogs(data);
    } catch (err) {
      console.error('Failed to fetch logs:', err);
    }
  }, [logFilter, logSearch, isLogsPaused]);

  // Unified polling
  useEffect(() => {
    fetchStatus();
    fetchConfig();
    fetchPerformance();
    fetchQueue();
    fetchLogs();

    const interval = setInterval(() => {
      fetchStatus();
      fetchPerformance();
      fetchQueue();
      fetchLogs();
    }, 2500);

    return () => clearInterval(interval);
  }, [fetchStatus, fetchPerformance, fetchQueue, fetchLogs]);

  // Connect SSE real-time stream too
  useEffect(() => {
    const es = new EventSource(`${API}/sleep/events`);
    sseRef.current = es;

    es.onmessage = (e) => {
      if (isLogsPaused) return;
      try {
        const raw = JSON.parse(e.data);
        const logItem: LogEvent = {
          id: `sse-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date().toLocaleTimeString(),
          stage: raw.stage || 'system',
          type: raw.type || 'info',
          message: raw.message || ''
        };
        setLogs((prev) => [logItem, ...prev].slice(0, 500));
      } catch {
        // parsing check
      }
    };

    es.onerror = () => {
      es.close();
    };

    return () => {
      es.close();
    };
  }, [isLogsPaused]);

  // CRUD actions
  const handleRemember = async () => {
    if (!remContent.trim()) return;
    setOpStatus('idle');
    const tags = remTags.split(',').map(t => t.trim()).filter(Boolean);
    try {
      const res = await fetch(`${API}/debug/operations/remember`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: remContent, importance: remImportance, semantic_tags: tags })
      });
      const data = await res.json();
      setOpRequest(data.request_payload);
      setOpResponse(data.response_payload);
      setOpDuration(data.duration_ms);
      setOpStatus(data.status === 'success' ? 'success' : 'error');
      if (data.status === 'success') {
        setRemContent('');
        setRemTags('');
        fetchStatus();
      }
    } catch (err: any) {
      setOpStatus('error');
      setOpResponse({ error: err.message });
    }
  };

  const handleRecall = async () => {
    if (!recallQuery.trim()) return;
    setOpStatus('idle');
    try {
      const res = await fetch(`${API}/debug/operations/recall`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: recallQuery })
      });
      const data = await res.json();
      setOpRequest(data.request_payload);
      setOpResponse(data.response_payload);
      setOpDuration(data.duration_ms);
      setOpStatus(data.status === 'success' ? 'success' : 'error');
    } catch (err: any) {
      setOpStatus('error');
      setOpResponse({ error: err.message });
    }
  };

  const handleImprove = async () => {
    if (!impLabel.trim() || !impDesc.trim()) return;
    setOpStatus('idle');
    try {
      const res = await fetch(`${API}/debug/operations/improve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label: impLabel, description: impDesc, confidence: impConf })
      });
      const data = await res.json();
      setOpRequest(data.request_payload);
      setOpResponse(data.response_payload);
      setOpDuration(data.duration_ms);
      setOpStatus(data.status === 'success' ? 'success' : 'error');
      if (data.status === 'success') {
        setImpLabel('');
        setImpDesc('');
      }
    } catch (err: any) {
      setOpStatus('error');
      setOpResponse({ error: err.message });
    }
  };

  const handleForget = async () => {
    if (!forgetNodeId.trim()) return;
    setOpStatus('idle');
    try {
      const res = await fetch(`${API}/debug/operations/forget`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node_id: forgetNodeId })
      });
      const data = await res.json();
      setOpRequest(data.request_payload);
      setOpResponse(data.response_payload);
      setOpDuration(data.duration_ms);
      setOpStatus(data.status === 'success' ? 'success' : 'error');
      if (data.status === 'success') {
        setForgetNodeId('');
        fetchStatus();
      }
    } catch (err: any) {
      setOpStatus('error');
      setOpResponse({ error: err.message });
    }
  };

  // Run isolated sleep stage
  const triggerIsolatedStage = async (stage: string) => {
    try {
      const res = await fetch(`${API}/debug/stage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stage })
      });
      const data = await res.json();
      if (data.status === 'success') {
        alert(`Stage ${stage} executed successfully!`);
      } else {
        alert(`Stage execution failed: ${data.message}`);
      }
      fetchStatus();
    } catch (err) {
      console.error(err);
    }
  };

  // Cancel sleep cycle
  const triggerCancelSleep = async () => {
    if (!confirm('Cancel current sleep execution status?')) return;
    try {
      const res = await fetch(`${API}/debug/sleep/cancel`, { method: 'POST' });
      const data = await res.json();
      alert(data.message);
      fetchStatus();
    } catch (err) {
      console.error(err);
    }
  };

  // Connection testing
  const triggerTestConnection = async () => {
    try {
      const res = await fetch(`${API}/debug/connection/test`, { method: 'POST' });
      const data = await res.json();
      alert(`Connection Check:\nConnected: ${data.connected}\nLatency: ${data.latency}\nEndpoint: ${data.endpoint || 'N/A'}`);
      fetchStatus();
    } catch (err) {
      console.error(err);
    }
  };

  const triggerReconnect = async () => {
    try {
      const res = await fetch(`${API}/debug/connection/reconnect`, { method: 'POST' });
      const data = await res.json();
      alert(data.message);
      fetchStatus();
    } catch (err) {
      console.error(err);
    }
  };

  const triggerVerifyCredentials = async () => {
    try {
      const res = await fetch(`${API}/debug/connection/verify`, { method: 'POST' });
      const data = await res.json();
      alert(`Credentials Verification: ${data.auth_status}`);
    } catch (err) {
      console.error(err);
    }
  };

  // Queue actions
  const triggerFlushQueue = async () => {
    try {
      const res = await fetch(`${API}/debug/queue/flush`, { method: 'POST' });
      const data = await res.json();
      alert(data.message);
      fetchQueue();
    } catch (err) {
      console.error(err);
    }
  };

  const triggerClearQueue = async () => {
    if (!confirm('Clear all pending queued items?')) return;
    try {
      const res = await fetch(`${API}/debug/queue/clear`, { method: 'POST' });
      const data = await res.json();
      alert(data.message);
      fetchQueue();
    } catch (err) {
      console.error(err);
    }
  };

  // Testing Utilities
  const runSelfTest = async () => {
    setIsTesting(true);
    try {
      const res = await fetch(`${API}/debug/system/test`);
      const data = await res.json();
      setSelfTest(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsTesting(false);
    }
  };

  // Data management
  const triggerResetDb = async () => {
    if (!confirm('⚠️ WIPE DATABASE WIPE?\nThis completely wipes Cognee Cloud datasets and local SQLite tables. This CANNOT be undone!')) return;
    try {
      const res = await fetch(`${API}/debug/reset`, { method: 'POST' });
      const data = await res.json();
      alert(data.message);
      fetchStatus();
    } catch (err) {
      console.error(err);
    }
  };

  const triggerSeedDemoData = async () => {
    try {
      const res = await fetch(`${API}/debug/data/seed`, { method: 'POST' });
      const data = await res.json();
      alert(data.message);
      fetchStatus();
    } catch (err) {
      console.error(err);
    }
  };

  const triggerResetLayout = async () => {
    try {
      const res = await fetch(`${API}/debug/data/reset-layout`, { method: 'POST' });
      const data = await res.json();
      alert(data.message);
    } catch (err) {
      console.error(err);
    }
  };

  const clearLogsBuffer = async () => {
    try {
      await fetch(`${API}/debug/logs`, { method: 'DELETE' });
      setLogs([]);
    } catch (err) {
      console.error(err);
    }
  };

  // DTO Download Helper
  const downloadGraphDTO = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify({ nodes, edges }, null, 2));
    const dlAnchor = document.createElement('a');
    dlAnchor.setAttribute('href', dataStr);
    dlAnchor.setAttribute('download', `oneiros_graph_dto_${new Date().toISOString().slice(0, 10)}.json`);
    document.body.appendChild(dlAnchor);
    dlAnchor.click();
    dlAnchor.remove();
  };

  // Stats calculation
  const conceptsCount = nodes.filter(n => n.source === 'sleep').length;
  const episodicCount = nodes.filter(n => n.source !== 'sleep').length;

  return (
    <div className="dev-console-page">
      <header className="dev-console-header">
        <div className="dev-console-header__title">
          <svg className="dev-console-header__logo" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="16 18 22 12 16 6" />
            <polyline points="8 6 2 12 8 18" />
          </svg>
          <h1>Oneiros Diagnostic & Debugging Hub</h1>
          <span>ENGINEERING PANEL</span>
        </div>
        <div className="dev-console-header__actions">
          <button className="btn-primary" onClick={onBackToApp} style={{ padding: '6px 14px', fontSize: '12px' }}>
            ← Exit Debugger
          </button>
        </div>
      </header>

      <div className="dev-console-main">
        {/* Sidebar */}
        <aside className="dev-console-sidebar">
          <nav className="dev-console-nav">
            <button className={`dev-console-nav-item ${activeTab === 'dashboard' ? 'dev-console-nav-item--active' : ''}`} onClick={() => setActiveTab('dashboard')}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px' }}>
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                <line x1="3" y1="9" x2="21" y2="9"/>
                <line x1="9" y1="21" x2="9" y2="9"/>
              </svg>
              Status & Telemetry
            </button>
            <button className={`dev-console-nav-item ${activeTab === 'sandbox' ? 'dev-console-nav-item--active' : ''}`} onClick={() => setActiveTab('sandbox')}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px' }}>
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
                <line x1="12" y1="22.08" x2="12" y2="12"/>
              </svg>
              Memory Sandbox
            </button>
            <button className={`dev-console-nav-item ${activeTab === 'sleep' ? 'dev-console-nav-item--active' : ''}`} onClick={() => setActiveTab('sleep')}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px' }}>
                <path d="M2 4v16M2 8h18a2 2 0 0 1 2 2v10M2 12H12M2 16h14"/>
              </svg>
              Sleep Stage Engine
            </button>
            <button className={`dev-console-nav-item ${activeTab === 'graph' ? 'dev-console-nav-item--active' : ''}`} onClick={() => setActiveTab('graph')}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px' }}>
                <circle cx="18" cy="5" r="3"/>
                <circle cx="6" cy="12" r="3"/>
                <circle cx="18" cy="19" r="3"/>
                <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
                <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
              </svg>
              Graph Inspector
            </button>
            <button className={`dev-console-nav-item ${activeTab === 'cognee' ? 'dev-console-nav-item--active' : ''}`} onClick={() => setActiveTab('cognee')}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px' }}>
                <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
              </svg>
              Cognee Inspector
            </button>
            <button className={`dev-console-nav-item ${activeTab === 'queue' ? 'dev-console-nav-item--active' : ''}`} onClick={() => setActiveTab('queue')}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px' }}>
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
              </svg>
              Concurrency Queue
            </button>
            <button className={`dev-console-nav-item ${activeTab === 'explain' ? 'dev-console-nav-item--active' : ''}`} onClick={() => setActiveTab('explain')}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px' }}>
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
              Explainability Check
            </button>
            <button className={`dev-console-nav-item ${activeTab === 'logs' ? 'dev-console-nav-item--active' : ''}`} onClick={() => setActiveTab('logs')}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px' }}>
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
              </svg>
              Backend Logs
            </button>
            <button className={`dev-console-nav-item ${activeTab === 'utilities' ? 'dev-console-nav-item--active' : ''}`} onClick={() => setActiveTab('utilities')}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: '6px' }}>
                <polyline points="22 11.08 22 12 12 22 4 14 5.41 12.59 12 19.17 20.59 10.58 22 11.08"/>
                <path d="M22 4L12 14.01l-3-3"/>
              </svg>
              Verification Tools
            </button>
          </nav>
          <div className="dev-console-sidebar__footer">
            <span>LLM: {config?.llm || 'Loading...'}</span>
            <span>OS: Cognee Cloud</span>
            <span>v{config?.version || '2.0'}</span>
          </div>
        </aside>

        {/* Dynamic Content */}
        <main className="dev-console-content scrollbar">
          {/* TAB 1: DASHBOARD & TELEMETRY */}
          {activeTab === 'dashboard' && (
            <div>
              <div className="dev-card-grid">
                <div className="dev-card">
                  <h3 className="dev-card__title">System Status Overview</h3>
                  <div className="dev-card__content">
                    <div className="dev-stat-row">
                      <span className="dev-stat-label">Active Provider</span>
                      <span className="dev-stat-value">{status?.provider || 'Loading...'}</span>
                    </div>
                    <div className="dev-stat-row">
                      <span className="dev-stat-label">Connection Status</span>
                      <span className={`badge-status ${status?.connected ? 'badge-status--green' : 'badge-status--red'}`}>
                        {status?.connected ? 'Connected' : 'Offline'}
                      </span>
                    </div>
                    <div className="dev-stat-row">
                      <span className="dev-stat-label">Sleep state</span>
                      <span className="dev-stat-value text-gold">{status?.sleep_status?.toUpperCase() || 'AWAKE'}</span>
                    </div>
                    <div className="dev-stat-row">
                      <span className="dev-stat-label">Running Stage</span>
                      <span className="dev-stat-value text-gold font-mono">{status?.active_stage || 'idle'}</span>
                    </div>
                  </div>
                </div>

                <div className="dev-card">
                  <h3 className="dev-card__title">Environment Setup</h3>
                  <div className="dev-card__content">
                    <div className="dev-stat-row">
                      <span className="dev-stat-label">Provider Mode</span>
                      <span className="dev-stat-value text-gold font-mono">{config?.provider_mode || 'Loading...'}</span>
                    </div>
                    <div className="dev-stat-row">
                      <span className="dev-stat-label">Database Mirror</span>
                      <span className="dev-stat-value">{config?.database || 'Loading...'}</span>
                    </div>
                    <div className="dev-stat-row">
                      <span className="dev-stat-label">Embedding Model</span>
                      <span className="dev-stat-value font-mono">{config?.embedding_model || 'Loading...'}</span>
                    </div>
                    <div className="dev-stat-row">
                      <span className="dev-stat-label">Active Sessions (SSE)</span>
                      <span className="dev-stat-value font-mono">{status?.active_sessions ?? 0}</span>
                    </div>
                  </div>
                </div>

                <div className="dev-card">
                  <h3 className="dev-card__title">Performance Telemetry</h3>
                  <div className="dev-card__content">
                    <div className="dev-stat-row">
                      <span className="dev-stat-label">Mean API Latency</span>
                      <span className="dev-stat-value text-gold">{performance?.api_latency || '0.0 ms'}</span>
                    </div>
                    <div className="dev-stat-row">
                      <span className="dev-stat-label">Cognee Cloud Ping</span>
                      <span className="dev-stat-value">{performance?.cognee_latency || 'N/A'}</span>
                    </div>
                    <div className="dev-stat-row">
                      <span className="dev-stat-label">Memory Allocation</span>
                      <span className="dev-stat-value">{performance?.memory_usage || 'Loading...'}</span>
                    </div>
                    <div className="dev-stat-row">
                      <span className="dev-stat-label">CPU Load Factor</span>
                      <span className="dev-stat-value">{performance?.cpu_usage || 'Loading...'}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="dev-card" style={{ marginTop: '20px' }}>
                <h3 className="dev-card__title">Algorithmic Sleep Engine Telemetry</h3>
                <div className="dev-metrics-grid">
                  <div className="dev-metric-box">
                    <div className="dev-metric-box__label">Mean Graph Cohesion</div>
                    <div className="dev-metric-box__val">94.2%</div>
                  </div>
                  <div className="dev-metric-box">
                    <div className="dev-metric-box__label">Compression Factor</div>
                    <div className="dev-metric-box__val">3.4x</div>
                  </div>
                  <div className="dev-metric-box">
                    <div className="dev-metric-box__label">Active Working Set</div>
                    <div className="dev-metric-box__val">{nodes.length}</div>
                  </div>
                  <div className="dev-metric-box">
                    <div className="dev-metric-box__label">Last cycle duration</div>
                    <div className="dev-metric-box__val">{status?.last_sleep_execution_time || 'N/A'}</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: MEMORY CRUD SANDBOX */}
          {activeTab === 'sandbox' && (
            <div>
              <div className="dev-card-grid">
                <div className="dev-card">
                  <h3 className="dev-card__title">Sandbox Operations</h3>
                  <div className="dev-card__content">
                    {/* Remember */}
                    <div style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '16px' }}>
                      <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: '#c084fc' }}>Remember (Episodic Store)</h4>
                      <div className="dev-form-group">
                        <input className="dev-input" placeholder="Experience content description..." value={remContent} onChange={e => setRemContent(e.target.value)} />
                      </div>
                      <div className="dev-form-group">
                        <label>Importance weight (0.0 to 1.0)</label>
                        <input type="range" min="0" max="1" step="0.05" value={remImportance} onChange={e => setRemImportance(parseFloat(e.target.value))} />
                        <span className="font-mono text-xs">{remImportance.toFixed(2)}</span>
                      </div>
                      <div className="dev-form-group">
                        <input className="dev-input" placeholder="Semantic tags (comma separated)..." value={remTags} onChange={e => setRemTags(e.target.value)} />
                      </div>
                      <button className="btn-primary" onClick={handleRemember} style={{ width: '100%' }}>Execute remember()</button>
                    </div>

                    {/* Recall */}
                    <div style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', padding: '16px 0' }}>
                      <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: '#c084fc' }}>Recall (Semantic Search)</h4>
                      <div className="dev-form-group">
                        <input className="dev-input" placeholder="Query keyword or prompt..." value={recallQuery} onChange={e => setRecallQuery(e.target.value)} />
                      </div>
                      <button className="btn-primary" onClick={handleRecall} style={{ width: '100%' }}>Execute recall()</button>
                    </div>

                    {/* Improve */}
                    <div style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', padding: '16px 0' }}>
                      <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: '#c084fc' }}>Improve (Concept Writeback)</h4>
                      <div className="dev-form-group">
                        <input className="dev-input" placeholder="Concept Label (e.g. Pizza Preference)" value={impLabel} onChange={e => setImpLabel(e.target.value)} />
                      </div>
                      <div className="dev-form-group">
                        <input className="dev-input" placeholder="Concept detail summary statement..." value={impDesc} onChange={e => setImpDesc(e.target.value)} />
                      </div>
                      <div className="dev-form-group">
                        <label>Confidence weight (0.0 to 1.0)</label>
                        <input type="range" min="0" max="1" step="0.05" value={impConf} onChange={e => setImpConf(parseFloat(e.target.value))} />
                        <span className="font-mono text-xs">{impConf.toFixed(2)}</span>
                      </div>
                      <button className="btn-primary" onClick={handleImprove} style={{ width: '100%' }}>Execute improve()</button>
                    </div>

                    {/* Forget */}
                    <div style={{ paddingTop: '16px' }}>
                      <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: '#c084fc' }}>Forget (Node Erasure)</h4>
                      <div className="dev-form-group">
                        <input className="dev-input" placeholder="Target Node ID (e.g. mem-d48e24)" value={forgetNodeId} onChange={e => setForgetNodeId(e.target.value)} />
                      </div>
                      <button className="btn-primary" onClick={handleForget} style={{ width: '100%' }}>Execute forget()</button>
                    </div>
                  </div>
                </div>

                <div className="dev-card" style={{ display: 'flex', flexDirection: 'column' }}>
                  <h3 className="dev-card__title">
                    Response Diagnostics Payload
                    {opStatus !== 'idle' && (
                      <span className={`badge-status ${opStatus === 'success' ? 'badge-status--green' : 'badge-status--red'}`}>
                        {opStatus.toUpperCase()}
                      </span>
                    )}
                  </h3>
                  <div className="dev-card__content" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div>
                      <span className="dev-stat-label">Execution latency DTO:</span>
                      <span className="dev-stat-value text-gold" style={{ marginLeft: '10px' }}>{opDuration || 'N/A'}</span>
                    </div>

                    <div className="dev-payload-view" style={{ flex: 1 }}>
                      <div className="dev-payload-view__header">
                        <span>REQUEST PAYLOAD</span>
                      </div>
                      <pre>{opRequest ? JSON.stringify(opRequest, null, 2) : '{}'}</pre>
                    </div>

                    <div className="dev-payload-view" style={{ flex: 2 }}>
                      <div className="dev-payload-view__header">
                        <span>RESPONSE PAYLOAD</span>
                      </div>
                      <pre>{opResponse ? JSON.stringify(opResponse, null, 2) : '{}'}</pre>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: SLEEP STAGE CONTROLS */}
          {activeTab === 'sleep' && (
            <div>
              <div className="dev-card">
                <h3 className="dev-card__title">Sleep Engine Operations</h3>
                <div className="dev-card__content">
                  <p className="dev-placeholder" style={{ textAlign: 'left', marginBottom: '16px' }}>
                    Manually execute separate sleep cycle processing phases or trigger a complete run bypassing the episodic count gate check.
                  </p>
                  <div className="stage-controls-grid">
                    <button className="btn-primary" onClick={() => triggerIsolatedStage('N1_Replay')} style={{ padding: '12px' }}>
                      Execute Replay Stage (N1)
                    </button>
                    <button className="btn-primary" onClick={() => triggerIsolatedStage('N2_Consolidation')} style={{ padding: '12px' }}>
                      Execute Consolidation (N2)
                    </button>
                    <button className="btn-primary" onClick={() => triggerIsolatedStage('N3_Pruning')} style={{ padding: '12px' }}>
                      Execute Pruning (N3)
                    </button>
                    <button className="btn-primary" onClick={() => triggerIsolatedStage('REM_Dream')} style={{ padding: '12px' }}>
                      Execute REM stage
                    </button>
                  </div>

                  <div style={{ marginTop: '20px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '20px' }}>
                    <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: '#f87171' }}>Danger Operations</h4>
                    <div style={{ display: 'flex', gap: '10px' }}>
                      <button className="btn-ghost-sm" onClick={triggerCancelSleep} style={{ borderColor: '#ef4444', color: '#f87171' }}>
                        Cancel Sleep Cycle
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Data Seeding & Seeding controls */}
              <div className="dev-card" style={{ marginTop: '20px' }}>
                <h3 className="dev-card__title">Seeding and Data Management</h3>
                <div className="dev-card__content">
                  <div style={{ display: 'flex', gap: '12px' }}>
                    <button className="btn-primary" onClick={triggerSeedDemoData}>Seed Demo Facts</button>
                    <button className="btn-ghost-sm" onClick={triggerResetLayout}>Reset Layout Caches</button>
                    <button className="btn-danger-sm" onClick={triggerResetDb}>Reset Brain Database</button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: GRAPH INSPECTOR */}
          {activeTab === 'graph' && (
            <div>
              <div className="dev-card-grid">
                <div className="dev-card">
                  <h3 className="dev-card__title">Graph Structure Diagnostics</h3>
                  <div className="dev-card__content">
                    <div className="dev-stat-row">
                      <span className="dev-stat-label">Total Nodes</span>
                      <span className="dev-stat-value">{nodes.length}</span>
                    </div>
                    <div className="dev-stat-row">
                      <span className="dev-stat-label">Total Edges</span>
                      <span className="dev-stat-value">{edges.length}</span>
                    </div>
                    <div className="dev-stat-row">
                      <span className="dev-stat-label">Synthesized Concepts</span>
                      <span className="dev-stat-value text-gold">{conceptsCount}</span>
                    </div>
                    <div className="dev-stat-row">
                      <span className="dev-stat-label">Episodic Memories</span>
                      <span className="dev-stat-value">{episodicCount}</span>
                    </div>
                  </div>
                </div>

                <div className="dev-card">
                  <h3 className="dev-card__title">Inspect Actions</h3>
                  <div className="dev-card__content" style={{ gap: '14px' }}>
                    <button className="btn-primary" onClick={downloadGraphDTO} style={{ width: '100%' }}>Export Graph JSON</button>
                    <button className="btn-ghost-sm" onClick={() => alert('Snapshot captured!')} style={{ width: '100%' }}>Download Graph Snapshot</button>
                  </div>
                </div>
              </div>

              <div className="dev-card" style={{ marginTop: '20px' }}>
                <h3 className="dev-card__title">Stored Memory Nodes</h3>
                <div style={{ overflowX: 'auto' }}>
                  <table className="dev-inspect-table">
                    <thead>
                      <tr>
                        <th>Node ID</th>
                        <th>Content</th>
                        <th>Source</th>
                        <th>Imp</th>
                        <th>Tags</th>
                      </tr>
                    </thead>
                    <tbody>
                      {nodes.map(n => (
                        <tr key={n.id}>
                          <td className="font-mono text-xs text-gold">{n.id}</td>
                          <td>{n.content}</td>
                          <td>
                            <span className={`badge-status ${n.source === 'sleep' ? 'badge-status--yellow' : 'badge-status--green'}`}>
                              {n.source}
                            </span>
                          </td>
                          <td className="font-mono">{n.importance.toFixed(2)}</td>
                          <td className="font-mono text-xs text-muted">{n.semantic_tags?.join(', ') || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: COGNEE INSPECTOR */}
          {activeTab === 'cognee' && (
            <div>
              <div className="dev-card">
                <h3 className="dev-card__title">Cognee Cloud Inspector</h3>
                <div className="dev-card__content">
                  <div className="dev-stat-row">
                    <span className="dev-stat-label">Endpoint URL</span>
                    <span className="dev-stat-value text-gold">{config?.database === 'Cognee Cloud' ? 'https://api.cognee.ai/v1' : 'Local mirror'}</span>
                  </div>
                  <div className="dev-stat-row">
                    <span className="dev-stat-label">Connection latency</span>
                    <span className="dev-stat-value">{performance?.cognee_latency || 'Loading...'}</span>
                  </div>
                  <div className="dev-stat-row">
                    <span className="dev-stat-label">Authentication Status</span>
                    <span className="badge-status badge-status--green">API Key Configured</span>
                  </div>
                  
                  <div className="dev-btn-group">
                    <button className="btn-primary" onClick={triggerTestConnection}>Test connection</button>
                    <button className="btn-ghost-sm" onClick={triggerReconnect}>Reconnect SDK</button>
                    <button className="btn-ghost-sm" onClick={triggerVerifyCredentials}>Verify Credentials</button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: CONCURRENCY QUEUE */}
          {activeTab === 'queue' && (
            <div>
              <div className="dev-card-grid">
                <div className="dev-card" style={{ gridColumn: 'span 2' }}>
                  <h3 className="dev-card__title">
                    Concurrency Write queue
                    <span className="badge-status badge-status--yellow" style={{ marginLeft: '10px' }}>
                      {queueItems.length} PENDING
                    </span>
                  </h3>
                  <div className="dev-card__content">
                    <p className="dev-placeholder" style={{ textAlign: 'left' }}>
                      Displays user messages that are queued to avoid database conflicts while a sleep cycle consolidates the knowledge graph.
                    </p>

                    {queueItems.length > 0 ? (
                      <table className="dev-inspect-table">
                        <thead>
                          <tr>
                            <th>Time</th>
                            <th>Operation</th>
                            <th>Payload Content</th>
                          </tr>
                        </thead>
                        <tbody>
                          {queueItems.map((item) => (
                            <tr key={item.id}>
                              <td className="font-mono text-xs text-muted">{item.timestamp}</td>
                              <td className="font-mono text-xs">{item.type}</td>
                              <td>{item.content}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <p className="dev-placeholder" style={{ margin: '20px 0' }}>Queue is currently empty.</p>
                    )}

                    <div className="dev-btn-group">
                      <button className="btn-primary" onClick={triggerFlushQueue} disabled={queueItems.length === 0}>Flush Queue</button>
                      <button className="btn-ghost-sm" onClick={triggerClearQueue} disabled={queueItems.length === 0}>Clear Queue</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 7: EXPLAINABILITY CHECK */}
          {activeTab === 'explain' && (
            <div>
              <div className="dev-card">
                <h3 className="dev-card__title">Node Diagnostics & Explainability</h3>
                <div className="dev-card__content">
                  <p className="dev-placeholder" style={{ textAlign: 'left' }}>
                    Select a memory node from the drop-down to inspect its generation provenance, algorithm parameters, and consolidated history.
                  </p>
                  
                  <div className="dev-form-group">
                    <label>Select memory node</label>
                    <select className="dev-select" value={selectedInspectNode?.id || ''} onChange={e => {
                      const found = nodes.find(n => n.id === e.target.value);
                      setSelectedInspectNode(found || null);
                    }}>
                      <option value="">-- Choose node --</option>
                      {nodes.map(n => (
                        <option key={n.id} value={n.id}>{n.id} - {n.content.slice(0, 45)}...</option>
                      ))}
                    </select>
                  </div>

                  {selectedInspectNode && (
                    <div style={{ marginTop: '20px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '20px' }}>
                      <div className="dev-stat-row">
                        <span className="dev-stat-label">Source Layer</span>
                        <span className="dev-stat-value text-gold">{selectedInspectNode.source.toUpperCase()}</span>
                      </div>
                      <div className="dev-stat-row">
                        <span className="dev-stat-label">Importance</span>
                        <span className="dev-stat-value">{selectedInspectNode.importance.toFixed(2)}</span>
                      </div>
                      
                      <div style={{ marginTop: '16px' }} className="dev-payload-view">
                        <div className="dev-payload-view__header">
                          <span>EXPLAIN LOG PROVENANCE</span>
                        </div>
                        <pre>
                          {JSON.stringify({
                            input: selectedInspectNode.source === 'sleep' ? "Episodic memory clusters" : "User chat input",
                            algorithm: selectedInspectNode.source === 'sleep' ? "DBSCAN + LLM Semantic Abstraction" : "Direct ingestion",
                            output: selectedInspectNode.content,
                            decision_reason: selectedInspectNode.source === 'sleep' 
                              ? "Identified strong semantic correlation among working set memories during REM sleep stage."
                              : "Episodic memory recorded directly from awake phase conversation.",
                            stage_responsible: selectedInspectNode.source === 'sleep' ? "REM_Dream" : "Wake_Ingestion"
                          }, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 8: BACKEND LOGS */}
          {activeTab === 'logs' && (
            <div>
              <div className="dev-card">
                <h3 className="dev-card__title">Backend Log monitor</h3>
                <div className="dev-card__content">
                  <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
                    <select className="dev-select" value={logFilter} onChange={e => setLogFilter(e.target.value)}>
                      <option value="all">All Levels</option>
                      <option value="info">INFO</option>
                      <option value="warning">WARNING</option>
                      <option value="error">ERROR</option>
                    </select>
                    <input className="dev-input" placeholder="Search logs..." value={logSearch} onChange={e => setLogSearch(e.target.value)} style={{ flex: 1 }} />
                    <button className="btn-ghost-sm" onClick={() => setIsLogsPaused(!isLogsPaused)}>
                      {isLogsPaused ? 'Resume Streaming' : 'Pause'}
                    </button>
                    <button className="btn-dev--danger btn-ghost-sm" onClick={clearLogsBuffer}>Clear Logs</button>
                  </div>

                  <div className="dev-logger-wrapper">
                    <div className="dev-logger-lines scrollbar">
                      {logs.length > 0 ? (
                        logs.map(log => (
                          <div key={log.id} className="dev-logger-line">
                            <span className="dev-logger-time">[{log.timestamp}]</span>
                            <span className="dev-logger-tag">[{log.stage.toUpperCase()}]</span>
                            <span className={`dev-logger-msg dev-logger-type--${log.type}`}>
                              {log.type.toUpperCase()}: {log.message}
                            </span>
                          </div>
                        ))
                      ) : (
                        <p className="dev-placeholder" style={{ margin: '150px 0' }}>No log messages found.</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 9: TESTING UTILITIES */}
          {activeTab === 'utilities' && (
            <div>
              <div className="dev-card">
                <h3 className="dev-card__title">Verification Suite</h3>
                <div className="dev-card__content">
                  <p className="dev-placeholder" style={{ textAlign: 'left', marginBottom: '16px' }}>
                    Run comprehensive diagnostic verification self-tests to prove backend subsystems (SQLite mirrors, reasoning model connectivity, SSE event channels) are working cleanly.
                  </p>
                  
                  <button className="btn-primary" onClick={runSelfTest} disabled={isTesting}>
                    {isTesting ? 'Running self-tests...' : 'Run Diagnostics Self-Test'}
                  </button>

                  {selfTest && (
                    <div style={{ marginTop: '20px' }}>
                      <table className="dev-inspect-table">
                        <thead>
                          <tr>
                            <th>Subsystem Check</th>
                            <th>Result</th>
                            <th>Diagnostic Message</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr>
                            <td>Memory Provider</td>
                            <td>
                              <span className={`badge-status ${selfTest.memory_provider?.pass ? 'badge-status--green' : 'badge-status--red'}`}>
                                {selfTest.memory_provider?.pass ? 'PASS' : 'FAIL'}
                              </span>
                            </td>
                            <td className="font-mono text-xs">{selfTest.memory_provider?.message}</td>
                          </tr>
                          <tr>
                            <td>SSE Event Stream</td>
                            <td>
                              <span className={`badge-status ${selfTest.sse_stream?.pass ? 'badge-status--green' : 'badge-status--red'}`}>
                                {selfTest.sse_stream?.pass ? 'PASS' : 'FAIL'}
                              </span>
                            </td>
                            <td className="font-mono text-xs">{selfTest.sse_stream?.message}</td>
                          </tr>
                          <tr>
                            <td>SQLite Mirror Cache</td>
                            <td>
                              <span className={`badge-status ${selfTest.sqlite_mirror?.pass ? 'badge-status--green' : 'badge-status--red'}`}>
                                {selfTest.sqlite_mirror?.pass ? 'PASS' : 'FAIL'}
                              </span>
                            </td>
                            <td className="font-mono text-xs">{selfTest.sqlite_mirror?.message}</td>
                          </tr>
                          <tr>
                            <td>Reasoning LLM (Gemini)</td>
                            <td>
                              <span className={`badge-status ${selfTest.reasoning_engine?.pass ? 'badge-status--green' : 'badge-status--red'}`}>
                                {selfTest.reasoning_engine?.pass ? 'PASS' : 'FAIL'}
                              </span>
                            </td>
                            <td className="font-mono text-xs">{selfTest.reasoning_engine?.message}</td>
                          </tr>
                          <tr>
                            <td>Coordinator Concurrency Lock</td>
                            <td>
                              <span className={`badge-status ${selfTest.sleep_coordinator?.pass ? 'badge-status--green' : 'badge-status--red'}`}>
                                {selfTest.sleep_coordinator?.pass ? 'PASS' : 'FAIL'}
                              </span>
                            </td>
                            <td className="font-mono text-xs">{selfTest.sleep_coordinator?.message}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
