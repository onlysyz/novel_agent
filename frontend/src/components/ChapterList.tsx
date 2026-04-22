import { ChapterSummary } from "../types";
import { useState, useEffect, useRef } from "react";
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
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);
  const [loading, setLoading] = useState(true);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadChapters();
  }, [outputDir]);

  // Sync selectedIndex when selectedChapter changes externally
  useEffect(() => {
    if (selectedChapter !== null) {
      const idx = chapters.findIndex((c) => c.number === selectedChapter);
      if (idx >= 0) setSelectedIndex(idx);
    }
  }, [selectedChapter, chapters]);

  // Arrow key navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (chapters.length === 0) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, chapters.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter" && selectedIndex >= 0) {
        e.preventDefault();
        onSelectChapter(chapters[selectedIndex].number);
      }
    };
    const el = listRef.current;
    el?.addEventListener("keydown", handleKeyDown);
    return () => el?.removeEventListener("keydown", handleKeyDown);
  }, [chapters, selectedIndex]);

  const loadChapters = async () => {
    setLoading(true);
    try {
      const chs = await invoke<ChapterSummary[]>("list_chapters", { outputDir });
      setChapters(chs);
    } catch (e) {
      console.error("Error loading chapters:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = async (e: React.MouseEvent, chapter_num: number) => {
    e.stopPropagation();
    try {
      await invoke("retry_chapter", { outputDir, chapterNum: chapter_num });
      await loadChapters();
    } catch (err) {
      console.error("Error retrying chapter:", err);
    }
  };

  return (
    <div className="chapter-list">
      <header className="page-header">
        <h1>{t("chapters_title")}</h1>
      </header>
      <div className="chapters-grid" ref={listRef} tabIndex={0} onFocus={() => { if (selectedIndex < 0 && chapters.length > 0) setSelectedIndex(0); }}>
        {loading ? (
          <div className="chapter-skeletons">
            {[1, 2, 3, 4, 5].map((n) => (
              <div key={n} className="chapter-card skeleton-card">
                <div className="skeleton-line w-1_3" />
                <div className="skeleton-line w-2_3" />
                <div className="skeleton-line w-1_2" />
              </div>
            ))}
          </div>
        ) : chapters.length === 0 ? (
          <p className="empty-state">{t("no_chapters_yet")}</p>
        ) : (
          chapters.map((ch, idx) => (
            <button
              key={ch.number}
              className={`chapter-card ${idx === selectedIndex ? 'selected' : ''} ${ch.status === 'failed' ? 'failed' : ''}`}
              onClick={() => { onSelectChapter(ch.number); setSelectedIndex(idx); }}
            >
              <div className="chapter-number">{t("chapter", { n: ch.number })}</div>
              <div className="chapter-title">{ch.title}</div>
              <div className="chapter-meta">
                <span>{ch.word_count.toLocaleString()} {t("words_count")}</span>
                {ch.score !== null && (
                  <span className="score">{t("score_label")}: {ch.score.toFixed(1)}</span>
                )}
                {ch.status === "failed" && (
                  <button
                    className="retry-btn"
                    onClick={(e) => handleRetry(e, ch.number)}
                  >
                    {t("retry") || "Retry"}
                  </button>
                )}
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
