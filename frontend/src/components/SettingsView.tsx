import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useTranslation } from "../i18n";

interface Props {
  cwd: string;
  onNewProject: () => void;
}

export default function SettingsView({ cwd, onNewProject }: Props) {
  const { t } = useTranslation();
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
      alert(t("seed_saved"));
    } catch (e) {
      console.error("Error saving seed:", e);
      alert(`${t("error_saving")}: ${e}`);
    }
  };

  return (
    <div className="settings-view">
      <header className="page-header">
        <h1>{t("settings_title")}</h1>
      </header>

      <section className="section">
        <h2>{t("project")}</h2>
        <div className="setting-item">
          <label>{t("project_path")}</label>
          <p className="setting-value">{projectPath}</p>
        </div>
      </section>

      <section className="section">
        <h2>{t("novel_concept_seed")}</h2>
        <textarea
          className="seed-input"
          value={seed}
          onChange={(e) => setSeed(e.target.value)}
          placeholder={t("novel_concept_placeholder")}
          rows={6}
        />
        <button className="btn-primary" onClick={handleSaveSeed}>{t("save_seed")}</button>
      </section>

      <section className="section">
        <h2>{t("new_project")}</h2>
        <p>{t("new_project_desc")}</p>
        <button className="btn-secondary" onClick={onNewProject}>{t("create_new_project")}</button>
      </section>

      <section className="section">
        <h2>{t("about")}</h2>
        <p>{t("novelforge_version")}</p>
        <p className="muted">{t("novelforge_desc")}</p>
      </section>
    </div>
  );
}
