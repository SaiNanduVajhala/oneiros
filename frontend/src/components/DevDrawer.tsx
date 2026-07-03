import { useState, useEffect, useRef } from 'react';
import './DevDrawer.css';

interface DevDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

interface DebugStatus {
  provider: string;
  connected: boolean;
  sleep_running: boolean;
  sleep_status?: 'idle' | 'dreaming' | 'complete';
  queue_size: number;
  active_stage: string;
}

interface DebugConfig {
  provider: string;
  provider_mode: string;
  database: string;
  llm: string;
  embedding_model: string;
  version: string;
}

interface ProvenanceData {
  nodes: Array<{
    id: string;
    content: string;
    access_count: number;
    importance: number;
    source: string;
    semantic_tags: string[];
  }>;
  edges: Array<{
    source: string;
    target: string;
    type: string;
    weight: number;
  }>;
}

interface LogEvent {
  id: string;
  timestamp: string;
  stage: string;
  type: string;
  message: string;
}

const API = 'http://localhost:8000/api';

export function DevDrawer({ isOpen, onClose }: DevDrawerProps) {
  const [status, setStatus] = useState<DebugStatus | null>(null);
  const [config, setConfig] = useState<DebugConfig | null>(null);
  const [provenance, setProvenance] = useState<ProvenanceData | null>(null);
  const [provTab, setProvTab] = useState<'table' | 'json'>('table');
  const [logs, setLogs] = useState<LogEvent[]>([]);
  const [isExecutingStage, setIsExecutingStage] = useState<string | null>(null);
  const [isResetting, setIsResetting] = useState(false);

  const sseRef = useRef<EventSource | null>(null);
  const logsEndRef = useRef<HTMLDivElement | null>(null);

  // Fetch status and config
  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API}/debug/status`);
      const data = await res.json();
      setStatus(data);
    } catch (err) {
      console.error('Failed to fetch debug status:', err);
    }
  };

  const fetchConfig = async () => {
    try {
      const res = await fetch(`${API}/debug/config`);
      const data = await res.json();
      setConfig(data);
    } catch (err) {
      console.error('Failed to fetch debug config:', err);
    }
  };

  const fetchProvenance = async () => {
    try {
      const res = await fetch(`${API}/chat/memories`);
      const data = await res.json();
      // Build ProvenanceData shape from memories response
      setProvenance({ nodes: data.nodes || [], edges: [] });
    } catch (err) {
      console.error('Failed to fetch memories for provenance:', err);
    }
  };

  // Poll status every 3 seconds while open
  useEffect(() => {
    if (!isOpen) return;
    fetchStatus();
    fetchConfig();
    fetchProvenance();

    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, [isOpen]);

  // Connect unified sleep event stream
  useEffect(() => {
    if (!isOpen) {
      if (sseRef.current) {
        sseRef.current.close();
        sseRef.current = null;
      }
      return;
    }

    if (!sseRef.current) {
      const es = new EventSource(`${API}/sleep/events`);
      sseRef.current = es;

      es.onmessage = (e) => {
        try {
          const raw = JSON.parse(e.data);
          const logItem: LogEvent = {
            id: Math.random().toString(36).substr(2, 9),
            timestamp: new Date().toLocaleTimeString(),
            stage: raw.stage || 'system',
            type: raw.type || 'info',
            message: raw.message || ''
          };
          setLogs((prev) => [...prev, logItem]);
        } catch { /* ignore parsing anomalies */ }
      };

      es.onerror = () => {
        es.close();
        sseRef.current = null;
      };
    }

    return () => {
      if (sseRef.current) {
        sseRef.current.close();
        sseRef.current = null;
      }
    };
  }, [isOpen]);

  // Scroll logs container to bottom on update
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  if (!isOpen) return null;

  // Execute isolated pipeline stage
  const runStage = async (stageName: string) => {
    setIsExecutingStage(stageName);
    try {
      const res = await fetch(`${API}/debug/stage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stage: stageName }),
      });
      const data = await res.json();
      if (data.status === 'success') {
        fetchStatus();
        fetchProvenance();
      } else {
        alert(`Stage Execution Error: ${data.message || 'Unknown issue'}`);
      }
    } catch (err) {
      console.error(err);
      alert('Failed to trigger stage execution.');
    } finally {
      setIsExecutingStage(null);
    }
  };

  // Reset database completely
  const resetDb = async () => {
    if (!confirm('Are you absolutely sure you want to wipe the Cognee Cloud dataset and local SQLite tables? This will delete all nodes and cannot be undone.')) {
      return;
    }
    setIsResetting(true);
    try {
      const res = await fetch(`${API}/debug/reset`, { method: 'POST' });
      const data = await res.json();
      if (data.status === 'success') {
        setProvenance(null);
        fetchStatus();
        alert('Database cleared successfully. All records wiped.');
      } else {
        alert(`Reset Error: ${data.message}`);
      }
    } catch (err) {
      console.error(err);
      alert('Reset failed.');
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="dev-drawer">
      <div className="dev-drawer__header">
        <div className="dev-drawer__title-group">
          <svg className="dev-drawer__icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent-primary)" strokeWidth="2">
            <polyline points="16 18 22 12 16 6" />
            <polyline points="8 6 2 12 8 18" />
          </svg>
          <h2>Developer Console</h2>
        </div>
        <button className="dev-drawer__close-btn" onClick={onClose} aria-label="Close developer drawer">&times;</button>
      </div>

      <div className="dev-drawer__content">
        {/* Section 1: System Status */}
        <div className="dev-panel">
          <h3 className="dev-panel__title">System Status</h3>
          <div className="dev-grid">
            <div className="dev-stat">
              <span className="dev-stat__label">Active Provider</span>
              <span className="dev-stat__value font-mono">{status?.provider || 'Loading...'}</span>
            </div>
            <div className="dev-stat">
              <span className="dev-stat__label">Connection</span>
              <span className={`dev-stat__value ${status?.connected ? 'text-success' : 'text-error'}`}>
                {status ? (status.connected ? 'Connected' : 'Offline') : 'Loading...'}
              </span>
            </div>
            <div className="dev-stat">
              <span className="dev-stat__label">Sleep State</span>
              <span className="dev-stat__value">
                {status ? (
                  status.sleep_status ? (
                    status.sleep_status === 'dreaming' ? 'Consolidating' :
                    status.sleep_status === 'complete' ? 'Rested' :
                    'Awake'
                  ) : (
                    status.sleep_running ? 'Consolidating' : 'Awake'
                  )
                ) : 'Loading...'}
              </span>
            </div>
            <div className="dev-stat">
              <span className="dev-stat__label">Queue Size</span>
              <span className="dev-stat__value font-mono">{status?.queue_size ?? '0'}</span>
            </div>
            <div className="dev-stat">
              <span className="dev-stat__label">Active Stage</span>
              <span className="dev-stat__value font-mono text-gold">{status?.active_stage || 'idle'}</span>
            </div>
          </div>
        </div>

        {/* Section 2: Runtime Configuration */}
        <div className="dev-panel">
          <h3 className="dev-panel__title">Runtime Configuration</h3>
          {config ? (
            <table className="dev-table config-table">
              <tbody>
                <tr>
                  <td>Mode</td>
                  <td className="font-mono text-gold">{config.provider_mode}</td>
                </tr>
                <tr>
                  <td>Database</td>
                  <td>{config.database}</td>
                </tr>
                <tr>
                  <td>LLM Core</td>
                  <td className="font-mono">{config.llm}</td>
                </tr>
                <tr>
                  <td>Embedding Model</td>
                  <td className="font-mono">{config.embedding_model}</td>
                </tr>
                <tr>
                  <td>Version</td>
                  <td className="font-mono">v{config.version}</td>
                </tr>
              </tbody>
            </table>
          ) : (
            <p className="dev-placeholder">Loading configuration...</p>
          )}
        </div>

        {/* Section 3: Sleep Stage Controls */}
        <div className="dev-panel">
          <h3 className="dev-panel__title">Isolated Stage Controls</h3>
          <div className="stage-controls-grid">
            <button
              className="btn-dev"
              onClick={() => runStage('N1_Replay')}
              disabled={!!isExecutingStage || status?.sleep_running}
            >
              {isExecutingStage === 'N1_Replay' ? 'Running N1...' : 'Run Replay (N1)'}
            </button>
            <button
              className="btn-dev"
              onClick={() => runStage('N2_Consolidation')}
              disabled={!!isExecutingStage || status?.sleep_running}
            >
              {isExecutingStage === 'N2_Consolidation' ? 'Running N2...' : 'Run Consolidation (N2)'}
            </button>
            <button
              className="btn-dev"
              onClick={() => runStage('N3_Pruning')}
              disabled={!!isExecutingStage || status?.sleep_running}
            >
              {isExecutingStage === 'N3_Pruning' ? 'Running N3...' : 'Run Pruning (N3)'}
            </button>
            <button
              className="btn-dev"
              onClick={() => runStage('REM_Dream')}
              disabled={!!isExecutingStage || status?.sleep_running}
            >
              {isExecutingStage === 'REM_Dream' ? 'Running REM...' : 'Run REM Dream'}
            </button>
          </div>
          <div className="dev-divider" />
          <button
            className="btn-dev btn-dev--danger"
            onClick={resetDb}
            disabled={isResetting || status?.sleep_running}
          >
            {isResetting ? 'Resetting Brain...' : 'Wipe & Reset Database'}
          </button>
        </div>

        {/* Section 4: Provenance Explorer */}
        <div className="dev-panel">
          <div className="dev-panel__header-row">
            <h3 className="dev-panel__title">Provenance Explorer</h3>
            <button className="btn-dev-refresh" onClick={fetchProvenance} title="Refresh graph DTO">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
              </svg>
              Refresh
            </button>
          </div>

          <div className="tab-buttons">
            <button
              className={`tab-btn ${provTab === 'table' ? 'active' : ''}`}
              onClick={() => setProvTab('table')}
            >
              Explorer
            </button>
            <button
              className={`tab-btn ${provTab === 'json' ? 'active' : ''}`}
              onClick={() => setProvTab('json')}
            >
              Raw DTO
            </button>
          </div>

          <div className="tab-content">
            {provTab === 'table' ? (
              <div className="provenance-table-wrapper scrollbar">
                {provenance && provenance.nodes.length > 0 ? (
                  <table className="dev-table">
                    <thead>
                      <tr>
                        <th>Content</th>
                        <th>Source</th>
                        <th>Tags</th>
                        <th>Imp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {provenance.nodes.map((node) => (
                        <tr key={node.id}>
                          <td className="node-content-cell">{node.content}</td>
                          <td>
                            <span className={`node-source-badge badge--${node.source}`}>
                              {node.source}
                            </span>
                          </td>
                          <td className="text-xs" style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                            {node.semantic_tags?.join(', ') || '—'}
                          </td>
                          <td className="font-mono text-center">{node.importance.toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p className="dev-placeholder">No memories stored yet. Say something to Oneiros.</p>
                )}
              </div>
            ) : (
              <div className="provenance-json-wrapper scrollbar">
                <pre className="font-mono text-xs">
                  {provenance ? JSON.stringify(provenance, null, 2) : '{}'}
                </pre>
              </div>
            )}
          </div>
        </div>

        {/* Section 5: Diagnostics Event Logs */}
        <div className="dev-panel">
          <div className="dev-panel__header-row">
            <h3 className="dev-panel__title">Live Event Log</h3>
            <button className="btn-dev-clear" onClick={() => setLogs([])}>
              Clear
            </button>
          </div>
          <div className="event-logs-container scrollbar">
            {logs.length > 0 ? (
              logs.map((log) => (
                <div key={log.id} className="log-line">
                  <span className="log-time font-mono">{log.timestamp}</span>
                  <span className="log-stage font-mono">[{log.stage}]</span>
                  <span className={`log-type log-type--${log.type} font-mono`}>{log.type.toUpperCase()}:</span>
                  <span className="log-message">{log.message}</span>
                </div>
              ))
            ) : (
              <p className="dev-placeholder">Awaiting SSE Event stream signals...</p>
            )}
            <div ref={logsEndRef} />
          </div>
        </div>
      </div>
    </div>
  );
}
