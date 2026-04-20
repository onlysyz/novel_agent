import { useState, useEffect, useRef, useMemo } from "react";
import { invoke } from "@tauri-apps/api/core";
import { PipelineState } from "../types";
import { useTranslation } from "../i18n";

interface Props {
  state: PipelineState;
  outputDir: string;
  onRunPhase: (phase: string) => Promise<void>;
  onNewProject: () => void;
  pipelineRunning?: boolean;
  pipelineMessage?: string;
  pipelineLog?: string[];
}

// ── Parse a raw log line into a structured step (or null if uninteresting) ──
interface ParsedStep {
  type: "foundation" | "chapter" | "review" | "score" | "complete" | "git" | "info";
  label: string;
  detail?: string;
}

function parseLine(line: string): ParsedStep | null {
  // [1/5] World Bible...
  const foundM = line.match(/^\[(\d+)\/(\d+)\]\s+(.+)/);
  if (foundM) return { type: "foundation", label: `[${foundM[1]}/${foundM[2]}] ${foundM[3]}` };

  // [Chapter 5/100]
  const chapM = line.match(/^\[Chapter\s+(\d+)\/(\d+)\]/);
  if (chapM) return { type: "chapter", label: `Chapter ${chapM[1]} / ${chapM[2]}` };

  // --- Chapter 05 ---  (review phase)
  const revM = line.match(/^---\s+Chapter\s+(\d+)/);
  if (revM) return { type: "review", label: `Reviewing Chapter ${revM[1]}` };

  // [1/3] Adversarial Edit... / [2/3] ... / [3/3] ...
  const subM = line.match(/^\s+\[(\d+)\/(\d+)\]\s+(.+)/);
  if (subM) return { type: "review", label: `  ↳ [${subM[1]}/${subM[2]}] ${subM[3]}` };

  // Score: 8.0, Iterations: 2
  const scoreM = line.match(/Score:\s*([\d.]+)/);
  if (scoreM) return { type: "score", label: line.trim() };

  // FOUNDATION PHASE COMPLETE / DRAFTING PHASE COMPLETE ...
  if (/PHASE COMPLETE/.test(line)) return { type: "complete", label: line.trim() };

  // [Git]
  if (/^\[Git\]/.test(line)) return { type: "git", label: line.trim() };

  // 3200 words, score: 7.8, time: 45.2s
  if (/\d+ words/.test(line)) return { type: "info", label: line.trim() };

  return null;
}

