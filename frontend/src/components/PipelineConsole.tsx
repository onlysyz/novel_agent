import { useEffect, useRef, useState } from "react";
import { useTranslation } from "../i18n";

interface Props {
  pipelineRunning: boolean;
  pipelineLog: string[];
  pipelineMessage: string;
  onClose?: () => void;
}

export default function PipelineConsole({ pipelineRunning, pipelineLog, pipelineMessage, onClose }: Props) {
  const { t } = useTranslation();
  const logRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  // Auto-scroll to bottom when new log entries arrive
  useEffect(() => {
    if (logRef.current && isAtBottom) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [pipelineLog, isAtBottom]);

  // Track if user has scrolled up
  const handleScroll = () => {
    if (logRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = logRef.current;
      setIsAtBottom(scrollHeight - scrollTop - clientHeight < 50);
    }
  };

  return (
    <div className="pipeline-console">
      <div className="console-header">
        <span className="console-title">
          {pipelineRunning ? "⏳ " + (pipelineMessage || t("running")) : "Console"}
        </span>
        <div className="console-actions">
          {pipelineRunning && <div className="console-spinner" />}
          {onClose && <button className="console-close" onClick={onClose}>×</button>}
        </div>
      </div>
      <div className="console-body" ref={logRef} onScroll={handleScroll}>
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
    </div>
  );
}
