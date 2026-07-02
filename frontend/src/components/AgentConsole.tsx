import { useState, useRef, useEffect } from 'react';
import type { ChatMessage } from '../types';
import './AgentConsole.css';

interface AgentConsoleProps {
  messages: ChatMessage[];
  historyMessages?: ChatMessage[];
  onSend: (msg: string) => void;
  onClearHistory?: () => void;
  isLoading?: boolean;
}

export function AgentConsole({
  messages,
  historyMessages = [],
  onSend,
  onClearHistory,
  isLoading = false,
}: AgentConsoleProps) {
  const [activeTab, setActiveTab] = useState<'console' | 'history'>('console');
  const [searchQuery, setSearchQuery] = useState('');
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (scrollRef.current) {
        scrollRef.current.scrollTo({
          top: scrollRef.current.scrollHeight,
          behavior: 'smooth'
        });
      }
    }, 80);
    return () => clearTimeout(timer);
  }, [messages, isLoading, activeTab]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    onSend(input.trim());
    setInput('');
  };

  const filteredHistory = historyMessages.filter(msg =>
    msg.content.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="panel agent-console">
      <div className="panel-header agent-console__header">
        <div className="agent-console__tabs">
          <button
            className={`agent-console__tab-btn ${activeTab === 'console' ? 'agent-console__tab-btn--active' : ''}`}
            onClick={() => setActiveTab('console')}
          >
            Console
          </button>
          <button
            className={`agent-console__tab-btn ${activeTab === 'history' ? 'agent-console__tab-btn--active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            History
          </button>
        </div>
      </div>

      {activeTab === 'console' ? (
        <>
          <div className="agent-console__messages" ref={scrollRef}>
            {messages.length === 0 && (
              <div className="agent-console__empty">
                <p>Ask Oneiros anything to build memories.</p>
                <p className="agent-console__hint">Memories accumulate → cognitive fatigue → sleep consolidation</p>
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`agent-console__msg agent-console__msg--${msg.role}`}>
                <span className="agent-console__role">{msg.role === 'user' ? 'You' : 'Oneiros'}</span>
                <p>{msg.content}</p>
              </div>
            ))}
            {isLoading && (
              <div className="agent-console__msg agent-console__msg--assistant agent-console__msg--loading">
                <span className="agent-console__role">Oneiros</span>
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            )}
          </div>
          <form className="chat-input-wrap" onSubmit={handleSubmit}>
            <input
              className="chat-input"
              type="text"
              placeholder={isLoading ? "Oneiros is thinking..." : "Ask Oneiros..."}
              value={input}
              onChange={e => setInput(e.target.value)}
              disabled={isLoading}
            />
            <button
              className="btn-primary"
              type="submit"
              style={{ padding: '10px 16px' }}
              disabled={isLoading || !input.trim()}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M2 8h12M10 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </form>
        </>
      ) : (
        <>
          <div className="agent-console__history-controls">
            <input
              className="chat-input agent-console__search-input"
              type="text"
              placeholder="Search past logs..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
            {onClearHistory && historyMessages.length > 0 && (
              <button className="btn-danger" onClick={onClearHistory} style={{ padding: '8px 12px', fontSize: '11px', whiteSpace: 'nowrap' }}>
                Clear All
              </button>
            )}
          </div>
          <div className="agent-console__messages" ref={scrollRef}>
            {filteredHistory.length === 0 ? (
              <div className="agent-console__empty">
                <p>{searchQuery ? "No matching messages found." : "No saved chat history."}</p>
              </div>
            ) : (
              filteredHistory.map((msg, i) => (
                <div key={i} className={`agent-console__msg agent-console__msg--${msg.role}`}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="agent-console__role">{msg.role === 'user' ? 'You' : 'Oneiros'}</span>
                    {msg.timestamp && (
                      <span className="agent-console__time" style={{ fontSize: '9px', color: 'var(--text-tertiary)' }}>
                        {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    )}
                  </div>
                  <p>{msg.content}</p>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
