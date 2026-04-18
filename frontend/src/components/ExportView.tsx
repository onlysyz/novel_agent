import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";

export default function ExportView() {
  const [manuscript, setManuscript] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadManuscript();
  }, []);

  const loadManuscript = async () => {
    try {
      const text = await invoke<string>("get_manuscript");
      setManuscript(text);
    } catch (e) {
      console.error("Error loading manuscript:", e);
    }
  };

  const handleExport = async (format: string) => {
    setLoading(true);
    try {
      // For now, just copy to clipboard
      await navigator.clipboard.writeText(manuscript);
      alert(`${format.toUpperCase()} content copied to clipboard!`);
    } catch (e) {
      console.error("Error exporting:", e);
      alert(`Error: ${e}`);
    } finally {
      setLoading(false);
    }
  };

  const wordCount = manuscript.split(/\s+/).filter(w => w.length > 0).length;

  return (
    <div className="export-view">
      <header className="page-header">
        <h1>Export</h1>
      </header>

      <section className="section">
        <h2>Manuscript</h2>
        <p className="muted">{wordCount.toLocaleString()} words</p>
        <div className="export-actions">
          <button
            className="btn-primary"
            onClick={() => handleExport("markdown")}
            disabled={loading || !manuscript}
          >
            Copy as Markdown
          </button>
          <button
            className="btn-secondary"
            onClick={() => handleExport("text")}
            disabled={loading || !manuscript}
          >
            Copy as Plain Text
          </button>
        </div>
      </section>

      <section className="section">
        <h2>Preview</h2>
        <pre className="manuscript-preview">
          {manuscript.slice(0, 5000) || "No manuscript available. Run the pipeline first."}
          {manuscript.length > 5000 && "\n\n... (truncated)"}
        </pre>
      </section>
    </div>
  );
}
