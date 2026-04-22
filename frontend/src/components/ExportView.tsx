import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useTranslation } from "../i18n";
import { useToast } from "./Toast";

interface Props {
  outputDir: string;
}

interface ExportFile {
  name: string;
  format: string;
  size_bytes: number;
  modified: string;
  path: string;
}

export default function ExportView({ outputDir }: Props) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const [manuscript, setManuscript] = useState("");
  const [exportFiles, setExportFiles] = useState<ExportFile[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadManuscript();
    loadExportFiles();
  }, [outputDir]);

  const loadManuscript = async () => {
    try {
      const text = await invoke<string>("get_manuscript", { outputDir });
      setManuscript(text);
    } catch (e) {
      console.error("Error loading manuscript:", e);
    }
  };

  const loadExportFiles = async () => {
    try {
      const files = await invoke<ExportFile[]>("list_exports", { outputDir });
      setExportFiles(files);
    } catch (e) {
      console.error("Error loading export files:", e);
    }
  };

  const handleOpen = async (file: ExportFile) => {
    try {
      await invoke("open_export_file", { outputDir, filename: file.name });
    } catch (e) {
      console.error("Error opening file:", e);
      showToast(`Error opening file: ${e}`, "error");
    }
  };

  const handleDownload = async (file: ExportFile) => {
    setLoading(true);
    try {
      const data = await invoke<string>("get_export_file", { outputDir, filename: file.name });
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
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
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
      showToast(`Error: ${e}`, "error");
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
    if (name.includes("manuscript.txt")) return `${t("nav_export")} (TXT)`;
    if (name.includes("manuscript.epub")) return `${t("nav_export")} (ePub)`;
    if (name.includes("cover")) return "Book Cover";
    if (name.includes("manuscript.pdf")) return `${t("nav_export")} (PDF)`;
    return name;
  };

  const wordCount = manuscript.split(/\s+/).filter(w => w.length > 0).length;

  return (
    <div className="export-view">
      <header className="page-header">
        <h1>{t("export_title")}</h1>
        <button className="btn-secondary" onClick={loadExportFiles} disabled={loading}>
          {t("refresh")}
        </button>
      </header>

      <section className="section">
        <h2>{t("available_files")}</h2>
        {exportFiles.length === 0 ? (
          <p className="empty-state">{t("no_export_files_yet")}</p>
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
                  <button className="btn-secondary" onClick={() => handleOpen(file)}>{t("open")}</button>
                  <button className="btn-primary" onClick={() => handleDownload(file)} disabled={loading}>
                    {t("download")}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="section">
        <h2>{t("quick_copy")}</h2>
        <p className="muted">{wordCount.toLocaleString()} {t("words_in_manuscript")}</p>
        <div className="export-actions">
          <button
            className="btn-secondary"
            onClick={() => { navigator.clipboard.writeText(manuscript); showToast(t("manuscript_copied"), "success"); }}
            disabled={!manuscript}
          >
            {t("copy_manuscript")}
          </button>
        </div>
      </section>

      <section className="section">
        <h2>{t("preview")}</h2>
        <pre className="manuscript-preview">
          {manuscript.slice(0, 5000) || t("no_manuscript_available")}
          {manuscript.length > 5000 && `\n\n${t("truncated")}`}
        </pre>
      </section>
    </div>
  );
}
