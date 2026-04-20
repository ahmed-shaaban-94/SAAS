import Link from "next/link";
import { Sparkles, ArrowRight } from "lucide-react";
import type { AlertData } from "./types";

export function AlertBanner({ data }: { data: AlertData }) {
  const href = data.actionHref ?? "#";

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-start gap-3.5 rounded-xl border border-accent/25 bg-gradient-to-r from-accent/[0.08] via-accent/[0.03] to-transparent p-4"
    >
      <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-accent/15 text-accent">
        <Sparkles className="h-4 w-4" aria-hidden />
      </div>

      <p className="flex-1 text-sm leading-relaxed text-text-secondary">
        <b className="text-text-primary">{data.title}</b>
        <span className="px-1.5 text-text-tertiary">·</span>
        {data.body}
      </p>

      <Link
        href={href}
        className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap text-sm font-semibold text-accent-strong hover:underline"
      >
        {data.action}
        <ArrowRight className="h-3.5 w-3.5" aria-hidden />
      </Link>
    </div>
  );
}
