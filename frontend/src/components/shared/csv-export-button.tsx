"use client";

import { Download } from "lucide-react";
import { useToast } from "@/components/ui/toast";

interface CsvExportButtonProps {
  data: Record<string, unknown>[];
  filename: string;
  className?: string;
}

/** Prevent CSV formula injection by prefixing dangerous characters with a single quote. */
function sanitizeCell(value: string): string {
  if (/^[=+\-@|\t\r]/.test(value)) {
    return "'" + value;
  }
  return value;
}

function toCsvString(data: Record<string, unknown>[]): string {
  if (data.length === 0) return "";

  const headers = Object.keys(data[0]);
  const rows = data.map((row) =>
    headers
      .map((h) => {
        const val = row[h];
        const str = val == null ? "" : sanitizeCell(String(val));
        // Escape quotes and wrap in quotes if it contains comma, quote, or newline
        if (str.includes(",") || str.includes('"') || str.includes("\n")) {
          return `"${str.replace(/"/g, '""')}"`;
        }
        return str;
      })
      .join(","),
  );

  return [headers.join(","), ...rows].join("\n");
}

export default function CsvExportButton({
  data,
  filename,
  className,
}: CsvExportButtonProps) {
  const { success } = useToast();

  const handleExport = () => {
    const csv = toCsvString(data);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = filename.endsWith(".csv") ? filename : `${filename}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    success(`Exported ${data.length} rows to ${link.download}`);
  };

  return (
    <button
      onClick={handleExport}
      disabled={data.length === 0}
      aria-label={`Export ${data.length} rows as CSV`}
      className={`inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-text-secondary transition-colors hover:bg-card hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-50 ${className ?? ""}`}
    >
      <Download className="h-4 w-4" />
      Export CSV
    </button>
  );
}
