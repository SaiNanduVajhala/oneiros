import { useState, useRef, useEffect } from 'react';
import type { ChatMessage } from '../types';
import './AgentConsole.css';

interface AgentConsoleProps {
  messages: ChatMessage[];
  onSend: (msg: string) => void;
}

export function AgentConsole({ messages, onSend }: AgentConsoleProps) {
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    onSend(input.trim());
    setInput('');
  };

  return (
    <div className="panel agent-console">
      <div className="panel-header">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <rect x="1" y="3" width="12" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.2" />
          <line x1="3" y1="6.5" x2="8" y2="6.5" stroke="currentColor" strokeWidth="1.2" />
          <line x1="3" y1="9" x2="6" y2="9" stroke="currentColor" strokeWidth="1.2" />
        </svg>
        Agent Console
      </div>
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
      </div>
      <form className="chat-input-wrap" onSubmit={handleSubmit}>
        <input
          className="chat-input"
          type="text"
          placeholder="Ask Oneiros..."
          value={input}
          onChange={e => setInput(e.target.value)}
        />
        <button className="btn-primary" type="submit" style={{ padding: '10px 16px' }}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M2 8h12M10 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </form>
    </div>
  );
}
