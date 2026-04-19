import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useTranslation } from "../i18n";

interface Props {
  cwd: string;
  onNewProject: () => void;
}

interface AIConfig {
  api_key: string;
  base_url: string;
  model: string;
  opus_model: string;
  target_words: string;
  chapter_target: string;
  output_dir: string;
  novel_title: string;
}

export default function SettingsView({ cwd, onNewProject }: Props) {
  const { t } = useTranslation();
  const [seed, setSeed] = useState("");
  const [projectPath, setProjectPath] = useState("");
  const [aiConfig, setAiConfig] = useState<AIConfig>({
    api_key: "",
    base_url: "",
    model: "claude-sonnet-4-20250514",
    opus_model: "opus-4-5-20251114",
    target_words: "80000",
    chapter_target: "22",
    output_dir: "",
    novel_title: "",
  });
  const [configSaved, setConfigSaved] = useState(false);

  useEffect(() => {
    loadSeed();
    loadPath();
    loadAIConfig();
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

  const loadAIConfig = async () => {
    try {
      const config = await invoke<AIConfig>("read_ai_config", { cwd });
      setAiConfig(config);
    } catch (e) {
      console.error("Error loading AI config:", e);
    }
  };

  const handleSaveSeed = async () => {
    try {
      // Get current language from existing seed or default to en
      const lang = await invoke<string>("read_language", { cwd });
      await invoke("write_seed", { cwd, seed, language: lang });
      alert(t("seed_saved"));
    } catch (e) {
      console.error("Error saving seed:", e);
      alert(`${t("error_saving")}: ${e}`);
    }
  };

  const handleSaveAIConfig = async () => {
    try {
      await invoke("write_ai_config", { cwd, config: aiConfig });
      setConfigSaved(true);
      setTimeout(() => setConfigSaved(false), 2000);
    } catch (e) {
      console.error("Error saving AI config:", e);
      alert(`Error: ${e}`);
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
        <h2>{t("ai_config")}</h2>
        <div className="setting-item">
          <label>{t("api_key")}</label>
          <input
            type="password"
            className="setting-input"
            value={aiConfig.api_key}
            onChange={(e) => setAiConfig({ ...aiConfig, api_key: e.target.value })}
            placeholder={t("api_key_placeholder")}
          />
        </div>
        <div className="setting-item">
          <label>{t("base_url")}</label>
          <input
            type="text"
            className="setting-input"
            value={aiConfig.base_url}
            onChange={(e) => setAiConfig({ ...aiConfig, base_url: e.target.value })}
            placeholder={t("base_url_placeholder")}
          />
        </div>
        <div className="setting-item">
          <label>{t("model")}</label>
          <input
            type="text"
            className="setting-input"
            value={aiConfig.model}
            onChange={(e) => setAiConfig({ ...aiConfig, model: e.target.value })}
            placeholder="claude-sonnet-4-20250514"
          />
        </div>
        <div className="setting-item">
          <label>{t("opus_model")}</label>
          <input
            type="text"
            className="setting-input"
            value={aiConfig.opus_model}
            onChange={(e) => setAiConfig({ ...aiConfig, opus_model: e.target.value })}
            placeholder="opus-4-5-20251114"
          />
        </div>
        <button className="btn-primary" onClick={handleSaveAIConfig}>
          {configSaved ? t("saved") : t("save")}
        </button>
      </section>

      <section className="section">
        <h2>{t("project_settings")}</h2>
        <div className="setting-item">
          <label>{t("target_words")}</label>
          <input
            type="number"
            className="setting-input"
            value={aiConfig.target_words}
            onChange={(e) => setAiConfig({ ...aiConfig, target_words: e.target.value })}
            placeholder="80000"
          />
        </div>
        <div className="setting-item">
          <label>{t("chapter_target")}</label>
          <input
            type="number"
            className="setting-input"
            value={aiConfig.chapter_target}
            onChange={(e) => setAiConfig({ ...aiConfig, chapter_target: e.target.value })}
            placeholder="22"
          />
        </div>
        <div className="setting-item">
          <label>{t("output_dir")}</label>
          <input
            type="text"
            className="setting-input"
            value={aiConfig.output_dir}
            onChange={(e) => setAiConfig({ ...aiConfig, output_dir: e.target.value })}
            placeholder={t("output_dir_placeholder")}
          />
        </div>
        <button className="btn-primary" onClick={handleSaveAIConfig}>
          {configSaved ? t("saved") : t("save")}
        </button>
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
