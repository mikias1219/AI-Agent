"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

export type Density = "comfortable" | "compact";

const STORAGE_KEY = "aura-density";

type DensityContextValue = {
  density: Density;
  setDensity: (value: Density) => void;
};

const DensityContext = createContext<DensityContextValue | null>(null);

function applyDensity(density: Density) {
  document.documentElement.setAttribute("data-density", density);
}

export function DensityProvider({ children }: { children: ReactNode }) {
  const [density, setDensityState] = useState<Density>("comfortable");

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY) as Density | null;
    const next = stored === "compact" || stored === "comfortable" ? stored : "comfortable";
    setDensityState(next);
    applyDensity(next);
  }, []);

  const setDensity = useCallback((value: Density) => {
    setDensityState(value);
    window.localStorage.setItem(STORAGE_KEY, value);
    applyDensity(value);
  }, []);

  return (
    <DensityContext.Provider value={{ density, setDensity }}>{children}</DensityContext.Provider>
  );
}

export function useDensity() {
  const ctx = useContext(DensityContext);
  if (!ctx) throw new Error("useDensity must be used within DensityProvider");
  return ctx;
}
