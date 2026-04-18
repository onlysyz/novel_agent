import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { FoundationDoc } from "../types";

type DocName = "world" | "characters" | "outline" | "canon" | "voice";

export default function FoundationView() {
  const [selectedDoc, setSelectedDoc] = useState<DocName>("world");
  const [doc, setDoc] = useState<FoundationDoc | null>(null);
  const [loading, setLoading] = useState(false);

  const loadDoc = async (name: DocName) => {
    setLoading(true);
    try {
      const d = await invoke<FoundationDoc>("read_foundation_doc", { name });
      setDoc(d);
      setSelectedDoc(name);
    } catch (e) {
      console.error("Error loading doc:", e);
      setDoc(null);
    } finally {
      setLoading(false);
    }
  };

  const docs: { key: DocName; label: string }[] = [
    { key: "world", label: "World Bible" },
    { key: "characters", label: "Characters" },
    { key: "outline", label: "Outline" },
    { key: "canon", label: "Canon" },
    { key: "voice", label: "Voice" },
  ];

  return (
    <div className="foundation-view">
      <header className="page-header">
        <h1>Foundation Documents</h1>
      </header>
      <div className="foundation-tabs">
        {docs.map((d) => (
          <button
            key={d.key}
            className={`tab ${selectedDoc === d.key ? "active" : ""}`}
            onClick={() => loadDoc(d.key)}
          >
            {d.label}
          </button>
        ))}
      </div>
      <div className="foundation-content">
        {loading ? (
          <p>Loading...</p>
        ) : doc ? (
          <div className="doc-view">
            <div className="doc-header">
              <h2>{doc.name.charAt(0).toUpperCase() + doc.name.slice(1)}</h2>
            </div>
            <pre className="doc-text">{doc.content}</pre>
          </div>
        ) : (
          <p className="empty-state">Select a document to view</p>
        )}
      </div>
    </div>
  );
}
