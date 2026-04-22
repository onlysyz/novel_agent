import { test as setup } from "@playwright/test";
import type { PipelineState, ChapterSummary } from "../src/types";

/** Mock state returned by read_state */
export const MOCK_STATE: PipelineState = {
  phase: "foundation",
  foundation_scores: {
    world: 7.5,
    characters: 7.0,
    outline: 7.2,
    canon: 6.8,
    voice: 7.1,
  },
  chapters: [
    { number: 1, title: "The Beginning", word_count: 3500, score: 7.5 },
    { number: 2, title: "The Journey", word_count: 3800, score: 7.8 },
    { number: 3, title: "The Confrontation", word_count: 3200, score: null },
  ],
  revision_cycles: 0,
};

/** Mock chapters returned by list_chapters */
export const MOCK_CHAPTERS: ChapterSummary[] = [
  { number: 1, title: "The Beginning", word_count: 3500, score: 7.5 },
  { number: 2, title: "The Journey", word_count: 3800, score: 7.8 },
  { number: 3, title: "The Confrontation", word_count: 3200, score: null },
];

/** Mock chapter content */
export const MOCK_CHAPTER_CONTENT = `# Chapter 1: The Beginning

Sarah stood at the edge of the ruined cathedral, her breath misting in the cold air. The broken stained glass windows cast colored shadows across the stone floor.

She reached into her pocket and pulled out the broken amulet. It was still warm.

"The key," she whispered. "It finally woke up."

## Scene Beats
- Sarah discovers the broken amulet
- She remembers her mother's last words
- The first survivor appears at the door

## World Building
- The ancient city walls are crumbling
- Magic has faded over centuries
`;

/** Add mock Tauri API to a page context - call this in beforeEach */
export async function mockTauriApi(page: any) {
  await page.context().addInitScript(({ MOCK_STATE, MOCK_CHAPTERS, MOCK_CHAPTER_CONTENT }) => {
    const listeners: Record<string, Set<(event: any) => void>> = {};

    const mockInvoke = async (cmd: string, _args?: Record<string, unknown>, _options?: any) => {
      switch (cmd) {
        case "get_project_path":
          return "/mock/novel/project";
        case "project_exists":
          return true;
        case "read_state":
          return JSON.parse(JSON.stringify(MOCK_STATE));
        case "list_chapters":
          return JSON.parse(JSON.stringify(MOCK_CHAPTERS));
        case "read_chapter":
          return {
            number: 1,
            title: "The Beginning",
            content: MOCK_CHAPTER_CONTENT,
            word_count: 3500,
            score: 7.5,
            has_revision: false,
          };
        case "read_ai_config":
          return { novel_title: "The Amulet War" };
        case "generate_title":
          return "The Amulet War: Awakening";
        case "save_chapter":
          return { success: true };
        case "run_pipeline_phase":
          return { success: true };
        case "check_pipeline_status":
          return false;
        default:
          return null;
      }
    };

    const mockListen = async (event: string, handler: (event: { payload: any }) => void) => {
      if (!(event in listeners)) {
        listeners[event] = new Set();
      }
      listeners[event].add(handler);
      return () => { listeners[event].delete(handler); };
    };

    const mockEmit = async (event: string, payload?: any) => {
      const handlers = listeners[event];
      if (handlers) {
        handlers.forEach((h) => h({ payload }));
      }
    };

    window.__TAURI_INTERNALS__ = {
      invoke: mockInvoke,
      transformCallback: (id: any, extraArg: any) => {},
      unregisterCallback: (id: any) => {},
      convertFileSrc: (path: string) => `http://localhost:1420/${path}`,
    };

    window.__TAURI__ = {
      invoke: mockInvoke,
      listen: mockListen,
      emit: mockEmit,
      _listeners: listeners,
    };

    window.isTauri = true;
  }, { MOCK_STATE, MOCK_CHAPTERS, MOCK_CHAPTER_CONTENT });
}