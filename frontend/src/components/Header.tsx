import type { SleepStatus } from '../types';
import './Header.css';

interface HeaderProps {
  status: SleepStatus;
  onDream: () => void;
  onWakeUp: () => void;
  onToggleDev?: () => void;
}

const STATUS_LABELS: Record<SleepStatus, string> = {
  idle: 'Awake',
  dreaming: 'Dreaming',
  complete: 'Rested',
};

export function Header({ status, onDream, onWakeUp, onToggleDev }: HeaderProps) {
  const showDevMode = import.meta.env.VITE_DEV_MODE === 'true';

  return (
    <header className="header">
      <div className="header__brand">
        <div className="header__logo" aria-hidden="true">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <circle cx="14" cy="14" r="12" stroke="var(--accent-primary)" strokeWidth="1" opacity="0.3" />
            <circle cx="14" cy="14" r="7" stroke="var(--accent-primary)" strokeWidth="1.2" opacity="0.7" />
            <circle cx="14" cy="14" r="2.5" fill="var(--accent-primary)" />
          </svg>
        </div>
        <h1 className="header__title">ONEIROS</h1>
        <span className="header__subtitle">Cognitive Memory OS</span>
        <span className="header__badge">HACKATHON</span>
      </div>

      <div className="header__controls">
        <div className="header__status">
          <span className={`status-dot status-dot--${status}`} />
          <span className="header__status-label">{STATUS_LABELS[status]}</span>
        </div>
        {showDevMode && onToggleDev && (
          <button
            className="btn-icon header__dev-btn"
            onClick={onToggleDev}
            title="Toggle Developer Console"
            aria-label="Toggle Developer Console"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          </button>
        )}
        <button
          className="btn-primary"
          onClick={status === 'complete' ? onWakeUp : onDream}
          disabled={status === 'dreaming'}
        >
          {status === 'dreaming' ? (
            <>
              <span className="btn-spinner" />
              Consolidating…
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
