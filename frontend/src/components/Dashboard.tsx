import { PipelineState } from "../types";
import { useTranslation } from "../i18n";

interface Props {
  state: PipelineState;
  onRunPhase: (phase: string) => Promise<void>;
  onRunFull: () => Promise<void>;
  onNewProject: () => void;
}

export default function Dashboard({ state, onRunPhase, onRunFull, onNewProject }: Props) {
  const { t } = useTranslation();

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
        <h1>{t("dashboard_title")}</h1>
        <button className="btn-secondary" onClick={onNewProject}>{t("dashboard_new_project")}</button>
      </header>

      <div className="stats-grid">
        <div className="stat-card">
          <h3>{t("phase")}</h3>
          <p className="stat-value phase">{state.phase || t("phase_not_started")}</p>
        </div>
        <div className="stat-card">
          <h3>{t("chapters")}</h3>
          <p className="stat-value">{state.chapters.length}</p>
        </div>
        <div className="stat-card">
          <h3>{t("words")}</h3>
          <p className="stat-value">{totalWords.toLocaleString()}</p>
        </div>
        <div className="stat-card">
          <h3>{t("avg_score")}</h3>
          <p className="stat-value">{avgChapterScore.toFixed(1)}</p>
        </div>
      </div>

      {state.foundation_scores && (
        <section className="section">
          <h2>{t("foundation_scores")}</h2>
          <div className="foundation-scores">
            <div className="score-bar">
              <span>{t("world")}</span>
              <div className="bar">
                <div className="fill" style={{ width: `${state.foundation_scores.world * 10}%` }} />
              </div>
              <span className="score">{state.foundation_scores.world.toFixed(1)}</span>
            </div>
            <div className="score-bar">
              <span>{t("characters")}</span>
              <div className="bar">
                <div className="fill" style={{ width: `${state.foundation_scores.characters * 10}%` }} />
              </div>
              <span className="score">{state.foundation_scores.characters.toFixed(1)}</span>
            </div>
            <div className="score-bar">
              <span>{t("outline")}</span>
              <div className="bar">
                <div className="fill" style={{ width: `${state.foundation_scores.outline * 10}%` }} />
              </div>
              <span className="score">{state.foundation_scores.outline.toFixed(1)}</span>
            </div>
            <div className="score-bar">
              <span>{t("canon")}</span>
              <div className="bar">
                <div className="fill" style={{ width: `${state.foundation_scores.canon * 10}%` }} />
              </div>
              <span className="score">{state.foundation_scores.canon.toFixed(1)}</span>
            </div>
            <div className="score-bar">
              <span>{t("voice")}</span>
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
          <h2>{t("chapter_progress")}</h2>
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
        <h2>{t("run_pipeline")}</h2>
        <div className="action-buttons">
          {state.phase === "none" || state.phase === "foundation" ? (
            <button className="btn-primary" onClick={() => handleRun("foundation")}>
              {t("run_foundation")}
            </button>
          ) : null}
          {state.phase === "drafting" ? (
            <button className="btn-primary" onClick={() => handleRun("drafting")}>
              {t("continue_drafting")}
            </button>
          ) : null}
          {state.phase === "review" ? (
            <button className="btn-primary" onClick={() => handleRun("review")}>
              {t("continue_review")}
            </button>
          ) : null}
          {state.phase === "export" ? (
            <button className="btn-primary" onClick={() => handleRun("export")}>
              {t("export")}
            </button>
          ) : null}
          <button className="btn-secondary" onClick={handleRunAll}>
            {t("run_full_pipeline")}
          </button>
        </div>
      </section>
    </div>
  );
}
