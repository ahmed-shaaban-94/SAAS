import React from 'react';

/**
 * Full-width AI insight banner.
 * Props: { data: { title, body, action } }
 */
export default function AlertBanner({ data }) {
  return (
    <div className="flex items-start gap-3.5 p-4 rounded-xl border border-accent/25
                    bg-gradient-to-r from-accent/[0.08] via-accent/[0.03] to-transparent">
      <div className="w-8 h-8 rounded-lg grid place-items-center bg-accent/15 text-accent shrink-0">
        <span aria-hidden>✶</span>
      </div>
      <p className="text-sm leading-relaxed text-ink-secondary flex-1">
        <b className="text-ink-primary">{data.title}</b> · {data.body}
      </p>
      <a href="#" className="text-sm font-semibold text-accent-strong whitespace-nowrap hover:underline">
        {data.action}
      </a>
    </div>
  );
}
