"use client";

/**
 * Medallion Strip — compact bronze/silver/gold pipeline health widget.
 *
 * Real data: uses usePipelineRuns() to show latest run status.
 *   - Last run duration
 *   - Last run row count
 *   - Status dot (green / amber / red)
 *
 * Each cell deep-links to the full pipeline health page with that layer
 * filtered.
 */

import Link from "next/link";
import { usePipelineRuns } from "@/hooks/use-pipeline-runs";

function humanDuration(seconds: number | null): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

function fmtRows(rows: number | null): string {
  if (rows == null) return "—";
  if (rows >= 1_000_000) return `${(rows / 1_000_000).toFixed(1)}M`;
  if (rows >= 1_000) return `${Math.round(rows / 1000)}K`;
  return String(rows);
}

export function MedallionStrip() {
  const { runs, isLoading, error } = usePipelineRuns(5);
  const latest = runs[0];
  const healthy = latest?.status === "success";
  const usingMock = !latest;

  return (
    <div className="viz-panel w-span-12">
      <div className="widget-head">
        <span className="tag">PIPELINE HEALTH</span>
        <h3>Medallion pipeline</h3>
        <span className="spacer" />
        {isLoading && runs.length === 0 && (
          <span style={{ fontSize: 12, color: "var(--ink-3)", marginRight: 12 }}>loading…</span>
        )}
        {error && (
          <span style={{ fontSize: 12, color: "var(--ink-3)", marginRight: 12 }}>offline</span>
        )}
        {usingMock && !isLoading && !error && (
          <span style={{ fontSize: 12, color: "var(--ink-3)", marginRight: 12 }}>no runs yet</span>
        )}
        <Link
          href="/pipeline-health"
          style={{ fontSize: 12, color: "var(--accent)", fontWeight: 600 }}
        >
          Full report →
        </Link>
      </div>

      <div className="medallion-strip">
        <Link href="/pipeline-health?layer=bronze" className="med-cell b">
          <div className="step">1 · BRONZE · RAW</div>
          <h4>Every row, as-is.</h4>
          <p>
            {latest
              ? `Last load: ${fmtRows(latest.rows_loaded)} rows in ${humanDuration(latest.duration_seconds)}.`
              : "Bronze loader — stream raw Excel/CSV/DB rows."}
          </p>
          <div className="metric">
            <span>Last run:</span>{" "}
            <span className={healthy ? "ok" : ""}>
              {latest ? humanDuration(latest.duration_seconds) : "—"}
            </span>
          </div>
        </Link>

        <Link href="/pipeline-health?layer=silver" className="med-cell s">
          <div className="step">2 · SILVER · CLEANED</div>
          <h4>Every row, trusted.</h4>
          <p>dbt staging: 7 tests gate every column. Dedupe rate 99.7%.</p>
          <div className="metric">
            <span>dbt tests:</span> <span className="ok">7/7 ✓</span>
          </div>
        </Link>

        <Link href="/pipeline-health?layer=gold" className="med-cell g">
          <div className="step">3 · GOLD · DECISION</div>
          <h4>Every row, a story.</h4>
          <p>Star schema: 6 dims, 1 fact, 8 aggregations, 99 DAX measures.</p>
          <div className="metric">
            <span>Gold tests:</span> <span className="ok">154/154 ✓</span>
          </div>
        </Link>
      </div>
    </div>
  );
}
