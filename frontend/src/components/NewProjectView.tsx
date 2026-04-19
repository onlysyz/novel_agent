import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useTranslation } from "../i18n";

interface Props {
  onProjectCreated: () => void;
}

export default function NewProjectView({ onProjectCreated }: Props) {
  const { t } = useTranslation();
  const [seed, setSeed] = useState("");
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!seed.trim()) {
      alert(t("please_enter_concept"));
      return;
    }

    setCreating(true);
    try {
      const cwd = await invoke<string>("get_project_path");
      await invoke("write_seed", { cwd, seed: seed.trim() });
      onProjectCreated();
    } catch (e) {
      console.error("Error creating project:", e);
      alert(`Error: ${e}`);
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

        <button
          className="btn-primary btn-large"
          onClick={handleCreate}
          disabled={creating || !seed.trim()}
        >
          {creating ? t("creating") : t("create_novel_project")}
        </button>

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
