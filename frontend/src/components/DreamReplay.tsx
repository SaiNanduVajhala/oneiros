import { useRef, useEffect } from 'react';
import type { VisEvent } from '../types';
import './DreamReplay.css';

interface DreamReplayProps {
  events: VisEvent[];
  onEventClick: (event: VisEvent) => void;
}

const STAGE_CONFIG: Record<string, { badge: string; className: string }> = {
  N1_Replay: { badge: 'N1', className: 'stage-badge--n1' },
  N2_Consolidation: { badge: 'N2', className: 'stage-badge--n2' },
  N3_Pruning: { badge: 'N3', className: 'stage-badge--n3' },
  REM_Dream: { badge: 'REM', className: 'stage-badge--rem' },
  system: { badge: 'SYS', className: 'stage-badge--system' },
};

const TYPE_ICONS: Record<string, string> = {
  cycle_start: '◉',
  stage_start: '▶',
  node_activate: '⚡',
  cluster_form: '◎',
  node_merge: '⊕',
  node_fade: '◌',
  conflict_resolve: '⚔',
  concept_create: '✦',
  edge_create: '↔',
  stage_complete: '✓',
  cycle_complete: '★',
};

export function DreamReplay({ events, onEventClick }: DreamReplayProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [events]);

  return (
    <div className="panel dream-replay">
      <div className="panel-header">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.2" />
          <polyline points="7,4 7,7 9.5,8.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
        </svg>
        Dream Replay
        <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', color: 'var(--text-muted)', fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>
          {events.length} events
        </span>
      </div>
      <div className="dream-replay__feed" ref={scrollRef}>
        {events.length === 0 && (
          <div className="dream-replay__empty">
            <p>No dream events yet.</p>
            <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>
              Press Dream to begin consolidation.
            </p>
          </div>
        )}
        {events.map((evt, i) => {
          const stageConf = STAGE_CONFIG[evt.stage] || STAGE_CONFIG.system;
          const icon = TYPE_ICONS[evt.type] || '·';

          return (
            <div
              key={i}
              className="dream-replay__event animate-slide-in-right"
              style={{ animationDelay: `${Math.min(i * 40, 600)}ms` }}
              onClick={() => onEventClick(evt)}
            >
              <div className="dream-replay__event-header">
                <span className={`stage-badge ${stageConf.className}`}>{stageConf.badge}</span>
                <span className="dream-replay__timestamp">{evt.timestamp}</span>
              </div>
              <div className="dream-replay__event-body">
                <span className="dream-replay__icon">{icon}</span>
                <span className="dream-replay__message">{evt.message}</span>
              </div>
              {evt.algorithm && (
                <div className="dream-replay__algo">
                  <span className="dream-replay__algo-label">Algorithm</span>
                  <span className="dream-replay__algo-name">{evt.algorithm}</span>
                </div>
              )}
              {evt.input_count !== undefined && evt.output_count !== undefined && (
                <div className="dream-replay__flow">
                  <span className="dream-replay__flow-num">{evt.input_count}</span>
                  <span className="dream-replay__flow-arrow">→</span>
                  <span className="dream-replay__flow-num">{evt.output_count}</span>
                  {typeof evt.duration_ms === 'number' && (
                    <span className="dream-replay__duration">{evt.duration_ms.toFixed(0)}ms</span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
