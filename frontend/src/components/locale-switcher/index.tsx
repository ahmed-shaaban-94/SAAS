"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { type Locale } from "@/i18n/config";

type Props = { currentLocale: Locale };

const OPTIONS: { code: Locale; label: string; aria: string }[] = [
  { code: "en", label: "EN", aria: "English" },
  { code: "ar", label: "عربي", aria: "Arabic" },
];

export function LocaleSwitcher({ currentLocale }: Props) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const select = async (next: Locale) => {
    if (next === currentLocale || isPending) return;
    const resp = await fetch("/api/locale", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ locale: next }),
    });
    if (!resp.ok) return;
    startTransition(() => router.refresh());
  };

  return (
    <div
      role="group"
      aria-label="Language"
      className="flex items-center gap-1 rounded-lg border border-divider p-0.5 text-xs"
    >
      {OPTIONS.map((o) => {
        const active = o.code === currentLocale;
        return (
          <button
            key={o.code}
            type="button"
            aria-label={o.aria}
            aria-pressed={active}
            onClick={() => select(o.code)}
            disabled={isPending}
            className={[
              "rounded-md px-2 py-1 transition-colors",
              active
                ? "bg-surface-2 text-text-primary"
                : "text-text-secondary hover:bg-divider hover:text-text-primary",
              isPending ? "opacity-50 cursor-not-allowed" : "",
            ].join(" ")}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
