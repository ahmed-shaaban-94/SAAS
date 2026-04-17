import type { ReactNode } from "react";

interface HeaderProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function Header({ title, description, action }: HeaderProps) {
  return (
    <div className="mb-4 sm:mb-6 flex items-start justify-between gap-4">
      <div>
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.26em] text-text-secondary">
          Data Pulse
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-text-primary sm:text-[2rem]">{title}</h1>
        {description && (
          <p className="mt-1 text-sm text-text-secondary sm:text-base">{description}</p>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
