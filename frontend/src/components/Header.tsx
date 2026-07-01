import type { SleepStatus } from '../types';
import './Header.css';

interface HeaderProps {
  status: SleepStatus;
  onDream: () => void;
  onWakeUp: () => void;
}

const STATUS_LABELS: Record<SleepStatus, string> = {
  idle: 'Awake',
  dreaming: 'Dreaming',
  complete: 'Rested',
};

export function Header({ status, onDream, onWakeUp }: HeaderProps) {
  return (
    <header className="header">
      <div className="header__brand">
        <div className="header__logo">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <circle cx="14" cy="14" r="12" stroke="var(--accent-cyan)" strokeWidth="1.5" opacity="0.4" />
            <circle cx="14" cy="14" r="7" stroke="var(--accent-cyan)" strokeWidth="1.5" />
            <circle cx="14" cy="14" r="2.5" fill="var(--accent-cyan)" />
          </svg>
        </div>
        <h1 className="header__title">ONEIROS</h1>
        <span className="header__subtitle">Cognitive Memory OS</span>
      </div>

      <div className="header__controls">
        <div className="header__status">
          <span className={`status-dot status-dot--${status}`} />
          <span className="header__status-label">{STATUS_LABELS[status]}</span>
        </div>
        <button
          className="btn-primary"
          onClick={status === 'complete' ? onWakeUp : onDream}
          disabled={status === 'dreaming'}
        >
          {status === 'dreaming' ? (
            <>
              <span className="btn-spinner" />
              Consolidating...
            </>
          ) : status === 'complete' ? (
            'Wake Up'
          ) : (
            'Dream'
          )}
        </button>
      </div>
    </header>
  );
}
