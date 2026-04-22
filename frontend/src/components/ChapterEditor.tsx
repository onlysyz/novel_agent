import { useState, useEffect, useRef } from "react";
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
  const [autoSaving, setAutoSaving] = useState(false);
  const autoSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSavedContent = useRef<string>("");

  useEffect(() => {
    loadChapter();
  }, [chapterNum]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (mod && e.key === "s") {
        e.preventDefault();
        if (hasChanges && !saving) handleSave();
      }
      if (e.key === "Escape" && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [hasChanges, saving, content]);

  const loadChapter = async () => {
    try {
      const ch = await invoke<Chapter>("read_chapter", { outputDir, chapterNum });
      setChapter(ch);
      setContent(ch.content);
      setHasChanges(false);
      lastSavedContent.current = ch.content;
    } catch (e) {
      console.error("Error loading chapter:", e);
    }
  };

  const scheduleAutoSave = () => {
    if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current);
    autoSaveTimer.current = setTimeout(async () => {
      if (!hasChanges) return;
      setAutoSaving(true);
      try {
        await onSave(content);
        lastSavedContent.current = content;
        setHasChanges(false);
      } catch (e) {
        console.error("Auto-save failed:", e);
      } finally {
        setAutoSaving(false);
      }
    }, 3000);
  };

  const handleContentChange = (newContent: string) => {
    setContent(newContent);
    const changed = newContent !== lastSavedContent.current;
    setHasChanges(changed);
    if (changed) scheduleAutoSave();
  };

  const handleSave = async () => {
    if (autoSaveTimer.current) clearTimeout(autoSaveTimer.current);
    setSaving(true);
    try {
      await onSave(content);
      lastSavedContent.current = content;
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
          {autoSaving && <span className="auto-saving">Auto-saving...</span>}
          {hasChanges && !autoSaving && <span className="unsaved">{t("unsaved")}</span>}
          <button className="btn-secondary" onClick={onClose}>
            {t("close")}<kbd className="shortcut-hint">Esc</kbd>
          </button>
          <button
            className="btn-primary"
            onClick={handleSave}
            disabled={!hasChanges || saving}
          >
            {saving ? t("saving") : t("save")}<kbd className="shortcut-hint">⌘S</kbd>
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
