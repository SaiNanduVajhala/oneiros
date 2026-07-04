import type { VisEvent, MemoryNode, AlgorithmTrace } from '../types';
import './ExplainPanel.css';

interface ExplainPanelProps {
  item: { type: string; data: unknown } | null;
  onClose: () => void;
}

function renderNodeExplain(node: MemoryNode) {
  return (
    <>
      <div className="explain-panel__section-title">Memory Node</div>
      <div className="explain-panel__node-id">{node.id}</div>
      <p className="explain-panel__content">{node.content}</p>
      
      <div className="explain-panel__section-title" style={{ marginTop: 'var(--space-md)' }}>Decision Rationale</div>
      <table className="explain-panel__table" style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 'var(--space-md)', fontSize: 'var(--text-sm)' }}>
        <tbody>
          <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
            <td style={{ padding: '8px 0', color: 'var(--text-tertiary)' }}>Source Layer</td>
            <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 600, color: node.source === 'sleep' ? 'var(--accent-primary)' : 'var(--accent-secondary)' }}>
              {node.source === 'sleep' ? 'REM Consolidation' : 'User Interaction'}
            </td>
          </tr>
          <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
            <td style={{ padding: '8px 0', color: 'var(--text-tertiary)' }}>Explicit Importance</td>
            <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 600 }}>{typeof node.importance === 'number' ? node.importance.toFixed(2) : '0.00'}</td>
          </tr>
          <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
            <td style={{ padding: '8px 0', color: 'var(--text-tertiary)' }}>Access Count</td>
            <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 600 }}>{node.access_count} hits</td>
          </tr>
          <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
            <td style={{ padding: '8px 0', color: 'var(--text-tertiary)' }}>Dynamic Importance</td>
            <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 600 }}>{(node.importance * 100).toFixed(0)}%</td>
          </tr>
          {typeof node.metadata?.retention_score === 'number' && (
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '8px 0', color: 'var(--text-tertiary)' }}>Retention Score</td>
              <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 600, color: 'var(--accent-success)' }}>{(node.metadata.retention_score as number).toFixed(3)}</td>
            </tr>
          )}
          <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
            <td style={{ padding: '8px 0', color: 'var(--text-tertiary)' }}>Pruning Threshold</td>
            <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 600, color: 'var(--accent-warning)' }}>&lt; 0.15 Retention</td>
          </tr>
          {!!node.metadata?.category && (
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '8px 0', color: 'var(--text-tertiary)' }}>Memory Category</td>
              <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 600 }}>{node.metadata.category as string}</td>
            </tr>
          )}
          {typeof node.metadata?.confidence === 'number' && (
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '8px 0', color: 'var(--text-tertiary)' }}>Extraction Confidence</td>
              <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 600 }}>{((node.metadata.confidence as number) * 100).toFixed(0)}%</td>
            </tr>
          )}
          {!!node.metadata?.status && (
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '8px 0', color: 'var(--text-tertiary)' }}>Lifecycle State</td>
              <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 600, color: 'var(--accent-primary)' }}>{node.metadata.status as string}</td>
            </tr>
          )}
          {!!node.metadata?.last_reinforced && (
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '8px 0', color: 'var(--text-tertiary)' }}>Last Reinforced</td>
              <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 600, fontSize: '11px' }}>{new Date(node.metadata.last_reinforced as string).toLocaleString()}</td>
            </tr>
          )}
          {!!node.metadata?.timestamp && (
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <td style={{ padding: '8px 0', color: 'var(--text-tertiary)' }}>Stored Timestamp</td>
              <td style={{ padding: '8px 0', textAlign: 'right', fontWeight: 600, fontSize: '11px' }}>{new Date(node.metadata.timestamp as string).toLocaleString()}</td>
            </tr>
          )}

        </tbody>
      </table>

      {!!node.metadata?.source_message && (
        <div style={{ marginTop: 'var(--space-md)', fontSize: 'var(--text-sm)', background: 'var(--bg-elevated, #1e1e2a)', padding: 'var(--space-sm, 8px)', borderRadius: 'var(--border-radius, 4px)', border: '1px solid var(--border-subtle, #2e2e3e)' }}>
          <strong style={{ color: 'var(--text-tertiary)' }}>Source Utterance:</strong>
          <p style={{ margin: '4px 0 0 0', fontStyle: 'italic' }}>"{node.metadata.source_message as string}"</p>
        </div>
      )}



      {node.semantic_tags.length > 0 && (
        <div className="explain-panel__tags" style={{ marginTop: 'var(--space-md)' }}>
          {node.semantic_tags.map(t => <span key={t} className="explain-panel__tag">{t}</span>)}
        </div>
      )}
      {node.explain_log.length > 0 && (
        <>
          <div className="explain-panel__section-title" style={{ marginTop: 'var(--space-lg)' }}>Audit Trail</div>
          <div className="explain-panel__log">
            {node.explain_log.map((entry, i) => (
              <div key={i} className="explain-panel__log-entry">{entry}</div>
            ))}
          </div>
        </>
      )}
    </>
  );
}

