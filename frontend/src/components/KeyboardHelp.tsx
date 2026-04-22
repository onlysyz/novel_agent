import { useEffect } from "react";
import { useTranslation } from "../i18n";

interface ShortcutItem {
  keys: string[];
  description: string;
}

interface Props {
  onClose: () => void;
}

export default function KeyboardHelp({ onClose }: Props) {
  const { t } = useTranslation();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const shortcuts: ShortcutItem[] = [
    { keys: ["⌘S"], description: t("shortcut_save") || "Save (Settings / Foundation)" },
    { keys: ["⌘↵"], description: t("shortcut_run_phase") || "Run current phase (Dashboard)" },
    { keys: ["↑", "↓"], description: t("shortcut_navigate_chapters") || "Navigate chapter list" },
    { keys: ["↵"], description: t("shortcut_select_chapter") || "Select highlighted chapter" },
    { keys: ["Esc"], description: t("shortcut_close_editor") || "Close editor / Cancel" },
    { keys: ["?"], description: t("shortcut_show_help") || "Show this help" },
  ];

  return (
    <div className="keyboard-help-overlay" onClick={onClose}>
      <div className="keyboard-help-modal" onClick={(e) => e.stopPropagation()}>
        <div className="keyboard-help-header">
          <h2>{t("keyboard_shortcuts") || "Keyboard Shortcuts"}</h2>
          <button className="btn-secondary" onClick={onClose}>✕</button>
        </div>
        <div className="keyboard-help-list">
          {shortcuts.map((s, i) => (
            <div key={i} className="keyboard-help-item">
              <div className="keyboard-help-keys">
                {s.keys.map((k) => <kbd key={k}>{k}</kbd>)}
              </div>
              <span className="keyboard-help-desc">{s.description}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}