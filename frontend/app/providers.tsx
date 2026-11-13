"use client";

import type { ReactNode } from "react";
import { AuthProvider } from "@/features/auth/use-auth";
import { DensityProvider } from "@/features/appearance/density-provider";
import { ThemeProvider } from "@/features/appearance/theme-provider";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <DensityProvider>
        <AuthProvider>{children}</AuthProvider>
      </DensityProvider>
    </ThemeProvider>
  );
}
