import { useState } from 'react';
import { useDreamState } from './hooks/useDreamState';
import { Header } from './components/Header';
import { AgentConsole } from './components/AgentConsole';
import { GraphViewport } from './components/GraphViewport';
import { DreamReplay } from './components/DreamReplay';
import { CognitiveMRI } from './components/CognitiveMRI';
import { ExplainPanel } from './components/ExplainPanel';
import { ShaderBackground } from './components/ShaderBackground';
import './App.css';

function App() {
  const {
    status,
    events,
    report,
    metrics,
    graphNodes,
    graphEdges,
    snapshots,
    chatMessages,
    selectedItem,
    startDream,
    wakeUp,
    sendMessage,
    setSelectedItem,
  } = useDreamState();

  // Playback index tracking (-1 = current/live view, >= 0 corresponds to snapshots array index)
  const [playbackIndex, setPlaybackIndex] = useState<number>(-1);

  // Determine active graph elements to display
  const isPlayingBack = playbackIndex >= 0 && playbackIndex < snapshots.length;
  const currentSnapshot = isPlayingBack ? snapshots[playbackIndex] : null;

  const displayNodes = currentSnapshot ? currentSnapshot.nodes : graphNodes;
  const displayEdges = currentSnapshot ? currentSnapshot.edges : graphEdges;
  const displayMetrics = currentSnapshot?.metrics ? currentSnapshot.metrics : metrics;

  const handleEventClick = (event: any) => {
    setSelectedItem({ type: 'event', data: event });
  };

  const handleNodeClick = (node: any) => {
    setSelectedItem({ type: 'node', data: node });
  };

  // Human readable stage labels for playback scrubbing
  const getStageLabel = (stage: string) => {
    if (stage === 'before') return 'Start';
    if (stage === 'N1_Replay') return 'N1 Replay';
    if (stage === 'N2_Consolidation') return 'N2 Consolidate';
    if (stage === 'N3_Pruning') return 'N3 Prune';
    if (stage === 'REM_Dream') return 'REM Dream';
    if (stage === 'after') return 'Complete';
    return stage;
  };

  const isAwake = status === 'idle';

  return (
    <>
      {/* 3D Shader Background Field */}
      <ShaderBackground />

      {/* Shared Header top bar */}
      <Header status={status} onDream={startDream} onWakeUp={wakeUp} />

      {/* Expandable Sidebar (Only visible in Awake state for desktop navigation) */}
      {isAwake && (
        <aside className="sidebar">
          <div className="sidebar__brand-area">
            <span className="sidebar__brand-title">Oneiros OS</span>
            <div className="sidebar__brand-sub">Active Session</div>
          </div>
          <nav className="sidebar__nav">
            <div className="sidebar__item sidebar__item--active">
              <span className="material-symbols-outlined sidebar__item-icon">forum</span>
              <span className="sidebar__item-label">Wake Agent</span>
            </div>
            <div className="sidebar__item">
              <span className="material-symbols-outlined sidebar__item-icon">hub</span>
              <span className="sidebar__item-label">Memory Graph</span>
            </div>
            <div className="sidebar__item">
              <span className="material-symbols-outlined sidebar__item-icon">waves</span>
              <span className="sidebar__item-label">Cognitive Stream</span>
            </div>
            <div className="sidebar__item">
              <span className="material-symbols-outlined sidebar__item-icon">visibility</span>
              <span className="sidebar__item-label">Inspector</span>
            </div>
          </nav>
          <div className="sidebar__footer">
            <button 
              className="synapse-btn btn-primary" 
              style={{ width: '100%', padding: '8px', fontSize: '12px' }}
              onClick={startDream}
            >
              Initiate REM
            </button>
          </div>
        </aside>
      )}

      {/* Main Workspace Layout */}
      <div className="dashboard-layout">
        {isAwake ? (
          /* Awake State Dashboard Layout */
          <div className="dashboard-awake">
            {/* Panel 1: Agent Chat Console */}
            <div className="grid-area-console">
              <AgentConsole messages={chatMessages} onSend={sendMessage} />
            </div>

            {/* Panel 2: Center 3D Graph Interaction Area */}
            <div className="dashboard-awake__center">
              <div className="dashboard-awake__center-graph">
                <GraphViewport
                  nodes={displayNodes}
                  edges={displayEdges}
                  events={events}
                  onNodeClick={handleNodeClick}
                />
              </div>
            </div>

            {/* Panel 3: Live Cognitive Stream timeline */}
            <div className="grid-area-replay">
              <DreamReplay events={events} onEventClick={handleEventClick} />
            </div>
          </div>
        ) : (
          /* Dreaming State Dashboard Layout */
          <div className="dashboard-dreaming">
            <div className="dashboard-dreaming__center-graph">
              <GraphViewport
                nodes={displayNodes}
                edges={displayEdges}
                events={events}
                onNodeClick={handleNodeClick}
              />
            </div>

            {/* Left Replay / Right metrics dashboard */}
            <div className="grid-area-replay">
              <DreamReplay events={events} onEventClick={handleEventClick} />
            </div>

            <div className="grid-area-mri">
              <CognitiveMRI
                metrics={displayMetrics}
                report={report}
                healthBefore={report ? report.memory_health_before : 0}
              />
            </div>

            {/* Playback Scrubber (Bottom panel) */}
            {snapshots.length > 0 && (
              <div className="playback-bar panel">
                <div className="playback-bar__header">
                  <span>Sleep Playback Scrubber</span>
                  {isPlayingBack && (
                    <span className="playback-bar__active-badge">
                      Scrubbing: {getStageLabel(snapshots[playbackIndex].stage)}
                    </span>
                  )}
                </div>
                <div className="playback-bar__controls">
                  <input
                    type="range"
                    min="-1"
                    max={snapshots.length - 1}
                    value={playbackIndex}
                    onChange={e => setPlaybackIndex(parseInt(e.target.value))}
                    className="playback-slider"
                  />
                  <div className="playback-ticks">
                    <span
                      className={`playback-tick ${playbackIndex === -1 ? 'active' : ''}`}
                      onClick={() => setPlaybackIndex(-1)}
                    >
                      Live
                    </span>
                    {snapshots.map((s, idx) => (
                      <span
                        key={idx}
                        className={`playback-tick ${playbackIndex === idx ? 'active' : ''}`}
                        onClick={() => setPlaybackIndex(idx)}
                      >
                        {getStageLabel(s.stage)}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Floating Explain Panel overlay */}
      <ExplainPanel item={selectedItem} onClose={() => setSelectedItem(null)} />

      {/* Unified Footer */}
      <footer className="footer">
        <nav className="footer__nav">
          <a href="#" className="footer__link">Replay</a>
          <a href="#" className="footer__link">Consolidation</a>
          <a href="#" className="footer__link">Pruning</a>
          <a href="#" className="footer__link">REM</a>
        </nav>
        <div className="footer__copyright">
          © 2124 Cognitive Synthetics
        </div>
      </footer>
    </>
  );
}

export default App;
