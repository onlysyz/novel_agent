import { useState, useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { marked } from "marked";
import { FoundationDoc } from "../types";
import { useTranslation } from "../i18n";
import { useToast } from "./Toast";
import { useSaveContext } from "../contexts/SaveContext";

type DocName = "world" | "characters" | "outline" | "canon" | "voice";

interface Props {
  outputDir: string;
}

export default function FoundationView({ outputDir }: Props) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const { registerSaveHandler } = useSaveContext();
  const [selectedDoc, setSelectedDoc] = useState<DocName>("world");
  const [doc, setDoc] = useState<FoundationDoc | null>(null);
  const [loading, setLoading] = useState(false);
  const [docHtml, setDocHtml] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState("");
  const [saving, setSaving] = useState(false);
  const [autoSaving, setAutoSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const autoSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSavedContent = useRef<string>("");

  // Render markdown content whenever doc changes
  useEffect(() => {
    if (doc?.content) {
      const html = marked(doc.content) as string;
      setDocHtml(html);
    } else {
      setDocHtml("");
    }
  }, [doc]);

  const loadDoc = async (name: DocName) => {
    if (isEditing && doc) {
      // User has unsaved edits, confirm before switching
      if (!window.confirm("You have unsaved changes. Discard them?")) return;
    }
    setIsEditing(false);
    setLoading(true);
    try {
      const d = await invoke<FoundationDoc>("read_foundation_doc", { outputDir, name });
      setDoc(d);
      setEditedContent(d.content);
      lastSavedContent.current = d.content;
      setHasChanges(false);
      setSelectedDoc(name);
    } catch (e) {
      console.error("Error loading doc:", e);
      setDoc(null);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = () => {
    lastSavedContent.current = doc?.content || "";
    setEditedContent(doc?.content || "");
    setHasChanges(false);
    setIsEditing(true);
  };

  const handleCancel = () => {
    if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current);
    setIsEditing(false);
    setEditedContent(doc?.content || "");
    setHasChanges(false);
  };

  const scheduleAutoSave = () => {
    if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current);
    autoSaveTimer.current = setTimeout(async () => {
      if (!hasChanges || !doc) return;
      setAutoSaving(true);
      try {
        await invoke("save_foundation_doc", { outputDir, name: doc.name, content: editedContent });
        lastSavedContent.current = editedContent;
        setHasChanges(false);
      } catch (e) {
        console.error("Auto-save failed:", e);
        showToast(`${t("error_saving")}: ${e}`, "error");
      } finally {
        setAutoSaving(false);
      }
    }, 3000);
  };

  const handleContentChange = (newContent: string) => {
    setEditedContent(newContent);
    const changed = newContent !== lastSavedContent.current;
    setHasChanges(changed);
    if (changed) scheduleAutoSave();
  };

  const handleSave = async () => {
    if (!doc) return;
    if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current);
    setSaving(true);
    try {
      await invoke("save_foundation_doc", { outputDir, name: doc.name, content: editedContent });
      lastSavedContent.current = editedContent;
      setDoc({ ...doc, content: editedContent });
      setIsEditing(false);
      setHasChanges(false);
      showToast(t("doc_saved"), "success");
    } catch (e) {
      console.error("Error saving doc:", e);
      showToast(`${t("error_saving")}: ${e}`, "error");
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    loadDoc("world");
    registerSaveHandler(null); // FoundationView has no global save action
  }, []);

  const docs: { key: DocName; labelKey: string }[] = [
    { key: "world", labelKey: "world_bible" },
    { key: "characters", labelKey: "characters" },
    { key: "outline", labelKey: "outline" },
    { key: "canon", labelKey: "canon" },
    { key: "voice", labelKey: "voice" },
  ];

  return (
    <div className="foundation-view">
      <header className="page-header">
        <h1>{t("foundation_title")}</h1>
      </header>
      <div className="foundation-tabs">
        {docs.map((d) => (
          <button
            key={d.key}
            className={`tab ${selectedDoc === d.key ? "active" : ""}`}
            onClick={() => loadDoc(d.key)}
          >
            {t(d.labelKey as any)}
          </button>
        ))}
      </div>
      <div className="foundation-content">
        {loading ? (
          <div className="foundation-skeleton">
            <div className="skeleton-line w-2_3" style={{ height: '1.5rem', marginBottom: '1rem' }} />
            <div className="skeleton-line w-full" style={{ marginBottom: '0.5rem' }} />
            <div className="skeleton-line w-5_6" style={{ marginBottom: '0.5rem' }} />
            <div className="skeleton-line w-full" style={{ marginBottom: '0.5rem' }} />
            <div className="skeleton-line w-3_4" style={{ marginBottom: '0.5rem' }} />
            <div className="skeleton-line w-5_6" style={{ marginBottom: '0.5rem' }} />
            <div className="skeleton-line w-1_2" />
          </div>
        ) : doc ? (
          <div className="doc-view">
            <div className="doc-header">
              <h2>{doc.name.charAt(0).toUpperCase() + doc.name.slice(1)}</h2>
              {!isEditing && (
                <button className="btn-secondary" onClick={handleEdit}>{t("edit")}</button>
              )}
            </div>
            {isEditing ? (
              <div className="doc-edit">
                <textarea
                  className="doc-edit-textarea"
                  value={editedContent}
                  onChange={(e) => handleContentChange(e.target.value)}
                  rows={20}
                />
                <div className="doc-edit-actions">
                  {autoSaving && <span className="auto-saving">Auto-saving...</span>}
                  {hasChanges && !autoSaving && <span className="unsaved">{t("unsaved")}</span>}
                  <button className="btn-secondary" onClick={handleCancel} disabled={saving}>{t("cancel")}</button>
                  <button className="btn-primary" onClick={handleSave} disabled={saving}>
                    {saving ? t("saving") : t("save")}
                  </button>
                </div>
              </div>
            ) : (
              <div className="doc-body" dangerouslySetInnerHTML={{ __html: docHtml }} />
            )}
          </div>
        ) : (
          <p className="empty-state">{t("select_doc_to_view")}</p>
        )}
      </div>
    </div>
  );
}