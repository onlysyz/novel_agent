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

  useEffect(() => {
    initProject();

    // Pipeline event listeners
    const unlistenStarted = listen("pipeline-started", () => {
      console.log("[App] pipeline-started event received");
      setPipelineRunning(true);
      setPipelineMessage(t("running"));
      setPipelineLog([]);
    });

    const unlistenProgress = listen<PipelineProgress>("pipeline-progress", (event) => {
      console.log("[App] pipeline-progress:", event.payload);
      setPipelineMessage(event.payload.message);
    });

    const unlistenLog = listen<string>("pipeline-log", (event) => {
      console.log("[App] pipeline-log:", event.payload);
      setPipelineLog((prev) => {
        const next = [...prev, event.payload];
        return next.length > 500 ? next.slice(next.length - 500) : next;
      });
    });

    const unlistenComplete = listen("pipeline-complete", async () => {
      console.log("[App] pipeline-complete event received");
      setPipelineRunning(false);
      setPipelineMessage("");
      await loadState();
    });

    const unlistenError = listen<string>("pipeline-error", (event) => {
      console.log("[App] pipeline-error:", event.payload);
      setPipelineRunning(false);
      setPipelineMessage("");
      alert(`Pipeline error: ${event.payload}`);
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
      // get_project_path() always returns the output_dir (novel files directory)
      const dir = await invoke<string>("get_project_path");
      console.log("[App] get_project_path returned:", dir);
      setOutputDir(dir);
      const exists = await invoke<boolean>("project_exists", { outputDir: dir });
      console.log("[App] project_exists:", exists);
      setHasProject(exists);
      if (exists) {
        await loadState(dir);
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
    console.log("[App] handleRunPhase called, phase:", phase, "outputDir:", outputDir);
    try {
      const result = await invoke("run_pipeline_phase", { phase, outputDir });
      console.log("[App] run_pipeline_phase returned:", result);
    } catch (e) {
      console.error("[App] run_pipeline_phase error:", e);
      alert(`启动失败: ${e}`);
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
        {/* GLOBAL TEST BUTTON */}
        <div style={{position: "fixed", top: 0, left: 0, background: "yellow", zIndex: 99999, padding: "20px"}}>
          <button onClick={() => { document.title = "GLOBAL TEST OK"; alert("Global test works!"); console.log("GLOBAL BUTTON CLICKED"); }}>
            全局测试按钮
          </button>
        </div>
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
