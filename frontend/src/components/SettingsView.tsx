import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";

interface Props {
  cwd: string;
  onNewProject: () => void;
}

export default function SettingsView({ cwd, onNewProject }: Props) {
  const [seed, setSeed] = useState("");
  const [projectPath, setProjectPath] = useState("");

  useEffect(() => {
    loadSeed();
    loadPath();
  }, [cwd]);

  const loadSeed = async () => {
    try {
      const s = await invoke<string>("read_seed", { cwd });
      setSeed(s);
    } catch (e) {
      console.error("Error loading seed:", e);
    }
  };

  const loadPath = async () => {
    try {
      const path = await invoke<string>("get_project_path");
      setProjectPath(path);
    } catch (e) {
      console.error("Error loading path:", e);
    }
  };

  const handleSaveSeed = async () => {
    try {
      await invoke("write_seed", { cwd, seed });
      alert("Seed saved!");
    } catch (e) {
      console.error("Error saving seed:", e);
      alert(`Error saving: ${e}`);
    }
  };

  return (
    <div className="settings-view">
      <header className="page-header">
        <h1>Settings</h1>
      </header>

      <section className="section">
        <h2>Project</h2>
        <div className="setting-item">
          <label>Project Path</label>
          <p className="setting-value">{projectPath}</p>
        </div>
      </section>

      <section className="section">
        <h2>Novel Concept (Seed)</h2>
        <textarea
          className="seed-input"
          value={seed}
          onChange={(e) => setSeed(e.target.value)}
          placeholder="Describe your novel concept..."
          rows={6}
        />
        <button className="btn-primary" onClick={handleSaveSeed}>Save Seed</button>
      </section>

      <section className="section">
        <h2>New Project</h2>
        <p>Start a new project from scratch. This will clear the current project.</p>
        <button className="btn-secondary" onClick={onNewProject}>Create New Project</button>
      </section>

      <section className="section">
        <h2>About</h2>
        <p>NovelForge v0.1.0</p>
        <p className="muted">Autonomous novel writing powered by dual-agent AI</p>
      </section>
    </div>
  );
}
