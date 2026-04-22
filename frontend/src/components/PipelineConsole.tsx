import { useEffect, useRef, useState, useMemo } from "react";
import { useTranslation } from "../i18n";

interface Props {
  pipelineRunning: boolean;
  pipelineLog: string[];
  pipelineMessage: string;
  onClose?: () => void;
  onCancel?: () => void;
  docked?: boolean;
}

// ── Parse a raw log line into a structured step (reused from Dashboard) ──
interface ParsedStep {
  type: "foundation" | "chapter" | "review" | "score" | "complete" | "git" | "info";
  label: string;
  detail?: string;
}

function parseLine(line: string): ParsedStep | null {
  const foundM = line.match(/^\[(\d+)\/(\d+)\]\s+(.+)/);
  if (foundM) return { type: "foundation", label: `[${foundM[1]}/${foundM[2]}] ${foundM[3]}` };

  const chapM = line.match(/^\[Chapter\s+(\d+)\/(\d+)\]/);
  if (chapM) return { type: "chapter", label: `Chapter ${chapM[1]} / ${chapM[2]}` };

  const revM = line.match(/^---\s+Chapter\s+(\d+)/);
  if (revM) return { type: "review", label: `Reviewing Chapter ${revM[1]}` };

  const subM = line.match(/^\s+\[(\d+)\/(\d+)\]\s+(.+)/);
  if (subM) return { type: "review", label: `  ↳ [${subM[1]}/${subM[2]}] ${subM[3]}` };

  const scoreM = line.match(/Score:\s*([\d.]+)/);
  if (scoreM) return { type: "score", label: line.trim() };

  if (/PHASE COMPLETE/.test(line)) return { type: "complete", label: line.trim() };

  if (/^\[Git\]/.test(line)) return { type: "git", label: line.trim() };

  if (/\d+ words/.test(line)) return { type: "info", label: line.trim() };

  return null;
}

export default function PipelineConsole({ pipelineRunning, pipelineLog, pipelineMessage, onClose, onCancel, docked = false }: Props) {
  const { t } = useTranslation();
  const logRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [showRawLog, setShowRawLog] = useState(false);
  const prevLogLengthRef = useRef(pipelineLog.length);

  // Parse log into structured steps
  const steps = useMemo(() =>
    pipelineLog.map(parseLine).filter((s): s is ParsedStep => s !== null),
    [pipelineLog]
  );

  // Track new entries count for flash animation
  const newEntriesCount = useMemo(() => {
    const prev = prevLogLengthRef.current;
    const curr = pipelineLog.length;
    prevLogLengthRef.current = curr;
    return Math.max(0, curr - prev);
  }, [pipelineLog]);

  // Flash animation: re-trigger when new entries arrive
  const [flashing, setFlashing] = useState(false);
  useEffect(() => {
    if (newEntriesCount > 0) {
      setFlashing(true);
      const id = setTimeout(() => setFlashing(false), 500);
      return () => clearTimeout(id);
    }
  }, [newEntriesCount]);

  // Auto-scroll to bottom when new log entries arrive
  useEffect(() => {
    if (logRef.current && isAtBottom) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [pipelineLog, isAtBottom]);

  const handleScroll = () => {
    if (logRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = logRef.current;
      setIsAtBottom(scrollHeight - scrollTop - clientHeight < 50);
    }
  };

  // Detect current phase from log entries or message
  const currentPhase = useMemo(() => {
    const msg = (pipelineMessage || "").toLowerCase();
    if (msg.includes("foundation")) return "foundation";
    if (msg.includes("drafting") || msg.includes("chapter")) return "drafting";
    if (msg.includes("review")) return "review";
    if (msg.includes("export")) return "export";
    // Also check log for phase complete markers
    for (const line of pipelineLog) {
      if (/FOUNDATION PHASE COMPLETE/.test(line)) return "drafting";
      if (/DRAFTING PHASE COMPLETE/.test(line)) return "review";
      if (/REVIEW PHASE COMPLETE/.test(line)) return "export";
    }
    return null;
  }, [pipelineMessage, pipelineLog]);

  const phases = [
    { key: "foundation", label: "Foundation" },
    { key: "drafting",   label: "Drafting" },
    { key: "review",    label: "Review" },
    { key: "export",     label: "Export" },
  ] as const;

  return (
    <div className={`pipeline-console${pipelineRunning ? " pipeline-running" : ""}${docked ? " pipeline-console--docked" : ""}`}>
      <div className="console-header">
        <span className="console-title">
          {pipelineRunning ? "⏳ " + (pipelineMessage || t("running")) : "Console"}
        </span>
        <div className="console-actions">
          {pipelineRunning && <div className="console-spinner" />}
          {pipelineRunning && (
            <button
              className="console-cancel"
              onClick={onCancel}
              title={t("cancel")}
            >
              ✕
            </button>
          )}
          <button className="log-toggle" onClick={() => setShowRawLog(v => !v)}>
            {showRawLog ? "Steps" : "Raw"}
          </button>
          {onClose && <button className="console-close" onClick={onClose}>×</button>}
        </div>
      </div>

      {/* Phase Stepper */}
      {currentPhase && (
        <div className="mini-stepper">
          {phases.map((phase, i) => (
            <div key={phase.key} className="mini-step-wrapper">
              <div className={`mini-step ${currentPhase === phase.key ? "active" : ""} ${phases.findIndex(p => p.key === currentPhase) > i ? "done" : ""}`}>
                <span className="mini-step-dot" />
                <span className="mini-step-label">{phase.label}</span>
              </div>
              {i < phases.length - 1 && <div className={`mini-step-line ${phases.findIndex(p => p.key === currentPhase) > i ? "done" : ""}`} />}
            </div>
          ))}
        </div>
      )}

      {showRawLog ? (
        <div className={`console-body${flashing ? " log-flash" : ""}`} key={showRawLog ? "raw" : "steps"} ref={logRef} onScroll={handleScroll}>
          {pipelineLog.map((line, i) => (
            <div key={i} className={`console-line${line.startsWith("[err]") ? " console-err" : ""}`}>
              {line}
            </div>
          ))}
          {pipelineRunning && (
            <div className="console-line console-cursor">
              <span className="cursor-blink">▌</span>
            </div>
          )}
          {!pipelineRunning && pipelineLog.length === 0 && (
            <div className="console-line console-info">{t("waiting_for_output")}</div>
          )}
        </div>
      ) : (
        <div className={`console-body progress-steps${flashing ? " log-flash" : ""}`} key={showRawLog ? "raw" : "steps"} ref={logRef} onScroll={handleScroll}>
          {steps.map((step, i) => (
            <div key={i} className={`progress-step step-${step.type}`} style={{ animationDelay: `${i * 25}ms` }}>
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
          {!pipelineRunning && steps.length === 0 && pipelineLog.length === 0 && (
            <div className="console-line console-info">{t("waiting_for_output")}</div>
          )}
          {!pipelineRunning && steps.length === 0 && pipelineLog.length > 0 && (
            <div className="console-line console-info">No structured steps parsed — click Raw to see raw log</div>
          )}
        </div>
      )}
    </div>
  );
}
