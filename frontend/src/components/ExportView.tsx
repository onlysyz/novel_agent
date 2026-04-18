import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";

interface Props {
  cwd: string;
}

interface ExportFile {
  name: string;
  format: string;
  size_bytes: number;
  modified: string;
  path: string;
}

export default function ExportView({ cwd }: Props) {
  const [manuscript, setManuscript] = useState("");
  const [exportFiles, setExportFiles] = useState<ExportFile[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadManuscript();
    loadExportFiles();
  }, [cwd]);

  const loadManuscript = async () => {
    try {
      const text = await invoke<string>("get_manuscript", { cwd });
      setManuscript(text);
    } catch (e) {
      console.error("Error loading manuscript:", e);
    }
  };

  const loadExportFiles = async () => {
    try {
      const files = await invoke<ExportFile[]>("list_exports", { cwd });
      setExportFiles(files);
    } catch (e) {
      console.error("Error loading export files:", e);
    }
  };

  const handleOpen = async (file: ExportFile) => {
    try {
      await invoke("open_export_file", { cwd, filename: file.name });
    } catch (e) {
      console.error("Error opening file:", e);
      alert(`Error opening file: ${e}`);
    }
  };

  const handleDownload = async (file: ExportFile) => {
    setLoading(true);
    try {
      const data = await invoke<string>("get_export_file", { cwd, filename: file.name });
      const mimeTypes: Record<string, string> = {
        text: "text/plain",
        epub: "application/epub+zip",
        pdf: "application/pdf",
        image: "image/png",
      };
      const mime = mimeTypes[file.format] || "application/octet-stream";
      const isText = file.format === "text";

      let blob: Blob;
      if (isText) {
        blob = new Blob([data], { type: mime });
      } else {
        const binary = atob(data);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
          bytes[i] = binary.charCodeAt(i);
        }
        blob = new Blob([bytes], { type: mime });
      }

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = file.name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Error downloading file:", e);
      alert(`Error: ${e}`);
    } finally {
      setLoading(false);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatLabel = (name: string) => {
    if (name.includes("manuscript.txt")) return "Manuscript (TXT)";
    if (name.includes("manuscript.epub")) return "Manuscript (ePub)";
    if (name.includes("cover")) return "Book Cover";
    if (name.includes("manuscript.pdf")) return "Manuscript (PDF)";
    return name;
  };

  const wordCount = manuscript.split(/\s+/).filter(w => w.length > 0).length;

  return (
    <div className="export-view">
      <header className="page-header">
        <h1>Export</h1>
        <button className="btn-secondary" onClick={loadExportFiles} disabled={loading}>
          Refresh
        </button>
      </header>

      <section className="section">
        <h2>Available Files</h2>
        {exportFiles.length === 0 ? (
          <p className="empty-state">No export files yet. Run the export phase first.</p>
        ) : (
          <div className="export-files-list">
            {exportFiles.map((file) => (
              <div key={file.name} className="export-file-item">
                <div className="export-file-info">
                  <span className="export-file-name">{formatLabel(file.name)}</span>
                  <span className="export-file-meta">
                    {file.format.toUpperCase()} · {formatSize(file.size_bytes)} · {file.modified}
                  </span>
                </div>
                <div className="export-file-actions">
                  <button
                    className="btn-secondary"
                    onClick={() => handleOpen(file)}
                  >
                    Open
                  </button>
                  <button
                    className="btn-primary"
                    onClick={() => handleDownload(file)}
                    disabled={loading}
                  >
                    Download
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <h2>Quick Copy</h2>
        <p className="muted">{wordCount.toLocaleString()} words in manuscript</p>
        <div className="export-actions">
          <button
            className="btn-secondary"
            onClick={() => {
              navigator.clipboard.writeText(manuscript);
              alert("Manuscript copied as Markdown!");
            }}
            disabled={!manuscript}
          >
            Copy Manuscript
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
