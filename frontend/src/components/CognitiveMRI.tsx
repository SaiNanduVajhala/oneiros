import { useEffect, useRef } from 'react';
import type { MetricsSnapshot } from '../types';
import './CognitiveMRI.css';

interface CognitiveMRIProps {
  metrics: MetricsSnapshot | null;
  report: any | null;
  healthBefore: number;
}

function getHealthColor(v: number): string {
  if (v >= 75) return 'var(--accent-success)';
  if (v >= 45) return 'var(--accent-warning)';
  return 'var(--accent-error)';
}

export function CognitiveMRI({ metrics, report, healthBefore }: CognitiveMRIProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const health = metrics?.memory_health ?? 0;
  const hasData = metrics !== null;

  // Draw radial gauge
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio;
    const size = 150;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = `${size}px`;
    canvas.style.height = `${size}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const cx = size / 2;
    const cy = size / 2;
    const r = 54;
    const lineWidth = 8;
    const startAngle = Math.PI * 0.75;
    const endAngle = Math.PI * 2.25;

    // Background arc
    ctx.beginPath();
    ctx.arc(cx, cy, r, startAngle, endAngle);
    ctx.strokeStyle = '#2a2a31';
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();

    if (!hasData) return;

    // Animated fill
    const targetAngle = startAngle + (health / 100) * (endAngle - startAngle);
    const color = getHealthColor(health);

    ctx.beginPath();
    ctx.arc(cx, cy, r, startAngle, targetAngle);
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Center text
    ctx.fillStyle = color;
    ctx.font = `600 28px 'Geist', system-ui`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`${typeof health === 'number' ? health.toFixed(0) : '0'}`, cx, cy - 6);

    ctx.fillStyle = '#6E6E78';
    ctx.font = `400 11px 'Geist', system-ui`;
    ctx.fillText('HEALTH', cx, cy + 16);
  }, [health, hasData]);

  return (
    <div className="panel cognitive-mri">
      <div className="panel-header">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.2" />
          <path d="M7 3.5v3.5h3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
        </svg>
        Memory Health & Story Diagnostics
      </div>
      <div className="cognitive-mri__body">
        <div className="cognitive-mri__gauge">
          <canvas ref={canvasRef} />
          {hasData && typeof health === 'number' && typeof healthBefore === 'number' && healthBefore > 0 && (
            <div className={`cognitive-mri__delta ${health >= healthBefore ? 'metric-delta--positive' : 'metric-delta--negative'}`}>
              {health >= healthBefore ? '↑' : '↓'} {Math.abs(health - healthBefore).toFixed(0)}% delta from {healthBefore.toFixed(0)}%
            </div>
          )}
        </div>
        
        {hasData && (
          <div className="cognitive-mri__diagnostic">
            <div className="cognitive-mri__status-wrap">
              <span className="cognitive-mri__status-label">State:</span>
              <span
                className="cognitive-mri__status-badge"
                style={{
                  color: health >= 75 ? 'var(--accent-success)' : health >= 45 ? 'var(--accent-warning)' : 'var(--accent-error)',
                  borderColor: health >= 75 ? 'var(--accent-success)' : health >= 45 ? 'var(--accent-warning)' : 'var(--accent-error)',
                  borderWidth: '1px',
                  borderStyle: 'solid',
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: 'var(--text-xs)',
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 600
                }}
              >
                {health >= 75 ? 'HEALTHY' : health >= 45 ? 'WARNING' : 'CRITICAL'}
              </span>
            </div>
            <p className="cognitive-mri__reason">
              {report?.summary_narrative
                ? report.summary_narrative
                : health >= 75
                ? 'Graph is fully consolidated: zero logical contradictions, minimal redundancies, and cohesive clustering.'
                : health >= 45
                ? 'Mild cognitive fatigue: some duplicate warnings or semantic fragmentation detected.'
                : 'Critical cognitive load: high contradictions, duplicates, and unlinked orphan elements.'}
            </p>
          </div>
        )}

        <div className="cognitive-mri__story-metrics">
          <div className="cognitive-mri__story-title">Consolidation Narrative</div>
          
          <div className="cognitive-mri__story-item">
            <span className="cognitive-mri__story-label">Memory Health Target</span>
            <span className="cognitive-mri__story-value" style={{ color: 'var(--accent-success)', fontWeight: 600 }}>
              {hasData && healthBefore > 0 ? `${healthBefore.toFixed(0)}% → ${health.toFixed(0)}%` : `${health.toFixed(0)}%`}
            </span>
          </div>

          <div className="cognitive-mri__story-item">
            <span className="cognitive-mri__story-label">Redundant Merges</span>
            <span className="cognitive-mri__story-value" style={{ color: 'var(--accent-secondary)' }}>
              {metrics ? `${metrics.duplicates_merged} merged` : '0 merged'}
            </span>
          </div>

          <div className="cognitive-mri__story-item">
            <span className="cognitive-mri__story-label">Logical Conflicts Resolved</span>
            <span className="cognitive-mri__story-value" style={{ color: 'var(--accent-warning)' }}>
              {metrics ? `${metrics.contradictions_resolved} fixed` : '0 fixed'}
            </span>
          </div>

          <div className="cognitive-mri__story-item">
            <span className="cognitive-mri__story-label">Abstract Concepts Synthesized</span>
            <span className="cognitive-mri__story-value" style={{ color: 'var(--accent-primary)' }}>
              {metrics ? `${metrics.concepts_generated} created` : '0 created'}
            </span>
          </div>

          <div className="cognitive-mri__story-item">
            <span className="cognitive-mri__story-label">Active Working Nodes</span>
            <span className="cognitive-mri__story-value" style={{ color: 'var(--text-secondary)' }}>
              {metrics ? `${metrics.nodes_replayed || 0} nodes` : '0 nodes'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
