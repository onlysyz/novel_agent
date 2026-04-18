import { PipelineState } from "../types";

interface Props {
  state: PipelineState;
  onRunPhase: (phase: string) => Promise<void>;
  onRunFull: () => Promise<void>;
  onNewProject: () => void;
}

export default function Dashboard({ state, onRunPhase, onRunFull, onNewProject }: Props) {
  const handleRun = async (phase: string) => {
    try {
      await onRunPhase(phase);
    } catch (e) {
      console.error(e);
      alert(`Error running ${phase}: ${e}`);
    }
  };

  const handleRunAll = async () => {
    try {
      await onRunFull();
    } catch (e) {
      console.error(e);
      alert(`Error: ${e}`);
    }
  };

  const totalWords = state.chapters.reduce((sum, ch) => sum + ch.word_count, 0);
  const avgChapterScore = state.chapters.length > 0
    ? state.chapters.reduce((sum, ch) => sum + (ch.score || 0), 0) / state.chapters.length
    : 0;

  return (
    <div className="dashboard">
      <header className="page-header">
        <h1>Dashboard</h1>
        <button className="btn-secondary" onClick={onNewProject}>New Project</button>
      </header>

      <div className="stats-grid">
        <div className="stat-card">
          <h3>Phase</h3>
          <p className="stat-value phase">{state.phase || "Not started"}</p>
        </div>
        <div className="stat-card">
          <h3>Chapters</h3>
          <p className="stat-value">{state.chapters.length}</p>
        </div>
        <div className="stat-card">
          <h3>Words</h3>
          <p className="stat-value">{totalWords.toLocaleString()}</p>
        </div>
        <div className="stat-card">
          <h3>Avg Score</h3>
          <p className="stat-value">{avgChapterScore.toFixed(1)}</p>
        </div>
      </div>

      {state.foundation_scores && (
        <section className="section">
          <h2>Foundation Scores</h2>
          <div className="foundation-scores">
            <div className="score-bar">
              <span>World</span>
              <div className="bar">
                <div className="fill" style={{ width: `${state.foundation_scores.world * 10}%` }} />
              </div>
              <span className="score">{state.foundation_scores.world.toFixed(1)}</span>
            </div>
            <div className="score-bar">
              <span>Characters</span>
              <div className="bar">
                <div className="fill" style={{ width: `${state.foundation_scores.characters * 10}%` }} />
              </div>
              <span className="score">{state.foundation_scores.characters.toFixed(1)}</span>
            </div>
            <div className="score-bar">
              <span>Outline</span>
              <div className="bar">
                <div className="fill" style={{ width: `${state.foundation_scores.outline * 10}%` }} />
              </div>
              <span className="score">{state.foundation_scores.outline.toFixed(1)}</span>
            </div>
            <div className="score-bar">
              <span>Canon</span>
              <div className="bar">
                <div className="fill" style={{ width: `${state.foundation_scores.canon * 10}%` }} />
              </div>
              <span className="score">{state.foundation_scores.canon.toFixed(1)}</span>
            </div>
            <div className="score-bar">
              <span>Voice</span>
              <div className="bar">
                <div className="fill" style={{ width: `${state.foundation_scores.voice * 10}%` }} />
              </div>
              <span className="score">{state.foundation_scores.voice.toFixed(1)}</span>
            </div>
          </div>
        </section>
      )}

      {state.chapters.length > 0 && (
        <section className="section">
          <h2>Chapter Progress</h2>
          <div className="chapter-progress">
            {state.chapters.map((ch) => (
              <div key={ch.number} className={`chapter-dot ${ch.score ? 'done' : 'pending'}`}>
                <span className="ch-num">{ch.number}</span>
                {ch.score && <span className="ch-score">{ch.score.toFixed(0)}</span>}
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="section actions">
        <h2>Run Pipeline</h2>
        <div className="action-buttons">
          {state.phase === "none" || state.phase === "foundation" ? (
            <button className="btn-primary" onClick={() => handleRun("foundation")}>
              Run Foundation
            </button>
          ) : null}
          {state.phase === "drafting" ? (
            <button className="btn-primary" onClick={() => handleRun("drafting")}>
              Continue Drafting
            </button>
          ) : null}
          {state.phase === "review" ? (
            <button className="btn-primary" onClick={() => handleRun("review")}>
              Continue Review
            </button>
          ) : null}
          {state.phase === "export" ? (
            <button className="btn-primary" onClick={() => handleRun("export")}>
              Export
            </button>
          ) : null}
          <button className="btn-secondary" onClick={handleRunAll}>
            Run Full Pipeline
          </button>
        </div>
      </section>
    </div>
  );
}
