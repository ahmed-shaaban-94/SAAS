"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { Languages } from "lucide-react";

export function LanguageToggle() {
  const router = useRouter();

  const toggleLocale = useCallback(() => {
    const current = document.cookie
      .split("; ")
      .find((c) => c.startsWith("NEXT_LOCALE="))
      ?.split("=")[1] ?? "en";

    const next = current === "en" ? "ar" : "en";
    document.cookie = `NEXT_LOCALE=${next};path=/;max-age=31536000`;
    router.refresh();
  }, [router]);

  const currentLocale = typeof document !== "undefined"
    ? document.cookie.split("; ").find((c) => c.startsWith("NEXT_LOCALE="))?.split("=")[1] ?? "en"
    : "en";

  return (
    <button
      onClick={toggleLocale}
      className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-text-secondary transition-colors hover:bg-divider hover:text-text-primary"
      title={currentLocale === "en" ? "Switch to Arabic" : "Switch to English"}
    >
      <Languages className="h-4 w-4" />
      <span>{currentLocale === "en" ? "العربية" : "English"}</span>
    </button>
  );
}
