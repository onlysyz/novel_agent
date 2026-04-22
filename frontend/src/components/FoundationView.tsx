import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { marked } from "marked";
import { FoundationDoc } from "../types";
import { useTranslation } from "../i18n";
import { useToast } from "./Toast";

type DocName = "world" | "characters" | "outline" | "canon" | "voice";

interface Props {
  outputDir: string;
}

export default function FoundationView({ outputDir }: Props) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const [selectedDoc, setSelectedDoc] = useState<DocName>("world");
  const [doc, setDoc] = useState<FoundationDoc | null>(null);
  const [loading, setLoading] = useState(false);
  const [docHtml, setDocHtml] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState("");
  const [saving, setSaving] = useState(false);

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
      setSelectedDoc(name);
    } catch (e) {
      console.error("Error loading doc:", e);
      setDoc(null);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = () => {
    setEditedContent(doc?.content || "");
    setIsEditing(true);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditedContent(doc?.content || "");
  };

  const handleSave = async () => {
    if (!doc) return;
    setSaving(true);
    try {
      await invoke("save_foundation_doc", { outputDir, name: doc.name, content: editedContent });
      setDoc({ ...doc, content: editedContent });
      setIsEditing(false);
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
          <p>{t("loading")}</p>
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
                  onChange={(e) => setEditedContent(e.target.value)}
                  rows={20}
                />
                <div className="doc-edit-actions">
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