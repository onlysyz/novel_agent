import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { View, PipelineState } from "./types";
import { I18nProvider, useTranslation } from "./i18n";
import Dashboard from "./components/Dashboard";
import ChapterList from "./components/ChapterList";
import ChapterEditor from "./components/ChapterEditor";
import FoundationView from "./components/FoundationView";
import SettingsView from "./components/SettingsView";
import ExportView from "./components/ExportView";
import NewProjectView from "./components/NewProjectView";

interface PipelineProgress {
  phase: string;
  step: string;
  message: string;
}

function AppInner() {
  const { t, lang, setLang } = useTranslation();
  const [view, setView] = useState<View>("dashboard");
  const [hasProject, setHasProject] = useState<boolean | null>(null);
  const [state, setState] = useState<PipelineState | null>(null);
  const [selectedChapter, setSelectedChapter] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [cwd, setCwd] = useState<string>("");
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineMessage, setPipelineMessage] = useState("");

  useEffect(() => {
    initProject();

    // Listen for pipeline events
    const unlistenStarted = listen("pipeline-started", (event) => {
      console.log("Pipeline started:", event.payload);
      setPipelineRunning(true);
      setPipelineMessage(t("running"));
    });

    const unlistenProgress = listen<PipelineProgress>("pipeline-progress", (event) => {
      console.log("Pipeline progress:", event.payload);
      setPipelineMessage(event.payload.message);
    });

    const unlistenComplete = listen("pipeline-complete", async (event) => {
      console.log("Pipeline complete:", event.payload);
      setPipelineRunning(false);
      setPipelineMessage("");
      await loadState();
    });

    const unlistenError = listen<string>("pipeline-error", (event) => {
      console.error("Pipeline error:", event.payload);
      setPipelineRunning(false);
      setPipelineMessage("");
      alert(`Pipeline error: ${event.payload}`);
    });

    return () => {
      unlistenStarted.then((f) => f());
      unlistenProgress.then((f) => f());
      unlistenComplete.then((f) => f());
      unlistenError.then((f) => f());
    };
  }, []);

  const initProject = async () => {
    try {
      const path = await invoke<string>("get_project_path");
      setCwd(path);
      const exists = await invoke<boolean>("project_exists", { cwd: path });
      setHasProject(exists);
      if (exists) {
        await loadState(path);
      }
    } catch (e) {
      console.error("Error checking project:", e);
    } finally {
      setLoading(false);
    }
  };

  const loadState = async (path?: string) => {
    try {
      const p = path || cwd;
      const s = await invoke<PipelineState>("read_state", { cwd: p });
      setState(s);
    } catch (e) {
      console.error("Error loading state:", e);
    }
  };

  const handleNewProject = () => {
    setHasProject(false);
    setView("settings");
  };

  const handleProjectCreated = async () => {
    try {
      // Reset state for new project
      await invoke("reset_project_state", { cwd });
    } catch (e) {
      console.error("Error resetting state:", e);
    }
    setHasProject(true);
    await loadState(cwd);
    setView("dashboard");
  };

  const handleCancelNewProject = () => {
    setHasProject(true);
    setView("dashboard");
  };

  const handleChapterSelect = (num: number) => {
    setSelectedChapter(num);
    setView("chapters");
  };

  const handleSaveChapter = async (content: string) => {
    if (selectedChapter === null) return;
    try {
      await invoke("save_chapter", { cwd, chapterNum: selectedChapter, content });
      await loadState();
    } catch (e) {
      console.error("Error saving chapter:", e);
    }
  };

  const handleRunPhase = async (phase: string) => {
    try {
      // Invoke returns immediately, pipeline runs in background
      // State is loaded when pipeline-complete event is received
      await invoke("run_pipeline_phase", { phase, cwd });
    } catch (e) {
      console.error("Error running phase:", e);
      throw e;
    }
  };

  if (loading) {
    return <div className="loading">{t("loading_novelforge")}</div>;
  }

  if (!hasProject) {
    return (
      <NewProjectView
        onProjectCreated={handleProjectCreated}
        onCancel={handleCancelNewProject}
      />
    );
  }

  return (
    <div className="app">
      <nav className="sidebar">
        <div className="logo">NovelForge</div>
        <ul className="nav-items">
          <li className={view === "dashboard" ? "active" : ""}>
            <button onClick={() => setView("dashboard")}>{t("nav_dashboard")}</button>
          </li>
          <li className={view === "chapters" ? "active" : ""}>
            <button onClick={() => setView("chapters")}>{t("nav_chapters")}</button>
          </li>
          <li className={view === "foundation" ? "active" : ""}>
            <button onClick={() => setView("foundation")}>{t("nav_foundation")}</button>
          </li>
          <li className={view === "export" ? "active" : ""}>
            <button onClick={() => setView("export")}>{t("nav_export")}</button>
          </li>
          <li className={view === "settings" ? "active" : ""}>
            <button onClick={() => setView("settings")}>{t("nav_settings")}</button>
          </li>
        </ul>
        <div className="lang-switch">
          <button
            className={lang === "en" ? "active" : ""}
            onClick={() => setLang("en")}
          >
            EN
          </button>
          <button
            className={lang === "zh" ? "active" : ""}
            onClick={() => setLang("zh")}
          >
            中文
          </button>
        </div>
        {state && (
          <div className="status">
            <div className="phase">{state.phase}</div>
            {state.phase === "drafting" && (
              <div className="progress">
                Ch {state.chapters.length}/?
              </div>
            )}
          </div>
        )}
      </nav>

      <main className="content">
        {view === "dashboard" && state && (
          <Dashboard
            state={state}
            onRunPhase={handleRunPhase}
            onNewProject={handleNewProject}
            pipelineRunning={pipelineRunning}
            pipelineMessage={pipelineMessage}
          />
        )}
        {view === "chapters" && (
          <ChapterList
            cwd={cwd}
            selectedChapter={selectedChapter}
            onSelectChapter={handleChapterSelect}
          />
        )}
        {view === "chapters" && selectedChapter !== null && (
          <ChapterEditor
            cwd={cwd}
            chapterNum={selectedChapter}
            onSave={handleSaveChapter}
            onClose={() => setSelectedChapter(null)}
          />
        )}
        {view === "foundation" && (
          <FoundationView cwd={cwd} />
        )}
        {view === "export" && state && (
          <ExportView cwd={cwd} />
        )}
        {view === "settings" && (
          <SettingsView cwd={cwd} onNewProject={handleNewProject} />
        )}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <I18nProvider>
      <AppInner />
    </I18nProvider>
  );
}
