import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { View, PipelineState } from "./types";
import Dashboard from "./components/Dashboard";
import ChapterList from "./components/ChapterList";
import ChapterEditor from "./components/ChapterEditor";
import FoundationView from "./components/FoundationView";
import SettingsView from "./components/SettingsView";
import ExportView from "./components/ExportView";
import NewProjectView from "./components/NewProjectView";

function App() {
  const [view, setView] = useState<View>("dashboard");
  const [hasProject, setHasProject] = useState<boolean | null>(null);
  const [state, setState] = useState<PipelineState | null>(null);
  const [selectedChapter, setSelectedChapter] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [cwd, setCwd] = useState<string>("");

  useEffect(() => {
    initProject();
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

  const handleProjectCreated = () => {
    setHasProject(true);
    loadState(cwd);
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
      await invoke("run_pipeline_phase", { phase, cwd });
      await loadState();
    } catch (e) {
      console.error("Error running phase:", e);
      throw e;
    }
  };

  const handleRunFull = async () => {
    try {
      await invoke("run_full_pipeline", { cwd });
      await loadState();
    } catch (e) {
      console.error("Error running pipeline:", e);
      throw e;
    }
  };

  if (loading) {
    return <div className="loading">Loading NovelForge...</div>;
  }

  if (!hasProject) {
    return (
      <NewProjectView
        onProjectCreated={handleProjectCreated}
      />
    );
  }

  return (
    <div className="app">
      <nav className="sidebar">
        <div className="logo">NovelForge</div>
        <ul className="nav-items">
          <li className={view === "dashboard" ? "active" : ""}>
            <button onClick={() => setView("dashboard")}>Dashboard</button>
          </li>
          <li className={view === "chapters" ? "active" : ""}>
            <button onClick={() => setView("chapters")}>Chapters</button>
          </li>
          <li className={view === "foundation" ? "active" : ""}>
            <button onClick={() => setView("foundation")}>Foundation</button>
          </li>
          <li className={view === "export" ? "active" : ""}>
            <button onClick={() => setView("export")}>Export</button>
          </li>
          <li className={view === "settings" ? "active" : ""}>
            <button onClick={() => setView("settings")}>Settings</button>
          </li>
        </ul>
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
            onRunFull={handleRunFull}
            onNewProject={handleNewProject}
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

export default App;
