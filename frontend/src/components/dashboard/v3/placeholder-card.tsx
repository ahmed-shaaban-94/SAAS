import { cn } from "@/lib/utils";

interface PlaceholderCardProps {
  title: string;
  note: string;
  issueNumber: number;
  minHeight?: number;
  className?: string;
}

export function PlaceholderCard({
  title,
  note,
  issueNumber,
  minHeight = 240,
  className,
}: PlaceholderCardProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-card border border-dashed border-border/40 bg-card p-5",
        className,
      )}
      style={{ minHeight }}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-[15px] font-semibold text-text-primary">{title}</h3>
        <a
          href={`https://github.com/ahmed-shaaban-94/Data-Pulse/issues/${issueNumber}`}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-full border border-border/50 px-2.5 py-0.5 text-[10.5px] uppercase tracking-[0.18em] text-text-tertiary hover:text-accent-strong"
        >
          #{issueNumber}
        </a>
      </div>
      <p className="text-sm leading-relaxed text-text-tertiary">{note}</p>
    </div>
  );
}
