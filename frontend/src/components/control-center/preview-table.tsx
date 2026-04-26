"use client";

import type { ConnectionPreviewResult } from "@/hooks/use-connections";
import { formatNumber } from "@/lib/formatters";

interface Props {
  preview: ConnectionPreviewResult;
  maxRows?: number;
}

export function PreviewTable({ preview, maxRows = 50 }: Props) {
  const columns = preview.columns.map((c) => c.source_name);
  const rows = preview.sample_rows.slice(0, maxRows);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-4 text-sm text-text-secondary">
        <span>
          <strong className="text-text-primary">{formatNumber(preview.row_count_estimate)}</strong>{" "}
          estimated rows
        </span>
        <span>
          <strong className="text-text-primary">{columns.length}</strong> columns
        </span>
        {preview.warnings.length > 0 && (
          <span className="text-yellow-500">
            {preview.warnings.length} warning{preview.warnings.length !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {preview.warnings.length > 0 && (
        <ul className="rounded-xl bg-yellow-500/10 px-4 py-3 text-sm text-yellow-500 space-y-1">
          {preview.warnings.map((w, i) => (
            <li key={i}>• {w}</li>
          ))}
        </ul>
      )}

      <div className="overflow-x-auto rounded-xl border border-border/50">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border/50 bg-card">
              {preview.columns.map((col) => (
                <th
                  key={col.source_name}
                  className="px-3 py-2 text-left font-medium text-text-secondary whitespace-nowrap"
                  title={`type: ${col.detected_type}`}
                >
                  <div>{col.source_name}</div>
                  <div className="font-normal text-text-tertiary">{col.detected_type}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, ri) => (
              <tr key={ri} className="border-b border-border/20 hover:bg-accent/10">
                {columns.map((col) => (
                  <td key={col} className="px-3 py-1.5 font-mono text-text-primary whitespace-nowrap">
                    {row[col] == null ? (
                      <span className="text-text-tertiary italic">null</span>
                    ) : (
                      String(row[col]).slice(0, 80)
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
