export interface Project {
  name: string;
  path: string;
  seed: string;
  phase: string;
  current_chapter: number;
  total_chapters: number;
  words_written: number;
  average_score: number;
}

export interface Chapter {
  number: number;
  title: string;
  content: string;
  word_count: number;
  score: number | null;
  has_revision: boolean;
}

export interface FoundationScores {
  world: number;
  characters: number;
  outline: number;
  canon: number;
  voice: number;
}

export interface ChapterSummary {
  number: number;
  title: string;
  word_count: number;
  score: number | null;
}

export interface PipelineState {
  phase: string;
  foundation_scores: FoundationScores;
  chapters: ChapterSummary[];
  revision_cycles: number;
}

export interface FoundationDoc {
  name: string;
  content: string;
  score: number;
}

export type View = "dashboard" | "chapters" | "foundation" | "settings" | "export";
