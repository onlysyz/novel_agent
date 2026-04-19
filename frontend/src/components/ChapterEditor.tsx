import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Chapter } from "../types";
import { useTranslation } from "../i18n";

interface Props {
  outputDir: string;
  chapterNum: number;
  onSave: (content: string) => Promise<void>;
  onClose: () => void;
}

export default function ChapterEditor({ outputDir, chapterNum, onSave, onClose }: Props) {
  const { t } = useTranslation();
  const [chapter, setChapter] = useState<Chapter | null>(null);
  const [content, setContent] = useState("");
  const [hasChanges, setHasChanges] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadChapter();
  }, [chapterNum]);

  const loadChapter = async () => {
    try {
      const ch = await invoke<Chapter>("read_chapter", { outputDir, chapterNum });
      setChapter(ch);
      setContent(ch.content);
      setHasChanges(false);
    } catch (e) {
      console.error("Error loading chapter:", e);
    }
  };

  const handleContentChange = (newContent: string) => {
    setContent(newContent);
    setHasChanges(newContent !== chapter?.content);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(content);
      setHasChanges(false);
    } catch (e) {
      console.error("Error saving:", e);
      alert(`Error saving: ${e}`);
    } finally {
      setSaving(false);
    }
  };

  const wordCount = content.split(/\s+/).filter(w => w.length > 0).length;

  return (
    <div className="chapter-editor">
      <header className="editor-header">
        <div className="editor-title">
          <h2>{t("chapter", { n: chapterNum })}</h2>
          {chapter && <span className="chapter-title">{chapter.title}</span>}
        </div>
        <div className="editor-actions">
          <span className="word-count">{wordCount.toLocaleString()} {t("words_count")}</span>
          {hasChanges && <span className="unsaved">{t("unsaved")}</span>}
          <button className="btn-secondary" onClick={onClose}>{t("close")}</button>
          <button
            className="btn-primary"
            onClick={handleSave}
            disabled={!hasChanges || saving}
          >
            {saving ? t("saving") : t("save")}
          </button>
        </div>
      </header>
      <textarea
        className="editor-content"
        value={content}
        onChange={(e) => handleContentChange(e.target.value)}
        placeholder={t("chapter_content_placeholder")}
      />
    </div>
  );
}
