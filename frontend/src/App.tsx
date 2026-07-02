import { useState } from 'react';
import { useDreamState } from './hooks/useDreamState';
import { Header } from './components/Header';
import { AgentConsole } from './components/AgentConsole';
import { GraphViewport } from './components/GraphViewport';
import { DreamReplay } from './components/DreamReplay';
import { CognitiveMRI } from './components/CognitiveMRI';
import { ExplainPanel } from './components/ExplainPanel';
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
    chatHistory,
    clearChatHistory,
    selectedItem,
    startDream,
    wakeUp,
    sendMessage,
    setSelectedItem,
    isSending,
  } = useDreamState();

  const [playbackIndex, setPlaybackIndex] = useState<number>(-1);

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
      <Header status={status} onDream={startDream} onWakeUp={wakeUp} />

      <div className="dashboard-layout">
        {isAwake ? (
          <div className="dashboard-awake stagger">
            <div className="grid-area-console">
              <AgentConsole
                messages={chatMessages}
                historyMessages={chatHistory}
                onSend={sendMessage}
                onClearHistory={clearChatHistory}
                isLoading={isSending}
              />
            </div>

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

            <div className="grid-area-replay">
              <DreamReplay events={events} onEventClick={handleEventClick} />
            </div>
          </div>
        ) : (
          <div className="dashboard-dreaming stagger">
            <div className="dashboard-dreaming__center-graph">
              <GraphViewport
                nodes={displayNodes}
                edges={displayEdges}
                events={events}
                onNodeClick={handleNodeClick}
              />
            </div>

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

            {snapshots.length > 0 && (
              <div className="playback-bar panel">
                <div className="playback-bar__header">
                  <span>Sleep Playback</span>
                  {isPlayingBack && (
                    <span className="playback-bar__active-badge">
                      {getStageLabel(snapshots[playbackIndex].stage)}
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

      <ExplainPanel item={selectedItem} onClose={() => setSelectedItem(null)} />
    </>
  );
}

export default App;
