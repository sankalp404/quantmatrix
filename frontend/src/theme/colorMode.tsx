import React from "react";

export type ColorMode = "light" | "dark";

type Ctx = {
  colorMode: ColorMode;
  setColorMode: (mode: ColorMode) => void;
  toggleColorMode: () => void;
};

const ColorModeContext = React.createContext<Ctx | null>(null);

const STORAGE_KEY = "qm.colorMode";

function applyToDom(mode: ColorMode) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  // Chakra v3 defaultConfig uses `.dark &` for dark styles.
  root.classList.toggle("dark", mode === "dark");
  // Keep a light marker for completeness (Chakra's light condition includes `.light &`).
  root.classList.toggle("light", mode === "light");
}

function readInitialMode(): ColorMode {
  if (typeof window === "undefined") return "dark";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  // Prefer OS theme if present; default to dark for finance dashboards.
  const prefersDark = window.matchMedia?.("(prefers-color-scheme: dark)")?.matches;
  return prefersDark ? "dark" : "light";
}

export function ColorModeProvider({ children }: { children: React.ReactNode }) {
  const [colorMode, setColorModeState] = React.useState<ColorMode>(() => readInitialMode());

  const setColorMode = React.useCallback((mode: ColorMode) => {
    setColorModeState(mode);
    try {
      window.localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      // ignore
    }
    applyToDom(mode);
  }, []);

  const toggleColorMode = React.useCallback(() => {
    setColorMode(colorMode === "dark" ? "light" : "dark");
  }, [colorMode, setColorMode]);

  React.useEffect(() => {
    applyToDom(colorMode);
  }, [colorMode]);

  const value = React.useMemo<Ctx>(() => ({ colorMode, setColorMode, toggleColorMode }), [
    colorMode,
    setColorMode,
    toggleColorMode,
  ]);

  return <ColorModeContext.Provider value={value}>{children}</ColorModeContext.Provider>;
}

export function useColorMode() {
  const ctx = React.useContext(ColorModeContext);
  if (!ctx) {
    throw new Error("useColorMode must be used within ColorModeProvider");
  }
  return ctx;
}


