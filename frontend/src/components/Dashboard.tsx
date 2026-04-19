import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { PipelineState } from "../types";
import { useTranslation } from "../i18n";

interface Props {
  state: PipelineState;
  onRunPhase: (phase: string) => Promise<void>;
  onNewProject: () => void;
  pipelineRunning?: boolean;
  pipelineMessage?: string;
}

export default function Dashboard({ state, onRunPhase, onNewProject, pipelineRunning = false, pipelineMessage = "" }: Props) {
  const { t } = useTranslation();
  const [isRunning, setIsRunning] = useState(false);
  const [novelTitle, setNovelTitle] = useState("");
  const [cwd, setCwd] = useState("");

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const path = await invoke<string>("get_project_path");
      setCwd(path);
      const config = await invoke<any>("read_ai_config", { cwd: path });
      if (config.novel_title) {
        setNovelTitle(config.novel_title);
      }
    } catch (e) {
      console.error("Error loading config:", e);
    }
  };

  const handleGenerateTitle = async () => {
    setIsRunning(true);
    try {
      const title = await invoke<string>("generate_title", { cwd });
      setNovelTitle(title);
    } catch (e) {
      console.error("Error generating title:", e);
      alert(`Error: ${e}`);
    } finally {
      setIsRunning(false);
    }
  };

  const handleRun = async (phase: string) => {
    setIsRunning(true);
    try {
      await onRunPhase(phase);
    } catch (e) {
      console.error(e);
      alert(`Error running ${phase}: ${e}`);
    } finally {
      setIsRunning(false);
    }
  };

  const totalWords = state.chapters.reduce((sum, ch) => sum + ch.word_count, 0);
  const avgChapterScore = state.chapters.length > 0
    ? state.chapters.reduce((sum, ch) => sum + (ch.score || 0), 0) / state.chapters.length
    : 0;

  // Determine current phase step
  const currentPhase = state.phase || "none";
  const hasFoundation = state.foundation_scores && (
    state.foundation_scores.world > 0 ||
    state.foundation_scores.characters > 0 ||
    state.foundation_scores.outline > 0
  );

  return (
    <div className="dashboard">
      <header className="page-header">
        <div>
          <h1>{novelTitle || t("dashboard_title")}</h1>
          {!novelTitle && hasFoundation && (
            <button className="btn-secondary btn-small" onClick={handleGenerateTitle} disabled={isRunning}>
              {isRunning ? t("generating") : t("generate_title")}
            </button>
          )}
        </div>
        <button className="btn-secondary" onClick={onNewProject}>{t("dashboard_new_project")}</button>
      </header>

      {/* Phase Stepper - Always visible */}
      <div className="phase-stepper">
        <div className={`step ${currentPhase !== "none" ? "done" : "active"}`}>
          <span className="step-num">1</span>
          <span className="step-label">{t("step_foundation")}</span>
        </div>
        <div className="step-line" />
        <div className={`step ${currentPhase === "drafting" || currentPhase === "review" || currentPhase === "export" || currentPhase === "complete" ? "active" : ""} ${hasFoundation ? "done" : ""}`}>
          <span className="step-num">2</span>
          <span className="step-label">{t("step_drafting")}</span>
        </div>
        <div className="step-line" />
        <div className={`step ${currentPhase === "review" || currentPhase === "export" || currentPhase === "complete" ? "active" : ""} ${currentPhase === "review" || currentPhase === "export" || currentPhase === "complete" ? "done" : ""}`}>
          <span className="step-num">3</span>
          <span className="step-label">{t("step_review")}</span>
        </div>
        <div className="step-line" />
        <div className={`step ${currentPhase === "export" || currentPhase === "complete" ? "active" : ""} ${currentPhase === "export" || currentPhase === "complete" ? "done" : ""}`}>
          <span className="step-num">4</span>
          <span className="step-label">{t("step_export")}</span>
        </div>
      </div>

      {/* Action Card - Context sensitive */}
      <div className="action-card">
        {pipelineRunning ? (
          <>
            <h2>{pipelineMessage || t("running")}</h2>
            <div className="running-indicator">
              <div className="spinner"></div>
            </div>
          </>
        ) : currentPhase === "none" || currentPhase === "foundation" ? (
          <>
            <h2>{hasFoundation ? t("continue_foundation") : t("start_foundation")}</h2>
            <p>{hasFoundation ? t("foundation_in_progress") : t("foundation_not_started")}</p>
            <button className="btn-primary btn-large" onClick={() => handleRun("foundation")} disabled={isRunning}>
              {isRunning ? t("running") : (hasFoundation ? t("run_foundation") : t("start_generating"))}
            </button>
          </>
        ) : currentPhase === "drafting" ? (
          <>
            <h2>{t("drafting_phase")}</h2>
            <p>{t("chapters_written", { n: state.chapters.length })}</p>
            <button className="btn-primary btn-large" onClick={() => handleRun("drafting")} disabled={isRunning}>
              {isRunning ? t("running") : t("continue_drafting")}
            </button>
          </>
        ) : currentPhase === "review" ? (
          <>
            <h2>{t("review_phase")}</h2>
            <button className="btn-primary btn-large" onClick={() => handleRun("review")} disabled={isRunning}>
              {isRunning ? t("running") : t("continue_review")}
            </button>
          </>
        ) : currentPhase === "export" || currentPhase === "complete" ? (
          <>
            <h2>{t("export_phase")}</h2>
            <p>{t("total_words_written", { n: totalWords })}</p>
            <button className="btn-primary btn-large" onClick={() => handleRun("export")} disabled={isRunning}>
              {isRunning ? t("running") : t("export")}
            </button>
          </>
        ) : null}
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <h3>{t("phase")}</h3>
          <p className="stat-value phase">{t(currentPhase) || t("phase_not_started")}</p>
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

      {hasFoundation && (
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
    </div>
  );
}
