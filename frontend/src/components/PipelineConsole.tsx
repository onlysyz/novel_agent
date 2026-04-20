import { useEffect, useRef } from "react";
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

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [pipelineLog]);

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
      <div className="console-body" ref={logRef}>
        {pipelineLog.map((line, i) => (
          <div key={i} className={`console-line${line.startsWith("[err]") ? " console-err" : ""}`}>
            {line}
          </div>
        ))}
        {pipelineRunning && pipelineLog.length === 0 && (
          <div className="console-line console-info">{t("waiting_for_output")}</div>
        )}
      </div>
    </div>
  );
}