export default function Dashboard({
  state, outputDir, onRunPhase, onNewProject,
  pipelineRunning = false, pipelineMessage = "", pipelineLog = [],
}: Props) {
  const { t } = useTranslation();
  const [isRunningTitle, setIsRunningTitle] = useState(false);
  const [novelTitle, setNovelTitle] = useState("");
  const [outputDirLoaded, setOutputDirLoaded] = useState(false);
  const [showFullLog, setShowFullLog] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);
  const stepsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (outputDir) { setOutputDirLoaded(true); loadTitle(); }
  }, [outputDir]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
    if (stepsRef.current) stepsRef.current.scrollTop = stepsRef.current.scrollHeight;
  }, [pipelineLog]);

  const loadTitle = async () => {
    try {
      const config = await invoke<any>("read_ai_config", { outputDir });
      if (config.novel_title) setNovelTitle(config.novel_title);
    } catch (e) { console.error("Error loading config:", e); }
  };

  const handleGenerateTitle = async () => {
    setIsRunningTitle(true);
    try {
      const title = await invoke<string>("generate_title", { outputDir });
      setNovelTitle(title);
    } catch (e) { alert(`Error: ${e}`); }
    finally { setIsRunningTitle(false); }
  };

  const handleRun = async (phase: string) => {
    alert(`点击了handleRun: ${phase}, outputDir=${outputDir}`);
    try { await onRunPhase(phase); }
    catch (e) { alert(`Error running ${phase}: ${e}`); }
  };

  // Parse log into structured steps (only meaningful lines)
  const steps = useMemo(() =>
    pipelineLog.map(parseLine).filter((s): s is ParsedStep => s !== null),
    [pipelineLog]
  );

  // Most recent meaningful step label for the action card summary
  const currentStep = steps.length > 0 ? steps[steps.length - 1].label : "";

  const totalWords = state.chapters.reduce((sum, ch) => sum + ch.word_count, 0);
  const avgChapterScore = state.chapters.length > 0
    ? state.chapters.reduce((sum, ch) => sum + (ch.score || 0), 0) / state.chapters.length : 0;
  const currentPhase = state.phase || "none";
  const hasFoundation = state.foundation_scores &&
    (state.foundation_scores.world > 0 || state.foundation_scores.characters > 0 || state.foundation_scores.outline > 0);

  console.log("[Dashboard] render, outputDir:", outputDir, "outputDirLoaded:", outputDirLoaded, "pipelineRunning:", pipelineRunning);

  return (
    <div className="dashboard">
      <header className="page-header">
        <div>
          <h1>{novelTitle || t("dashboard_title")}</h1>
          {!novelTitle && hasFoundation && (
            <button className="btn-secondary btn-small" onClick={handleGenerateTitle} disabled={isRunningTitle}>
              {isRunningTitle ? t("generating") : t("generate_title")}
            </button>
          )}
        </div>
        <button className="btn-secondary" onClick={onNewProject}>{t("dashboard_new_project")}</button>
      </header>

      {/* Phase Stepper */}
      <div className="phase-stepper">
        <div className={`step ${currentPhase !== "none" ? "done" : "active"}`}>
          <span className="step-num">1</span><span className="step-label">{t("step_foundation")}</span>
        </div>
        <div className="step-line" />
        <div className={`step ${currentPhase === "drafting" || currentPhase === "review" || currentPhase === "export" || currentPhase === "complete" ? "active" : ""} ${hasFoundation ? "done" : ""}`}>
          <span className="step-num">2</span><span className="step-label">{t("step_drafting")}</span>
        </div>
        <div className="step-line" />
        <div className={`step ${currentPhase === "review" || currentPhase === "export" || currentPhase === "complete" ? "active" : ""} ${currentPhase === "review" || currentPhase === "export" || currentPhase === "complete" ? "done" : ""}`}>
          <span className="step-num">3</span><span className="step-label">{t("step_review")}</span>
        </div>
        <div className="step-line" />
        <div className={`step ${currentPhase === "export" || currentPhase === "complete" ? "active" : ""} ${currentPhase === "export" || currentPhase === "complete" ? "done" : ""}`}>
          <span className="step-num">4</span><span className="step-label">{t("step_export")}</span>
        </div>
      </div>

      {/* Action Card */}
      <div className="action-card">
        {/* TEST BUTTON - remove after testing */}
        <button onClick={() => { document.title = "TEST CLICKED"; console.log("TEST CLICKED"); }} style={{background: "red", color: "white", padding: "20px", margin: "20px", display: "block", zIndex: 9999, position: "relative"}}>
          测试按钮 - 点击改变标题
        </button>
        {pipelineRunning ? (
          <>
            <h2>{pipelineMessage || t("running")}</h2>
            {currentStep && <p className="current-step">{currentStep}</p>}
            <div className="running-indicator"><div className="spinner"></div></div>
          </>
        ) : currentPhase === "none" || currentPhase === "foundation" ? (
          <>
            <h2>{hasFoundation ? t("continue_foundation") : t("start_foundation")}</h2>
            <p>{hasFoundation ? t("foundation_in_progress") : t("foundation_not_started")}</p>
            <button className="btn-primary btn-large" onClick={() => handleRun("foundation")}>
              {pipelineRunning ? t("running") : hasFoundation ? t("run_foundation") : t("start_generating")}
            </button>
          </>
        ) : currentPhase === "drafting" ? (
          <>
            <h2>{t("drafting_phase")}</h2>
            <p>{t("chapters_written", { n: state.chapters.length })}</p>
            <button className="btn-primary btn-large" onClick={() => handleRun("drafting")} disabled={pipelineRunning}>
              {pipelineRunning ? t("running") : t("continue_drafting")}
            </button>
          </>
        ) : currentPhase === "review" ? (
          <>
            <h2>{t("review_phase")}</h2>
            <button className="btn-primary btn-large" onClick={() => handleRun("review")} disabled={pipelineRunning}>
              {pipelineRunning ? t("running") : t("continue_review")}
            </button>
          </>
        ) : currentPhase === "export" || currentPhase === "complete" ? (
          <>
            <h2>{t("export_phase")}</h2>
            <p>{t("total_words_written", { n: totalWords })}</p>
            <button className="btn-primary btn-large" onClick={() => handleRun("export")} disabled={pipelineRunning}>
              {pipelineRunning ? t("running") : t("export")}
            </button>
          </>
        ) : null}
      </div>

      {/* Progress Panel – visible whenever there are log lines */}
      {pipelineLog.length > 0 && (
        <div className="progress-panel">
          <div className="progress-panel-header">
            <span className="progress-panel-title">
              {pipelineRunning ? "⏳ Running…" : "✓ Last run"}
            </span>
            <div className="progress-panel-actions">
              <button className="log-toggle" onClick={() => setShowFullLog(v => !v)}>
                {showFullLog ? "Hide raw log" : "Raw log"}
              </button>
            </div>
          </div>

          {/* Structured steps */}
          <div className="progress-steps" ref={stepsRef}>
            {steps.map((step, i) => (
              <div key={i} className={`progress-step step-${step.type}`}>
                {step.type === "foundation" && <span className="step-icon">⚙</span>}
                {step.type === "chapter"    && <span className="step-icon">✍</span>}
                {step.type === "review"     && <span className="step-icon">🔍</span>}
                {step.type === "score"      && <span className="step-icon">★</span>}
                {step.type === "complete"   && <span className="step-icon">✅</span>}
                {step.type === "git"        && <span className="step-icon">💾</span>}
                {step.type === "info"       && <span className="step-icon">ℹ</span>}
                <span className="step-text">{step.label}</span>
              </div>
            ))}
            {pipelineRunning && <div className="step-cursor">▌</div>}
          </div>

          {/* Raw log (collapsible) */}
          {showFullLog && (
            <div className="raw-log" ref={logRef}>
              {pipelineLog.map((line, i) => (
                <div key={i} className={`log-line${line.startsWith("[err]") ? " log-err" : ""}`}>{line}</div>
              ))}
            </div>
          )}
        </div>
      )}

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
            {(["world", "characters", "outline", "canon", "voice"] as const).map((key) => (
              <div className="score-bar" key={key}>
                <span>{t(key)}</span>
                <div className="bar"><div className="fill" style={{ width: `${state.foundation_scores[key] * 10}%` }} /></div>
                <span className="score">{state.foundation_scores[key].toFixed(1)}</span>
              </div>
            ))}
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
