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
import PipelineConsole from "./components/PipelineConsole";
import AlertModal from "./components/AlertModal";

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

  // outputDir = where all novel files live (seed.txt, world.md, chapters/, etc.)
  const [outputDir, setOutputDir] = useState<string>("");

  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineMessage, setPipelineMessage] = useState("");
  const [pipelineLog, setPipelineLog] = useState<string[]>([]);
  const [alertMessage, setAlertMessage] = useState<string | null>(null);

  useEffect(() => {
    initProject();

    // Pipeline event listeners
    const unlistenStarted = listen("pipeline-started", () => {
      console.log("[App] Received pipeline-started event!");
      setPipelineRunning(true);
      setPipelineMessage(t("running"));
      setPipelineLog([]);
    });

    const unlistenProgress = listen<PipelineProgress>("pipeline-progress", (event) => {
      setPipelineMessage(event.payload.message);
      // Append to pipelineLog for streaming console display
      setPipelineLog((prev) => {
        const next = [...prev, event.payload.message];
        return next.length > 500 ? next.slice(next.length - 500) : next;
      });
    });

    const unlistenLog = listen<string>("pipeline-log", (event) => {
      setPipelineLog((prev) => {
        const next = [...prev, event.payload];
        return next.length > 500 ? next.slice(next.length - 500) : next;
      });
    });

    const unlistenComplete = listen("pipeline-complete", async () => {
      setPipelineRunning(false);
      setPipelineMessage("");
      await loadState();
    });

    const unlistenError = listen<string>("pipeline-error", (event) => {
      setPipelineRunning(false);
      setPipelineMessage("");
      setAlertMessage(`Pipeline error: ${event.payload}`);
    });

    return () => {
      unlistenStarted.then((f) => f());
      unlistenProgress.then((f) => f());
      unlistenLog.then((f) => f());
      unlistenComplete.then((f) => f());
      unlistenError.then((f) => f());
    };
  }, []);

  const initProject = async () => {
    try {
      const dir = await invoke<string>("get_project_path");
      setOutputDir(dir);
      const exists = await invoke<boolean>("project_exists", { outputDir: dir });
      setHasProject(exists);
      if (exists) {
        await loadState(dir);
        // Check if a pipeline is already running (from crash recovery)
        console.log("[App] Checking pipeline status for:", dir);
        try {
          const pipelineAlreadyRunning = await invoke<boolean>("check_pipeline_status", { outputDir: dir });
          console.log("[App] Pipeline already running:", pipelineAlreadyRunning);
          if (pipelineAlreadyRunning) {
            setPipelineRunning(true);
            setPipelineMessage("Resuming...");
          }
        } catch (e) {
          console.error("[App] check_pipeline_status error:", e);
        }
      }
    } catch (e) {
      console.error("Error initialising project:", e);
    } finally {
      setLoading(false);
    }
  };

  const loadState = async (dir?: string) => {
    try {
      const d = dir || outputDir;
      const s = await invoke<PipelineState>("read_state", { outputDir: d });
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
      await invoke("reset_project_state", { outputDir });
    } catch (e) {
      console.error("Error resetting state:", e);
    }
    setHasProject(true);
    await loadState(outputDir);
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
      await invoke("save_chapter", { outputDir, chapterNum: selectedChapter, content });
      await loadState();
    } catch (e) {
      console.error("Error saving chapter:", e);
    }
  };

  // Runs a pipeline phase; outputDir is passed so Python knows where to write files
  const handleRunPhase = async (phase: string) => {
    console.log("[App] handleRunPhase starting, phase:", phase, "outputDir:", outputDir);
    try {
      const result = await invoke("run_pipeline_phase", { phase, outputDir });
      console.log("[App] handleRunPhase completed, result:", result);
    } catch (e) {
      console.error("[App] handleRunPhase failed:", e);
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
          <button className={lang === "en" ? "active" : ""} onClick={() => setLang("en")}>EN</button>
          <button className={lang === "zh" ? "active" : ""} onClick={() => setLang("zh")}>中文</button>
        </div>
        {state && (
          <div className="status">
            <div className="phase">{state.phase}</div>
            {state.phase === "drafting" && (
              <div className="progress">Ch {state.chapters.length}/?</div>
            )}
          </div>
        )}
      </nav>

      <main className="content">
        {view === "dashboard" && state && (
          <Dashboard
            state={state}
            outputDir={outputDir}
            onRunPhase={handleRunPhase}
            onNewProject={handleNewProject}
            pipelineRunning={pipelineRunning}
            pipelineMessage={pipelineMessage}
            pipelineLog={pipelineLog}
          />
        )}
        {view === "chapters" && (
          <ChapterList
            outputDir={outputDir}
            selectedChapter={selectedChapter}
            onSelectChapter={handleChapterSelect}
          />
        )}
        {view === "chapters" && selectedChapter !== null && (
          <ChapterEditor
            outputDir={outputDir}
            chapterNum={selectedChapter}
            onSave={handleSaveChapter}
            onClose={() => setSelectedChapter(null)}
          />
        )}
        {view === "foundation" && (
          <FoundationView outputDir={outputDir} />
        )}
        {view === "export" && state && (
          <ExportView outputDir={outputDir} />
        )}
        {view === "settings" && (
          <SettingsView outputDir={outputDir} onNewProject={handleNewProject} />
        )}
      </main>

      {(pipelineRunning || pipelineLog.length > 0) && (
        <PipelineConsole
          pipelineRunning={pipelineRunning}
          pipelineMessage={pipelineMessage}
          pipelineLog={pipelineLog}
        />
      )}

      {alertMessage && (
        <AlertModal message={alertMessage} onClose={() => setAlertMessage(null)} />
      )}
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
