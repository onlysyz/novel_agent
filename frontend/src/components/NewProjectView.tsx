import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useTranslation } from "../i18n";
import { useToast } from "./Toast";

interface Props {
  onProjectCreated: () => void;
  onCancel: () => void;
}

const LANGUAGES = [
  { code: "en", name: "English" },
  { code: "zh", name: "中文" },
  { code: "ja", name: "日本語" },
  { code: "ko", name: "한국어" },
  { code: "es", name: "Español" },
  { code: "fr", name: "Français" },
  { code: "de", name: "Deutsch" },
];

export default function NewProjectView({ onProjectCreated, onCancel }: Props) {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const [seed, setSeed] = useState("");
  const [language, setLanguage] = useState("en");
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!seed.trim()) {
      showToast(t("please_enter_concept"), "error");
      return;
    }

    setCreating(true);
    try {
      const outputDir = await invoke<string>("get_project_path");
      await invoke("write_seed", { outputDir, seed: seed.trim(), language });
      onProjectCreated();
    } catch (e) {
      console.error("Error creating project:", e);
      showToast(`Error: ${e}`, "error");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="new-project-view">
      <div className="new-project-card">
        <div className="logo">NovelForge</div>
        <h1>{t("start_your_novel")}</h1>
        <p className="tagline">{t("tagline")}</p>

        <div className="seed-input-container">
          <label htmlFor="seed">{t("novel_concept")}</label>
          <div className="language-selector">
            <label htmlFor="language">{t("novel_language")}</label>
            <select
              id="language"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              {LANGUAGES.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.name}
                </option>
              ))}
            </select>
          </div>
          <textarea
            id="seed"
            value={seed}
            onChange={(e) => setSeed(e.target.value)}
            placeholder={t("seed_placeholder")}
            rows={5}
          />
          <p className="hint">
            {t("hint")}
          </p>
        </div>

        <div className="btn-group">
          <button
            className="btn-secondary"
            onClick={onCancel}
            disabled={creating}
          >
            {t("cancel")}
          </button>
          <button
            className="btn-primary"
            onClick={handleCreate}
            disabled={creating || !seed.trim()}
          >
            {creating ? t("creating") : t("create_novel_project")}
          </button>
        </div>

        <p className="examples">
          <strong>{t("examples")}</strong>
          <br />A detective must solve her own murder to save her daughter.
          <br />A librarian discovers books that predict the future.
          <br />Two rival chefs fall in love while competing on a reality TV show.
        </p>
      </div>
    </div>
  );
}
