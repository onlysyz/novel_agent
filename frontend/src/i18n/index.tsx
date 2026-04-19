import { createContext, useContext, useState, ReactNode } from "react";
import { translations, Language } from "./translations";

interface I18nContextValue {
  lang: Language;
  setLang: (lang: Language) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Language>(() => {
    const stored = localStorage.getItem("novelforge_lang");
    return stored === "zh" || stored === "en" ? stored : "en";
  });

  const handleSetLang = (l: Language) => {
    setLang(l);
    localStorage.setItem("novelforge_lang", l);
  };

  const t = (key: string, params?: Record<string, string | number>): string => {
    const dict = translations[lang] as Record<string, string>;
    let text = dict[key] || (translations.en as Record<string, string>)[key] || key;
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        text = text.replace(`{${k}}`, String(v));
      });
    }
    return text;
  };

  return (
    <I18nContext.Provider value={{ lang, setLang: handleSetLang, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useTranslation() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useTranslation must be used within I18nProvider");
  return ctx;
}
