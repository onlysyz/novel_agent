import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";

interface Props {
  onProjectCreated: () => void;
}

export default function NewProjectView({ onProjectCreated }: Props) {
  const [seed, setSeed] = useState("");
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!seed.trim()) {
      alert("Please enter a novel concept");
      return;
    }

    setCreating(true);
    try {
      // Write seed file
      await invoke("write_seed", { seed: seed.trim() });
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
        <h1>Start Your Novel</h1>
        <p className="tagline">Describe your story concept, and watch it unfold.</p>

        <div className="seed-input-container">
          <label htmlFor="seed">Novel Concept</label>
          <textarea
            id="seed"
            value={seed}
            onChange={(e) => setSeed(e.target.value)}
            placeholder="A retired assassin is forced back into service when her daughter is kidnapped by the same criminal syndicate she once worked for..."
            rows={5}
          />
          <p className="hint">
            The more specific your concept, the better the AI can craft your story.
          </p>
        </div>

        <button
          className="btn-primary btn-large"
          onClick={handleCreate}
          disabled={creating || !seed.trim()}
        >
          {creating ? "Creating..." : "Create Novel Project"}
        </button>

        <p className="examples">
          <strong>Examples:</strong>
          <br />A detective must solve her own murder to save her daughter.
          <br />A librarian discovers books that predict the future.
          <br />Two rival chefs fall in love while competing on a reality TV show.
        </p>
      </div>
    </div>
  );
}
