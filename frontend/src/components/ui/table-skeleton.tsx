import { cn } from "@/lib/utils";

interface TableSkeletonProps {
  /** Number of skeleton rows to render */
  rows?: number;
  /** Number of columns to show per row */
  cols?: number;
  /** Optional className for the wrapper */
  className?: string;
  /** Whether to show a header row */
  showHeader?: boolean;
}

/**
 * Skeleton loader for table data — staggered shimmer per row.
 * Each row fades in at a slightly later delay for a cascade effect.
 */
export function TableSkeleton({
  rows = 5,
  cols = 4,
  className,
  showHeader = true,
}: TableSkeletonProps) {
  const colWidths = ["w-8", "flex-1", "w-24", "w-20"];

  return (
    <div className={cn("overflow-x-auto", className)} aria-busy="true" aria-label="Loading table data">
      <table className="w-full min-w-[400px] text-left text-sm">
        {showHeader && (
          <thead>
            <tr className="border-b border-border">
              {Array.from({ length: cols }).map((_, ci) => (
                <th key={ci} className="pb-2.5 pr-4">
                  <div className="h-3 w-16 rounded bg-divider animate-shimmer" />
                </th>
              ))}
            </tr>
          </thead>
        )}
        <tbody>
          {Array.from({ length: rows }).map((_, ri) => (
            <tr
              key={ri}
              className="border-b border-divider"
              style={{ animationDelay: `${ri * 0.07}s` }}
            >
              {Array.from({ length: cols }).map((_, ci) => (
                <td key={ci} className="py-3 pr-4">
                  <div
                    className={cn(
                      "h-4 rounded bg-divider animate-shimmer",
                      colWidths[ci] ?? "w-20",
                      ci === 1 && "w-full max-w-[200px]",
                    )}
                    style={{ animationDelay: `${(ri * cols + ci) * 0.04}s` }}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Skeleton for ranking lists — shows rank badge + name + bar + value pattern.
 */
export function RankingTableSkeleton({ rows = 5, className }: { rows?: number; className?: string }) {
  return (
    <div className={cn("overflow-x-auto", className)} aria-busy="true" aria-label="Loading rankings">
      <table className="w-full min-w-[500px] text-left text-[13px]">
        <thead>
          <tr className="border-b border-border">
            {["#", "Name", "Revenue", "Share"].map((_, i) => (
              <th key={i} className="pb-2.5 pr-4">
                <div className="h-3 w-14 rounded bg-divider animate-shimmer" style={{ animationDelay: `${i * 0.05}s` }} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, ri) => (
            <tr key={ri} className="border-b border-divider">
              <td className="py-3 pr-3">
                <div className="h-7 w-7 rounded-full bg-divider animate-shimmer" style={{ animationDelay: `${ri * 0.07}s` }} />
              </td>
              <td className="py-3 pr-4 max-w-[220px]">
                <div
                  className="h-4 rounded bg-divider animate-shimmer"
                  style={{
                    width: `${70 + Math.sin(ri) * 20}%`,
                    animationDelay: `${ri * 0.07 + 0.05}s`,
                  }}
                />
              </td>
              <td className="py-3 pr-4 text-right">
                <div className="ml-auto h-4 w-20 rounded bg-divider animate-shimmer" style={{ animationDelay: `${ri * 0.07 + 0.1}s` }} />
              </td>
              <td className="py-3 text-right">
                <div className="ml-auto flex items-center gap-2 justify-end">
                  <div className="h-1.5 w-16 rounded-full bg-divider animate-shimmer" style={{ animationDelay: `${ri * 0.07 + 0.15}s` }} />
                  <div className="h-4 w-10 rounded bg-divider animate-shimmer" style={{ animationDelay: `${ri * 0.07 + 0.2}s` }} />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
