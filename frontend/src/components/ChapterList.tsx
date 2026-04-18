import { ChapterSummary } from "../types";
import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";

interface Props {
  cwd: string;
  selectedChapter: number | null;
  onSelectChapter: (num: number) => void;
}

export default function ChapterList({ cwd, selectedChapter, onSelectChapter }: Props) {
  const [chapters, setChapters] = useState<ChapterSummary[]>([]);

  useEffect(() => {
    loadChapters();
  }, [cwd]);

  const loadChapters = async () => {
    try {
      const chs = await invoke<ChapterSummary[]>("list_chapters", { cwd });
      setChapters(chs);
    } catch (e) {
      console.error("Error loading chapters:", e);
    }
  };

  return (
    <div className="chapter-list">
      <header className="page-header">
        <h1>Chapters</h1>
      </header>
      <div className="chapters-grid">
        {chapters.length === 0 ? (
          <p className="empty-state">No chapters yet. Run the drafting phase to generate chapters.</p>
        ) : (
          chapters.map((ch) => (
            <button
              key={ch.number}
              className={`chapter-card ${selectedChapter === ch.number ? 'selected' : ''}`}
              onClick={() => onSelectChapter(ch.number)}
            >
              <div className="chapter-number">Chapter {ch.number}</div>
              <div className="chapter-title">{ch.title}</div>
              <div className="chapter-meta">
                <span>{ch.word_count.toLocaleString()} words</span>
                {ch.score !== null && (
                  <span className="score">Score: {ch.score.toFixed(1)}</span>
                )}
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
