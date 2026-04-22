import { createContext, useContext, useCallback, useRef } from "react";

interface SaveContextValue {
  registerSaveHandler: (handler: (() => void) | null) => void;
  triggerSave: () => void;
}

const SaveContext = createContext<SaveContextValue>({ registerSaveHandler: () => {}, triggerSave: () => {} });

export function useSaveContext() {
  return useContext(SaveContext);
}

export function SaveProvider({ children }: { children: React.ReactNode }) {
  const handlerRef = useRef<(() => void) | null>(null);

  const registerSaveHandler = useCallback((handler: (() => void) | null) => {
    handlerRef.current = handler;
  }, []);

  const triggerSave = useCallback(() => {
    if (handlerRef.current) handlerRef.current();
  }, []);

  return (
    <SaveContext.Provider value={{ registerSaveHandler, triggerSave }}>
      {children}
    </SaveContext.Provider>
  );
}