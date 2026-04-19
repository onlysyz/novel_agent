import { ChapterSummary } from "../types";
import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useTranslation } from "../i18n";

interface Props {
  outputDir: string;
  selectedChapter: number | null;
  onSelectChapter: (num: number) => void;
}

export default function ChapterList({ outputDir, selectedChapter, onSelectChapter }: Props) {
  const { t } = useTranslation();
  const [chapters, setChapters] = useState<ChapterSummary[]>([]);

  useEffect(() => {
    loadChapters();
  }, [outputDir]);

  const loadChapters = async () => {
    try {
      const chs = await invoke<ChapterSummary[]>("list_chapters", { outputDir });
      setChapters(chs);
    } catch (e) {
      console.error("Error loading chapters:", e);
    }
  };

  return (
    <div className="chapter-list">
      <header className="page-header">
        <h1>{t("chapters_title")}</h1>
      </header>
      <div className="chapters-grid">
        {chapters.length === 0 ? (
          <p className="empty-state">{t("no_chapters_yet")}</p>
        ) : (
          chapters.map((ch) => (
            <button
              key={ch.number}
              className={`chapter-card ${selectedChapter === ch.number ? 'selected' : ''}`}
              onClick={() => onSelectChapter(ch.number)}
            >
              <div className="chapter-number">{t("chapter", { n: ch.number })}</div>
              <div className="chapter-title">{ch.title}</div>
              <div className="chapter-meta">
                <span>{ch.word_count.toLocaleString()} {t("words_count")}</span>
                {ch.score !== null && (
                  <span className="score">{t("score_label")}: {ch.score.toFixed(1)}</span>
                )}
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