function renderTraceExplain(trace: AlgorithmTrace) {
  return (
    <div className="explain-panel__trace">
      <div className="explain-panel__trace-flow">
        <div className="explain-panel__trace-box explain-panel__trace-box--input">
          <span className="explain-panel__trace-label">INPUT</span>
          <span className="explain-panel__trace-desc">{trace.input_description}</span>
          <span className="explain-panel__trace-count">{trace.input_count}</span>
        </div>
        <div className="explain-panel__trace-arrow">↓</div>
        <div className="explain-panel__trace-box explain-panel__trace-box--algo">
          <span className="explain-panel__trace-label">ALGORITHM</span>
          <span className="explain-panel__trace-algo">{trace.algorithm}</span>
          {trace.parameters && Object.keys(trace.parameters).length > 0 && (
            <div className="explain-panel__trace-params">
              {Object.entries(trace.parameters).map(([k, v]) => (
                <span key={k}>{k}: {String(v)}</span>
              ))}
            </div>
          )}
        </div>
        <div className="explain-panel__trace-arrow">↓</div>
        <div className="explain-panel__trace-box explain-panel__trace-box--output">
          <span className="explain-panel__trace-label">OUTPUT</span>
          <span className="explain-panel__trace-desc">{trace.output_description}</span>
          <span className="explain-panel__trace-count">{trace.output_count}</span>
        </div>
      </div>
      {typeof trace.duration_ms === 'number' && trace.duration_ms > 0 && (
        <div className="explain-panel__trace-timing">
          Completed in {trace.duration_ms.toFixed(0)}ms
        </div>
      )}
      {trace.details && trace.details.length > 0 && (
        <div className="explain-panel__trace-details">
          {trace.details.map((d, i) => <div key={i}>{d}</div>)}
        </div>
      )}
    </div>
  );
}

function renderEventExplain(event: VisEvent) {
  return (
    <>
      <div className="explain-panel__section-title">Event Detail</div>
      <div className="explain-panel__event-info">
        <span className={`stage-badge stage-badge--${event.stage.startsWith('N1') ? 'n1' : event.stage.startsWith('N2') ? 'n2' : event.stage.startsWith('N3') ? 'n3' : event.stage.startsWith('REM') ? 'rem' : 'system'}`}>
          {event.stage}
        </span>
        <span className="explain-panel__event-type">{event.type}</span>
        <span className="explain-panel__event-time">{event.timestamp}</span>
      </div>
      <p className="explain-panel__content">{event.message}</p>
      {event.trace && renderTraceExplain(event.trace)}
      {!event.trace && event.algorithm && (
        <div className="explain-panel__algo-inline">
          <span className="explain-panel__trace-label">Algorithm</span>
          <span className="explain-panel__trace-algo">{event.algorithm}</span>
        </div>
      )}
    </>
  );
}

export function ExplainPanel({ item, onClose }: ExplainPanelProps) {
  if (!item) return null;

  return (
    <div className="explain-panel-overlay" onClick={onClose}>
      <div className="explain-panel" onClick={e => e.stopPropagation()}>
        <div className="explain-panel__header">
          <span>Explainability</span>
          <button className="explain-panel__close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <div className="explain-panel__body">
          {item.type === 'node' && renderNodeExplain(item.data as MemoryNode)}
          {item.type === 'event' && renderEventExplain(item.data as VisEvent)}
          {item.type === 'metric' && (
            <div>
              <div className="explain-panel__section-title">Metric Detail</div>
              <p className="explain-panel__content">
                {(item.data as { label: string; value: number }).label}: {(item.data as { label: string; value: number }).value}
              </p>
              <p style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)', marginTop: 'var(--space-md)' }}>
                This value is derived from the cognitive engine's algorithm output. Click events in the Dream Replay timeline to see the full Input → Algorithm → Output trace.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
