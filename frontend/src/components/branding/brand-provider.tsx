"use client";

import { createContext, useContext, useEffect } from "react";
import { useBranding, type BrandingConfig } from "@/hooks/use-branding";

const BrandContext = createContext<BrandingConfig | null>(null);

export function useBrandContext() {
  return useContext(BrandContext);
}

/**
 * Injects tenant branding as CSS custom properties on <html>.
 * Falls back gracefully to defaults defined in globals.css.
 */
export function BrandProvider({ children }: { children: React.ReactNode }) {
  const { data: branding } = useBranding();

  useEffect(() => {
    if (!branding) return;

    const root = document.documentElement;

    if (branding.primary_color) {
      root.style.setProperty("--brand-primary", branding.primary_color);
    }
    if (branding.accent_color) {
      root.style.setProperty("--brand-accent", branding.accent_color);
    }
    if (branding.sidebar_bg) {
      root.style.setProperty("--brand-sidebar", branding.sidebar_bg);
    }
    if (branding.font_family && branding.font_family !== "Inter") {
      root.style.setProperty("--brand-font", branding.font_family);
    }

    return () => {
      root.style.removeProperty("--brand-primary");
      root.style.removeProperty("--brand-accent");
      root.style.removeProperty("--brand-sidebar");
      root.style.removeProperty("--brand-font");
    };
  }, [branding]);

  return (
    <BrandContext.Provider value={branding ?? null}>
      {children}
    </BrandContext.Provider>
  );
}
