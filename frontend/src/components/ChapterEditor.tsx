import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Chapter } from "../types";

interface Props {
  cwd: string;
  chapterNum: number;
  onSave: (content: string) => Promise<void>;
  onClose: () => void;
}

export default function ChapterEditor({ cwd, chapterNum, onSave, onClose }: Props) {
  const [chapter, setChapter] = useState<Chapter | null>(null);
  const [content, setContent] = useState("");
  const [hasChanges, setHasChanges] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadChapter();
  }, [chapterNum]);

  const loadChapter = async () => {
    try {
      const ch = await invoke<Chapter>("read_chapter", { cwd, chapterNum });
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
          <h2>Chapter {chapterNum}</h2>
          {chapter && <span className="chapter-title">{chapter.title}</span>}
        </div>
        <div className="editor-actions">
          <span className="word-count">{wordCount.toLocaleString()} words</span>
          {hasChanges && <span className="unsaved">Unsaved</span>}
          <button className="btn-secondary" onClick={onClose}>Close</button>
          <button
            className="btn-primary"
            onClick={handleSave}
            disabled={!hasChanges || saving}
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </header>
      <textarea
        className="editor-content"
        value={content}
        onChange={(e) => handleContentChange(e.target.value)}
        placeholder="Chapter content will appear here..."
      />
    </div>
  );
}
